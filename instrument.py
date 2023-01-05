import pyvisa


class Instrument:
    def __init__(self):
        self._output = False    # no output voltage after start
        self._connected = False     # connection with PS
        self._inst = None   # representation of the PS for read/write commands

    def connect(self, visa_resource_id):
        # rm = pyvisa.ResourceManager('@py')    # Linux version
        rm = pyvisa.ResourceManager('')
        rm.list_resources()
        # connect to a specific instrument
        self._inst = rm.open_resource(visa_resource_id, timeout=1000, resource_pyclass=pyvisa.resources.USBInstrument)
        self._connected = True