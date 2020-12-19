import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg)
from matplotlib.figure import Figure
from rigol_4102 import RigolDG4102Pulser, RigolDG4102Params
import numpy as np


def test_data(number):
    try:
        val = int(number)
        if val < 5:
            messagebox.showerror(title='Error', message='One of the numbers is lower than 5 us')
            return 'false'
        return 'true'
    except ValueError:
        try:
            float(number)
            messagebox.showerror(title='Error', message='One of the numbers is a float number')
            return 'false'
        except ValueError:
            messagebox.showerror(title='Error', message='One of the numbers is a string')
            return 'false'


# class for plotting the entered data using Matplotlib
class MatplotlibPlot:
    def __init__(self, master):     # initialization
        self.f = Figure(figsize=(4, 3), dpi=100)    # set the Figure for plots
        self.f.patch.set_facecolor('#f5f5f5')       # set color of the Figure
        self.ax = self.f.add_axes([0.12, 0.15, 0.8, 0.8])             # add axes
        self.canvas = FigureCanvasTkAgg(self.f, master=master)    # set the canvas
        self.canvas.get_tk_widget().pack()  # position the canvas in GUI

    # plot waveforms using matplotlib
    def plot_waveforms(self, ch2_state, pulse_length_neg, pos_pulse_delay, pulse_length_pos, period, scale):
        # ch2_state - State of the channel two (enabled or disabled)
        # pulse_length_neg - Time ON of the negative pulse
        # pos_pulse_delay - Delay of the positive pulse
        # pulse_length_pos - Time ON of the positive pulse
        # period - Period time

        t = np.arange(0, period, 0.1)   # prepare time array with a step of 0.1 us
        y_neg = np.zeros(len(t))        # prepare array of y values for neg. pulse (same number of values as t)
        y_pos = np.zeros(len(t))        # prepare array of y values for pos. pulse (same number of values as t)

        # for times where the negative pulse is ON change the y_neg
        # value to 3.7 (output voltage); times 10 is due to the step of 0.1 us
        # "+ 1" enables to have first point zero and second 3.7 (to plot the whole rectangular pulse)
        for idx in range(pulse_length_neg * 10):
            y_neg[idx+1] = 3.7

        # similar as in the previous case, but this time taking into account preceding negative pulse
        # and positive pulse delay
        for idx in range(((pulse_length_neg + pos_pulse_delay) * 10),
                         ((pulse_length_neg + pos_pulse_delay + pulse_length_pos) * 10)):

            y_pos[idx+1] = 3.7

        self.ax.clear()     # clear the previous plot
        self.set_x_lim(period, scale)    # set x limits taking into account the current scale value
        self.ax.set_xlabel('Time [us]')     # set x label
        self.ax.set_ylabel('Voltage [V]')   # set y label
        self.ax.plot(t, y_neg, color='red')     # plot the wave form of the negative pulse using a red color
        if ch2_state == 'normal':               # when CH2 is enabled
            self.ax.plot(t, y_pos, color='blue')    # plot the wave form of the positive pulse using a blue color
        self.canvas.draw()  # show the canvas at the screen

    def set_x_lim(self, period, scale):
        max_value = period/100*scale
        x_offset = max_value/10
        self.ax.set_xlim(-x_offset, period/100*scale + x_offset)


class HuPulserGui:
    def __init__(self, master):
        self.bg_color = '#f5f5f5'
        self.root = master
        master.title(":* pulsed power supply control")
        # load last state of GUI
        self.parameters = RigolDG4102Params()  # TODO change name

        # main frame
        main_frame = tk.Frame(master, background=self.bg_color)
        main_frame.pack(side=tk.TOP)
        # status bar
        self.status = tk.StringVar('')
        self.StatusBar = tk.Label(master, textvariable=self.status, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.StatusBar.pack(side=tk.BOTTOM, fill=tk.X)

        # *** main frame widgets ***
        # pulser frame
        pulser_frame = tk.LabelFrame(main_frame, background=self.bg_color, borderwidth=2, relief=tk.RIDGE,
                                     text='  PULSER  ')
        pulser_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=(5, 2))

        self.pulser_hw = tk.StringVar()
        self.pulser_hw.set('Rigol 4102')
        self.Pulser_Hw_OptionMenu = tk.OptionMenu(pulser_frame, self.pulser_hw, 'Rigol 4102')
        self.Pulser_Hw_OptionMenu.grid(row=0, column=0, padx=5)
        self.pulser_connected = tk.IntVar(value=0)
        self.Pulser_Connected_Checkbutton = tk.Checkbutton(pulser_frame, text='Connected', command=self.pulser_connect,
                                                           background=self.bg_color, variable=self.pulser_connected)
        self.Pulser_Connected_Checkbutton.grid(row=0, column=1, padx=5)

        self.Label_Frequency = tk.Label(pulser_frame, text="Pulse frequency", background=self.bg_color)
        self.Label_Frequency.grid(row=1, column=0, padx=5, pady=(10, 0), sticky='E')
        self.Entry_Frequency = tk.Entry(pulser_frame, width=10)
        self.Entry_Frequency.id = 'freq'
        # self.Entry_Frequency.bind("<Return>", self.plot_data_main)
        self.Entry_Frequency.bind("<Return>", self.entry_confirmed)
        self.Entry_Frequency.bind("<KeyRelease>", self.entry_modified)
        self.Entry_Frequency.bind("<F10>", self.start_pulsing_main)

        self.Entry_Frequency.grid(row=1, column=1, padx=5, pady=(10, 0), sticky='E')
        self.Entry_Frequency.insert(0, str(self.parameters.frequency))
        self.Label_Frequency_Units = tk.Label(pulser_frame, text="Hz", background=self.bg_color)
        self.Label_Frequency_Units.grid(row=1, column=2, padx=5, pady=(10, 0), sticky='W')

        self.Label_Channel1 = tk.Label(pulser_frame, text="Channel 1", background=self.bg_color)
        self.Label_Channel1.grid(row=2, column=0, padx=5, pady=(5, 0), sticky='E')

        self.Label_t_on_neg = tk.Label(pulser_frame, text=u'T\u2092\u2099\u207B', background=self.bg_color)
        self.Label_t_on_neg.grid(row=3, column=0, padx=5, sticky='E')
        self.Entry_t_on_neg = tk.Entry(pulser_frame, width=10)
        # self.Entry_t_on_neg.focus_set()
        self.Entry_t_on_neg.bind("<Return>", self.plot_data_main)
        self.Entry_t_on_neg.bind("<F10>", self.start_pulsing_main)
        self.Entry_t_on_neg.grid(row=3, column=1, padx=5, sticky='E')
        self.Entry_t_on_neg.insert(0, str(self.parameters.pulse_length_neg))
        self.Label_t_on_neg_Units = tk.Label(pulser_frame, text=u'\u00B5s', background=self.bg_color)
        self.Label_t_on_neg_Units.grid(row=3, column=2, padx=5, sticky='W')

        self.Label_Channel2 = tk.Label(pulser_frame, text="Channel 2", background=self.bg_color)
        self.Label_Channel2.grid(row=4, column=0, padx=5, pady=(5, 0), sticky='E')
        self.Btn_activate_text = tk.StringVar(pulser_frame)
        if self.parameters.ch2_state == 'disabled':
            self.Btn_activate_text.set("Enable")
        else:
            self.Btn_activate_text.set("Disable")
        self.Button_activate_ch2 = ttk.Button(pulser_frame, text="Activate", command=self.btn_activate_ch2,
                                              textvariable=self.Btn_activate_text)
        self.Button_activate_ch2.grid(row=4, column=1, padx=5, pady=(5, 0))

        self.Label_delay_pulse_pos = tk.Label(pulser_frame, text='Delay', background=self.bg_color)
        self.Label_delay_pulse_pos.grid(row=5, column=0, padx=5, sticky='E')
        self.Entry_delay_pulse_pos = tk.Entry(pulser_frame, width=10)
        self.Entry_delay_pulse_pos.bind("<Return>", self.plot_data_main)
        self.Entry_delay_pulse_pos.bind("<F10>", self.start_pulsing_main)
        self.Entry_delay_pulse_pos.grid(row=5, column=1, padx=5, sticky='E')
        self.Entry_delay_pulse_pos.insert(0, str(self.parameters.pos_pulse_delay))
        self.Entry_delay_pulse_pos['state'] = self.parameters.ch2_state
        self.Label_delay_pulse_pos_Units = tk.Label(pulser_frame, text=u'\u00B5s', background=self.bg_color)
        self.Label_delay_pulse_pos_Units.grid(row=5, column=2, padx=5, sticky='W')

        self.Label_t_on_pos = tk.Label(pulser_frame, text=u'T\u2092\u2099\u207A', background=self.bg_color)
        self.Label_t_on_pos.grid(row=6, column=0, padx=5, sticky='E')
        self.Entry_t_on_pos = tk.Entry(pulser_frame, width=10)
        self.Entry_t_on_pos.bind("<F10>", self.start_pulsing_main)
        self.Entry_t_on_pos.bind("<Return>", self.plot_data_main)
        self.Entry_t_on_pos.grid(row=6, column=1, padx=5, sticky='E')
        self.Entry_t_on_pos.insert(0, str(self.parameters.pulse_length_pos))
        self.Entry_t_on_pos['state'] = self.parameters.ch2_state
        self.Label_t_on_pos_Units = tk.Label(pulser_frame, text=u'\u00B5s', background=self.bg_color)
        self.Label_t_on_pos_Units.grid(row=6, column=2, padx=5, sticky='W')

        self.Button_plot_data = ttk.Button(pulser_frame, text="Plot", command=self.plot_data_main)
        self.Button_plot_data.grid(row=7, column=1, padx=5, pady=(5, 0))
        self.Button_send_data = ttk.Button(pulser_frame, text="Send", command=self.start_pulsing_main)
        self.Button_send_data.grid(row=8, column=1, padx=5, pady=0)
        self.Button_stop = ttk.Button(pulser_frame, text="Stop", command=self.stop_pulsing_main)
        self.Button_stop.grid(row=9, column=1, padx=5, pady=0)

        self.ch1_active = tk.IntVar()
        self.CheckButton_CH1_active = ttk.Checkbutton(pulser_frame, text="CH 1 active", state=tk.DISABLED,
                                                      variable=self.ch1_active)
        self.CheckButton_CH1_active.grid(row=8, column=0, padx=5, pady=5)
        self.ch2_active = tk.IntVar()
        self.CheckButton_ch2_active = ttk.Checkbutton(pulser_frame, text="CH 2 active", state=tk.DISABLED,
                                                      variable=self.ch2_active)
        self.CheckButton_ch2_active.grid(row=9, column=0, padx=5, pady=5)

        self.frequency_old = self.parameters.frequency
        self.frequency_changed = 'YES'

        plot_frame = tk.LabelFrame(main_frame, background=self.bg_color, borderwidth=2, relief=tk.RIDGE,
                                   text='  PLOT  ')
        plot_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=(5, 2))
        self.m_plot = MatplotlibPlot(plot_frame)
        self.PlotScale = tk.Scale(plot_frame, orient=tk.HORIZONTAL, from_=1, to=100,
                                  command=self.change_plot_scale, background=self.bg_color)
        self.PlotScale.set(100)
        self.PlotScale.pack()
        self.m_plot.plot_waveforms(self.parameters.ch2_state, self.parameters.pulse_length_neg,
                                   self.parameters.pos_pulse_delay, self.parameters.pulse_length_pos,
                                   self.parameters.period, self.PlotScale.get())

        # **** init hardware objects ****
        self.pulser = RigolDG4102Pulser()

    def change_plot_scale(self, value):
        value = int(value)
        self.m_plot.set_x_lim(self.parameters.period, value)
        self.m_plot.canvas.draw()  # show the canvas at the screen

    def get_actual_data(self, plot_data):
        value_frequency = self.Entry_Frequency.get()
        value_t_on_neg = self.Entry_t_on_neg.get()
        value_delay = self.Entry_delay_pulse_pos.get()
        value_t_on_pos = self.Entry_t_on_pos.get()
        value_period = int(1e6 / int(value_frequency))

        if test_data(value_frequency) == 'true' and test_data(value_t_on_neg) == 'true' \
                and test_data(value_delay) == 'true' and test_data(value_t_on_pos) == 'true':
            if (int(value_t_on_neg) + int(value_delay) + int(value_t_on_pos)) < value_period:
                if int(value_frequency) < 10001:
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
                messagebox.showerror(title='Error', message=u'T\u2092\u2099\u207B + delay + '
                                                            u'T\u2092\u2099\u207A needs to be lower than the period'
                                                            u' time (' + str(value_period) + '\u00B5s)')

    def entry_modified(self, event):
        print(event)
        print(event.widget.get())
        event.widget.config(fg='blue')

    def entry_confirmed(self, event):
        event.widget.config(fg='black')
        print(event.widget.id)

    def start_pulsing_main(self, *args):
        if self.pulser_connected.get():
            self.get_actual_data('NO')
            self.parameters.save_data(self.parameters.ch2_state)
            self.pulser.start_pulsing_rigol(self.parameters.frequency, self.frequency_changed,
                                            self.parameters.pulse_length_neg, self.parameters.pos_pulse_delay,
                                            self.parameters.pulse_length_pos, self.Entry_t_on_pos['state'])
            self.ch1_active.set(self.pulser.get_channel_state(1))
            self.ch2_active.set(self.pulser.get_channel_state(2))

    def stop_pulsing_main(self, *args):
        if self.pulser_connected.get():
            self.pulser.stop_pulsing_rigol()
            self.ch1_active.set(self.pulser.get_channel_state(1))
            self.ch2_active.set(self.pulser.get_channel_state(2))

    def plot_data_main(self, *args):
        self.get_actual_data('YES')
        # self.parameters.save_data(self.parameters.ch2_state)
        # self.pulser.start_pulsing_rigol(self.parameters.frequency, self.frequency_changed,
        # self.parameters.pulse_length_neg, self.parameters.pos_pulse_delay, self.parameters.pulse_length_pos,
        # self.Entry_t_on_pos['state'])
        self.m_plot.plot_waveforms(self.parameters.ch2_state, self.parameters.pulse_length_neg,
                                   self.parameters.pos_pulse_delay, self.parameters.pulse_length_pos,
                                   self.parameters.period, self.PlotScale.get())

    def btn_activate_ch2(self):
        if self.Entry_t_on_pos['state'] == tk.NORMAL:
            self.Entry_t_on_pos.config(state=tk.DISABLED)
            self.Entry_delay_pulse_pos.config(state=tk.DISABLED)
            self.Btn_activate_text.set("Enable")
            self.parameters.ch2_state = 'disabled'
            # self.pulser.change_state_channel(2, 'OFF')
        else:
            self.Entry_t_on_pos.config(state=tk.NORMAL)
            self.Entry_delay_pulse_pos.config(state=tk.NORMAL)
            self.Btn_activate_text.set("Disable")
            self.parameters.ch2_state = 'normal'
            # self.start_pulsing_main()

    def on_closing(self):
        self.stop_pulsing_main()
        self.root.destroy()

    def pulser_connect(self):
        if self.pulser_connected.get():
            try:
                self.pulser.connect('USB0::6833::1601::DG4E202901834::0::INSTR')
                self.Pulser_Connected_Checkbutton.select()
            except ValueError as e:
                self.pulser_connected.set(0)
                messagebox.showerror('Error', 'Connection to RigolDG4102 failed\n\n'+str(e))
        else:
            self.stop_pulsing_main()
