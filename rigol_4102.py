import numpy as np
import pyvisa
import time


class RigolDG4102Pulser:
    def __init__(self):
        self._amplitude = 3.7   # both channels have fixed amplitude 3.7 V
        self._frequency_coefficient_ch2 = 1.01
        self._connected = False
        self._output = False
        self._ch2_enabled = False
        self._frequency = 10
        self._neg_pulse_length = 100
        self._pos_pulse_delay = 10
        self._pos_pulse_length = 20
        self._inst = None

    @property   # connected
    def connected(self):    # get connected status
        return self._connected

    def connect(self, visa_resource_id):
        rm = pyvisa.ResourceManager()
        # connect to a specific instrument

        self._inst = rm.open_resource(visa_resource_id, open_timeout=1000,
                                      resource_pyclass=pyvisa.resources.MessageBasedResource)
        # instrument initialization
        self._inst.write(":SYSTem:PRESet DEFault")  # set the default values of the fun. generator
        self._inst.write(":DISPlay:BRIGhtness 100")  # set the brightness of the display
        self._inst.write(":OUTPut1 OFF")  # turn OFF the channel 1
        self._inst.write(":OUTPut1:IMPedance 50")
        self._inst.write(":OUTPut2 OFF")  # turn OFF the channel 2
        self._inst.write(":OUTPut2:IMPedance 50")
        self.__cmd_frequency()   # set frequency and amplitude for both channels
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

    @property    # output
    def output(self):   # get output
        return self._output

    @output.setter
    def output(self, value):   # set output
        if not self._connected:
            self._output = False
        elif value != self._output:  # if different from actual value
            self._output = value
            str_value = 'ON' if value else 'OFF'
            if self._ch2_enabled:   # set both channels
                self._inst.write(':OUTPut1 ' + str_value)
                self._inst.write(':OUTPut2 ' + str_value)
            else:                   # set only channel 1
                self._inst.write(':OUTPut1 '+str_value)

    @property   # ch2_enabled
    def ch2_enabled(self):
        return self._ch2_enabled

    @ch2_enabled.setter
    def ch2_enabled(self, value):
        self._ch2_enabled = value
        if self._connected:
            if value:   # if channel 2 is being enabled
                self.__cmd_pulse_shape(2)
                self.__cmd_positive_pulse_synchronization()
                if self._output:
                    self._inst.write(':OUTPut2 ON')
            else:
                self._inst.write(':OUTPut2 OFF')

    @property   # frequency
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
        if self._neg_pulse_length + self._pos_pulse_delay + self._pos_pulse_length >= int(1e6 / int_value):
            period = int(1e6 / self._frequency)
            raise ValueError(u'T\u2092\u2099\u207B + delay + T\u2092\u2099\u207A needs to be lower than the period'
                             + u' time (' + str(period) + '\u00B5s)')
        if int_value != self._frequency:  # do something only if frequency is changed
            self._frequency = int_value
            if self._connected:
                is_pulsing = self._output  # save if the pulser is active
                if is_pulsing:
                    self.output = False   # turn of the output before frequency is changed
                    time.sleep(0.1)
                self.__cmd_frequency()  # update frequency in instrument
                time.sleep(0.1)
                self.__cmd_pulse_shape(1)   # update pulse shape which depends on frequency
                self.__cmd_negative_pulse_modulation()  # needs to be started again with every change of the pulse shape
                if self._ch2_enabled:  # update pulse shape for positive pulse if active
                    self.__cmd_pulse_shape(2)
                    self.__cmd_positive_pulse_synchronization()  # likely needs to be started again as well
                time.sleep(0.1)
                if is_pulsing:
                    self.output = True   # turn output on again

    @property
    def neg_pulse_length(self):
        return self._neg_pulse_length

    @neg_pulse_length.setter
    def neg_pulse_length(self, value):
        try:
            int_value = int(value)
        except ValueError:
            raise ValueError('Pulse length input must be an integer')
        if int_value < 5:
            raise ValueError('Pulse length input must be at least 5 us')
        if int_value + self._pos_pulse_delay + self._pos_pulse_length >= int(1e6 / self._frequency):
            period = int(1e6 / self._frequency)
            raise ValueError(u'T\u2092\u2099\u207B + delay + T\u2092\u2099\u207A needs to be lower than the period'
                             + u' time (' + str(period) + '\u00B5s)')
        if int_value != self._neg_pulse_length:
            self._neg_pulse_length = int_value  # update the value
            if self._connected:
                if self._output and self._ch2_enabled:  # if pulsing and ch2 enabled
                    self.__cmd_channel_state(2, False)   # turn off channel 2 while changing negative pulse length
                    time.sleep(0.1)  # wait some time
                self.__cmd_pulse_shape(1)  # update pulse shape
                self.__cmd_negative_pulse_modulation()  # needs to be started again with every change of the pulse shape
                if self._ch2_enabled:  # update pulse shape for positive pulse if active
                    self.__cmd_pulse_shape(2)
                    self.__cmd_positive_pulse_synchronization()
                time.sleep(0.1)
                if self._ch2_enabled:
                    self.__cmd_channel_state(2, True)  # turn channel 2 on again

    @property
    def pos_pulse_delay(self):
        return self._pos_pulse_delay

    @pos_pulse_delay.setter
    def pos_pulse_delay(self, value):
        try:
            int_value = int(value)
        except ValueError:
            raise ValueError('Pulse delay input must be an integer')
        if int_value < 5:
            raise ValueError('Pulse delay input must be at least 5 us')
        if self._neg_pulse_length + int_value + self._pos_pulse_length >= int(1e6 / self._frequency):
            period = int(1e6 / self._frequency)
            raise ValueError(u'T\u2092\u2099\u207B + delay + T\u2092\u2099\u207A needs to be lower than the period'
                             + u' time (' + str(period) + '\u00B5s)')
        if int_value != self._pos_pulse_delay:
            self._pos_pulse_delay = int_value    # update the value
            if self._connected:
                self.__cmd_pulse_shape(2)
                self.__cmd_positive_pulse_synchronization()

    @property
    def pos_pulse_length(self):
        return self._pos_pulse_length

    @pos_pulse_length.setter
    def pos_pulse_length(self, value):
        try:
            int_value = int(value)
        except ValueError:
            raise ValueError('Pulse length input must be an integer')
        if int_value < 5:
            raise ValueError('Pulse length input must be at least 5 us')
        if self._neg_pulse_length + self._pos_pulse_delay + int_value >= int(1e6 / self._frequency):
            period = int(1e6 / self._frequency)
            raise ValueError(u'T\u2092\u2099\u207B + delay + T\u2092\u2099\u207A needs to be lower than the period'
                             + u' time (' + str(period) + '\u00B5s)')
        if int_value != self._pos_pulse_length:
            self._pos_pulse_length = int_value  # update the value
            if self._connected:
                self.__cmd_pulse_shape(2)
                self.__cmd_positive_pulse_synchronization()

    def get_period(self):
        return int(1e6/self._frequency)

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
        self._inst.write(':SOURce2:APPLy:CUSTom ' + str(self._frequency * self._frequency_coefficient_ch2) +
                         ',' + str(2 * self._amplitude) + ',0,0')  # channel 2, increase by 1 percent, see coefficient

    def set_all(self, frequency, neg_ton, pos_delay, pos_ton, ch2_enabled):
        try:
            int_frequency = int(frequency)
        except ValueError:
            raise ValueError('Frequency input must be an integer')
        if int_frequency > 10000:
            raise ValueError('Frequency input must be lower than 10 kHz')
        try:
            int_neg_ton = int(neg_ton)
        except ValueError:
            raise ValueError('Pulse length input must be an integer')
        if int_neg_ton < 5:
            raise ValueError('Pulse length input must be at least 5 us')
        try:
            int_pos_ton = int(pos_ton)
        except ValueError:
            raise ValueError('Pulse length input must be an integer')
        if int_pos_ton < 5:
            raise ValueError('Pulse length input must be at least 5 us')
        try:
            int_pos_delay = int(pos_delay)
        except ValueError:
            raise ValueError('Pulse delay input must be an integer')
        if int_pos_delay < 5:
            raise ValueError('Pulse delay input must be at least 5 us')
        if int_neg_ton + int_pos_delay + int_pos_ton >= int(1e6 / int_frequency):
            period = int(1e6 / self._frequency)
            raise ValueError(u'T\u2092\u2099\u207B + delay + T\u2092\u2099\u207A needs to be lower than the period'
                             + u' time (' + str(period) + '\u00B5s)')
        self._frequency = int_frequency
        self._neg_pulse_length = int_neg_ton
        self._pos_pulse_delay = int_pos_delay
        self._pos_pulse_length = int_pos_delay
        if self._connected:
            is_pulsing = self._output  # save if the pulser is active
            if is_pulsing:
                self.output = False  # turn of the output before frequency is changed
                time.sleep(0.1)
            self.__cmd_frequency()  # update frequency in instrument
            time.sleep(0.1)
            self.__cmd_pulse_shape(1)  # update pulse shape which depends on frequency
            self.__cmd_negative_pulse_modulation()  # needs to be started again with every change of the pulse shape
            if self._ch2_enabled:  # update pulse shape for positive pulse if active
                self.__cmd_pulse_shape(2)
                self.__cmd_positive_pulse_synchronization()  # likely needs to be started again as well
            time.sleep(0.1)
            if is_pulsing:
                self.output = True  # turn output on again

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
        self._inst.write(":SOURce2:BURSt:TRIGger:SLOP NEG")  # start the trigger when falling signal
        # (end of the positive pulse)
        # self.inst.write(":SOURce2:BURSt:INTernal:PERiod 0.0001")

    # send command describing the shape of the pulse for the given channel
    def __cmd_pulse_shape(self, channel):
        # channel - channel number (1 or 2)
        period = 1e6 / self._frequency  # period
        if channel == 1:   # set pulse length and delay from class properties depending on channel number
            t_on = self._neg_pulse_length
            delay = 0
        else:
            t_on = self._pos_pulse_length
            delay = self._pos_pulse_delay

        number_of_points = 16384  # number of points describing the pulse shape during the period
        # (16384 is the maximum value)
        pulse = np.zeros(number_of_points)  # set the initial array for the description of the pulse shape
        # during the period (all values are "0")
        t_on_in_points = int(t_on / period * number_of_points)  # calculate the number of points
        # corresponding to the negative pulse
        delay_in_points = int(delay / period * number_of_points)  # calculate the number of points
        # corresponding to the delay of the pulse
        pulse[delay_in_points:delay_in_points + t_on_in_points] = 1   # set pulse to 1 for times inside the pulse
        pulse_str = ", ".join(map(str, pulse))  # convert "pos_pulse_shape" to a string with values deliminated by ","
        self._inst.write(':SOURce' + str(channel) + ':TRACE:DATA VOLATILE,' + pulse_str)  # send to shape data

