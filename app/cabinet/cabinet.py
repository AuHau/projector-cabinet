import machine
import onewire
import ds18x20
import ulogging as logging
import uasyncio as asyncio

from cabinet import settings
from cabinet.actuator import Actuator
from cabinet.fan import Fan
from utils import singleton

TEMP_RETRIES = 4
TEMP_RETRIES_INTERVAL = 500


@singleton
class Cabinet:
    def __init__(self):
        self._moving = False
        self._settings = settings.PersistentSettings()
        self._actuator = Actuator()
        self._log = logging.getLogger('Cabinet')

        self._usb_trigger = machine.Pin(settings.USB_TRIGGER_PIN, machine.Pin.OUT)
        self._usb_trigger.off()

        self._fan = Fan()

        self._temp = ds18x20.DS18X20(onewire.OneWire(machine.Pin(settings.TEMP_PIN)))
        self._temp_rom = None

    def start(self):
        self._actuator.start()

        roms = self._temp.scan()
        if len(roms) == 0:
            self._log.error("No temperature sensor found!")
        elif len(roms) != 1:
            self._log.error("Found more then one sensor!")
        else:
            self._log.info(f'Found {roms[0]} temperature sensor')
            self._temp_rom = roms[0]

    def is_on(self):
        return self._actuator.is_extended()

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
        successful = await self._actuator.go_to(self._settings.actuator_target)
        self._moving = False
        self._fan.set(50)

        if successful:
            self._log.info("Successfully opened cabinet")
        else:
            self._log.warning("Actuator did not reach the target! Had to stop before.")

        return successful

    async def turn_off(self):
        if self._moving:
            self._log.warning("Cabinet is still moving!")
            return

        self._log.info("Closing cabinet")
        self._moving = True
        self._usb_trigger.off()
        successful = await self._actuator.go_back()
        self._moving = False
        self._fan.off()

        if successful:
            self._log.info("Successfully closed cabinet")
        else:
            self._log.warning("Actuator did not reach the target! Had to stop before.")

        return successful

    async def get_temp(self):
        if self._temp_rom is None:
            return -100

        for _ in range(TEMP_RETRIES):
            try:
                self._temp.convert_temp()
                await asyncio.sleep_ms(750)
                temp = self._temp.read_temp(self._temp_rom)
                self._log.info(f'Current temperature {temp}')
                return temp
            except Exception:
                pass
            await asyncio.sleep_ms(TEMP_RETRIES_INTERVAL)

        self._log.error(f'After {TEMP_RETRIES} retries, it was not possible to get temperature')
        return -100
