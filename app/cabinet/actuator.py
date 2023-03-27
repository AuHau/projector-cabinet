import machine
import uasyncio as asyncio
import ulogging as logging
import aadc

from ina219 import INA219
from utils import singleton
from cabinet import settings

# In ADC reading unit; defines the target range
ADC_PRECISION = 100
CURRENT_SENSOR_SHUNT_OHMS = 0.1
ACTUATOR_TIMEOUT = 20_000  # In milliseconds
MAX_ADC_VALUE = pow(2, 16)


def _convert_actuators_extension_to_adc(goal):
    return goal / settings.ACTUATOR_LENGTH * MAX_ADC_VALUE


def _convert_from_adc_to_actuators_extension(reading):
    return reading / MAX_ADC_VALUE * settings.ACTUATOR_LENGTH


def enum(**enums):
    return type('Enum', (), enums)


MovingDirection = enum(NONE='nowhere', FORWARD='forward', BACKWARD='backward')


def _reverse_moving_direction(value):
    if value == MovingDirection.NONE:
        return MovingDirection.NONE
    elif value == MovingDirection.FORWARD:
        return MovingDirection.BACKWARD
    elif value == MovingDirection.BACKWARD:
        return MovingDirection.FORWARD
    else:
        raise ValueError("Unknown state!")


@singleton
class Actuator:
    def __init__(self):
        self._moving_direction = MovingDirection.NONE
        self._log = logging.getLogger('Actuator')
        self._log_obstacle = logging.getLogger('Actuator:ObstacleDetection')
        self._settings = settings.PersistentSettings()
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
        self.current_sensor = INA219(CURRENT_SENSOR_SHUNT_OHMS, i2c, log_level=logging.WARNING)
        self.current_sensor.configure()

    def start(self):
        asyncio.create_task(self._log_values())

    def is_extended(self):
        return self.position_adc_pin.read_u16() > ADC_PRECISION

    async def go_back(self):
        self._log.info("Going back")
        await self.go_to(0)

    async def go_to(self, target):
        try:
            finished_move_event = asyncio.Event()
            while not finished_move_event.is_set():
                move_task = asyncio.create_task(self._go_to(target, finished_move_event))

                # _detect_obstacle cancels the move_task when obstacle is detected and specifies
                # the new target value for the move
                target = await asyncio.wait_for_ms(self._detect_obstacles(finished_move_event, move_task),
                                                   ACTUATOR_TIMEOUT)

                if target is None:
                    break
        except TimeoutError:
            self._log.warning("The go_to routine timed out!")
        finally:
            # We might or might not have been avoiding obstacles, but lets reset it to default value
            # at the end of the move just as precaution, so it is ready for future moves!
            self._avoiding_obstacle = False

    async def _go_to(self, target, finished_event):
        current_position = _convert_from_adc_to_actuators_extension(self.position_adc_pin.read_u16())
        where_to_move = MovingDirection.FORWARD if target > current_position else MovingDirection.BACKWARD
        adc_target = _convert_actuators_extension_to_adc(target)

        self._log.info(
            f"Going to target {target}mm. Current position {current_position}mm ==> Moving {where_to_move.upper()}")

        if where_to_move == MovingDirection.FORWARD:
            self._go_forward()
        elif where_to_move == MovingDirection.BACKWARD:
            self._go_back()

        await self.position_adc(adc_target - ADC_PRECISION, adc_target + ADC_PRECISION)
        self._log.debug(f"Finished the move {current_position}mm --> {target}mm")
        self._stop()
        finished_event.set()

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

    def _get_obstacle_target(self, current_move_direction):
        target_retraction = _convert_from_adc_to_actuators_extension(self.position_adc_pin.read_u16())
        if current_move_direction == MovingDirection.FORWARD:
            target_retraction -= self._settings.actuator_obstacle_reverse_distance
        elif current_move_direction == MovingDirection.BACKWARD:
            target_retraction += self._settings.actuator_obstacle_reverse_distance
        else:
            self._log_obstacle.error("We should be avoiding obstacle but we are not moving!")

        if target_retraction < 0:
            return 0

        if target_retraction > settings.ACTUATOR_LENGTH:
            return settings.ACTUATOR_LENGTH

        self._log_obstacle.info(f"Reversing {self._settings.actuator_obstacle_reverse_distance}mm to {target_retraction}mm.")

        return target_retraction

    def _is_in_range(self, reading):
        return _convert_actuators_extension_to_adc(
            self.target) + ADC_PRECISION >= reading >= _convert_actuators_extension_to_adc(self.target) - ADC_PRECISION

    async def _detect_obstacles(self, finished_move_event, move_task):
        if not self._settings.actuator_obstacle_current:
            self._log_obstacle.warning("Obstacle current is not defined. No obstacle detection is happening.")
            await finished_move_event.wait()
            return

        # SMA = Simple Moving Average
        sma_values = []
        sma_sum = 0

        # We monitor the current only while actuator is moving which is signaled by this event
        while not finished_move_event.is_set():
            current = self.current_sensor.current()
            max_allowed_current = self._settings.actuator_obstacle_max_value_coefficient * self._settings.actuator_obstacle_current

            if current > max_allowed_current:
                current = max_allowed_current

            sma_sum += current
            sma_values.append(current)

            # We have filled the SMA window size
            if len(sma_values) > self._settings.actuator_obstacle_sma_window:
                sma_sum -= sma_values.pop(0)

            current_sma = sma_sum / self._settings.actuator_obstacle_sma_window

            if current_sma > self._settings.actuator_obstacle_current:
                self._log_obstacle.warning("Obstacle detected!")
                self._log.debug(f"SMA(sum={sma_sum};values={sma_values})")

                current_move_direction = self._moving_direction
                move_task.cancel()  # We stop the current _go_to() coroutine
                self._stop()  # and stop the movement

                # When we are already doing the obstacle retraction and detect another
                # obstacle, then it is highly probable that the drawer is stuck so lets just
                # completely stop in order not to make anymore damage.
                if self._avoiding_obstacle:
                    self._log_obstacle.warning("Obstacle is blocked! ==> Stopping completely")
                    return None  # As we are already stopped, lets just not return any new target
                else:
                    self._avoiding_obstacle = True
                    await asyncio.sleep_ms(1000)
                    return self._get_obstacle_target(current_move_direction)

            await asyncio.sleep_ms(self._settings.actuator_current_monitoring_interval)

        return None  # None represents no new target

    async def _log_values(self):
        if not self._log.isEnabledFor(logging.DEBUG):
            return

        while True:
            reading = self.position_adc_pin.read_u16()
            self._log.debug(
                f"Extended: {_convert_from_adc_to_actuators_extension(reading)}mm (raw: {reading}); Current: {self.current_sensor.current()}mA")
            await asyncio.sleep_ms(1200)
