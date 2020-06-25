import tkinter as tk
import numpy as np
import pyvisa
import time
from tkinter import messagebox
from tkinter import ttk
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg)
from matplotlib.figure import Figure
from sys import platform as _platform


# class for plotting the entered data using Matplotlib
class Matplotlib_plot():
    def __init__(self):     # initialization
        self.f = Figure(figsize=(9, 4), dpi=100)    # set the Figure for plots
        self.f.patch.set_facecolor('#f5f5f5')       # set color of the Figure
        self.ax = self.f.add_subplot(121)           # set the left plot (detailed view)
        self.ax2 = self.f.add_subplot(122)          # set the right plot (whole period)
        self.f.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.15)  # adjust margins of the figure
        self.canvas = FigureCanvasTkAgg(self.f, master=root)    # set the canvas

    # plot waveforms using matplolib
    def plot_waveforms(self, ch2_state, pulse_length_neg, pos_pulse_delay, pulse_length_pos, period):
        # ch2_state - State of the channel two (enabled or disabled)
        # pulse_length_neg - Time ON of the negative pulse
        # pos_pulse_delay - Delay of the positive pulse
        # pulse_length_pos - Time ON of the positive pulse
        # period - Period time

        t = np.arange(0, period, 0.1)   # prepare time array with a step of 0.1 us
        y_neg = np.zeros(len(t))        # prepare array of y values for neg. pulse (same number of values as t)
        y_pos = np.zeros(len(t))        # prepare array of y values for pos. pulse (same number of values as t)

        for idx in range(pulse_length_neg * 10):    # for times where the negative pulse is ON change the y_neg value to 3.7 (output voltage); times 10 is due to the step of 0.1 us
            y_neg[idx+1] = 3.7                      # "+ 1" enables to have first point zero and second 3.7 (to plot the whole rectangular pulse)

        for idx in range(((pulse_length_neg + pos_pulse_delay) * 10), ((pulse_length_neg + pos_pulse_delay + pulse_length_pos) * 10)):  # similar as in the previous case, but this time taking into account preceding negative pulse and positive pulse delay
            y_pos[idx+1] = 3.7

        x_offset = (pulse_length_neg + pos_pulse_delay + pulse_length_pos) * 10 * 0.01  # offset of plotted "x" values (left and right)
        # set the left plot
        self.ax.clear()     # clear the previous plot
        self.ax2.clear()    # clear the previous plot
        self.ax.set_title('Detailed view')  # set title
        self.ax.set_xlim(-x_offset, pulse_length_neg + pos_pulse_delay + pulse_length_pos+x_offset)     # set x limits taking into account the x_offset value
        self.ax.set_xlabel('Time [us]')     # set xlabel
        self.ax.set_ylabel('Voltage [V]')   # set ylabel
        self.ax.plot(t, y_neg, color='red')     # plot the wave form of the negative pulse using a red color
        if ch2_state == 'normal':               # when CH2 is enabled
            self.ax.plot(t, y_pos, color='blue')    # plot the wave form of the positive pulse using a blue color

        # set the right plot (similar as left plot, but with different xlim (this time with whole period; adjusted automatically by Matplotlib))
        self.ax2.set_title('Whole period')
        self.ax2.set_xlabel('Time [us]')
        self.ax2.set_ylabel('Voltage [V]')
        self.ax2.plot(t, y_neg, color='red')
        if ch2_state == 'normal':
            self.ax2.plot(t, y_pos, color='blue')

        self.canvas.draw()  # show the canvas at the screen
        self.canvas.get_tk_widget().grid(row=0, column=7, padx=0, pady=0)   # position the canvas in GUI


# class for storing the discharge parameters
class Parameters:
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
        data = np.loadtxt('saved_data.txt', skiprows=3, dtype=[('frequency', 'int32'), ('t_on-', 'int32'), ('delay', 'int32'), ('t_on+', 'int32')])     # read the matrix of value from the file (first three lines are skipped)
        self.frequency = data['frequency']      # initialize the values
        self.pulse_length_neg = data['t_on-']   # ...
        self.pos_pulse_delay = data['delay']    # ...
        self.pulse_length_pos = data['t_on+']   # ...s
        self.period = int(1e6/self.frequency)   # calculate the period

    # save the discharge parameters to the file "saved_data.txt"
    def save_data(self, ch2_state):
        # ch2_state - state of the channel 2 (enabled or disabled)
        data = np.array([self.frequency, self.pulse_length_neg, self.pos_pulse_delay, self.pulse_length_pos])
        np.savetxt('saved_data.txt', data[None], delimiter='  ', header='CH2 ' + ch2_state + '\n Frequency	t_on-	delay	t_on+\n(Hz)	(us)	(us)	(us)', fmt='%i')


# class for setting the Rigol DG4102 generator
class RigolDG4102:
    def __init__(self, frequency):
        ########## establish communication ###################
        # rm = pyvisa.ResourceManager('@py')  # package pyvisa-py (no VISA from NI is needed)
        rm = pyvisa.ResourceManager()
        # rm.list_resources()                       # list all possible connections
        print(rm.list_resources())                # print the possible connections
        self.inst = rm.open_resource('USB0::6833::1601::DG4E202901834::0::INSTR', timeout=1000, chunk_size=1024000)  # connect to a specific instrument
        # print(inst.query("*IDN?"))                # print IDN of the instrument
        # self.inst.read_termination = '\no'  # specify termination for read commands
        ########## establish communication ###################
        self.ch_states = [0, 0]      # set the states of CH1 (index 0) and CH2 (index 1) to 0 (OFF)
        ############################## SYSTEM INITIALIZATION #############################
        self.inst.write(":SYSTem:PRESet DEFault")  # set the default values of the fun. generator
        self.inst.write(":DISPlay:BRIGhtness 100")  # set the brightness of the display
        self.inst.write(":OUTPut1 OFF")             # turn OFF the channel 1
        self.inst.write(":OUTPut2 OFF")             # turn OFF the channel 2
        ############################## NEGATIVE PULSE #############################
        self.set_pulse_frequency_and_amplitude(1, frequency, 1, 3.7)    # set the frequency and output voltages for the negative pulse (CH1)

        self.inst.write(":SOURce1:TRACE:DATA:POINts:INTerpolate OFF")  # unset the linear interpolation of the points of the arb. pulse
        self.inst.write(":OUTPut1:IMPedance 50")
        self.start_neg_pulse_modulation()       # start modulation of the negative pulse (CH1)

        self.frequency_coefficient_CH2 = 1.01       # frequency coefficient for channel 2
        ############################## POSITIVE PULSE #############################
        self.set_pulse_frequency_and_amplitude(2, frequency, self.frequency_coefficient_CH2, 3.7)  # set the frequency and output voltages for positive pulse (CH2)
        self.inst.write(":SOURce2:TRACE:DATA:POINts:INTerpolate OFF")  # unset the linear interpolation of the points of the arb. pulse
        self.inst.write(":OUTPut2:IMPedance 50")
        self.start_positive_pulse_synchronization()     # start synchronization of the positive pulse (CH2) by the output of the negative pulse (CH1)

    # prepare a command describing the arbitrary pulse
    def prepare_command_for_arb_pulse_profile(self, channel, frequency, delay, t_on):  # function return a string command for definition of the shape of the pulse
        # channel - channel number (1 or 2)
        # frequency - frequency of the pulses
        # delay - delay of the positive pulse
        # t_on - time duration of the pulse

        number_of_points = 16384  # number of points describing the pulse shape during the period (16384 is the maximum value)
        period = 1e6 / frequency  # period

        pulse_shape = np.full(number_of_points, 0)  # set the initial array for the description of the pulse shape during the period (all values are "0")
        pulse_duty_cycle = t_on / period  # calculate duty cycle of the pulse
        t_on_in_points = int(pulse_duty_cycle * number_of_points)  # calculate the number of points corresponding to the negative pulse

        delay_duty_cycle = delay / period  # calculate duty cycle of the pulse delay
        delay_in_points = int(delay_duty_cycle * number_of_points)  # calculate the number of points corresponding to the delay of the pulse

        for i in range(delay_in_points, delay_in_points + t_on_in_points):  # change the value for all the points corresponding to the pulse to "1"
            pulse_shape[i] = 1

        pulse_pos_str = ", ".join(map(str, pulse_shape))  # convert "pos_pulse_shape" to a string with values deliminated by ","

        pulse_profile_command_base = ':SOURce' + str(channel) + ':TRACE:DATA VOLATILE,'  # prepare first part of the command setting the shape of the pos. arb. pulse
        pulse_profile_command = pulse_profile_command_base + pulse_pos_str  # add the desired shape of the pos. arb. pulse
        return pulse_profile_command    # return the resulting command

    # set the frequency and output voltages for one channel
    def set_pulse_frequency_and_amplitude(self, channel, frequency, frequency_coefficient, amplitude):
        # channel - channel number (1 or 2)
        # frequency - frequency of the pulses
        # frequency_coefficient - for CH1 the coefficient is 1 and for CH2 needs to be higher than 1; reason is that the period of the positive pulses has to be lower than the period of the negative pulses (otherwise positive pulses have half frequency)

        APPLy_command_freq = ':SOURce'+str(channel)+':APPLy:CUSTom ' + str(frequency * frequency_coefficient) + ','+str(2*amplitude)+',0,0'  # prepare the command for an initiation of the arbitrary pulses with a frequency "frequency" and amplitude of 3.7 V
        # print(APPLy_command_freq)
        self.inst.write(APPLy_command_freq)  # initiate the positive arbitrary pulses
        # APPLy_command_amplitude_high = ":SOURce"+str(channel)+":VOLTage:HIGH "+str(amplitude)
        # self.inst.write(APPLy_command_amplitude_high) # set the high level of the output changes (other value does not have to work with the output modulation)
        # APPLy_command_amplitude_low = ":SOURce" + str(channel) + ":VOLTage:LOW -"+str(amplitude)
        # self.inst.write(APPLy_command_amplitude_low)  # set the low level of the output changes (other value does not have to work with the output modulation)

    # send the command describing the shape of the pulse to the generator
    def set_pulse_shape_channel(self, channel, frequency, delay, t_on):
        # channel - channel number (1 or 2)
        # frequency - frequency of the pulses
        # delay - delay of the pulse (0 for the negative pulse)
        # t_on - duration of the pulse

        pulse_profile_command = self.prepare_command_for_arb_pulse_profile(channel, frequency, delay, t_on)  # return a string command enabling definition of the pulse shape
        # print(pulse_profile_command)
        self.inst.write(pulse_profile_command)  # send the command to the fun. generator

    # change the status of a channel based on "new_state" input
    def change_state_channel(self, channel, new_state):
        # channel - channel number (1 or 2)
        # new_state - new state of the channel

        if self.ch_states[channel-1] == 0 and new_state == 'ON':
            self.inst.write(":OUTPut"+str(channel)+" ON")  # turn on the channel
            self.ch_states[int(channel)-1] = 1
        elif self.ch_states[channel-1] == 1 and new_state == 'OFF':
            self.inst.write(":OUTPut"+str(channel)+" OFF")  # turn OFF the channel
            self.ch_states[int(channel)-1] = 0

    # start the external modulation of the negative pulse
    def start_neg_pulse_modulation(self):
        ##### SET THE NEGATIVE PULSE MODULATION FOR NEGATIVE PULSE #####
        self.inst.write(":SOURce1:MOD ON")  # turn on the modulation of the negative pulses
        self.inst.write(":SOURce1:MOD:TYPe ASK")  # set the type of the modulation ("ASK")
        self.inst.write(":SOURce1:MOD:ASKey:POLarity POSitive")  # set the polarity for the modulation
        self.inst.write(":SOURce1:MOD:ASKey:SOURce EXTernal")  # use the external input for the modulation
        self.inst.write(":SOURce1:MOD:ASKey:AMPLitude 0")  # set the coefficient for the modulation

    # start the synchronization of the positive pulse by the negative pulse
    def start_positive_pulse_synchronization(self):
        self.inst.write(":SOURce2:BURSt ON")  # start "Burst" regime for the negative pulse (the positive pulse needs to be synchronized by the signal for the neg. pulse (synchr. output for CH1 does not work))
        self.inst.write(":SOURce2:BURSt:NCYCles 1")  # one positive pulse after the trigger
        self.inst.write(":SOURce2:BURSt:MODE TRIGgered")  # start the trigger mode
        self.inst.write(":SOURce2:BURSt:TRIGger:SOURce EXTernal")  # set the external trigger
        self.inst.write(":SOURce2:BURSt:GATE:POLarity NORMal")  # start the trigger when there is a change from the "high" level
        self.inst.write(":SOURce2:BURSt:TRIGger:SLOP NEG")  # start the trigger when falling signal (end of the positive pulse)
        # inst.write(":SOURce2:BURSt:INTernal:PERiod 0.0001")

    # start pulsing of the generator
    def start_pulsing_rigol(self, frequency, frequency_changed, t_on_neg, delay, t_on_pos, ch2_state):
        # frequency - frequency of pulses
        # frequency_changed - has frequency changed since the last call of the function? (to avoid unnecessary setting of the frequency in the generator connected with more unstable behavior of the generator)
        # t_on_neg - time duration of the negative pulse
        # delay - delay of the positive pulse
        # t_on_pos - time duration of the positive pulse
        # ch2_state - state of the positve pulse (CH2) (enabled ot disabled)
        if frequency_changed == 'YES':              # if the frequency has changed since the last call
            self.change_state_channel(2, 'OFF')     # turn off the output for positive pulse
            time.sleep(0.1)                         # wait some time
            self.set_pulse_frequency_and_amplitude(1, frequency, 1, 3.7)    # set the frequency and output voltages for the negative pulse

        self.set_pulse_shape_channel(1, frequency, 0, t_on_neg)             # set the pulse shape for the negative pulse
        self.start_neg_pulse_modulation()                                   # start the modulation of the negative pulse (needs to be strated again each change of the pulse shape)
        self.change_state_channel(1, 'ON')                                  # turn on the output for the negative pulse

        if ch2_state == tk.NORMAL:                      # if the positive pulse is enabled
            if frequency_changed == 'YES':              # if the frequency has changed since the last call
                self.set_pulse_frequency_and_amplitude(2, frequency, self.frequency_coefficient_CH2, 3.7)  # set the frequency and output voltages for the positive pulse
                time.sleep(0.1)                         # wait some time
                self.change_state_channel(1, 'ON')      # turn on the output for the negative pulse

            self.set_pulse_shape_channel(2, frequency, delay, t_on_pos)     # set the pulse shape for the positive pulse
            self.start_positive_pulse_synchronization()                     # start synchronization of the positive pulse
            self.change_state_channel(2, 'ON')                              # turn on the output for the positive pulse
        else:
            self.change_state_channel(2, 'OFF')                             # otherwise turn off the output for the positive pulse

    # stop pulsing of the generator
    def stop_pulsing_rigol(self):
        self.change_state_channel(1, 'OFF')          # turn off the output for the negative pulse
        self.change_state_channel(2, 'OFF')          # turn off the output for the positive pulse


class MainApplication:
    # Btn_activate_text = StringVar()
    # Btn_activate_text.set("Disable")
    def __init__(self, master):
        self.bgcolor = '#f5f5f5'
        frame = tk.Frame(master, background=self.bgcolor)
        frame.grid()
        frame.master.title(":* power supply")
        self.parameters = Parameters()
        self.rigol = RigolDG4102(self.parameters.frequency)
        self.m_plot = Matplotlib_plot()
        self.Btn_activate_text = tk.StringVar(frame)
        if self.parameters.ch2_state == 'disabled':
            self.Btn_activate_text.set("Enable")
        else:
            self.Btn_activate_text.set("Disable")
        self.frequency_old = self.parameters.frequency
        self.frequency_changed = 'YES'

        self.create_widgets(frame)

    def get_actual_data(self, plot_data):
        value_frequency = self.Entry_Frequency.get()
        value_t_on_neg = self.Entry_t_on_neg.get()
        value_delay = self.Entry_delay_pulse_pos.get()
        value_t_on_pos = self.Entry_t_on_pos.get()
        value_period = int(1e6 / int(value_frequency))

        if self.test_data(value_frequency) == 'true' and self.test_data(value_t_on_neg) == 'true' and self.test_data(value_delay) == 'true' and self.test_data(value_t_on_pos) == 'true':
            if (int(value_t_on_neg) + int(value_delay) + int(value_t_on_pos)) < value_period:
                if (int(value_frequency) < 10001):
                    self.parameters.pulse_length_neg = int(value_t_on_neg)
                    self.parameters.pos_pulse_delay = int(value_delay)
                    self.parameters.pulse_length_pos = int(value_t_on_pos)
                    self.parameters.frequency = int(value_frequency)
                    self.parameters.period = int(1e6 / int(value_frequency))
                    if plot_data == 'NO':
                        if value_frequency == self.frequency_old:
                            self.frequency_changed = 'NO'
                        else:
                            self.frequency_changed = 'YES'
                            self.frequency_old = value_frequency
                    else:
                        self.frequency_changed = 'NO'
                else:
                    messagebox.showerror(title='Error', message='Frequency needs to be lower than 10 kHz.')
            else:
                messagebox.showerror(title='Error', message=u'T\u2092\u2099\u207B + delay + T\u2092\u2099\u207A needs to be lower than the period time (' + str(value_period) + '\u00B5s)')

    def test_data(self, number):
        try:
            val = int(number)
            if val < 5:
                messagebox.showerror(title='Error', message='One of the numbers is lower than 5 us')
                return 'false'
            return 'true'
        except ValueError:
            try:
                val = float(number)
                messagebox.showerror(title='Error', message='One of the numbers is a float number')
                return 'false'
            except ValueError:
                messagebox.showerror(title='Error', message='One of the numbers is a string')
                return 'false'

    def start_pulsing_main(self, *args):
        self.get_actual_data('NO')
        self.parameters.save_data(self.parameters.ch2_state)
        self.rigol.start_pulsing_rigol(self.parameters.frequency, self.frequency_changed, self.parameters.pulse_length_neg, self.parameters.pos_pulse_delay, self.parameters.pulse_length_pos, self.Entry_t_on_pos['state'])

    def plot_data_main(self, *args):
        self.get_actual_data('YES')
        # self.parameters.save_data(self.parameters.ch2_state)
        # self.rigol.start_pulsing_rigol(self.parameters.frequency, self.frequency_changed, self.parameters.pulse_length_neg, self.parameters.pos_pulse_delay, self.parameters.pulse_length_pos, self.Entry_t_on_pos['state'])
        self.m_plot.plot_waveforms(self.parameters.ch2_state, self.parameters.pulse_length_neg, self.parameters.pos_pulse_delay, self.parameters.pulse_length_pos, self.parameters.period)

    def btn_activate_CH2(self):
        if self.Entry_t_on_pos['state'] == tk.NORMAL:
            self.Entry_t_on_pos.config(state=tk.DISABLED)
            self.Entry_delay_pulse_pos.config(state=tk.DISABLED)
            self.Btn_activate_text.set("Enable")
            self.parameters.ch2_state = 'disabled'
            # self.rigol.change_state_channel(2, 'OFF')
        else:
            self.Entry_t_on_pos.config(state=tk.NORMAL)
            self.Entry_delay_pulse_pos.config(state=tk.NORMAL)
            self.Btn_activate_text.set("Disable")
            self.parameters.ch2_state = 'normal'
            # self.start_pulsing_main()

    def on_closing(self):
        self.rigol.stop_pulsing_rigol()
        root.destroy()

    def create_widgets(self, frame):
        self.Label_Frequency = tk.Label(frame, text="Pulse frequency", background=self.bgcolor)
        self.Label_Frequency.grid(row=0, column=1, padx=(40, 10), pady=10)
        self.Entry_Frequency = tk.Entry(frame, width=10)
        self.Entry_Frequency.bind("<Return>", self.plot_data_main)
        self.Entry_Frequency.bind("<F10>", self.start_pulsing_main)
        self.Entry_Frequency.grid(row=0, column=2, columnspan=3, padx=0, pady=10)
        self.Entry_Frequency.insert(0, str(self.parameters.frequency))
        self.Label_Frequency_Units = tk.Label(frame, text="Hz", background=self.bgcolor)
        self.Label_Frequency_Units.grid(row=0, column=3, padx=0, pady=10)

        self.Label_Channel1 = tk.Label(frame, text="Channel 1", background=self.bgcolor)
        self.Label_Channel1.grid(row=1, column=1, padx=10, pady=10, sticky='E')

        self.Label_t_on_neg = tk.Label(frame, text=u'T\u2092\u2099\u207B', background=self.bgcolor)
        self.Label_t_on_neg.grid(row=2, column=1, padx=10, pady=10, sticky='E')
        self.Entry_t_on_neg = tk.Entry(frame, width=10)
        # self.Entry_t_on_neg.focus_set()
        self.Entry_t_on_neg.bind("<Return>", self.plot_data_main)
        self.Entry_t_on_neg.bind("<F10>", self.start_pulsing_main)
        self.Entry_t_on_neg.grid(row=2, column=2, columnspan=3, padx=10, pady=10)
        self.Entry_t_on_neg.insert(0, str(self.parameters.pulse_length_neg))
        self.Label_t_on_neg_Units = tk.Label(frame, text=u'\u00B5s', background=self.bgcolor)
        self.Label_t_on_neg_Units.grid(row=2, column=3, padx=0, pady=10, sticky='W')

        self.Label_Channel2 = tk.Label(frame, text="Channel 2", background=self.bgcolor)
        self.Label_Channel2.grid(row=3, column=1, padx=10, pady=10, sticky='E')

        self.Label_delay_pulse_pos = tk.Label(frame, text='Delay', background=self.bgcolor)
        self.Label_delay_pulse_pos.grid(row=4, column=1, padx=10, pady=10, sticky='E')
        self.Entry_delay_pulse_pos = tk.Entry(frame, width=10)
        self.Entry_delay_pulse_pos.bind("<Return>", self.plot_data_main)
        self.Entry_delay_pulse_pos.bind("<F10>", self.start_pulsing_main)
        self.Entry_delay_pulse_pos.grid(row=4, column=2, columnspan=3, padx=10, pady=10)
        self.Entry_delay_pulse_pos.insert(0, str(self.parameters.pos_pulse_delay))
        self.Entry_delay_pulse_pos['state'] = self.parameters.ch2_state
        self.Label_delay_pulse_pos_Units = tk.Label(frame, text=u'\u00B5s', background=self.bgcolor)
        self.Label_delay_pulse_pos_Units.grid(row=4, column=3, padx=0, pady=10, sticky='W')

        self.Label_t_on_pos = tk.Label(frame, text=u'T\u2092\u2099\u207A', background=self.bgcolor)
        self.Label_t_on_pos.grid(row=5, column=1, padx=10, pady=10, sticky='E')
        self.Entry_t_on_pos = tk.Entry(frame, width=10)
        self.Entry_t_on_pos.bind("<F10>", self.start_pulsing_main)
        self.Entry_t_on_pos.bind("<Return>", self.plot_data_main)
        self.Entry_t_on_pos.grid(row=5, column=2, columnspan=3, padx=10, pady=10)
        self.Entry_t_on_pos.insert(0, str(self.parameters.pulse_length_pos))
        self.Entry_t_on_pos['state'] = self.parameters.ch2_state
        self.Label_t_on_pos_Units = tk.Label(frame, text=u'\u00B5s', background=self.bgcolor)
        self.Label_t_on_pos_Units.grid(row=5, column=3, padx=0, pady=10, sticky='W')

        self.Button_activate_CH2 = ttk.Button(frame, text="Activate", command=self.btn_activate_CH2, textvariable=self.Btn_activate_text)
        self.Button_activate_CH2.grid(row=3, column=2, padx=10, pady=10)
        self.Button_plot_data = ttk.Button(frame, text="Plot", command=self.plot_data_main)
        self.Button_plot_data.grid(row=6, column=1, padx=10, pady=10, sticky='E')
        self.Button_send_data = ttk.Button(frame, text="Send", command=self.start_pulsing_main)
        self.Button_send_data.grid(row=6, column=2, rowspan = 2, padx=10, pady=10)
        self.Button_stop = ttk.Button(frame, text="Stop", command=self.rigol.stop_pulsing_rigol)
        self.Button_stop.grid(row=6, column=5, padx=10, pady=10)

        self.m_plot.plot_waveforms(self.parameters.ch2_state, self.parameters.pulse_length_neg, self.parameters.pos_pulse_delay, self.parameters.pulse_length_pos, self.parameters.period)


if __name__ == "__main__":
    root = tk.Tk()
    # tk.Style().configure("TButton", padding=6, relief="flat", background="#ccc")
    # tk.Style.theme_use("default")
    s = ttk.Style()
    if _platform == "win32":
        s.theme_use("vista")
    elif _platform in ["linux", "linux2"]:
        s.theme_use("clam")
    elif _platform == "darwin":
        s.theme_use("aqua")

    app = MainApplication(root)
    root.configure(bg='#f5f5f5')
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()