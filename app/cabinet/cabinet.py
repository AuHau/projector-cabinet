import machine
import btn
import ulogging as logging

from cabinet import settings
from cabinet.actuator import Actuator
from cabinet.settings import PersistentSettings
from utils import singleton


@singleton
class Cabinet:
    def __init__(self):
        self._moving = False
        self.settings = PersistentSettings()
        self.actuator = Actuator()
        self._log = logging.getLogger('Cabinet')

        trigger_btn_pin = machine.Pin(settings.TRIGGER_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
        self.trigger_btn = btn.Pushbutton(trigger_btn_pin)

        self.usb_trigger = machine.Pin(settings.USB_TRIGGER_PIN, machine.Pin.OUT)
        self.usb_trigger.off()

        # fan_pwm_pin = machine.Pin(settings.FAN_PWM_PIN)
        # self.fan = Fan(fan_pwm_pin)

    def start(self):
        # self.trigger_btn.press_func(self.fan.toggle_speed)
        self.trigger_btn.press_func(self.trigger)
        self.actuator.start()

    async def trigger(self):
        if self.actuator.is_extended():
            await self.close()
        else:
            await self.open()

    async def open(self):
        if self._moving:
            self._log.warning("Cabinet is still moving!")
            return

        self._log.info("Opening cabinet")
        self._moving = True
        self.usb_trigger.on()
        await self.actuator.go_to(self.settings.actuator_target)
        self._moving = False
        self._log.info("Successfully opened cabinet")

    async def close(self):
        if self._moving:
            self._log.warning("Cabinet is still moving!")
            return

        self._log.info("Closing cabinet")
        self._moving = True
        self.usb_trigger.off()
        await self.actuator.go_back()
        self._moving = False
        self._log.info("Successfully closed cabinet")
