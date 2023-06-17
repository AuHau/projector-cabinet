import machine
import uasyncio as asyncio
import ulogging as logging

from utils import singleton
from cabinet import settings

PWM_FREQ = 5000
MAX_DUTY_VALUE = pow(2, 16)


@singleton
class Fan:
    def __init__(self):
        self._log = logging.getLogger('Fan')

        fan_pin = machine.Pin(settings.FAN_PWM_PIN, machine.Pin.OUT)
        self._pwm = machine.PWM(fan_pin, freq=PWM_FREQ)
        self.duty_cycle = 0

    def set(self, duty_cycle):
        self.duty_cycle = duty_cycle
        self._pwm.duty_u16((self.duty_cycle * MAX_DUTY_VALUE)//100)

    def off(self):
        self._pwm.duty_u16(0)
