import numpy as np
import pyvisa
import time

frequency_coefficient_ch2 = 1.01


# class for storing the discharge parameters
class RigolDG4102Params:
    def __init__(self):
        self.ch2_state = ''     # state of the channel 2 (enabled or disabled)
        self.frequency = 0      # frequency of the pulses
        self.period = 0         # period
        self.pulse_length_neg = 0   # Time duration of the negative pulse length
        self.pos_pulse_delay = 0    # Time duration of the delay of the positive pulse
        self.pulse_length_pos = 0   # Time duration of the positive pulse length
        self.load_data()            # load saved data from the file "saved_data.txt"

    # load saved data from the file "saved_data.txt"
    def load_data(self):
        with open('saved_data.txt', 'r') as f:  # open the file
            line = f.readline().split()         # read first line of the file
            self.ch2_state = line[2]            # split the line into simple strings
            f.close()                           # close the file
        data = np.loadtxt('saved_data.txt', skiprows=3, dtype=[('frequency', 'int32'),
                          ('t_on-', 'int32'), ('delay', 'int32'), ('t_on+', 'int32')])  # read the matrix of value from
        # the file (first three lines are skipped)
        self.frequency = data['frequency']      # initialize the values
        self.pulse_length_neg = data['t_on-']   # ...
        self.pos_pulse_delay = data['delay']    # ...
        self.pulse_length_pos = data['t_on+']   # ...s
        self.period = int(1e6/self.frequency)   # calculate the period

    # save the discharge parameters to the file "saved_data.txt"
    def save_data(self, ch2_state):
        # ch2_state - state of the channel 2 (enabled or disabled)
        data = np.array([self.frequency, self.pulse_length_neg, self.pos_pulse_delay, self.pulse_length_pos])
        np.savetxt('saved_data.txt', data[None], delimiter='  ', header='CH2 ' + ch2_state +
                   '\n Frequency	t_on-	delay	t_on+\n(Hz)	(us)	(us)	(us)', fmt='%i')


# prepare a command describing the arbitrary pulse
# function returns a string command for the definition of the shape of the pulse
def prepare_command_for_arb_pulse_profile(channel, frequency, delay, t_on):
    # channel - channel number (1 or 2)
    # frequency - frequency of the pulses
    # delay - delay of the positive pulse
    # t_on - time duration of the pulse
    number_of_points = 16384  # number of points describing the pulse shape during the period
    # (16384 is the maximum value)
    period = 1e6 / frequency  # period

    pulse_shape = np.full(number_of_points, 0)  # set the initial array for the description of the pulse shape
    # during the period (all values are "0")
    pulse_duty_cycle = t_on / period  # calculate duty cycle of the pulse
    t_on_in_points = int(pulse_duty_cycle * number_of_points)  # calculate the number of points
    # corresponding to the negative pulse

    delay_duty_cycle = delay / period  # calculate duty cycle of the pulse delay
    delay_in_points = int(delay_duty_cycle * number_of_points)  # calculate the number of points
    # corresponding to the delay of the pulse

    for i in range(delay_in_points, delay_in_points + t_on_in_points):  # change the value for all the points
        pulse_shape[i] = 1                                              # corresponding to the pulse to "1"

    pulse_pos_str = ", ".join(map(str, pulse_shape))  # convert "pos_pulse_shape" to a string with values
    # deliminated by ","

    # prepare first part of the command setting the shape of the pos. arb. pulse
    pulse_profile_command_base = ':SOURce' + str(channel) + ':TRACE:DATA VOLATILE,'
    pulse_profile_command = pulse_profile_command_base + pulse_pos_str   # add the desired shape of
    # the positive arbitrary pulse
    return pulse_profile_command    # return the resulting command


# class for setting the Rigol DG4102 generator
class RigolDG4102:
    def __init__(self, frequency):
        self._channel_state = [0, 0]  # set the states of CH1 (index 0) and CH2 (index 1) to 0 (OFF)
        # **** establish communication ****
        # rm = pyvisa.ResourceManager('@py')  # package pyvisa-py (no VISA from NI is needed)
        rm = pyvisa.ResourceManager()
        # rm.list_resources()                       # list all possible connections
        print(rm.list_resources())                # print the possible connections
        # connect to a specific instrument
        self.inst = rm.open_resource('USB0::6833::1601::DG4E202901834::0::INSTR', timeout=1000, chunk_size=1024000)
        # print(inst.query("*IDN?"))                # print IDN of the instrument
        # self.inst.read_termination = '\no'  # specify termination for read commands
        # **** establish communication ****

        # **** SYSTEM INITIALIZATION ****
        self.inst.write(":SYSTem:PRESet DEFault")  # set the default values of the fun. generator
        self.inst.write(":DISPlay:BRIGhtness 100")  # set the brightness of the display
        self.inst.write(":OUTPut1 OFF")             # turn OFF the channel 1
        self.inst.write(":OUTPut2 OFF")             # turn OFF the channel 2
        # **** NEGATIVE PULSE ****
        self.set_pulse_frequency_and_amplitude(1, frequency, 1, 3.7)   # set the frequency and output voltages
        # for the negative pulse (CH1)

        self.inst.write(":SOURce1:TRACE:DATA:POINts:INTerpolate OFF")  # unset the linear interpolation of the points
        # of the arb. pulse
        self.inst.write(":OUTPut1:IMPedance 50")
        self.start_neg_pulse_modulation()       # start modulation of the negative pulse (CH1)

        # self.frequency_coefficient_ch2 = 1.01       # frequency coefficient for channel 2
        # ********** POSITIVE PULSE *********
        self.set_pulse_frequency_and_amplitude(2, frequency, frequency_coefficient_ch2, 3.7)  # set the frequency
        # and output voltages for positive pulse (CH2)
        self.inst.write(":SOURce2:TRACE:DATA:POINts:INTerpolate OFF")  # unset the linear interpolation of the points
        # of the arb. pulse
        self.inst.write(":OUTPut2:IMPedance 50")
        self.start_positive_pulse_synchronization()     # start synchronization of the positive pulse (CH2)
        # by the output of the negative pulse (CH1)

    # set the frequency and output voltages for one channel
    def set_pulse_frequency_and_amplitude(self, channel, frequency, frequency_coefficient, amplitude):
        # channel - channel number (1 or 2)
        # frequency - frequency of the pulses
        # frequency_coefficient - for CH1 the coefficient is 1 and for CH2 needs to be higher than 1;
        # the reason is that the period of the positive pulses has to be lower than the period of the negative pulses
        # (otherwise positive pulses have half frequency)

        apply_command_freq = ':SOURce'+str(channel)+':APPLy:CUSTom ' + str(frequency * frequency_coefficient) + ','\
                             + str(2*amplitude)+',0,0'  # prepare the command for an initiation of the arbitrary pulses
        # with a frequency "frequency" and amplitude of 3.7 V
        # print(APPLy_command_freq)
        self.inst.write(apply_command_freq)  # initiate the positive arbitrary pulses
        # apply_command_amplitude_high = ":SOURce"+str(channel)+":VOLTage:HIGH "+str(amplitude)
        # self.inst.write(apply_command_amplitude_high) # set the high level of the output changes
        # (other value does not have to work with the output modulation)
        # apply_command_amplitude_low = ":SOURce" + str(channel) + ":VOLTage:LOW -"+str(amplitude)
        # self.inst.write(apply_command_amplitude_low)  # set the low level of the output changes
        # (other value does not have to work with the output modulation)

    # send the command describing the shape of the pulse to the generator
    def set_pulse_shape_channel(self, channel, frequency, delay, t_on):
        # channel - channel number (1 or 2)
        # frequency - frequency of the pulses
        # delay - delay of the pulse (0 for the negative pulse)
        # t_on - duration of the pulse

        # return a string command enabling definition of the pulse shape
        pulse_profile_command = prepare_command_for_arb_pulse_profile(channel, frequency, delay, t_on)
        # print(pulse_profile_command)
        self.inst.write(pulse_profile_command)  # send the command to the fun. generator

    # change the state of a channel based on "new_state" input
    def set_channel_state(self, channel, new_state):
        # channel - channel number (1 or 2)
        # new_state - new state of the channel (ON, OFF)
        if self._channel_state[channel-1] == 0 and new_state == 'ON':
            self.inst.write(":OUTPut" + str(channel) + " ON")  # turn on the channel
            self._channel_state[int(channel)-1] = 1
        elif self._channel_state[channel-1] == 1 and new_state == 'OFF':
            self.inst.write(":OUTPut" + str(channel) + " OFF")  # turn OFF the channel
            self._channel_state[int(channel)-1] = 0

    # start the external modulation of the negative pulse
    def start_neg_pulse_modulation(self):
        # ****  SET THE NEGATIVE PULSE MODULATION FOR NEGATIVE PULSE ****
        self.inst.write(":SOURce1:MOD ON")  # turn on the modulation of the negative pulses
        self.inst.write(":SOURce1:MOD:TYPe ASK")  # set the type of the modulation ("ASK")
        self.inst.write(":SOURce1:MOD:ASKey:POLarity POSitive")  # set the polarity for the modulation
        self.inst.write(":SOURce1:MOD:ASKey:SOURce EXTernal")  # use the external input for the modulation
        self.inst.write(":SOURce1:MOD:ASKey:AMPLitude 0")  # set the coefficient for the modulation

    # start the synchronization of the positive pulse by the negative pulse
    def start_positive_pulse_synchronization(self):
        self.inst.write(":SOURce2:BURSt ON")  # start "Burst" regime for the negative pulse
        # (the positive pulse needs to be synchronized by the signal for the neg. pulse
        # (synchr. output for CH1 does not work))
        self.inst.write(":SOURce2:BURSt:NCYCles 1")  # one positive pulse after the trigger
        self.inst.write(":SOURce2:BURSt:MODE TRIGgered")  # start the trigger mode
        self.inst.write(":SOURce2:BURSt:TRIGger:SOURce EXTernal")  # set the external trigger
        self.inst.write(":SOURce2:BURSt:GATE:POLarity NORMal")  # start the trigger when there is a change from
        # the "high" level
        self.inst.write(":SOURce2:BURSt:TRIGger:SLOP NEG")  # start the trigger when falling signal
        # (end of the positive pulse)
        # self.inst.write(":SOURce2:BURSt:INTernal:PERiod 0.0001")

    # start pulsing of the generator
    def start_pulsing_rigol(self, frequency, frequency_changed, t_on_neg, delay, t_on_pos, ch2_state):
        # frequency - frequency of pulses
        # frequency_changed - has frequency changed since the last call of the function? (to avoid unnecessary
        # setting of the frequency in the generator connected with more unstable behavior of the generator)
        # t_on_neg - time duration of the negative pulse
        # delay - delay of the positive pulse
        # t_on_pos - time duration of the positive pulse
        # ch2_state - state of the positive pulse (CH2) (enabled ot disabled)
        if frequency_changed == 'YES':              # if the frequency has changed since the last call
            self.set_channel_state(2, 'OFF')     # turn off the output for positive pulse
            time.sleep(0.1)                         # wait some time
            self.set_pulse_frequency_and_amplitude(1, frequency, 1, 3.7)    # set the frequency and output voltages
            # for the negative pulse

        self.set_pulse_shape_channel(1, frequency, 0, t_on_neg)             # set the pulse shape for the negative pulse
        self.start_neg_pulse_modulation()                                   # start the modulation of the negative pulse
        # (needs to be started again with every change of the pulse shape)
        self.set_channel_state(1, 'ON')                                  # turn on the output for the negative pulse

        if ch2_state == 'normal':                       # if the positive pulse is enabled
            if frequency_changed == 'YES':              # if the frequency has changed since the last call
                # set the frequency and output voltages for the positive pulse
                self.set_pulse_frequency_and_amplitude(2, frequency, frequency_coefficient_ch2, 3.7)
                time.sleep(0.1)                         # wait some time
                self.set_channel_state(1, 'ON')      # turn on the output for the negative pulse

            self.set_pulse_shape_channel(2, frequency, delay, t_on_pos)   # set the pulse shape for the positive pulse
            self.start_positive_pulse_synchronization()                   # start synchronization of the positive pulse
            self.set_channel_state(2, 'ON')                            # turn on the output for the positive pulse
        else:
            self.set_channel_state(2, 'OFF')                  # otherwise turn off the output for the positive pulse

    # stop pulsing of the generator
    def stop_pulsing_rigol(self):
        self.set_channel_state(1, 'OFF')          # turn off the output for the negative pulse
        self.set_channel_state(2, 'OFF')          # turn off the output for the positive pulse

    def get_channel_state(self, channel):
        return self._channel_state[int(channel)-1]


