from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg)
from matplotlib.figure import Figure
import matplotlib.ticker as ticker
import configparser
from tkinter import messagebox
import os


# class for plotting the entered data using Matplotlib
class MatplotlibPlotBase:
    def __init__(self, master, size_x, size_y):     # initialization
        self._f = Figure()
        self._f.patch.set_facecolor('#f5f5f5')       # set color of the Figure
        self._f.set_size_inches(size_x, size_y)
        self.canvas = FigureCanvasTkAgg(self._f, master=master)  # set the canvas
        self.canvas.get_tk_widget().pack()  # position the canvas in GUI


class MatplotlibPlot1axes(MatplotlibPlotBase):
    def __init__(self, master):     # initialization
        super().__init__(master, size_x=4, size_y=2.5)
        self._ax = self._f.add_axes([0.12, 0.2, 0.8, 0.75])             # add axes

    def plot_waveforms(self, t, wf1, wf2, ch2_state, period, scale):
        self._ax.clear()  # clear the previous plot
        self.set_x_lim(period, scale)  # set x limits taking into account the current scale value
        self._ax.set_xlabel('Time [$\\mathrm{\\mu s}$]')  # set x label
        self._ax.set_ylabel('Amplitude')  # set y label
        self._ax.plot(t, wf1, color='red')  # plot the wave form of the negative pulse using a red color
        if ch2_state:  # when CH2 is enabled
            self._ax.plot(t, wf2, color='blue')  # plot the wave form of the positive pulse using a blue color
        self._ax.set_ylim(-0.2, 1.2)
        self._ax.set_yticks([0, 1])
        self.canvas.draw()  # show the canvas at the screen

    def set_x_lim(self, period, scale):
        max_value = period/100*scale
        x_offset = max_value/10
        self._ax.set_xlim(-x_offset, period/100*scale + x_offset)


class MatplotlibPlot3axes(MatplotlibPlotBase):
    def __init__(self, master):  # initialization
        super().__init__(master, size_x=5, size_y=2.5)
        self._ax1 = self._f.add_axes([0.125, 0.2, 0.615, 0.75])  # add axes
        self._ax2 = self._ax1.twinx()
        self._ax3 = self._ax1.twinx()
        self._y_max_values = [0.0, 0.0, 0.0]  # (Ax1, Ax2, Ax3)
        self.config = configparser.ConfigParser()
        # self._config.read('hupulser.ini') # Linux version
        config_path = os.path.join(os.path.dirname(__file__), 'hupulser.ini')
        self.config.read(config_path)
        try:
            self.set_y_max_values(0, self.config['DC1 - plot']['max_voltage'])
            self.set_y_max_values(1, self.config['DC1 - plot']['max_power'])
            self.set_y_max_values(2, self.config['DC1 - plot']['max_current'])
        except KeyError:  # key Pulser not found in config (no config present)
            messagebox.showinfo('Info', 'Max values for plots were not found in ini file.')

    @property
    def y_max_values(self):
        return self._y_max_values

    def set_y_max_values(self, ax_number, value):
        try:
            int_ax_number = int(ax_number)
        except ValueError:
            raise ValueError('Axes number must be an integer')
        if int_ax_number < 0 or int_ax_number > 2:
            raise ValueError('Axes number must be between 0 and 2 (0 = Ax1, 1 = Ax2, 2 = Ax3')
        try:
            float_value = float(value)
        except ValueError:
            raise ValueError('Max value for each axis must be a number')
        if float_value < 0 or float_value > 2000:
            raise ValueError('Max value for each axes must be than 2000')
        else:
            self._y_max_values[int_ax_number] = float_value

    def plot_waveforms_realtime(self, iter_number, time, voltage, power, current, voltage_ps, power_ps):
        self._ax1.clear()  # clear the previous plot
        self._ax2.clear()  # clear the previous plot
        self._ax3.clear()  # clear the previous plot
        self.make_patch_spines_invisible(self._ax2)
        self._ax2.spines["right"].set_visible(True)

        self._ax1.set_xlabel('Time (s)')  # set x label
        self._ax1.set_ylabel('Voltage (V)')  # set y label
        self._ax2.set_ylabel('Power (W)')  # set y label
        self._ax3.set_ylabel('Current (mA)')  # set y label
        p1, = self._ax1.plot(time, voltage,
                                color='blue')  # plot the wave form of the negative pulse using a red color
        p1, = self._ax1.plot(time, voltage_ps, color='blue',
                                linestyle="dashed")  # plot the wave form of the negative pulse using a red color
        p2, = self._ax2.plot(time, power,
                                color='black')  # plot the wave form of the negative pulse using a red color
        p2, = self._ax2.plot(time, power_ps, color='black', linestyle="dashed")
        p3, = self._ax3.plot(time, current,
                                color='red')  # plot the wave form of the negative pulse using a red color
        self._ax1.yaxis.label.set_color(p1.get_color())
        self._ax2.yaxis.label.set_color(p2.get_color())
        self._ax3.yaxis.label.set_color(p3.get_color())
        self._ax3.spines['right'].set_position(('outward', 45))  # Move Target current axis to right

        self._ax1.tick_params(axis='y', colors=p1.get_color())
        self._ax1.tick_params(which='minor', axis='y', colors=p1.get_color())
        self._ax2.tick_params(axis='y', colors=p2.get_color())
        self._ax2.tick_params(which='minor', axis='y', colors=p2.get_color())
        self._ax3.tick_params(axis='y', colors=p3.get_color())
        self._ax3.tick_params(which='minor', axis='y', colors=p3.get_color())
        self._ax1.tick_params(axis='x')

        self._ax2.set_zorder(2)  # default zorder is 0 for ax1 and ax2
        self._ax2.patch.set_visible(False)  # prevents ax1 from hiding ax2
        self._ax1.set_zorder(1)  # default zorder is 0 for ax1 and ax2
        self._ax1.patch.set_visible(False)  # prevents ax1 from hiding ax2

        self._ax1.set_ylim(0, self._y_max_values[0])
        self._ax2.set_ylim(0, self._y_max_values[1])
        self._ax3.set_ylim(0, self._y_max_values[2])
        self._ax1.xaxis.set_major_locator(ticker.MultipleLocator(1))
        self._ax1.xaxis.set_minor_locator(ticker.MultipleLocator(0.5))

    def make_patch_spines_invisible(self, ax):
        ax.set_frame_on(True)
        ax.patch.set_visible(False)
        for sp in ax.spines.values():
            sp.set_visible(False)