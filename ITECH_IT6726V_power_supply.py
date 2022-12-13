import pyvisa
import time
import threading
import usb
import configparser
from data_buffer import DataBuffer
from tkinter import messagebox


# DC power supply ITECH_IT6726V
class ItechIT6726VPowerSupply:
    def __init__(self):
        self._mode = 1  # first mode after start is Power mode
        self._setpoint = [0.0, 0.0, 0.0]  # (U, P, I)
        self._setpoint_max = (3000, 1200, 5000)  # max U, P, I according to power supply
        self._output = 0    # no output voltage after start
        self._connected = False     # connection with PS
        self._inst = None   # representation of the PS for read/write commands
        self._status = {'outputON': False}
        self._thread = None
        self.config = configparser.ConfigParser()
        self.config.read('hupulser.ini')    # read file with initial settings
        try:
            # number of values in the buffer; used for storing the data and for plotting
            self._buffer_no_elements = int(self.config['DC1']['buffer_size'])
        except KeyError:
            messagebox.showinfo('Info', 'Size of buffer not found in ini file. Taking standard value of 10 values.')
            self._buffer_no_elements = 10
        try:
            # number of last values used for a filter (average value) to determine mode
            self._mode_determination_no_of_values = int(self.config['DC1']['mode_determination_no_of_values'])
        except KeyError:
            messagebox.showinfo('Info', 'Number of last values for averaging for mode determination not found in ini '
                                        'file. Taking standard value of 5.')
            self._mode_determination_no_of_values = 5
        # initialization of individual buffers
        self._buffer_time = DataBuffer(self._buffer_no_elements)
        self._buffer_voltage_calc = DataBuffer(self._buffer_no_elements)
        self._buffer_voltage_ps = DataBuffer(self._buffer_no_elements)
        self._buffer_power_ps = DataBuffer(self._buffer_no_elements)
        self._buffer_current_ps = DataBuffer(self._buffer_no_elements)
        # initialization of PID values for voltage, power and current mode
        self._pid_values_voltage = [0.0, 0.0, 0.0]  # (P, I, D)
        self._pid_values_power = [0.0, 0.0, 0.0]  # (P, I, D)
        self._pid_values_current = [0.0, 0.0, 0.0]  # (P, I, D)
        # initialization of the sleep time in the main pid loop
        self._pid_sleep_time = 0
        # initialization of the max and min voltage values used in the PID loop
        self._over_voltage_protection = 0
        self._under_voltage_protection = 0
        try:
            # load the saved values from the ini file
            self.set_pid_values(0, 0, self.config['DC1']['p_voltage'])
            self.set_pid_values(0, 1, self.config['DC1']['i_voltage'])
            self.set_pid_values(0, 2, self.config['DC1']['d_voltage'])
            self.set_pid_values(1, 0, self.config['DC1']['p_power'])
            self.set_pid_values(1, 1, self.config['DC1']['i_power'])
            self.set_pid_values(1, 2, self.config['DC1']['d_power'])
            self.set_pid_values(2, 0, self.config['DC1']['p_current'])
            self.set_pid_values(2, 1, self.config['DC1']['i_current'])
            self.set_pid_values(2, 2, self.config['DC1']['d_current'])
            self._pid_sleep_time = float(self.config['DC1']['pid_sleep_time'])
        except KeyError:  # key Pulser not found in config (no config present)
            messagebox.showinfo('Info', 'PID values were not found in ini file.')
        try:
            self._pid_sleep_time = float(self.config['DC1']['pid_sleep_time'])
            self._over_voltage_protection = float(self.config['DC1']['over_voltage_protection'])
            self._under_voltage_protection = float(self.config['DC1']['under_voltage_protection'])
        except KeyError:  # key Pulser not found in config (no config present)
            messagebox.showinfo('Info', 'PID sleep time, OVP or UVP value were not found in ini file.')

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value):
        try:
            int_value = int(value)
        except ValueError:
            raise ValueError('Mode value must be an integer')
        if int_value < 0 or int_value > 2:
            raise ValueError('Mode value must be between 0 and 2 (0 = P mode, 1 = U mode, 2 = I mode')
        self._mode = int_value

    @property
    def setpoints(self):
        return self._setpoint

    def get_setpoints(self):
        return self._setpoint

    def set_setpoint_for_mode(self, mode, value):
        try:
            int_mode = int(mode)
        except ValueError:
            raise ValueError('Mode value must be an integer')
        if int_mode < 0 or int_mode > 2:
            raise ValueError('Mode value must be between 0 and 2 (0 = P mode, 1 = U mode, 2 = I mode')
        else:
            try:  # check new value
                int_value = int(value)
            except ValueError:
                raise ValueError('Setpoint value must be an integer')
            if int_value < 0 or int_value > self._setpoint_max[int_mode]:
                raise ValueError('Setpoint value must be between 0 and ' + str(self._setpoint_max[int_mode]))
            else:
                self._setpoint[int_mode] = int_value

    @property
    def inst(self):
        return self._inst

    @property
    def buffer_time(self):
        return self._buffer_time.buffer

    @property
    def buffer_voltage(self):
        return self._buffer_voltage_calc.buffer

    @property
    def buffer_voltage_ps(self):
        return self._buffer_voltage_ps.buffer

    @property
    def buffer_power(self):
        return self._buffer_power_ps.buffer

    @property
    def buffer_current(self):
        return self._buffer_current_ps.buffer

    @property
    def buffer_power_ps(self):
        return self._buffer_power_ps.buffer

    def get_pid_values(self, mode):
        # return PID values for the current mode
        if mode == 0:
            return self._pid_values_voltage
        elif mode == 1:
            return self._pid_values_power
        elif mode == 2:
            return self._pid_values_current
        else:
            raise ValueError('Mode for PID must be 1 (Power) or 2 (Current).')

    def set_pid_values(self, mode, index, new_value):
        try:
            int_index = int(index)
        except ValueError:
            raise ValueError('Axes number must be an integer')
        if int_index < 0 or int_index > 2:
            raise ValueError('PID number index must be between 0 and 2 (0 = P, 1 = I, 2 = D')
        try:
            float_value = float(new_value)
        except ValueError:
            raise ValueError('Max value for each axis must be a number')
        if mode == 0:
            self._pid_values_voltage[index] = float_value
        elif mode == 1:
            self._pid_values_power[index] = float_value
        elif mode == 2:
            self._pid_values_current[index] = float_value
        else:
            raise ValueError('Mode for PID must be 1 (Power) or 2 (Current).')

    def pid_control(self, p_voltage, i_voltage, d_voltage, p_power, i_power, d_power, p_current, i_current, d_current):
        e_sum = 0
        actual_value = 0
        u_prev = 0
        e_prev = 0

        avg_buffer_voltage_ps = 0
        avg_buffer_power_ps = 0
        avg_buffer_current_ps = 0

        time_start = time.time()  # get the actual epoch time in seconds
        time_prev = time.time() - time_start    # calculate the initial time
        # take the initial error of the controlled value (SETPOINT - 0 = SETPOINT) based on the selected mode
        if self.mode == 0:
            e_prev = self.get_setpoints()[self.mode]
        elif self.mode == 1:
            e_prev = self.get_setpoints()[self.mode]
        elif self.mode == 2:
            e_prev = self.get_setpoints()[self.mode]
        mode_prev = self.mode   # keep the initial mode value
        # time.sleep(0.05)

        while self._status['outputON']:     # until output is not turned off
            voltage_ps, power_ps, current_ps = self.read_actual_value_for_pid()
            self._mode = self.mode_determination(avg_buffer_voltage_ps, avg_buffer_power_ps, avg_buffer_current_ps, mode_prev)
            if not mode_prev == self.mode:  # if the mode was changed
                e_sum = u_prev
            if self.mode == 0:  # voltage mode
                actual_value = voltage_ps
                time_prev, e_prev, e_sum, u_prev = self.pid_control_one_cycle(time_start, time_prev, e_prev,
                                                                                e_sum, p_voltage, i_voltage,
                                                                                d_voltage, actual_value,
                                                                                self.get_setpoints()[self.mode])
            if self.mode == 1:  # power mode
                actual_value = power_ps
                time_prev, e_prev, e_sum, u_prev = self.pid_control_one_cycle(time_start, time_prev, e_prev,
                                                                        e_sum, p_power, i_power, d_power, actual_value,
                                                                        self.get_setpoints()[self.mode])
            if self.mode == 2:  # current mode
                actual_value = current_ps
                time_prev, e_prev, e_sum, u_prev = self.pid_control_one_cycle(time_start, time_prev, e_prev,
                                                                        e_sum, p_current, i_current, d_current,
                                                                        actual_value, self.get_setpoints()[self.mode])

            self.add_values_to_buffers(time_prev, u_prev, voltage_ps, power_ps, current_ps)
            avg_buffer_voltage_ps, avg_buffer_power_ps, avg_buffer_current_ps = \
                            self.calculate_average_values_for_mode_determination(self._mode_determination_no_of_values)
            mode_prev = self.mode   # keep the actual mode for the next run
            time.sleep(self._pid_sleep_time)    # allow the PS voltage to react on the request

    def pid_control_one_cycle(self, time_start, time_prev, e_prev, e_sum, p, i, d, actual_value, desired_value):
        e = desired_value - actual_value  # calculate the actual error of the power (P element)
        time_act = time.time() - time_start  # get the actual time in seconds
        dt = time_act - time_prev  # calculate the time duration of the cycle
        e_sum = e_sum + e * dt  # calculate the integral of the power error (I element)
        dedt = (e - e_prev) / dt  # calculate time derivation of the power error (D element)
        time_prev = time_act  # keep the actual time for the next cycle
        e_prev = e  # keep the actual error for the next cycle
        u = p * e + i * e_sum + d * dedt  # calculate the new voltage value
        u = round(u, 1)     # round the value
        if u < self._under_voltage_protection:
            u = self._under_voltage_protection
        if u > self._over_voltage_protection:
            u = self._over_voltage_protection
        self._inst.write("VOLT " + str(u))  # send the new voltage value to the PS
        u_prev = u  # keep the actual voltage
        return time_prev, e_prev, e_sum, u_prev

    def read_actual_value_for_pid(self):
        # read actual values from the PS
        value_voltage_ps = 0
        value_power_ps = 0
        value_current_ps = 0
        try:
            value_voltage_ps = float(self._inst.query("MEASure:VOLTage?"))  # get the actual voltage of the PS
            value_power_ps = float(self._inst.query("MEASure:POWEr?"))  # get the actual power of the PS
            value_current_ps = float(self._inst.query("MEASure:CURRent?")) * 1000 # get the actual current of the PS in mA
        except usb.core.USBError as exc:
            print("Communication issue - error : {}".format(exc.strerror))
        return value_voltage_ps, value_power_ps, value_current_ps

    def add_values_to_buffers(self, process_time, voltage_calc, voltage_ps, power_ps, current_ps):
        self._buffer_time.update(process_time)
        self._buffer_voltage_calc.update(voltage_calc)
        self._buffer_voltage_ps.update(voltage_ps)
        self._buffer_power_ps.update(power_ps)
        self._buffer_current_ps.update(current_ps)

    def clear_buffers(self):
        self._buffer_time.clear()
        self._buffer_voltage_calc.clear()
        self._buffer_voltage_ps.clear()
        self._buffer_power_ps.clear()
        self._buffer_current_ps.clear()

    def calculate_average_values_for_mode_determination(self, n):
        avg_voltage_ps = self._buffer_voltage_ps.average_value_from_last_n_values(n)
        avg_power_ps = self._buffer_power_ps.average_value_from_last_n_values(n)
        avg_current_ps = self._buffer_current_ps.average_value_from_last_n_values(n)
        return avg_voltage_ps, avg_power_ps, avg_current_ps

    def mode_determination(self, avg_voltage_ps, avg_power_ps, avg_current_ps, mode_prev):
        voltage_max = round(self.get_setpoints()[0])
        power_max = round(self.get_setpoints()[1])
        current_max = round(self.get_setpoints()[2])
        avg_voltage_ps = round(avg_voltage_ps)
        avg_power_ps = round(avg_power_ps)
        avg_current_ps = round(avg_current_ps)
        mode = mode_prev

        if avg_voltage_ps >= voltage_max:
            mode = 0
        elif avg_power_ps >= power_max:
            mode = 1
        elif avg_current_ps >= current_max:
            mode = 2

        if mode == 0 and (avg_power_ps > power_max):
            mode = 1
        elif mode == 0 and (avg_current_ps > current_max):
            mode = 2

        if mode == 1 and (avg_voltage_ps > voltage_max):
            mode = 0
        elif mode == 1 and (avg_current_ps > current_max):
            mode = 2

        if mode == 2 and (avg_voltage_ps > voltage_max):
            mode = 0
        elif mode == 2 and (avg_power_ps > power_max):
            mode = 1
        return mode

    @property
    def output(self):
        return self._status['outputON']

    @output.setter
    def output(self, value):
        if self._connected:
            if value:   # switch power supply ON
                self._inst.write(":OUTPut ON")  # output voltage ON
                self._status['outputON'] = True
                # get the actual PID values
                p_voltage = self.get_pid_values(0)[0]
                i_voltage = self.get_pid_values(0)[1]
                d_voltage = self.get_pid_values(0)[2]
                p_power = self.get_pid_values(1)[0]
                i_power = self.get_pid_values(1)[1]
                d_power = self.get_pid_values(1)[2]
                p_current = self.get_pid_values(2)[0]
                i_current = self.get_pid_values(2)[1]
                d_current = self.get_pid_values(2)[2]
                # start new thread with PID regulation!!!
                threading.Thread(target=self.pid_control, args=(p_voltage, i_voltage, d_voltage, p_power, i_power,
                                                                d_power, p_current, i_current, d_current)).start()
            else:       # output voltage OFF
                self._inst.write(":OUTPut OFF")
                self._status['outputON'] = False    # change the status (output ON/OFF)

    @property
    def status(self):
        return self._status

    @property
    def connected(self):
        return self._connected

    def connect(self, visa_resource_id):
        rm = pyvisa.ResourceManager('@py')
        rm.list_resources()
        # connect to a specific instrument
        self._inst = rm.open_resource(visa_resource_id, timeout=1000, resource_pyclass=pyvisa.resources.USBInstrument)
        self._connected = True

    def disconnect(self):
        if self._output:
            self.output = False  # stop output
        self._inst.close()
        self._connected = False
