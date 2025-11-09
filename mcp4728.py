import smbus
from enum import IntEnum

class Gain(IntEnum):
    GAIN_1 = 0
    GAIN_2 = 1

class Vref(IntEnum):
    VDD = 0
    INTERNAL_2_048V = 1

class McpChannel(IntEnum):
    CH_A = 0
    CH_B = 1
    CH_C = 2
    CH_D = 3

class Command(IntEnum):
    # Commands take the general form:
    # DDDD DXYZ
    #
    # DDDD D is the command itself as described by the datasheet
    #
    # XY == DAC1:DAC0 which is a 2-bit number indicating which DAC/channel
    # the command is run on, or starts with.
    # 00 == Channel A (DAC 0), 01 == Channel B (DAC 1)
    # 10 == Channel C (DAC 2), 11 == Channel D (DAC 3)
    #
    # Z == UDAC. See datasheet for more, but for the rpi implementation this
    # is to remain 0 to apply the update after all data sent.

    # Command is 0101 0DDX
    # The STARTING dac is chosen by DD, and the payload should contain DAC values
    # for the starting channel through the last channel (D). 
    #
    # E.g. DD == 00 means start channel A, and provide values for A, B, C, D
    #      DD == 10 means start channel C, and provide values for C, D
    SEQ_WRITE_CMD = 0x50

    # Command is 0101 1DDX
    # The dac to apply the value to is chosen by DD
    SINGLE_WRITE_CMD = 0x50

class MCP4728(object):
    DEFAULT_BUS_NUM = 1
    DEFAULT_DAC_ADDRESS = 0x60

    CH_MAP = {
        McpChannel.CH_A: 0x0,
        McpChannel.CH_B: 0x2,
        McpChannel.CH_C: 0x4,
        McpChannel.CH_D: 0x6
    }

    GAIN_MAP = {
        Gain.GAIN_1: 0x0,
        Gain.GAIN_2: 0x1000
    }

    VREF_MAP = {
        Vref.VDD: 0x0,
        Vref.INTERNAL_2_048V: 0x8000
    }

    def __init__(self, address=DEFAULT_DAC_ADDRESS, busnum=DEFAULT_BUS_NUM):
        self.address = address
        self.bus = smbus.SMBus(busnum)
        self.vref_base = Vref.VDD
        self.gain_base = Gain.GAIN_1

    def setAllValues(self, ch_a_val, ch_b_val, ch_c_val, ch_d_val):
        val = [*self._getChValue(ch_a_val), *self._getChValue(ch_b_val),
               *self._getChValue(ch_c_val), *self._getChValue(ch_d_val)]
        try:
            self.bus.write_i2c_block_data(self.address, Command.SEQ_WRITE_CMD, val)
        except Exception as e:
            print(f"Exception when writing all values: {e}")

    def setOneVal(self, channel: McpChannel, value):
        try:
            self.bus.write_i2c_block_data(self.address, Command.SINGLE_WRITE_CMD | self.CH_MAP[channel],
                                          self._getChValue(value))
        except Exception as e:
            print(f"Exception when writing single channel value: {e}")

    # Don't need to actually set these, just the base. They are set when DAC val is .
    def setVRefs(self, vref: Vref):
        self.vref_base = self.VREF_MAP[vref]
    def setGains(self, gain: Gain):
        self.gain_base = self.GAIN_MAP[gain]

    def _getChValue(self, value):
        # clamp value to bounds
        value = max(0, value)
        value = min(4095, value)

        # Set the appropriate bits or vref and gain, then bitmask the values appropriately
        result = self.vref_base | self.gain_base | value
        return [(result >> 8) & 0xFF, (result) & 0xFF]

