import enum

import machine
import uasyncio as asyncio
import ulogging as logging

from cabinet import settings
from lib import aadc
from lib.ina219 import INA219
from lib.singleton import singleton

# In ADC reading unit; defines the target range
ADC_PRECISION = 50

# In milliseconds
CURRENT_MONITORING_INTERVAL = 10
CURRENT_SMA_WINDOW = 10
CURRENT_SENSOR_SHUNT_OHMS = 0.1

MAX_ADC_VALUE = pow(2, 16)


def _convert_actuators_extension_to_adc(goal):
    return goal / settings.ACTUATOR_LENGTH * MAX_ADC_VALUE


def _convert_from_adc_to_actuators_extension(reading):
    return reading / MAX_ADC_VALUE * settings.ACTUATOR_LENGTH


class MovingDirection(enum.Enum):
    NONE = 'nowhere'
    FORWARD = 'forward'
    BACKWARD = 'backward'

    def reverse(self):
        if self.value == self.NONE:
            return self.NONE
        elif self.name == self.FORWARD:
            return self.BACKWARD
        elif self.name == self.BACKWARD:
            return self.FORWARD
        else:
            raise ValueError("Unknown state!")


@singleton
class Actuator:
    def __init__(self):
        self._moving_direction = MovingDirection.NONE
        self._log = logging.getLogger('Actuator')
        self._avoiding_obstacle = False

        self.position_adc_pin = machine.ADC(machine.Pin(settings.POSITION_ADC_PIN), atten=machine.ADC.ATTN_11DB)
        self.position_adc = aadc.AADC(self.position_adc_pin)
        self.position_adc.sense(False)  # Will make it to wait until the reading is in given range

        self.in1 = machine.Pin(settings.ACTUATOR_IN1_PIN, machine.Pin.OUT)
        self.in2 = machine.Pin(settings.ACTUATOR_IN2_PIN, machine.Pin.OUT)
        self.in1.off()
        self.in2.off()

        i2c = machine.SoftI2C(machine.Pin(settings.ACTUATOR_CURRENT_SCL_PIN),
                              machine.Pin(settings.ACTUATOR_CURRENT_SDA_PIN))
        self.current_sensor = INA219(CURRENT_SENSOR_SHUNT_OHMS, i2c, log_level=logging.DEBUG)
        self.current_sensor.configure()

    def start(self):
        asyncio.create_task(self._log_values())
        asyncio.create_task(self._monitor_current())

    def is_extended(self):
        return self.position_adc_pin.read_u16() > ADC_PRECISION

    async def go_back(self):
        self._log.info("Going back")
        self._go_back()
        await self.position_adc(0, 0)
        self._stop()

    async def go_to(self, target):
        current_position = _convert_from_adc_to_actuators_extension(self.position_adc_pin.read_u16())
        where_to_move = MovingDirection.FORWARD if target > current_position else MovingDirection.BACKWARD
        adc_target = _convert_actuators_extension_to_adc(target)

        self._log.info(f"Going to target {target}mm. Current position {current_position}mm ==> Moving {where_to_move.value.upper()}")

        if where_to_move == MovingDirection.FORWARD:
            self._go_forward()
        elif where_to_move == MovingDirection.BACKWARD:
            self._go_back()

        result = await self.position_adc(adc_target - ADC_PRECISION, adc_target + ADC_PRECISION)

        # -1 means that AADC waiting was canceled and some other routine took over the control in the meanwhile
        if result != -1:
            self._stop()

    def _go_forward(self):
        self._moving_direction = MovingDirection.FORWARD
        self.in1.on()

    def _go_back(self):
        self._moving_direction = MovingDirection.BACKWARD
        self.in2.on()

    def _stop(self):
        self._log.info("Stopping")
        self._moving_direction = MovingDirection.NONE
        self.in1.off()
        self.in2.off()

    async def _handle_obstacle(self):
        self._log.warning(f"Obstacle detected! Reversing {settings.ACTUATOR_OBSTACLE_REVERSE_DISTANCE}mm.")
        self._avoiding_obstacle = True

        target_retraction = _convert_from_adc_to_actuators_extension(self.position_adc_pin.read_u16())
        if self._moving_direction == MovingDirection.FORWARD:
            target_retraction -= settings.ACTUATOR_OBSTACLE_REVERSE_DISTANCE
        elif self._moving_direction == MovingDirection.BACKWARD:
            target_retraction += settings.ACTUATOR_OBSTACLE_REVERSE_DISTANCE
        else:
            self._log.error("We should be avoiding obstacle but we are not moving!")

        await self.go_to(target_retraction)

        self._avoiding_obstacle = False
        self._log.info("Finished avoiding obstacle.")

    def _is_in_range(self, reading):
        return _convert_actuators_extension_to_adc(
            self.target) + ADC_PRECISION >= reading >= _convert_actuators_extension_to_adc(self.target) - ADC_PRECISION

    async def _monitor_current(self):
        if not settings.ACTUATOR_OBSTACLE_CURRENT:
            return

        # SMA = Simple Moving Average
        sma_values = []
        sma_sum = 0

        while True:
            current = self.current_sensor.current()
            sma_sum += current
            sma_values.append(current)

            # We have filled the SMA window size
            if len(sma_values) > CURRENT_SMA_WINDOW:
                sma_sum -= sma_values.pop(0)

            current_sma = sma_sum / CURRENT_SMA_WINDOW

            if current_sma > settings.ACTUATOR_OBSTACLE_CURRENT:
                self.position_adc.cancel()  # We cancel any currently awaiting movements

                if self._avoiding_obstacle:
                    self._log.warning("Obstacle is blocked! ==> Stopping")
                    self._stop()
                else:
                    # We do not await the coroutine, because the obstacle detection needs to run alongside the obstacle
                    # avoidance as it might run into another obstacle when backing off.
                    # In which case the actuator will stop.
                    asyncio.create_task(self._handle_obstacle())

                    # We reset the SMA window in order to not get double triggering
                    sma_values = []
                    sma_sum = 0

            await asyncio.sleep_ms(CURRENT_MONITORING_INTERVAL)

    async def _log_values(self):
        if not self._log.isEnabledFor(logging.DEBUG):
            return

        while True:
            reading = self.position_adc_pin.read_u16()
            self._log.debug(
                f"Extended: {_convert_from_adc_to_actuators_extension(reading)}mm (raw: {reading}); Current: {self.current_sensor.current()}mA")
            await asyncio.sleep_ms(1200)
