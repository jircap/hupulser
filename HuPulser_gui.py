import time
import tkinter as tk
from tkinter import messagebox
import numpy as np
from custom_widgets import ToggleButton, Indicator
from rigol_4102 import RigolDG4102Pulser
from ITECH_IT6726V_power_supply import ItechIT6726VPowerSupply
import configparser
from matplotlib.animation import FuncAnimation
from matplotlib_plots import MatplotlibPlot1axes, MatplotlibPlot3axes
import threading
import os


class HuPulserGui:
    def __init__(self, master):
        self.root = master
        master.title(":* pulsed power supply control")
        # **** init hardware objects ****
        self._ps1 = ItechIT6726VPowerSupply()
        self._pulser = RigolDG4102Pulser()
        # load last state of instruments
        self._config = configparser.ConfigParser()
        # self._config.read('hupulser.ini') # Linux version
        config_path = os.path.join(os.path.dirname(__file__), 'hupulser.ini')
        self._config.read(config_path)
        try:
            self._ps1.set_setpoint_for_mode(0, self._config['DC1']['setpoint_voltage'])
            self._ps1.set_setpoint_for_mode(1, self._config['DC1']['setpoint_power'])
            self._ps1.set_setpoint_for_mode(2, self._config['DC1']['setpoint_current'])
            self._ps1.set_setpoint_for_mode(2, self._config['DC1']['setpoint_current'])
        except KeyError:
            messagebox.showinfo('Info', 'Some config values for DC1 not found in ini file.')
        try:
            self._pulser.frequency = self._config['Pulser']['frequency']
            self._pulser.pulse_shape = self._config['Pulser']['pulse_shape'].split(',')
            self._pulser.ch2_enabled = self._config['Pulser']['ch2_enabled'] == 'True'
            self._over_voltage_protection = self._config['DC1']['over_voltage_protection']
        except KeyError:
            messagebox.showinfo('Info', 'Some config values for Pulser not found in ini file.')

        # main frame
        main_frame = tk.Frame(master, background=self.root['bg'])
        main_frame.pack(side=tk.TOP)
        # status bar
        self.status = tk.StringVar(None)
        self.status_bar = tk.Label(master, textvariable=self.status, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # *** main frame widgets ***
        # DC POWER SUPPLY FRAME
        ps1_frame = tk.LabelFrame(main_frame, background=self.root['bg'], borderwidth=2, relief=tk.RIDGE,
                                  text='  ITECH IT6726V  ')
        ps1_frame.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=(5, 2))
        ps1_connect_frame = tk.Frame(ps1_frame, background=self.root['bg'])
        ps1_connect_frame.pack()
        self.button_ps1_connect = tk.Button(ps1_connect_frame, text='Connect', command=self.ps1_connect,
                                            relief=tk.GROOVE)
        self.button_ps1_connect.grid(row=0, column=0, padx=5, sticky='W')
        self.indicator_ps1_connected = Indicator(ps1_connect_frame, text='Connected')
        self.indicator_ps1_connected.grid(row=0, column=1, columnspan=2, padx=5, sticky='E')
        self.button_ps1_output = tk.Button(ps1_connect_frame, text="DC ON/OFF", relief=tk.GROOVE,
                                           command=self.ps1_toggle_output)
        self.button_ps1_output.grid(row=1, column=0, columnspan=2, padx=5, pady=(10, 0), sticky='W')
        self.indicator_ps1_output = Indicator(ps1_connect_frame, 'DC ON')
        self.indicator_ps1_output.grid(row=1, column=1, columnspan=2, padx=5, pady=(10, 0), sticky='E')

        # VALUES
        ps1_values_frame = tk.Frame(ps1_frame, background=self.root['bg'])
        ps1_values_frame.pack()

        label_ps1_setpoints = tk.Label(ps1_values_frame, text='Limits')
        label_ps1_setpoints.grid(row=0, column=1, padx=5, pady=(5, 0), sticky='E')

        label_ps1_live = tk.Label(ps1_values_frame, text='Live')
        label_ps1_live.grid(row=0, column=2, padx=5, pady=(5, 0), sticky='E')

        label_ps1_voltage = tk.Label(ps1_values_frame, text='Voltage')
        label_ps1_voltage.grid(row=1, column=0, padx=5, pady=(5, 0), sticky='E')
        self.entry_ps1_voltage_SP = tk.Entry(ps1_values_frame, width=6, justify=tk.RIGHT)
        self.entry_ps1_voltage_SP.insert(0, self._ps1.setpoints[0])
        self.entry_ps1_voltage_SP.bind("<Return>", lambda event, mode=0,
                                                          entry=self.entry_ps1_voltage_SP: self.ps1_setpoint_confirmed(
            mode, entry))
        self.entry_ps1_voltage_SP.bind("<FocusOut>", lambda event, mode=0,
                                                            entry=self.entry_ps1_voltage_SP: self.ps1_setpoint_focus_out(
            mode, entry))
        self.entry_ps1_voltage_SP.grid(row=1, column=1, padx=5, pady=(5, 0), sticky='E')
        self.label_ps1_voltage_live = tk.Label(ps1_values_frame, width=6, anchor='e', text='0', relief=tk.SUNKEN,
                                               bg='#f5f5f5', bd=1, padx=0)
        self.label_ps1_voltage_live.grid(row=1, column=2, padx=5, pady=(5, 0), sticky='E')
        label_ps1_voltage_unit = tk.Label(ps1_values_frame, text='V')
        label_ps1_voltage_unit.grid(row=1, column=3, padx=5, pady=(5, 0), sticky='W')
        self.indicator_ps1_voltage_regime = Indicator(ps1_values_frame, '')
        self.indicator_ps1_voltage_regime.grid(row=1, column=4, padx=5, pady=(5, 0), sticky='E')

        label_ps1_power = tk.Label(ps1_values_frame, text='Power')
        label_ps1_power.grid(row=2, column=0, padx=5, pady=(5, 0), sticky='E')
        self.entry_ps1_power_SP = tk.Entry(ps1_values_frame, width=6, justify=tk.RIGHT)
        self.entry_ps1_power_SP.insert(0, self._ps1.setpoints[1])
        self.entry_ps1_power_SP.bind("<Return>", lambda event, mode=1, entry=self.entry_ps1_power_SP: self.ps1_setpoint_confirmed(mode, entry))
        self.entry_ps1_power_SP.bind("<FocusOut>", lambda event, mode=1, entry=self.entry_ps1_power_SP: self.ps1_setpoint_focus_out(mode, entry))
        self.entry_ps1_power_SP.grid(row=2, column=1, padx=5, pady=(5, 0), sticky='E')
        self.label_ps1_power_live = tk.Label(ps1_values_frame, width=6, anchor='e', text='0', relief=tk.SUNKEN,
                                        bg='#f5f5f5', bd=1, padx=0)
        self.label_ps1_power_live.grid(row=2, column=2, padx=5, pady=(5, 0), sticky='E')
        label_ps1_power_unit = tk.Label(ps1_values_frame, text='W')
        label_ps1_power_unit.grid(row=2, column=3, padx=5, pady=(5, 0), sticky='W')
        self.indicator_ps1_power_regime = Indicator(ps1_values_frame, '')
        self.indicator_ps1_power_regime.grid(row=2, column=4, padx=5, pady=(5, 0), sticky='E')

        label_ps1_current = tk.Label(ps1_values_frame, text='Current')
        label_ps1_current.grid(row=3, column=0, padx=5, pady=(5, 0), sticky='E')
        self.entry_ps1_current_SP = tk.Entry(ps1_values_frame, width=6, justify=tk.RIGHT)
        self.entry_ps1_current_SP.insert(0, self._ps1.setpoints[2])
        self.entry_ps1_current_SP.bind("<Return>", lambda event, mode=2, entry=self.entry_ps1_current_SP: self.ps1_setpoint_confirmed(mode, entry))
        self.entry_ps1_current_SP.bind("<FocusOut>", lambda event, mode=2, entry=self.entry_ps1_current_SP: self.ps1_setpoint_focus_out(mode, entry))
        self.entry_ps1_current_SP.grid(row=3, column=1, padx=5, pady=(5, 0), sticky='E')
        self.label_ps1_current_live = tk.Label(ps1_values_frame, width=6, anchor='e', text='0', relief=tk.SUNKEN,
                                          bg='#f5f5f5', bd=1, padx=0)
        self.label_ps1_current_live.grid(row=3, column=2, padx=5, pady=(5, 0), sticky='E')
        label_ps1_current_unit = tk.Label(ps1_values_frame, text='mA')
        label_ps1_current_unit.grid(row=3, column=3, padx=5, pady=(5, 0), sticky='W')
        self.indicator_ps1_current_regime = Indicator(ps1_values_frame, '')
        self.indicator_ps1_current_regime.grid(row=3, column=4, padx=5, pady=(5, 0), sticky='E')

        # PID
        # PID VOLTAGE
        ps1_pid = tk.Frame(ps1_frame, background=self.root['bg'], pady=5)
        ps1_pid.pack()

        label_ps_pid_p_coef_voltage = tk.Label(ps1_pid, text='Voltage mode')
        label_ps_pid_p_coef_voltage.grid(row=0, column=1, padx=2, pady=(5, 0), columnspan=6, sticky='W')
        label_ps_pid_p_coef_voltage = tk.Label(ps1_pid, text='P')
        label_ps_pid_p_coef_voltage.grid(row=1, column=0, padx=2, pady=(5, 0), sticky='E')
        self.entry_ps_pid_p_coef_voltage = tk.Entry(ps1_pid, width=6, justify=tk.RIGHT)
        self.entry_ps_pid_p_coef_voltage.insert(0, self._ps1.get_pid_values(0)[0])
        self.entry_ps_pid_p_coef_voltage.bind("<Return>", lambda event, mode=0, index=0,
                                                               entry=self.entry_ps_pid_p_coef_voltage: self.pid_value_confirmed(
            mode, index, entry))
        self.entry_ps_pid_p_coef_voltage.bind("<FocusOut>", lambda event, mode=0, index=0,
                                                                 entry=self.entry_ps_pid_p_coef_voltage: self.pid_value_focus_out(
            mode, index, entry))
        self.entry_ps_pid_p_coef_voltage.grid(row=1, column=1, padx=2, pady=(5, 0), sticky='E')

        label_ps_pid_i_coef_voltage = tk.Label(ps1_pid, text='I')
        label_ps_pid_i_coef_voltage.grid(row=1, column=2, padx=2, pady=(5, 0), sticky='E')
        self.entry_ps_pid_i_coef_voltage = tk.Entry(ps1_pid, width=6, justify=tk.RIGHT)
        self.entry_ps_pid_i_coef_voltage.insert(0, self._ps1.get_pid_values(0)[1])
        self.entry_ps_pid_i_coef_voltage.bind("<Return>", lambda event, mode=0, index=1,
                                                               entry=self.entry_ps_pid_i_coef_voltage: self.pid_value_confirmed(
            mode, index, entry))
        self.entry_ps_pid_i_coef_voltage.bind("<FocusOut>", lambda event, mode=0, index=1,
                                                                 entry=self.entry_ps_pid_i_coef_voltage: self.pid_value_focus_out(
            mode, index, entry))
        self.entry_ps_pid_i_coef_voltage.grid(row=1, column=3, padx=2, pady=(5, 0), sticky='E')

        label_ps_pid_d_coef_voltage = tk.Label(ps1_pid, text='D')
        label_ps_pid_d_coef_voltage.grid(row=1, column=4, padx=2, pady=(5, 0), sticky='E')
        self.entry_ps_pid_d_coef_voltage = tk.Entry(ps1_pid, width=6, justify=tk.RIGHT)
        self.entry_ps_pid_d_coef_voltage.insert(0, self._ps1.get_pid_values(0)[2])
        self.entry_ps_pid_d_coef_voltage.bind("<Return>", lambda event, mode=0, index=2,
                                                               entry=self.entry_ps_pid_d_coef_voltage: self.pid_value_confirmed(
            mode, index, entry))
        self.entry_ps_pid_d_coef_voltage.bind("<FocusOut>", lambda event, mode=0, index=2,
                                                                 entry=self.entry_ps_pid_d_coef_voltage: self.pid_value_focus_out(
            mode,
            index, entry))
        self.entry_ps_pid_d_coef_voltage.grid(row=1, column=5, padx=2, pady=(5, 0), sticky='E')

        # PID POWER
        label_ps_pid_p_coef_power = tk.Label(ps1_pid, text='Power mode')
        label_ps_pid_p_coef_power.grid(row=2, column=1, padx=2, pady=(5, 0), columnspan=6, sticky='W')
        label_ps_pid_p_coef_power = tk.Label(ps1_pid, text='P')
        label_ps_pid_p_coef_power.grid(row=3, column=0, padx=2, pady=(5, 0), sticky='E')
        self.entry_ps_pid_p_coef_power = tk.Entry(ps1_pid, width=6, justify=tk.RIGHT)
        self.entry_ps_pid_p_coef_power.insert(0, self._ps1.get_pid_values(1)[0])
        self.entry_ps_pid_p_coef_power.bind("<Return>", lambda event, mode=1, index=0,
                                        entry=self.entry_ps_pid_p_coef_power: self.pid_value_confirmed(mode, index, entry))
        self.entry_ps_pid_p_coef_power.bind("<FocusOut>", lambda event, mode=1, index=0,
                                        entry=self.entry_ps_pid_p_coef_power: self.pid_value_focus_out(mode, index, entry))
        self.entry_ps_pid_p_coef_power.grid(row=3, column=1, padx=2, pady=(5, 0), sticky='E')

        label_ps_pid_i_coef_power = tk.Label(ps1_pid, text='I')
        label_ps_pid_i_coef_power.grid(row=3, column=2, padx=2, pady=(5, 0), sticky='E')
        self.entry_ps_pid_i_coef_power = tk.Entry(ps1_pid, width=6, justify=tk.RIGHT)
        self.entry_ps_pid_i_coef_power.insert(0, self._ps1.get_pid_values(1)[1])
        self.entry_ps_pid_i_coef_power.bind("<Return>", lambda event, mode=1, index=1,
                                                         entry=self.entry_ps_pid_i_coef_power: self.pid_value_confirmed(mode, index, entry))
        self.entry_ps_pid_i_coef_power.bind("<FocusOut>", lambda event, mode=1, index=1,
                                                           entry=self.entry_ps_pid_i_coef_power: self.pid_value_focus_out(mode, index, entry))
        self.entry_ps_pid_i_coef_power.grid(row=3, column=3, padx=2, pady=(5, 0), sticky='E')

        label_ps_pid_d_coef_power = tk.Label(ps1_pid, text='D')
        label_ps_pid_d_coef_power.grid(row=3, column=4, padx=2, pady=(5, 0), sticky='E')
        self.entry_ps_pid_d_coef_power = tk.Entry(ps1_pid, width=6, justify=tk.RIGHT)
        self.entry_ps_pid_d_coef_power.insert(0, self._ps1.get_pid_values(1)[2])
        self.entry_ps_pid_d_coef_power.bind("<Return>", lambda event, mode=1, index=2,
                                                         entry=self.entry_ps_pid_d_coef_power: self.pid_value_confirmed(mode, index, entry))
        self.entry_ps_pid_d_coef_power.bind("<FocusOut>", lambda event, mode=1, index=2,
                                            entry=self.entry_ps_pid_d_coef_power: self.pid_value_focus_out(mode,
                                            index, entry))
        self.entry_ps_pid_d_coef_power.grid(row=3, column=5, padx=2, pady=(5, 0), sticky='E')

        # PID CURRENT
        label_ps_pid_p_coef_power = tk.Label(ps1_pid, text='Current mode')
        label_ps_pid_p_coef_power.grid(row=4, column=1, padx=2, pady=(5, 0), columnspan=6, sticky='W')
        label_ps_pid_p_coef_current = tk.Label(ps1_pid, text='P')
        label_ps_pid_p_coef_current.grid(row=5, column=0, padx=2, pady=(5, 0), sticky='E')
        self.entry_ps_pid_p_coef_current = tk.Entry(ps1_pid, width=6, justify=tk.RIGHT)
        self.entry_ps_pid_p_coef_current.insert(0, self._ps1.get_pid_values(2)[0])
        self.entry_ps_pid_p_coef_current.bind("<Return>", lambda event, mode=2, index=0,
                                                         entry=self.entry_ps_pid_p_coef_current: self.pid_value_confirmed(mode, index,
                                                                                                                  entry))
        self.entry_ps_pid_p_coef_current.bind("<FocusOut>", lambda event, mode=2, index=0,
                                                           entry=self.entry_ps_pid_p_coef_current: self.pid_value_focus_out(mode, index, entry))
        self.entry_ps_pid_p_coef_current.grid(row=5, column=1, padx=2, pady=(5, 0), sticky='E')

        label_ps_pid_i_coef_current = tk.Label(ps1_pid, text='I')
        label_ps_pid_i_coef_current.grid(row=5, column=2, padx=2, pady=(5, 0), sticky='E')
        self.entry_ps_pid_i_coef_current = tk.Entry(ps1_pid, width=6, justify=tk.RIGHT)
        self.entry_ps_pid_i_coef_current.insert(0, self._ps1.get_pid_values(2)[1])
        self.entry_ps_pid_i_coef_current.bind("<Return>", lambda event, mode=2, index=1,
                                                         entry=self.entry_ps_pid_i_coef_current: self.pid_value_confirmed(mode, index, entry))
        self.entry_ps_pid_i_coef_current.bind("<FocusOut>", lambda event, mode=2, index=1, entry=self.entry_ps_pid_i_coef_current: self.pid_value_focus_out(mode, index, entry))
        self.entry_ps_pid_i_coef_current.grid(row=5, column=3, padx=2, pady=(5, 0), sticky='E')

        label_ps_pid_d_coef_current = tk.Label(ps1_pid, text='D')
        label_ps_pid_d_coef_current.grid(row=5, column=4, padx=2, pady=(5, 0), sticky='E')
        self.entry_ps_pid_d_coef_current = tk.Entry(ps1_pid, width=6, justify=tk.RIGHT)
        self.entry_ps_pid_d_coef_current.insert(0, self._ps1.get_pid_values(2)[2])
        self.entry_ps_pid_d_coef_current.bind("<Return>", lambda event, mode=2, index=2,
                                                         entry=self.entry_ps_pid_d_coef_current: self.pid_value_confirmed(mode, index, entry))
        self.entry_ps_pid_d_coef_current.bind("<FocusOut>", lambda event, mode=2, index=2,
                                                           entry=self.entry_ps_pid_d_coef_current: self.pid_value_focus_out(mode, index, entry))
        self.entry_ps_pid_d_coef_current.grid(row=5, column=5, padx=2, pady=(5, 0), sticky='E')

        # PS PLOT FRAME
        ps_plot_frame = tk.LabelFrame(main_frame, background=self.root['bg'], borderwidth=2, relief=tk.RIDGE,
                                   text='  PS PLOT  ')
        ps_plot_frame.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=(5, 2))
        self._m_plot_ps = MatplotlibPlot3axes(ps_plot_frame)

        self._anim = FuncAnimation(self._m_plot_ps, self._m_plot_ps.plot_waveforms_realtime,
                             fargs=(self._ps1.buffer_time, self._ps1.buffer_voltage_ps, self._ps1.buffer_power_ps,
                                    self._ps1.buffer_current_ps)
                                   , frames=10, interval=100)

        ### PS PLOT CONFGI
        ps_plot_config = tk.Frame(ps_plot_frame, background=self.root['bg'], pady=30)
        ps_plot_config.pack()

        label_ps_plot_voltage_max_limit = tk.Label(ps_plot_config, text='Voltage', fg='blue')
        label_ps_plot_voltage_max_limit.grid(row=0, column=0, padx=5, sticky='E')
        self.entry_ps_plot_voltage_max_limit = tk.Entry(ps_plot_config, width=6, justify=tk.RIGHT)
        self.entry_ps_plot_voltage_max_limit.insert(0, self._m_plot_ps.y_max_values[0])
        self.entry_ps_plot_voltage_max_limit.bind("<Return>", lambda event, ax=0,
                            entry=self.entry_ps_plot_voltage_max_limit: self.ps1_plot_y_setpoint_confirmed(ax, entry))
        self.entry_ps_plot_voltage_max_limit.bind("<FocusOut>", lambda event, ax=0,
                            entry=self.entry_ps_plot_voltage_max_limit: self.ps1_plot_y_setpoint_focus_out(ax, entry))
        self.entry_ps_plot_voltage_max_limit.grid(row=0, column=1, padx=5, sticky='E')
        label_ps_plot_voltage_max_limit_unit = tk.Label(ps_plot_config, text='V', fg='blue')
        label_ps_plot_voltage_max_limit_unit.grid(row=0, column=2, padx=5, sticky='W')

        label_ps_plot_power_max_limit = tk.Label(ps_plot_config, text='Power')
        label_ps_plot_power_max_limit.grid(row=0, column=3, padx=5, sticky='E')
        self.entry_ps_plot_power_max_limit = tk.Entry(ps_plot_config, width=6, justify=tk.RIGHT)
        self.entry_ps_plot_power_max_limit.insert(0, self._m_plot_ps.y_max_values[1])
        self.entry_ps_plot_power_max_limit.bind("<Return>", lambda event, ax=1,
                                                                     entry=self.entry_ps_plot_power_max_limit: self.ps1_plot_y_setpoint_confirmed(
            ax, entry))
        self.entry_ps_plot_power_max_limit.bind("<FocusOut>", lambda event, ax=1,
                                                                       entry=self.entry_ps_plot_power_max_limit: self.ps1_plot_y_setpoint_focus_out(
            ax, entry))
        self.entry_ps_plot_power_max_limit.grid(row=0, column=4, padx=5, sticky='E')
        label_ps_plot_power_max_limit_unit = tk.Label(ps_plot_config, text='W')
        label_ps_plot_power_max_limit_unit.grid(row=0, column=5, padx=5, sticky='W')

        label_ps_plot_current_max_limit = tk.Label(ps_plot_config, text='Current', fg='red')
        label_ps_plot_current_max_limit.grid(row=0, column=6, padx=5, sticky='E')
        self.entry_ps_plot_current_max_limit = tk.Entry(ps_plot_config, width=6, justify=tk.RIGHT)
        self.entry_ps_plot_current_max_limit.insert(0, self._m_plot_ps.y_max_values[2])
        self.entry_ps_plot_current_max_limit.bind("<Return>", lambda event, ax=2,
                                                                   entry=self.entry_ps_plot_current_max_limit: self.ps1_plot_y_setpoint_confirmed(
            ax, entry))
        self.entry_ps_plot_current_max_limit.bind("<FocusOut>", lambda event, ax=2,
                                                                     entry=self.entry_ps_plot_current_max_limit: self.ps1_plot_y_setpoint_focus_out(
            ax, entry))
        self.entry_ps_plot_current_max_limit.grid(row=0, column=7, padx=5, sticky='E')
        label_ps_plot_current_max_limit_unit = tk.Label(ps_plot_config, text='mA', fg='red')
        label_ps_plot_current_max_limit_unit.grid(row=0, column=8, padx=5, sticky='W')

        # PULSER FRAME
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
        self.entry_pulser_frequency.insert(0, self._pulser.frequency)
        label_pulser_frequency_units = tk.Label(pulser_frame, text="Hz", background=self.root['bg'])
        label_pulser_frequency_units.grid(row=2, column=2, padx=5, pady=(5, 0), sticky='W')

        label_channel1 = tk.Label(pulser_frame, text="Pulse shape", background=self.root['bg'])
        label_channel1.grid(row=3, column=0, padx=5, pady=(5, 0), sticky='E')

        self.text_pulser_shape = tk.Text(pulser_frame, width=10, height=6, font='TkDefaultFont')
        self.text_pulser_shape.grid(row=3, column=1, padx=5, pady=(5, 0), sticky='E')
        for s in self._pulser.pulse_shape:
            self.text_pulser_shape.insert(tk.INSERT, s + '\n')  # fill text by actual value from pulser
        label_pulser_shape_units = tk.Label(pulser_frame, text="\u00B5s", background=self.root['bg'])
        label_pulser_shape_units.grid(row=3, column=2, padx=5, pady=(5, 0), sticky='W')

        self.scrollbar_pulser_shape = tk.Scrollbar(pulser_frame, command=self.text_pulser_shape.yview)
        self.scrollbar_pulser_shape.grid(row=3, column=1, padx=5, pady=(5, 0), sticky='NSE')
        self.text_pulser_shape['yscrollcommand'] = self.scrollbar_pulser_shape.set
        self.button_pulser_set_shape = tk.Button(pulser_frame, text="Set shape", relief=tk.GROOVE,
                                                 command=self.pulser_shape)
        self.button_pulser_set_shape.grid(row=4, column=1, padx=5, pady=(5, 0))

        self.toggleButton_pulser_activate_ch2 = ToggleButton(pulser_frame, text="Enable channel 2",
                                                             command=self.pulser_activate_ch2, ind_height=12)
        self.toggleButton_pulser_activate_ch2.grid(row=5, column=0, columnspan=2, padx=5, pady=(5, 0))
        self.toggleButton_pulser_activate_ch2.on = self._pulser.ch2_enabled

        self.indicator_pulser_ch1_output = Indicator(pulser_frame, 'Channel 1 output')
        self.indicator_pulser_ch1_output.grid(row=6, column=0, columnspan=2, padx=5)

        self.indicator_pulser_ch2_output = Indicator(pulser_frame, 'Channel 2 output')
        self.indicator_pulser_ch2_output.grid(row=7, column=0, columnspan=2, padx=5)

        # PULSER PLOT
        plot_frame = tk.LabelFrame(main_frame, background=self.root['bg'], borderwidth=2, relief=tk.RIDGE,
                                   text='  PULSER PLOT  ')
        plot_frame.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=(5, 2))
        self._m_plot_pulser = MatplotlibPlot1axes(plot_frame)
        self.scale_plot = tk.Scale(plot_frame, orient=tk.HORIZONTAL, from_=1, to=100,
                                   command=self.plot_change_scale, background=self.root['bg'])
        self.scale_plot.set(100)
        self.scale_plot.pack()
        t, wf1, wf2 = self._pulser.get_waveforms()
        self._m_plot_pulser.plot_waveforms(t, wf1, wf2, self._pulser.ch2_enabled, self._pulser.get_period(),
                                   self.scale_plot.get())

        # search for special key press (F1, F2, ...) and modify pulse shape accordingly
        for s in self._config['Pulser']:   # look for preset pulse shapes
            if s[0:6] == 'preset':  # if preset found
                key = s[7:9]        # decode key from preset string
                self.root.bind_all("<{:s}>".format(key).upper(), self.pulser_special_key_press)  # register key callback

    # connect or disconnect DC1 power supply
    def ps1_connect(self):
        if not self._ps1.connected:
            try:
                self._ps1.connect(self._config['DC1']['resource_id'])
            except Exception as e:
                messagebox.showerror('Error', 'Connection to IT6726V failed\n\n' + str(e))
            finally:
                self.indicator_ps1_connected.on = self._ps1.connected
                self._ps1.inst.write("*CLS")     # clean the PS register
                self._ps1.inst.write("*RST")     # set the PS default settings
                self._ps1.inst.write("CURR:LEVel 0")  # set the PS default settings
                self._ps1.inst.write("VOLT:PROT " + str(self._over_voltage_protection))
        else:
            self.ps1_stop()
            self._ps1.disconnect()
            self.indicator_ps1_output.on = self._ps1.status['outputON']
            self.indicator_ps1_connected.on = self._ps1.connected
            # turn off the corresponding indicators
            self.indicator_ps1_voltage_regime.on = False
            self.indicator_ps1_power_regime.on = False
            self.indicator_ps1_current_regime.on = False
            self.indicator_ps1_current_regime.on = False

    # periodic update of U, P, I values in GUI; running in a thread
    def ps1_periodic_update(self):
        while self._ps1.output:
            # take the last value from the corresponding buffers
            self.label_ps1_voltage_live.config(text=str(round(self._ps1.buffer_voltage_ps[-1])))
            self.label_ps1_power_live.config(text=str(round(self._ps1.buffer_power_ps[-1])))
            self.label_ps1_current_live.config(text=str(round(self._ps1.buffer_current_ps[-1])))
            # activate the corresponding indicator based on the actual mode
            if self._ps1.mode == 0:
                self.indicator_ps1_voltage_regime.on = True
                self.indicator_ps1_power_regime.on = False
                self.indicator_ps1_current_regime.on = False
            elif self._ps1.mode == 1:
                self.indicator_ps1_voltage_regime.on = False
                self.indicator_ps1_power_regime.on = True
                self.indicator_ps1_current_regime.on = False
            elif self._ps1.mode == 2:
                self.indicator_ps1_voltage_regime.on = False
                self.indicator_ps1_power_regime.on = False
                self.indicator_ps1_current_regime.on = True
            time.sleep(0.2)

    def ps1_setpoint_focus_out(self, mode, entry):
        float_new_value = 0.0
        try:
            float_new_value = float(entry.get())
        except ValueError as e:
            messagebox.showerror('Error', str(e))
            entry.config(fg='red')
        if not np.isclose(float_new_value, float(self._ps1.setpoints[mode])):
            entry.config(fg='red')
        else:
            entry.config(fg='black')

    def ps1_setpoint_confirmed(self, mode, entry):
        try:
            new_value = entry.get()
            self._ps1.set_setpoint_for_mode(mode, new_value)
            entry.config(fg='black')
        except ValueError as e:
            messagebox.showerror('Error', str(e))

    def pid_value_confirmed(self, pid_values, index, entry):
        try:
            new_value = entry.get()
            self._ps1.set_pid_values(pid_values, index, new_value)
            entry.config(fg='black')
        except ValueError as e:
            messagebox.showerror('Error', str(e))

    def pid_value_focus_out(self, mode, index, entry):
        float_new_value = 0.0
        try:
            float_new_value = float(entry.get())
        except ValueError as e:
            messagebox.showerror('Error', str(e))
            entry.config(fg='red')
        if not np.isclose(float_new_value, float(self._ps1.get_pid_values(mode)[index])):
            entry.config(fg='red')
        else:
            entry.config(fg='black')

    def ps1_toggle_output(self):
        self._ps1.output = not self._ps1.output
        self.indicator_ps1_output.on = self._ps1.status['outputON']
        if not self._ps1.output:
            self._ps1.mode = 1 # initial mode is Power mode
            self.indicator_ps1_voltage_regime.on = False
            self.indicator_ps1_power_regime.on = False
            self.indicator_ps1_current_regime.on = False
        if self._ps1.output:
            self._ps1.clear_buffers()
            threading.Thread(target=self.ps1_periodic_update).start()

    def ps1_plot_y_setpoint_confirmed(self, ax_number, entry):
        # new max y value for axis in PS plot
        try:
            new_value = entry.get()
            self._m_plot_ps.set_y_max_values(ax_number, new_value)
            entry.config(fg='black')
        except ValueError as e:
            messagebox.showerror('Error', str(e))

    def ps1_plot_y_setpoint_focus_out(self, ax_number, entry):
        float_new_value = 0.0
        try:
            float_new_value = float(entry.get())
        except ValueError as e:
            messagebox.showerror('Error', str(e))
            entry.config(fg='red')
        if not np.isclose(float_new_value, float(self._m_plot_ps.y_max_values[ax_number])):
            entry.config(fg='red')
        else:
            entry.config(fg='black')

    def ps1_stop(self):
        self._ps1.output = False

    def pulser_connect(self):
        if not self._pulser.connected:
            try:
                self._pulser.connect('USB0::6833::1601::DG4E223201180::0::INSTR')
                self._pulser.initialization()
            except Exception as e:
                messagebox.showerror('Error', 'Connection to RigolDG4102 failed\n\n' + str(e))
            finally:
                self.indicator_pulser_connected.on = self._pulser.connected
        else:
            self.pulser_stop()
            self._pulser.disconnect()
            self.indicator_pulser_connected.on = self._pulser.connected

    def pulser_frequency_modified(self, event):
        # check if new value is different from instrument value
        try:
            new_value = int(event.widget.get())
            value = self._pulser.frequency
            # pulser instance to get the value stored in pulser class instance
            if new_value != value:
                event.widget.config(fg='red')
            else:
                event.widget.config(fg='black')
        except ValueError:
            event.widget.config(fg='red')

    def pulser_frequency_confirmed(self, event):
        try:
            self._pulser.frequency = event.widget.get()
            event.widget.config(fg='black')
            t, wf1, wf2 = self._pulser.get_waveforms()
            self._m_plot_pulser.plot_waveforms(t, wf1, wf2, self._pulser.ch2_enabled, self._pulser.get_period(),
                                       self.scale_plot.get())
        except ValueError as e:
            messagebox.showerror('Error', str(e))

    def pulser_activate_ch2(self):
        self._pulser.ch2_enabled = self.toggleButton_pulser_activate_ch2.on
        t, wf1, wf2 = self._pulser.get_waveforms()
        self._m_plot_pulser.plot_waveforms(t, wf1, wf2, self._pulser.ch2_enabled, self._pulser.get_period(),
                                   self.scale_plot.get())
        self.indicator_pulser_ch2_output.on = self._pulser.output and self._pulser.ch2_enabled

    def pulser_shape(self):
        self._pulser.pulse_shape = self.text_pulser_shape.get("1.0", 'end').split()
        t, wf1, wf2 = self._pulser.get_waveforms()
        self._m_plot_pulser.plot_waveforms(t, wf1, wf2, self._pulser.ch2_enabled, self._pulser.get_period(),
                                   self.scale_plot.get())

    def pulser_toggle_output(self):
        self._pulser.output = not self._pulser.output
        self.indicator_pulser_ch1_output.on = self._pulser.output
        self.indicator_pulser_ch2_output.on = self._pulser.output and self._pulser.ch2_enabled

    def pulser_stop(self):
        self._pulser.output = False
        self.indicator_pulser_ch1_output.on = self._pulser.output
        self.indicator_pulser_ch2_output.on = self._pulser.output and self._pulser.ch2_enabled

    def pulser_special_key_press(self, event):
        # change the pulse shape based on the pressed special key (F1, F2, F3)
        self.text_pulser_shape.delete('1.0', 'end')
        for s in self._config['Pulser']['preset_{:s}'.format(event.keysym).lower()].split(','):
            self.text_pulser_shape.insert(tk.INSERT, s + '\n')  # fill text by actual value from pulser

    def plot_change_scale(self, value):
        value = int(value)
        self._m_plot_pulser.set_x_lim(self._pulser.get_period(), value)
        self._m_plot_pulser.canvas.draw()  # show the canvas at the screen

    def on_closing(self):
        self.pulser_stop()   # stop pulsing
        # save state to config
        setpoints = self._ps1.setpoints
        self._config.set('DC1', 'setpoint_voltage', str(setpoints[0]))
        self._config.set('DC1', 'setpoint_power', str(setpoints[1]))
        self._config.set('DC1', 'setpoint_current', str(setpoints[2]))
        self._config.set('DC1', 'p_voltage', str(self._ps1.get_pid_values(0)[0]))
        self._config.set('DC1', 'i_voltage', str(self._ps1.get_pid_values(0)[1]))
        self._config.set('DC1', 'd_voltage', str(self._ps1.get_pid_values(0)[2]))
        self._config.set('DC1', 'p_power', str(self._ps1.get_pid_values(1)[0]))
        self._config.set('DC1', 'i_power', str(self._ps1.get_pid_values(1)[1]))
        self._config.set('DC1', 'd_power', str(self._ps1.get_pid_values(1)[2]))
        self._config.set('DC1', 'p_current', str(self._ps1.get_pid_values(2)[0]))
        self._config.set('DC1', 'i_current', str(self._ps1.get_pid_values(2)[1]))
        self._config.set('DC1', 'd_current', str(self._ps1.get_pid_values(2)[2]))

        self._config.set('DC1 - plot', 'max_voltage', str(self._m_plot_ps.y_max_values[0]))
        self._config.set('DC1 - plot', 'max_power', str(self._m_plot_ps.y_max_values[1]))
        self._config.set('DC1 - plot', 'max_current', str(self._m_plot_ps.y_max_values[2]))

        self._config.set('Pulser', 'frequency', str(self._pulser.frequency))
        self._config.set('Pulser', 'pulse_shape', ','.join(self.text_pulser_shape.get("1.0", 'end').split()))
        self._config.set('Pulser', 'ch2_enabled', str(self._pulser.ch2_enabled))

        config_path = os.path.join(os.path.dirname(__file__), 'hupulser.ini')
        # with open('hupulser.ini', 'w') as config_file: # Linux version
        with open(config_path, 'w') as config_file:
            self._config.write(config_file)
        self.root.destroy()
