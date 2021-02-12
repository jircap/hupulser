import tkinter as tk
from tkinter import messagebox
from custom_widgets import ToggleButton, Indicator
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg)
from matplotlib.figure import Figure
from rigol_4102 import RigolDG4102Pulser
from adl_power_supply import ADLPowerSupply
import configparser


# class for plotting the entered data using Matplotlib
class MatplotlibPlot:
    def __init__(self, master):     # initialization
        self.f = Figure(figsize=(4, 2.5), dpi=100)    # set the Figure for plots
        self.f.patch.set_facecolor('#f5f5f5')       # set color of the Figure
        self.ax = self.f.add_axes([0.12, 0.2, 0.8, 0.75])             # add axes
        self.canvas = FigureCanvasTkAgg(self.f, master=master)    # set the canvas
        self.canvas.get_tk_widget().pack()  # position the canvas in GUI

    def plot_waveforms(self, t, wf1, wf2, ch2_state, period, scale):
        self.ax.clear()  # clear the previous plot
        self.set_x_lim(period, scale)  # set x limits taking into account the current scale value
        self.ax.set_xlabel('Time [$\\mathrm{\\mu s}$]')  # set x label
        self.ax.set_ylabel('Amplitude')  # set y label
        self.ax.plot(t, wf1, color='red')  # plot the wave form of the negative pulse using a red color
        if ch2_state:  # when CH2 is enabled
            self.ax.plot(t, wf2, color='blue')  # plot the wave form of the positive pulse using a blue color
        self.ax.set_ylim(-0.2, 1.2)
        self.ax.set_yticks([0, 1])
        self.canvas.draw()  # show the canvas at the screen

    def set_x_lim(self, period, scale):
        max_value = period/100*scale
        x_offset = max_value/10
        self.ax.set_xlim(-x_offset, period/100*scale + x_offset)


class HuPulserGui:
    def __init__(self, master):
        self.root = master
        master.title(":* pulsed power supply control")
        # **** init hardware objects ****
        self.pulser = RigolDG4102Pulser()
        self.ps1 = ADLPowerSupply()
        # load last state of instruments
        self.config = configparser.ConfigParser()
        self.config.read('hupulser.ini')
        try:
            self.ps1.mode = self.config['DC1']['mode']
            self.ps1.set_mode_setpoint_passive(0, self.config['DC1']['setpoint_power'])
            self.ps1.set_mode_setpoint_passive(1, self.config['DC1']['setpoint_voltage'])
            self.ps1.set_mode_setpoint_passive(2, self.config['DC1']['setpoint_current'])
        except KeyError:  # key Pulser not found in config (no config present)
            messagebox.showinfo('Info', 'Some config values for DC1 not found in ini file.')
        try:
            self.pulser.frequency = self.config['Pulser']['frequency']
            self.pulser.pulse_shape = self.config['Pulser']['pulse_shape'].split(',')
            self.pulser.ch2_enabled = self.config['Pulser']['ch2_enabled'] == 'True'
        except KeyError:  # key Pulser not found in config (no config present)
            messagebox.showinfo('Info', 'Some config values for Pulser not found in ini file.')

        # main frame
        main_frame = tk.Frame(master, background=self.root['bg'])
        main_frame.pack(side=tk.TOP)
        # status bar
        self.status = tk.StringVar('')
        self.status_bar = tk.Label(master, textvariable=self.status, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # *** main frame widgets ***
        # dc power supply frame
        ps1_frame = tk.LabelFrame(main_frame, background=self.root['bg'], borderwidth=2, relief=tk.RIDGE,
                                  text='  DC POWER negative  ')
        ps1_frame.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=(5, 2))
        ps1_connect_frame = tk.Frame(ps1_frame, background=self.root['bg'])
        ps1_connect_frame.pack()
        self.button_ps1_connect = tk.Button(ps1_connect_frame, text='Connect', command=self.ps1_connect,
                                            relief=tk.GROOVE)
        self.button_ps1_connect.grid(row=0, column=0, padx=5, sticky='W')
        self.indicator_ps1_connected = Indicator(ps1_connect_frame, text='Connected')
        self.indicator_ps1_connected.grid(row=0, column=1, columnspan=2, padx=5)
        self.button_ps1_output = tk.Button(ps1_connect_frame, text="DC ON/OFF", relief=tk.GROOVE,
                                           command=self.ps1_toggle_output)
        self.button_ps1_output.grid(row=1, column=0, columnspan=2, padx=5, pady=(5, 0), sticky='W')
        # control mode
        ps1_mode_frame = tk.Frame(ps1_frame, background=self.root['bg'])
        ps1_mode_frame.pack()
        label_ps1_mode = tk.Label(ps1_mode_frame, text='Control mode')
        label_ps1_mode.grid(row=0, column=0, columnspan=3, padx=5)
        self.ps1_mode = tk.IntVar()
        self.ps1_mode.set(self.ps1.mode)
        self.radioButton_modeP = tk.Radiobutton(ps1_mode_frame, text='P', value=0, variable=self.ps1_mode,
                                                command=self.ps1_mode_set)
        self.radioButton_modeP.grid(row=1, column=0, padx=5, sticky='E')
        self.radioButton_modeU = tk.Radiobutton(ps1_mode_frame, text='U', value=1, variable=self.ps1_mode,
                                                command=self.ps1_mode_set)
        self.radioButton_modeU.grid(row=1, column=1, padx=5, sticky='E')
        self.radioButton_modeI = tk.Radiobutton(ps1_mode_frame, text='I', value=2, variable=self.ps1_mode,
                                                command=self.ps1_mode_set)
        self.radioButton_modeI.grid(row=1, column=2, padx=5, sticky='E')

        # values
        ps1_values_frame = tk.Frame(ps1_frame, background=self.root['bg'])
        ps1_values_frame.pack()
        label_ps1_setpoint = tk.Label(ps1_values_frame, text='Setpoint')
        label_ps1_setpoint.grid(row=0, column=0, padx=5, sticky='E')
        self.entry_ps1_setpoint = tk.Entry(ps1_values_frame, width=8, justify=tk.RIGHT)
        self.entry_ps1_setpoint.insert(0, self.ps1.setpoint)
        self.entry_ps1_setpoint.bind("<Return>", self.ps1_setpoint_confirmed)
        self.entry_ps1_setpoint.bind("<FocusOut>", self.ps1_setpoint_modified)
        self.entry_ps1_setpoint.grid(row=0, column=1, padx=5, sticky='E')
        self.ps1_unit = tk.StringVar()
        self.ps1_unit.set('W')
        label_ps1_setpoint_unit = tk.Label(ps1_values_frame, textvariable=self.ps1_unit)
        label_ps1_setpoint_unit.grid(row=0, column=2, padx=5, sticky='W')
        self.ps1_mode_set()  # update unit label from current mode radiobutton setting

        label_ps1_power = tk.Label(ps1_values_frame, text='Power')
        label_ps1_power.grid(row=1, column=0, padx=5, pady=(5, 0), sticky='E')
        self.label_ps1_power = tk.Label(ps1_values_frame, width=6, anchor='e', text='0', relief=tk.SUNKEN,
                                        bg='#f5f5f5', bd=1, padx=0)
        self.label_ps1_power.grid(row=1, column=1, padx=5, pady=(5, 0), sticky='E')
        label_ps1_power_unit = tk.Label(ps1_values_frame, text='W')
        label_ps1_power_unit.grid(row=1, column=2, padx=5, pady=(5, 0), sticky='W')

        label_ps1_voltage = tk.Label(ps1_values_frame, text='Voltage')
        label_ps1_voltage.grid(row=2, column=0, padx=5, sticky='E')
        self.label_ps1_voltage = tk.Label(ps1_values_frame, width=6, anchor='e', text='0', relief=tk.SUNKEN,
                                          bg='#f5f5f5', bd=1, padx=0)
        self.label_ps1_voltage.grid(row=2, column=1, padx=5, sticky='E')
        label_ps1_voltage_unit = tk.Label(ps1_values_frame, text='V')
        label_ps1_voltage_unit.grid(row=2, column=2, padx=5, sticky='W')

        label_ps1_current = tk.Label(ps1_values_frame, text='Current')
        label_ps1_current.grid(row=3, column=0, padx=5, sticky='E')
        self.label_ps1_current = tk.Label(ps1_values_frame, width=6, anchor='e', text='0', relief=tk.SUNKEN,
                                          bg='#f5f5f5', bd=1, padx=0)
        self.label_ps1_current.grid(row=3, column=1, padx=5, sticky='E')
        label_ps1_current_unit = tk.Label(ps1_values_frame, text='mA')
        label_ps1_current_unit.grid(row=3, column=2, padx=5, sticky='W')
        # indicators
        ps1_indicators_frame = tk.Frame(ps1_frame, background=self.root['bg'])
        ps1_indicators_frame.pack()
        self.indicator_ps1_output = Indicator(ps1_indicators_frame, 'DC ON')
        self.indicator_ps1_output.grid(row=0, column=0, padx=5, sticky='E')
        self.indicator_ps1_mains = Indicator(ps1_indicators_frame, 'Mains ON')
        self.indicator_ps1_mains.grid(row=1, column=0, padx=5, sticky='E')
        self.indicator_ps1_plasma = Indicator(ps1_indicators_frame, 'Plasma ON')
        self.indicator_ps1_plasma.grid(row=2, column=0, padx=5, sticky='E')
        self.indicator_ps1_error = Indicator(ps1_indicators_frame, 'Error', color_on='#e00000', color_off='#500000')
        self.indicator_ps1_error.grid(row=3, column=0, padx=5, sticky='E')

        self.indicator_ps1_active = Indicator(ps1_indicators_frame, 'Active', color_on='#e00000',
                                              color_off='#500000')
        self.indicator_ps1_active.grid(row=0, column=1, padx=5, sticky='E')
        self.indicator_ps1_interlock = Indicator(ps1_indicators_frame, 'Interlock', color_on='#e00000',
                                                 color_off='#500000')
        self.indicator_ps1_interlock.grid(row=1, column=1, padx=5, sticky='E')
        self.indicator_ps1_setpoint = Indicator(ps1_indicators_frame, 'Setpoint Error', color_on='#e00000',
                                                color_off='#500000')
        self.indicator_ps1_setpoint.grid(row=2, column=1, padx=5, sticky='E')
        label_ps1_cmd_error_label = tk.Label(ps1_indicators_frame, text='Cmd Error')
        label_ps1_cmd_error_label.grid(row=3, column=1, padx=5, sticky='W')
        self.label_ps1_cmd_error = tk.Label(ps1_indicators_frame, width=3, text='0', relief=tk.SUNKEN,
                                            bg='#f5f5f5', bd=1, padx=0)
        self.label_ps1_cmd_error.grid(row=3, column=1, padx=5, sticky='E')

        # pulser frame
        pulser_frame = tk.LabelFrame(main_frame, background=self.root['bg'], borderwidth=2, relief=tk.RIDGE,
                                     text='  PULSER  ')
        pulser_frame.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=(5, 2))
        self.button_pulser_connect = tk.Button(pulser_frame, text='Connect', command=self.pulser_connect,
                                               relief=tk.GROOVE)
        self.button_pulser_connect.grid(row=0, column=0, padx=5, sticky='W')
        self.indicator_pulser_connected = Indicator(pulser_frame, text='Connected')
        self.indicator_pulser_connected.grid(row=0, column=1, padx=5)
        self.button_pulser_output = tk.Button(pulser_frame, text="Pulsing ON/OFF", relief=tk.GROOVE,
                                              command=self.pulser_toggle_output)
        self.button_pulser_output.grid(row=1, column=0, columnspan=2, padx=5, pady=(5, 0), sticky='W')

        label_pulser_frequency = tk.Label(pulser_frame, text="Frequency", background=self.root['bg'])
        label_pulser_frequency.grid(row=2, column=0, padx=5, pady=(5, 0), sticky='E')
        self.entry_pulser_frequency = tk.Entry(pulser_frame, width=10, justify=tk.RIGHT)
        self.entry_pulser_frequency.bind("<Return>", self.pulser_frequency_confirmed)
        self.entry_pulser_frequency.bind("<FocusOut>", self.pulser_frequency_modified)
        self.entry_pulser_frequency.grid(row=2, column=1, padx=5, pady=(5, 0), sticky='E')
        self.entry_pulser_frequency.insert(0, self.pulser.frequency)
        label_pulser_frequency_units = tk.Label(pulser_frame, text="Hz", background=self.root['bg'])
        label_pulser_frequency_units.grid(row=2, column=2, padx=5, pady=(5, 0), sticky='W')

        label_channel1 = tk.Label(pulser_frame, text="Pulse shape", background=self.root['bg'])
        label_channel1.grid(row=3, column=0, padx=5, pady=(5, 0), sticky='E')

        self.text_pulser_shape = tk.Text(pulser_frame, width=10, height=6, font='TkDefaultFont')
        self.text_pulser_shape.grid(row=3, column=1, padx=5, pady=(5, 0), sticky='E')
        for s in self.pulser.pulse_shape:
            self.text_pulser_shape.insert(tk.INSERT, s + '\n')  # fill text by actual value from pulser
        label_pulser_shape_units = tk.Label(pulser_frame, text="\u00B5s", background=self.root['bg'])
        label_pulser_shape_units.grid(row=3, column=2, padx=5, pady=(5, 0), sticky='W')
        self.button_pulser_set_shape = tk.Button(pulser_frame, text="Set shape", relief=tk.GROOVE,
                                                 command=self.pulser_shape)
        self.button_pulser_set_shape.grid(row=4, column=1, padx=5, pady=(5, 0))

        self.toggleButton_pulser_activate_ch2 = ToggleButton(pulser_frame, text="Enable channel 2",
                                                             command=self.pulser_activate_ch2, ind_height=12)
        self.toggleButton_pulser_activate_ch2.grid(row=5, column=0, columnspan=2, padx=5, pady=(5, 0))
        self.toggleButton_pulser_activate_ch2.on = self.pulser.ch2_enabled

        self.indicator_pulser_ch1_output = Indicator(pulser_frame, 'Channel 1 output')
        self.indicator_pulser_ch1_output.grid(row=6, column=0, columnspan=2, padx=5)

        self.indicator_pulser_ch2_output = Indicator(pulser_frame, 'Channel 2 output')
        self.indicator_pulser_ch2_output.grid(row=7, column=0, columnspan=2, padx=5)

        plot_frame = tk.LabelFrame(main_frame, background=self.root['bg'], borderwidth=2, relief=tk.RIDGE,
                                   text='  PLOT  ')
        plot_frame.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=(5, 2))
        self.m_plot = MatplotlibPlot(plot_frame)
        self.scale_plot = tk.Scale(plot_frame, orient=tk.HORIZONTAL, from_=1, to=100,
                                   command=self.plot_change_scale, background=self.root['bg'])
        self.scale_plot.set(100)
        self.scale_plot.pack()
        t, wf1, wf2 = self.pulser.get_waveforms()
        self.m_plot.plot_waveforms(t, wf1, wf2, self.pulser.ch2_enabled, self.pulser.get_period(),
                                   self.scale_plot.get())

#         self.pulser_activate_ch2()  # call the pushbutton callback to enable/disable entry fields accordingly
        # register after callback
        try:
            self.root.after(self.config['DC1']['update_interval'], self.ps1_periodic_update)
        except KeyError:  # key Pulser not found in config (no config present)
            self.config['DC1'].update({'update_interval': '500'})
            self.root.after(self.config['DC1']['update_interval'], self.ps1_periodic_update)
            messagebox.showwarning('Warning', 'Update interval not found in DC1 ini file. Using 500 ms.')

    # connect or disconnect DC1 power supply
    def ps1_connect(self):
        if not self.ps1.connected:
            try:
                try:
                    baud_rate = int(self.config['DC1']['baud_rate'])
                    if baud_rate not in [9600, 19200, 57600, 115200, 921600]:
                        baud_rate = 9600
                        messagebox.showwarning('Warning', 'Incompatible baud rate, must be one of the following:\n'
                                                          '9600, 19200, 57600, 115200 or 921600 (RS-485 only).\n'
                                                          'Using baud rate of 9600.')
                except ValueError:
                    messagebox.showwarning('Warning', 'Baud rate must be an integer. Using baud rate of 9600.')
                    baud_rate = 9600

                self.ps1.connect(self.config['DC1']['resource_id'], baud=baud_rate)
            except Exception as e:
                messagebox.showerror('Error', 'Connection to ADL power supply failed\n\n' + str(e))
            finally:
                self.indicator_ps1_connected.on = self.ps1.connected
                if self.ps1.connected:
                    self.ps1_update_status_indicators()
        else:  # if connected -> disconnect
            self.ps1_stop()
            self.ps1.disconnect()
            self.indicator_ps1_connected.on = self.ps1.connected

    # regular timer used to poll actual values from the DC power supply
    # without regular interrogating, the ADL power supply automatically turns off
    def ps1_periodic_update(self):
        power, voltage, current = self.ps1.update_pui()   # get actual values, this updates status
        self.label_ps1_power.config(text=str(power))
        self.label_ps1_voltage.config(text=str(voltage))
        self.label_ps1_current.config(text=str(current))
        self.ps1_update_status_indicators()    # show actual status by indicators
        self.root.after(int(self.config['DC1']['update_interval']), self.ps1_periodic_update)

    def ps1_mode_set(self):
        new_mode = self.ps1_mode.get()  # get value from radiobuttons
        self.ps1.mode = new_mode  # change mode in instrument
        self.entry_ps1_setpoint.delete(0, 'end')
        # get setpoint value stored in instrument (after mode change)
        self.entry_ps1_setpoint.insert(0, self.ps1.setpoint)
        self.entry_ps1_setpoint.config(fg='black')
        if new_mode == 0:    # change unit label according to mode
            self.ps1_unit.set('W')
        elif new_mode == 1:
            self.ps1_unit.set('V')
        elif new_mode == 2:
            self.ps1_unit.set('mA')
        else:
            self.ps1_unit.set('')

    def ps1_setpoint_modified(self):
        # check if new value is different from instrument value
        try:
            new_value = int(self.entry_ps1_setpoint.get())
            if new_value != self.ps1.setpoint:
                self.entry_ps1_setpoint.config(fg='red')
            else:
                self.entry_ps1_setpoint.config(fg='black')
        except ValueError:
            self.entry_ps1_setpoint.config(fg='red')

    def ps1_setpoint_confirmed(self):
        try:
            self.ps1.setpoint = self.entry_ps1_setpoint.get()
            self.entry_ps1_setpoint.config(fg='black')
        except ValueError as e:
            messagebox.showerror('Error', str(e))

    def ps1_update_status_indicators(self):
        # self.ps1.update_status()   # depending on the workflow, this might not be necessary as status bytes are
        # are updated with every command
        self.indicator_ps1_output.on = self.ps1.status['outputON']
        self.indicator_ps1_mains.on = self.ps1.status['mainsON']
        self.indicator_ps1_plasma.on = self.ps1.status['plasmaON']
        self.indicator_ps1_active.on = self.ps1.status['activeToggle']
        self.indicator_ps1_interlock.on = self.ps1.status['interlock']
        self.indicator_ps1_setpoint.on = not self.ps1.status['setpointOK']
        self.indicator_ps1_error.on = self.ps1.status['error']
        self.label_ps1_cmd_error.config(text=str(self.ps1.status['commandErrorCode']))

    def ps1_toggle_output(self):
        self.ps1.output = not self.ps1.output
        self.ps1_update_status_indicators()

    def ps1_stop(self):
        self.ps1.output = False
        self.ps1_update_status_indicators()

    def pulser_connect(self):
        if not self.pulser.connected:
            try:
                self.pulser.connect('USB0::6833::1601::DG4E202901834::0::INSTR')
            except Exception as e:
                messagebox.showerror('Error', 'Connection to RigolDG4102 failed\n\n' + str(e))
            finally:
                self.indicator_pulser_connected.on = self.pulser.connected
        else:
            self.pulser_stop()
            self.pulser.disconnect()
            self.indicator_pulser_connected.on = self.pulser.connected

    def pulser_frequency_modified(self, event):
        # check if new value is different from instrument value
        try:
            new_value = int(event.widget.get())
            value = self.pulser.frequency
            # pulser instance to get the value stored in pulser class instance
            if new_value != value:
                event.widget.config(fg='red')
            else:
                event.widget.config(fg='black')
        except ValueError:
            event.widget.config(fg='red')

    def pulser_frequency_confirmed(self, event):
        try:
            self.pulser.frequency = event.widget.get()
            event.widget.config(fg='black')
            t, wf1, wf2 = self.pulser.get_waveforms()
            self.m_plot.plot_waveforms(t, wf1, wf2, self.pulser.ch2_enabled, self.pulser.get_period(),
                                       self.scale_plot.get())
        except ValueError as e:
            messagebox.showerror('Error', str(e))

    def pulser_activate_ch2(self):
        self.pulser.ch2_enabled = self.toggleButton_pulser_activate_ch2.on
        t, wf1, wf2 = self.pulser.get_waveforms()
        self.m_plot.plot_waveforms(t, wf1, wf2, self.pulser.ch2_enabled, self.pulser.get_period(),
                                   self.scale_plot.get())
        self.indicator_pulser_ch2_output.on = self.pulser.output and self.pulser.ch2_enabled

    def pulser_shape(self):
        self.pulser.pulse_shape = self.text_pulser_shape.get("1.0", 'end').split()
        t, wf1, wf2 = self.pulser.get_waveforms()
        self.m_plot.plot_waveforms(t, wf1, wf2, self.pulser.ch2_enabled, self.pulser.get_period(),
                                   self.scale_plot.get())

    def pulser_toggle_output(self):
        self.pulser.output = not self.pulser.output
        self.indicator_pulser_ch1_output.on = self.pulser.output
        self.indicator_pulser_ch2_output.on = self.pulser.output and self.pulser.ch2_enabled

    def pulser_stop(self):
        self.pulser.output = False
        self.indicator_pulser_ch1_output.on = self.pulser.output
        self.indicator_pulser_ch2_output.on = self.pulser.output and self.pulser.ch2_enabled

    def plot_change_scale(self, value):
        value = int(value)
        self.m_plot.set_x_lim(self.pulser.get_period(), value)
        self.m_plot.canvas.draw()  # show the canvas at the screen

    def on_closing(self):
        self.pulser_stop()   # stop pulsing
        # save state to config
        setpoints = self.ps1.get_setpoints()
        self.config.set('DC1', 'mode', str(self.ps1.mode))
        self.config.set('DC1', 'setpoint_power', str(setpoints[0]))
        self.config.set('DC1', 'setpoint_voltage', str(setpoints[1]))
        self.config.set('DC1', 'setpoint_current', str(setpoints[2]))

        self.config.set('Pulser', 'frequency', str(self.pulser.frequency))
        self.config.set('Pulser', 'pulse_shape', ','.join(self.text_pulser_shape.get("1.0", 'end').split()))
        self.config.set('Pulser', 'ch2_enabled', str(self.pulser.ch2_enabled))

        with open('hupulser.ini', 'w') as config_file:
            self.config.write(config_file)
        self.root.destroy()
