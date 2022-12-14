import numpy as np
from math import ceil
import pyvisa
import time as time_module
from instrument import Instrument


class RigolDG4102Pulser(Instrument):
    def __init__(self):
        super().__init__()
        self._num_wf_points = 16384
        self._amplitude = 3.7  # both channels have fixed amplitude 3.7 V
        self._frequency_coefficient_ch2 = 1.01
        # self._connected = False
        # self._output = False
        self._ch2_enabled = False
        self._frequency = 10
        # or num_points-1 (how is interpolation done?)
        self._pulse_shape = []
        self._ch1_waveform = np.zeros(self._num_wf_points, dtype=int)
        self._ch2_waveform = np.zeros(self._num_wf_points, dtype=int)
        self.pulse_shape = ['100-']   # set default pulse shape, trigger setter function
        self._neg_pulse_length = 100
        self._pos_pulse_delay = 10
        self._pos_pulse_length = 20
        # self._inst = None

    @property  # connected
    def connected(self):  # get connected status
        return self._connected

    def initialization(self):
        # rm = pyvisa.ResourceManager('@py')
        # connect to a specific instrument

        # self._inst = rm.open_resource(visa_resource_id, open_timeout=1000,
        #                               resource_pyclass=pyvisa.resources.USBInstrument)
        # instrument initialization
        self._inst.write(":SYSTem:PRESet DEFault")  # set the default values of the fun. generator
        self._inst.write(":DISPlay:BRIGhtness 100")  # set the brightness of the display
        self._inst.write(":OUTPut1 OFF")  # turn OFF the channel 1
        self._inst.write(":OUTPut1:IMPedance 50")
        self._inst.write(":OUTPut2 OFF")  # turn OFF the channel 2
        self._inst.write(":OUTPut2:IMPedance 50")
        self.__cmd_frequency()  # set frequency and amplitude for both channels
        self._inst.write(":SOURce1:TRACE:DATA:POINts:INTerpolate OFF")  # unset the linear interpolation of the points
        self._inst.write(":SOURce2:TRACE:DATA:POINts:INTerpolate OFF")  # unset the linear interpolation of the points
        # set negative pulse
        self.__cmd_pulse_shape(1)
        self.__cmd_negative_pulse_modulation()
        # set positive pulse
        self.__cmd_pulse_shape(2)
        self.__cmd_positive_pulse_synchronization()
        self._output = False
        self._connected = True  # set connected to True if not exception has been risen so far

    def disconnect(self):
        if self._output:
            self.output = False  # stop pulsing
        self._inst.close()
        self._connected = False

    @property  # output
    def output(self):  # get output
        return self._output

    @output.setter
    def output(self, value):  # set output
        if not self._connected:
            self._output = False
        elif value != self._output:  # if different from actual value
            self._output = value
            str_value = 'ON' if value else 'OFF'
            if self._ch2_enabled:  # set both channels
                self._inst.write(':OUTPut1 ' + str_value)
                self._inst.write(':OUTPut2 ' + str_value)
            else:  # set only channel 1
                self._inst.write(':OUTPut1 ' + str_value)

    @property  # ch2_enabled
    def ch2_enabled(self):
        return self._ch2_enabled

    @ch2_enabled.setter
    def ch2_enabled(self, value):
        self._ch2_enabled = value
        if self._connected:
            if value:  # if channel 2 is being enabled
                self.__cmd_pulse_shape(2)
                self.__cmd_positive_pulse_synchronization()
                if self._output:
                    self._inst.write(':OUTPut2 ON')
            else:
                self._inst.write(':OUTPut2 OFF')

    @property  # frequency
    def frequency(self):
        return self._frequency

    @frequency.setter
    def frequency(self, value):
        try:
            int_value = int(value)
        except ValueError:
            raise ValueError('Frequency input must be an integer')
        if int_value > 10000:
            raise ValueError('Frequency input must be lower than 10 kHz')
        if int_value != self._frequency:  # do something only if frequency is changed
            self._frequency = int_value
            # adapt pulse shape
            self.__parse_pulse_shape(self._pulse_shape)   # use actual pulse shape to update waveforms based on
            # new frequency
            if self._connected:
                is_pulsing = self._output  # save if the pulser is active
                if is_pulsing:
                    self.output = False  # turn of the output before frequency is changed
                    time_module.sleep(0.1)
                self.__cmd_frequency()  # update frequency in instrument
                time_module.sleep(0.1)
                self.__cmd_pulse_shape(1)  # update pulse shape which depends on frequency
                self.__cmd_negative_pulse_modulation()  # needs to be started again with every change of the pulse shape
                if self._ch2_enabled:  # update pulse shape for positive pulse if active
                    self.__cmd_pulse_shape(2)
                    self.__cmd_positive_pulse_synchronization()  # likely needs to be started again as well
                time_module.sleep(0.1)
                if is_pulsing:
                    self.output = True  # turn output on again

    @property
    def pulse_shape(self):
        return self._pulse_shape

    # parse pulse shape string, check validity, depends on actual frequency
    # updates channel 1 and 2 waveforms
    def __parse_pulse_shape(self, shape):
        # check pulse shape string validity
        dt = 1e6 / (self._frequency * self._num_wf_points)
        time_step = [0]  # time in dt steps
        polarity = [0]
        for s in shape:
            if s[-1] == '-':  # negative pulse
                polarity.append(-1)
                s1 = s[:-1]
            elif s[-1] == '+':  # positive pulse
                polarity.append(1)
                s1 = s[:-1]
            else:  # delay
                polarity.append(0)
                s1 = s
            try:
                value = float(s1)
            except ValueError:
                raise ValueError('Invalid value of pulse length in ' + s)
            if value < dt:
                raise ValueError('Pulse length is shorter than minimal step (' + str(dt) +
                                 ') determined by given frequency')
            value_step = round(value / dt)  # divide by dt and round
            if value_step * dt < 5.:  # if lower than 5 us (limit), try rounding up
                value_step = ceil(value / dt)  # divide by dt and round
            if value_step * dt < 5.:  # interval shorter than 5 us not allowed to ensure power supply is safe
                raise ValueError('Pulse or delay length must be longer than 5 us')
            time_step.append(time_step[-1] + value_step)
        if time_step[-1] >= self._num_wf_points:
            raise ValueError('Total pulse length must shorter than pulse period')
        # set channel waveforms
        self._ch1_waveform.fill(0)  # set all zeros
        self._ch2_waveform.fill(0)
        for i in range(1, len(time_step)):  # go through prepared list of intervals, from 2nd to last
            if polarity[i] == -1:
                self._ch1_waveform[time_step[i - 1]:time_step[i]] = 1
            elif polarity[i] == 1:
                self._ch2_waveform[time_step[i - 1]:time_step[i]] = 1

    @pulse_shape.setter
    def pulse_shape(self, shape):
        self.__parse_pulse_shape(shape)
        self._pulse_shape = shape    # update shape string
        if self._connected:  # send commands to instrument
            if self._output and self._ch2_enabled:  # if pulsing and ch2 enabled
                self.__cmd_channel_state(2, False)  # turn off channel 2 while changing negative pulse length
                time_module.sleep(0.1)  # wait some time
            self.__cmd_pulse_shape(1)
            self.__cmd_negative_pulse_modulation()  # needs to be started again with every change of the pulse shape
            self.__cmd_pulse_shape(2)
            self.__cmd_positive_pulse_synchronization()
            time_module.sleep(0.1)
            if self._output and self._ch2_enabled:
                self.__cmd_channel_state(2, True)  # turn channel 2 on again

    def get_waveforms(self):
        dt = 1e6/(self._frequency*self._num_wf_points)
        t = np.arange(0, self._num_wf_points)*dt
        return t, self._ch1_waveform, self._ch2_waveform

    def get_period(self):
        return 1e6 / self._frequency

    def __cmd_channel_state(self, channel, value):
        str_value = 'ON' if value else 'OFF'
        if self._ch2_enabled:  # set both channels
            self._inst.write(':OUTPut' + str(channel) + ' ' + str_value)

    # set frequency and amplitude for both channels
    def __cmd_frequency(self):
        # with a frequency "frequency" and amplitude of 3.7 V
        # print(APPLy_command_freq)
        # set frequency of both channels - they are coupled
        # arbitrary pulse mode
        # amplitude must be multiplied by 2
        self._inst.write(':SOURce1:APPLy:CUSTom ' + str(self._frequency) +
                         ',' + str(2 * self._amplitude) + ',0,0')  # channel 1
        freq2 = 1/(1/self._frequency-1e-6)   # decrease period by 1us to ensure there us no overlap with next pulse
        freq2_str = '{:.4f}'.format(freq2)   # format string to necessary precision
        #self._inst.write(':SOURce2:APPLy:CUSTom ' + str(self._frequency * self._frequency_coefficient_ch2) +
        #                 ',' + str(2 * self._amplitude) + ',0,0')  # channel 2, increase by 1 percent, see coefficient
        self._inst.write(':SOURce2:APPLy:CUSTom ' + freq2_str +
                         ',' + str(2 * self._amplitude) + ',0,0')  # channel 2, increase by 1 percent, see coefficient

    # send commands to enable negative pulse modulation for arc detection
    def __cmd_negative_pulse_modulation(self):
        self._inst.write(":SOURce1:MOD ON")  # turn on the modulation of the negative pulses
        self._inst.write(":SOURce1:MOD:TYPe ASK")  # set the type of the modulation ("ASK")
        self._inst.write(":SOURce1:MOD:ASKey:POLarity POSitive")  # set the polarity for the modulation
        self._inst.write(":SOURce1:MOD:ASKey:SOURce EXTernal")  # use the external input for the modulation
        self._inst.write(":SOURce1:MOD:ASKey:AMPLitude 0")  # set the coefficient for the modulation

    # send commands to set triggering of positive pulse
    def __cmd_positive_pulse_synchronization(self):
        self._inst.write(":SOURce2:BURSt ON")  # start "Burst" regime for the negative pulse
        # (the positive pulse needs to be synchronized by the signal for the neg. pulse
        # (synchr. output for CH1 does not work))
        self._inst.write(":SOURce2:BURSt:NCYCles 1")  # one positive pulse after the trigger
        self._inst.write(":SOURce2:BURSt:MODE TRIGgered")  # start the trigger mode
        self._inst.write(":SOURce2:BURSt:TRIGger:SOURce EXTernal")  # set the external trigger
        self._inst.write(":SOURce2:BURSt:GATE:POLarity NORMal")  # start the trigger when there is a change from
        # the "high" level
        self._inst.write(":SOURce2:BURSt:TRIGger:SLOP POS")  # start the trigger when falling signal
        # (end of the positive pulse)
        # self.inst.write(":SOURce2:BURSt:INTernal:PERiod 0.0001")

    # send command describing the shape of the pulse for the given channel
    def __cmd_pulse_shape(self, channel):
        if channel == 1:
            wf_str = ", ".join(map(str, self._ch1_waveform))  # convert "pos_pulse_shape" to a string with values
            # delimited by ","
        elif channel == 2:
            wf_str = ", ".join(map(str, self._ch2_waveform))
        else:
            return
        self._inst.write(':SOURce'+str(channel)+':TRACE:DATA VOLATILE,' + wf_str)  # send shape data
