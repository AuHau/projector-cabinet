import machine
import btn
import ulogging as logging

from cabinet import settings
from cabinet.actuator import Actuator
from cabinet.fan import Fan
from utils import singleton


@singleton
class Cabinet:
    def __init__(self):
        self._moving = False
        self._settings = settings.PersistentSettings()
        self._actuator = Actuator()
        self._log = logging.getLogger('Cabinet')

        trigger_btn_pin = machine.Pin(settings.TRIGGER_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
        self.trigger_btn = btn.Pushbutton(trigger_btn_pin)

        self._usb_trigger = machine.Pin(settings.USB_TRIGGER_PIN, machine.Pin.OUT)
        self._usb_trigger.off()

        self._fan = Fan()

    def start(self):
        self.trigger_btn.press_func(self.trigger)
        self._actuator.start()

    async def trigger(self):
        if self._actuator.is_extended():
            await self.turn_off()
        else:
            await self.turn_on()

    async def turn_on(self):
        if self._moving:
            self._log.warning("Cabinet is still moving!")
            return

        self._log.info("Opening cabinet")
        self._moving = True
        self._usb_trigger.on()
        await self._actuator.go_to(self._settings.actuator_target)
        self._moving = False
        self._log.info("Successfully opened cabinet")
        self._fan.on()

    async def turn_off(self):
        if self._moving:
            self._log.warning("Cabinet is still moving!")
            return

        self._log.info("Closing cabinet")
        self._moving = True
        self._usb_trigger.off()
        await self._actuator.go_back()
        self._moving = False
        self._log.info("Successfully closed cabinet")
        self._fan.off()
