import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg)
from matplotlib.figure import Figure
from rigol_4102 import RigolDG4102Pulser
import configparser
import numpy as np


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
        if ch2_state:               # when CH2 is enabled
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
        self.config = configparser.ConfigParser()
        self.config.read('hupulser.ini')
        # **** init hardware objects ****
        self.pulser = RigolDG4102Pulser()
        self.pulser.set_all(self.config['RigolPulser']['frequency'],
                            self.config['RigolPulser']['neg_length'],
                            self.config['RigolPulser']['pos_delay'],
                            self.config['RigolPulser']['pos_length'],
                            self.config['RigolPulser']['ch2_enabled'])

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
        self.Entry_Frequency.inst_property = RigolDG4102Pulser.frequency
        self.Entry_Frequency.bind("<Return>", self.entry_confirmed)
        self.Entry_Frequency.bind("<FocusOut>", self.entry_modified)
        self.Entry_Frequency.grid(row=1, column=1, padx=5, pady=(10, 0), sticky='E')
        self.Entry_Frequency.insert(0, self.pulser.frequency)
        self.Label_Frequency_Units = tk.Label(pulser_frame, text="Hz", background=self.bg_color)
        self.Label_Frequency_Units.grid(row=1, column=2, padx=5, pady=(10, 0), sticky='W')

        self.Label_Channel1 = tk.Label(pulser_frame, text="Channel 1", background=self.bg_color)
        self.Label_Channel1.grid(row=2, column=0, padx=5, pady=(5, 0), sticky='E')

        self.Label_t_on_neg = tk.Label(pulser_frame, text=u'T\u2092\u2099\u207B', background=self.bg_color)
        self.Label_t_on_neg.grid(row=3, column=0, padx=5, sticky='E')
        self.Entry_t_on_neg = tk.Entry(pulser_frame, width=10)
        self.Entry_t_on_neg.inst_property = RigolDG4102Pulser.neg_pulse_length
        self.Entry_t_on_neg.bind("<Return>", self.entry_confirmed)
        self.Entry_t_on_neg.bind("<FocusOut>", self.entry_modified)
        self.Entry_t_on_neg.grid(row=3, column=1, padx=5, sticky='E')
        self.Entry_t_on_neg.insert(0, self.pulser.neg_pulse_length)
        self.Label_t_on_neg_Units = tk.Label(pulser_frame, text=u'\u00B5s', background=self.bg_color)
        self.Label_t_on_neg_Units.grid(row=3, column=2, padx=5, sticky='W')

        self.Label_Channel2 = tk.Label(pulser_frame, text="Channel 2", background=self.bg_color)
        self.Label_Channel2.grid(row=4, column=0, padx=5, pady=(5, 0), sticky='E')
        self.Btn_activate_text = tk.StringVar(pulser_frame)
        self.Btn_activate_text.set('Disable') if self.pulser.ch2_enabled else self.Btn_activate_text.set('Enable')
        self.Button_activate_ch2 = ttk.Button(pulser_frame, text="Activate", command=self.btn_activate_ch2,
                                              textvariable=self.Btn_activate_text)
        self.Button_activate_ch2.grid(row=4, column=1, padx=5, pady=(5, 0))

        self.Label_delay_pulse_pos = tk.Label(pulser_frame, text='Delay', background=self.bg_color)
        self.Label_delay_pulse_pos.grid(row=5, column=0, padx=5, sticky='E')
        self.Entry_delay_pulse_pos = tk.Entry(pulser_frame, width=10)
        self.Entry_delay_pulse_pos.inst_property = RigolDG4102Pulser.pos_pulse_delay
        self.Entry_delay_pulse_pos.bind("<Return>", self.entry_confirmed)
        self.Entry_delay_pulse_pos.bind("<FocusOut>", self.entry_modified)
        self.Entry_delay_pulse_pos.grid(row=5, column=1, padx=5, sticky='E')
        self.Entry_delay_pulse_pos.insert(0, self.pulser.pos_pulse_delay)
        if self.pulser.ch2_enabled:
            self.Entry_delay_pulse_pos['state'] = tk.NORMAL
        else:
            self.Entry_delay_pulse_pos['state'] = tk.DISABLED
        self.Label_delay_pulse_pos_Units = tk.Label(pulser_frame, text=u'\u00B5s', background=self.bg_color)
        self.Label_delay_pulse_pos_Units.grid(row=5, column=2, padx=5, sticky='W')

        self.Label_t_on_pos = tk.Label(pulser_frame, text=u'T\u2092\u2099\u207A', background=self.bg_color)
        self.Label_t_on_pos.grid(row=6, column=0, padx=5, sticky='E')
        self.Entry_t_on_pos = tk.Entry(pulser_frame, width=10)
        self.Entry_t_on_pos.inst_property = RigolDG4102Pulser.pos_pulse_length
        self.Entry_t_on_pos.bind("<FocusOut>", self.entry_modified)
        self.Entry_t_on_pos.bind("<Return>", self.entry_confirmed)
        self.Entry_t_on_pos.grid(row=6, column=1, padx=5, sticky='E')
        self.Entry_t_on_pos.insert(0, self.pulser.pos_pulse_length)
        if self.pulser.ch2_enabled:
            self.Entry_t_on_pos['state'] = tk.NORMAL
        else:
            self.Entry_t_on_pos['state'] = tk.DISABLED
        self.Label_t_on_pos_Units = tk.Label(pulser_frame, text=u'\u00B5s', background=self.bg_color)
        self.Label_t_on_pos_Units.grid(row=6, column=2, padx=5, sticky='W')

        self.Button_start = ttk.Button(pulser_frame, text="Start", command=self.start_pulsing)
        self.Button_start.grid(row=8, column=1, padx=5, pady=0)
        self.Button_stop = ttk.Button(pulser_frame, text="Stop", command=self.stop_pulsing)
        self.Button_stop.grid(row=9, column=1, padx=5, pady=0)

        self.ch1_active = tk.BooleanVar()
        self.CheckButton_CH1_active = ttk.Checkbutton(pulser_frame, text="CH 1 active", state=tk.DISABLED,
                                                      variable=self.ch1_active)
        self.CheckButton_CH1_active.grid(row=8, column=0, padx=5, pady=5)

        self.ch2_active = tk.BooleanVar()
        self.CheckButton_ch2_active = ttk.Checkbutton(pulser_frame, text="CH 2 active", state=tk.DISABLED,
                                                      variable=self.ch2_active)
        self.CheckButton_ch2_active.grid(row=9, column=0, padx=5, pady=5)

        plot_frame = tk.LabelFrame(main_frame, background=self.bg_color, borderwidth=2, relief=tk.RIDGE,
                                   text='  PLOT  ')
        plot_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=(5, 2))
        self.m_plot = MatplotlibPlot(plot_frame)
        self.PlotScale = tk.Scale(plot_frame, orient=tk.HORIZONTAL, from_=1, to=100,
                                  command=self.change_plot_scale, background=self.bg_color)
        self.PlotScale.set(100)
        self.PlotScale.pack()
        self.m_plot.plot_waveforms(self.pulser.ch2_enabled, self.pulser.neg_pulse_length, self.pulser.pos_pulse_delay,
                                   self.pulser.pos_pulse_length, self.pulser.get_period(), self.PlotScale.get())

    def change_plot_scale(self, value):
        value = int(value)
        self.m_plot.set_x_lim(self.pulser.get_period(), value)
        self.m_plot.canvas.draw()  # show the canvas at the screen

    def entry_modified(self, event):
        # check if new value is different from instrument value
        try:
            new_value = int(event.widget.get())
            value = event.widget.inst_property.fget(self.pulser)  # use property link stored in widget and pulser instance
            # to get the value stored in pulser class instance
            if new_value != value:
                event.widget.config(fg='red')
            else:
                event.widget.config(fg='black')
        except ValueError:
            event.widget.config(fg='red')

    def entry_confirmed(self, event):
        try:
            event.widget.inst_property.fset(self.pulser, event.widget.get())
            event.widget.config(fg='black')
            self.plot_data()
        except ValueError as e:
            messagebox.showerror('Error', str(e))

    def start_pulsing(self, *args):
        self.pulser.output = True
        self.ch1_active.set(self.pulser.output)
        self.ch2_active.set(self.pulser.output and self.pulser.ch2_enabled)

    def stop_pulsing(self, *args):
        self.pulser.output = False
        self.ch1_active.set(self.pulser.output)
        self.ch2_active.set(self.pulser.output and self.pulser.ch2_enabled)

    def plot_data(self, *args):
        self.m_plot.plot_waveforms(self.pulser.ch2_enabled, self.pulser.neg_pulse_length, self.pulser.pos_pulse_delay,
                                   self.pulser.pos_pulse_length, self.pulser.get_period(), self.PlotScale.get())

    def btn_activate_ch2(self):
        if self.Entry_t_on_pos['state'] == tk.NORMAL:
            self.Entry_t_on_pos.config(state=tk.DISABLED)
            self.Entry_delay_pulse_pos.config(state=tk.DISABLED)
            self.Btn_activate_text.set("Enable")
            self.pulser.ch2_enabled = False
            self.plot_data()
        else:
            self.Entry_t_on_pos.config(state=tk.NORMAL)
            self.Entry_delay_pulse_pos.config(state=tk.NORMAL)
            self.Btn_activate_text.set("Disable")
            self.pulser.ch2_enabled = True
            self.plot_data()

    def on_closing(self):
        self.stop_pulsing()   # stop pulsing
        self.config['RigolPulser'] = {'frequency': self.pulser.frequency, 'neg_length': self.pulser.neg_pulse_length,
                                      'pos_delay': self.pulser.pos_pulse_delay,
                                      'pos_length': self.pulser.pos_pulse_length,
                                      'ch2_enabled': self.pulser.ch2_enabled}
        with open('hupulser.ini', 'w') as config_file:
            self.config.write(config_file)
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
            self.stop_pulsing()
