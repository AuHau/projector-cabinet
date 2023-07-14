import machine
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
        self._log.info(f'Setting fan to {duty_cycle}%')
        pwm = ((self.duty_cycle * MAX_DUTY_VALUE)//100)-1
        self._pwm.duty_u16(pwm if pwm > 0 else 0)

    def off(self):
        self._log.info('Setting fan to 0%')
        self.duty_cycle = 0
        self._pwm.duty_u16(0)
