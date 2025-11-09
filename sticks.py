from mcp4728 import *
from enum import IntEnum
from math import sin, cos, radians
from time import sleep

class Channel(IntEnum):
    CH_A = 0
    CH_B = 1
    CH_C = 2
    CH_D = 3

class Sticks(object):

    MAX_VAL = 4095
    MIN_VAL = 0

    def __init__(self, lx_channel: Channel, ly_channel: Channel, rx_channel: Channel,
                 ry_channel: Channel, vref=Vref.VDD, gain=Gain.GAIN_1,
                 address=MCP4728.DEFAULT_DAC_ADDRESS, busnum=1):
        if 4 != len(set([lx_channel, ly_channel, rx_channel, ry_channel])):
            print("Channels must be unique!")
            raise SystemError(1)

        for ch in [lx_channel, ly_channel, rx_channel, ry_channel]:
            if ch not in Channel:
                print("Invalid channel provided!")
                raise SystemError(1)

        self.lx_channel = lx_channel
        self.ly_channel = ly_channel
        self.rx_channel = rx_channel
        self.ry_channel = ry_channel

        self.max = self.MAX_VAL
        self.min = self.MIN_VAL
        self.deadzone_range = 0
        self.centre_value = 2047
        self.position_percent_mult_value = (self.max - self.centre_value - self.deadzone_range) / 100.0

        self.positions = [0,0,0,0]

        self.dac = MCP4728(address, busnum)
        self.dac.setGains(gain)
        self.dac.setVRefs(vref)

    def configure(self, max: int, min: int, deadzone_range: int, reset_sticks=True):
        if self.MAX_VAL < max:
            print(f"Tried to change max to out-of-range value {max}")
            return False
        elif self.MIN_VAL > min:
            print(f"Tried to change min to out-of-range value {min}")
            return False
        elif max <= min:
            print(f"Max ({max}) must be greater than min ({min})")
            return False
        elif ((max - min) / 2 <= deadzone_range):
            print("Deadzone range must be less than half the difference of max and min values!")
            return False

        self.max = max
        self.min = min
        self.deadzone_range = deadzone_range
        self.centre_value = (max - min) / 2
        self.position_percent_mult_value = (self.max - self.centre_value - self.deadzone_range) / 100.0

        if reset_sticks:
            # Empirical time that it takes for the DAC to be ready again 
            self.resetSticks()
            sleep(0.05)

    def setLeftStickPosition(self, x: float, y: float):
        if not self._validatePositions(x, y):
            return False
        self.positions[self.lx_channel] = self._getPos(x)
        self.positions[self.ly_channel] = self._getPos(y)
        self._applyStickPositions()
        return True

    def setLeftStickPositionAngle(self, angle: float, magnitude: int):
        if not self._validateAngleMagnitude(angle, magnitude):
            return False
        self.positions[self.lx_channel] = self._getXPosFromAngle(angle, magnitude)
        self.positions[self.ly_channel] = self._getYPosFromAngle(angle, magnitude)
        self._applyStickPositions()
        return True

    def setRightStickPosition(self, x: float, y: float):
        if not self._validatePositions(x, y):
            return False
        self.positions[self.rx_channel] = self._getPos(x)
        self.positions[self.ry_channel] = self._getPos(y)
        self._applyStickPositions()

    def setRightStickPositionAngle(self, angle: float, magnitude: int):
        if not self._validateAngleMagnitude(angle, magnitude):
            return False
        self.positions[self.rx_channel] = self._getXPosFromAngle(angle, magnitude)
        self.positions[self.ry_channel] = self._getYPosFromAngle(angle, magnitude)
        self._applyStickPositions()
        return True

    def setStickPositions(self, lx: float, ly: float, rx: float, ry: float):
        if not self._validatePositions(lx, ly):
            return False
        if not self._validatePositions(rx, ry):
            return False
        self.positions[self.lx_channel] = self._getPos(lx)
        self.positions[self.ly_channel] = self._getPos(ly)
        self.positions[self.rx_channel] = self._getPos(rx)
        self.positions[self.ry_channel] = self._getPos(ry)
        self._applyStickPositions()

    def resetSticks(self):
        self.setStickPositions(0, 0, 0, 0)

    def _validatePositions(self, x: float, y: float):
        if 100 < x:
            print("Attempted to set X position of stick higher than 100%")
            print(x)
            return False
        if -100 > x:
            print("Attempted to set X position of stick lower than -100%")
            return False
        if 100 < y:
            print("Attempted to set Y position of stick higher than 100%")
            return False
        if -100 > y:
            print("Attempted to set Y position of stick lower than -100%")
            return False
        return True

    def _validateAngleMagnitude(self, angle: float, magnitude: int):
        if 360 < angle:
            print("angle higher than 360 deg")
            return False
        if 0 > angle:
            print("Attempted to set angle less then 0 deg")
            return False
        if 100 < magnitude:
            print("Attempted to set magnitude of angle higher than 100%")
            return False
        if -100 > magnitude:
            print("Attempted to set magnitude of angle lower than -100%")
            return False
        return True

    def _getPos(self, position: float, deadzone_factor: float = 1):
        pos = self.centre_value + (position * self.position_percent_mult_value)
        if 0 > position:
            pos -= self.deadzone_range * abs(deadzone_factor)
        elif 0 < position:
            pos += self.deadzone_range * abs(deadzone_factor)
        return int(pos)

    def _getXPosFromAngle(self, angle: float, magnitude: int):
        return self._getPos(sin(radians(angle)) * magnitude, sin(radians(angle)))

    def _getYPosFromAngle(self, angle: float, magnitude: int):
        return self._getPos(cos(radians(angle)) * magnitude, cos(radians(angle)))

    def _applyStickPositions(self):
        self.dac.setAllValues(*self.positions)
