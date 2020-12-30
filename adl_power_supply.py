import struct
import pyvisa
from crccheck.crc import Crc16Modbus


# DC power supply from ADL
class ADLPowerSupply:
    def __init__(self):
        self._address = 0
        self._mode = 0
        self._setpoint = [0, 0, 0]  # (P, U, I)
        self._setpoint_max = (1000, 1000, 1000)  # (P, U, I)
        self._mode_f_code = (11, 9, 10)  # function code for setting mode and setpoint (P, U, I)
        self._power = 0
        self._voltage = 0
        self._current = 0
        self._output = 0
        self._connected = False
        self._inst = None
        self._status = {'activeToggle': False, 'interlock': True, 'remote': True, 'setpointOK': True, 'mainsON': False,
                        'outputON': False, 'plasmaON': False, 'modeP': True, 'modeU': False, 'modeI': False,
                        'ramp': False, 'jouleMode': False, 'jouleLimit': False, 'pulseON': False, 'error': False,
                        'commandError': False, 'watchdogError': False, 'commandErrorCode': 0}
        # msg = b'\x00\x0b\x1d\x01\x00\x3a\x98\x00\x00\x00\x00\x00\x00\x42\x3b\x0d'

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
        if self._connected:
            # send new mode, this updates status bytes
            self.__send_command_and_read(self._mode_f_code[int_value],
                                         (self._setpoint[int_value], 0, 0, 0))
            if (int_value == 0 and not self._status['modeP']) or (int_value == 1 and not self._status['modeU']) or \
                    (int_value == 2 and not self._status['modeI']):
                raise ValueError('Setpoint readback does not match sent value')
        self._mode = int_value

    @property
    def setpoint(self):
        return self._setpoint[self._mode]

    @setpoint.setter
    def setpoint(self, value):
        try:
            int_value = int(value)
        except ValueError:
            raise ValueError('Setpoint value must be an integer')
        if int_value < 0 or int_value > self._setpoint_max[self._mode]:
            raise ValueError('Setpoint value must be between 0 and ' + str(self._setpoint_max[self._mode]))
        if self._connected:
            data = self.__send_command_and_read(self._mode_f_code[self._mode], (int_value, 0, 0, 0))
            if data[0] != int_value:   # check setpoint value sent back equals the desired value
                raise ValueError('Setpoint readback does not match sent value')
        self._setpoint[self._mode] = int_value  # if not connected set value into virtual instrument anyway

    def get_setpoints(self):
        return self._setpoint

    def set_setpoints(self, P, U, I):
        self._setpoint = [P, U, I]

    @property
    def output(self):
        return self._status['outputON']

    @output.setter
    def output(self, value):
        if self._connected:
            if value:   # switch power supply ON
                self.__send_command_and_read(1, (0, 0, 0, 0))
            else:       # switch power supply OFF
                self.__send_command_and_read(2, (0, 0, 0, 0))
            # send command o

    @property
    def status(self):
        return self._status

    def update_pui(self):
        if self._connected:
            data = self.__send_command_and_read(3, (0, 0, 0, 0))
            self._power = data[2]
            self._voltage = data[0]
            self._current = data[1]
        return self._power, self._voltage, self._current

    def update_status(self):
        self.__send_command_and_read(13, (0, 0, 0, 0))  # command to read status
        # reads only status bytes, no additional data

    def connect(self, visa_resource_id):
        rm = pyvisa.ResourceManager()
        # connect to a specific instrument
        self._inst = rm.open_resource(visa_resource_id, open_timeout=1000,
                                      resource_pyclass=pyvisa.resources.MessageBasedResource)
        # instrument initialization

    # sends a command to the instrument: f_code = 1-byte function code,
    # par is a 4-tuple with 2-byte parameter values
    # reads the instrument response, status bytes are read and self._status is updated
    # any data read are returned in a 4-tuple
    def __send_command_and_read(self, f_code, par):
        cmd = struct.pack('>BBHHHH', self._address, f_code, par[0], par[1], par[3], par[4])  # encode command
        crc = struct.pack('<H', Crc16Modbus.calc(cmd))  # calculate CRC checksum
        msg = cmd + crc + struct.pack('B', 59)  # compose message and add terminating character
        ret_msg = self._inst.query(msg)  # send msg and query for response
        resp = ret_msg[0:13]           # extract response without CRC and termination character
        crc = struct.unpack('<H', ret_msg[13:15])[0]    # decode CRC
        crc_check = Crc16Modbus.calc(resp)      # calculate CRC from response
        if crc == crc_check:  # CRC OK
            resp_decoded = struct.unpack('>BBBBBHHHH', resp)    # decode response into bytes and shorts
            address = resp_decoded[0]
            function = resp_decoded[1]
            self._status['activeToggle'] = bool(resp_decoded[2] & 1)
            self._status['interlock'] = bool(resp_decoded[2] & 2)
            self._status['remote'] = bool(resp_decoded[2] & 4)
            self._status['setpointOK'] = bool(resp_decoded[2] & 8)
            self._status['mainsON'] = bool(resp_decoded[2] & 16)
            self._status['outputON'] = bool(resp_decoded[2] & 32)
            self._status['plasmaON'] = bool(resp_decoded[2] & 128)
            self._status['modeP'] = bool(resp_decoded[3] & 1)
            self._status['modeU'] = bool(resp_decoded[3] & 2)
            self._status['modeI'] = bool(resp_decoded[3] & 4)
            self._status['ramp'] = bool(resp_decoded[3] & 16)
            self._status['jouleMode'] = bool(resp_decoded[3] & 32)
            self._status['jouleLimit'] = bool(resp_decoded[3] & 64)
            self._status['pulseON'] = bool(resp_decoded[3] & 128)
            self._status['error'] = bool(resp_decoded[4] & 1)
            self._status['commandError'] = bool(resp_decoded[4] & 2)
            self._status['watchdogError'] = bool(resp_decoded[4] & 4)
            self._status['commandErrorCode'] = (resp_decoded[4] & 248) >> 3   # mask highest 5 bits
            # 248 = int('0b11111000', 2)
            data = resp_decoded[5:]
            return data
        else:  # CRC does not match
            raise ValueError("CRC mismatch for received message")

