import math
import machine
import uasyncio as asyncio
import ulogging as logging

from cabinet import settings
from utils import singleton

# Voltage which the ADC works with
ADC_VOLTAGE = 3300

# Number of samples that is taken for the current reading before reaching the final value
NUMBER_OF_SAMPLES = 1484

# How often is current retrieved
READING_INTERVAL_MS = 500

# Calibration value of the current sensor
CALIBRATION = 0.0415

CURRENT_SMA_WINDOW = 4  # Number of readings for the Simple Moving Average Window
ADC_COUNTS = 1 << 10
offset = ADC_COUNTS


@singleton
class Projector:
    """
    Class that represents the Project's states.
    It mainly senses the current going to the projector to determine if the projector is turned on or off.
    """

    def __init__(self, cabinet):
        self._log = logging.getLogger('Projector')
        self._current_adc_pin = machine.ADC(machine.Pin(settings.PROJECTOR_CURRENT_PIN), atten=machine.ADC.ATTN_11DB)
        self._cabinet = cabinet
        self._projector_on = False

    def start(self):
        asyncio.create_task(self._reading_loop())

    def _read_current(self):
        global offset

        sum = 0
        for i in range(NUMBER_OF_SAMPLES):
            sample = self._current_adc_pin.read_u16()

            # Digital low pass filter extracts the 2.5 V or 1.65 V dc offset,
            #  then subtract this - signal is now centered on 0 counts.
            offset = (offset + (sample - offset) / 1024)
            filtered = sample - offset

            # Root-mean-square method current
            # 1) square current values
            sq = filtered * filtered
            # 2) sum
            sum += sq

        ratio = CALIBRATION * ((ADC_VOLTAGE / 1000.0) / (ADC_COUNTS))
        return ratio * math.sqrt(sum / NUMBER_OF_SAMPLES)

    async def _reading_loop(self):
        # SMA = Simple Moving Average
        sma_values = []
        sma_sum = 0

        while True:
            current = self._read_current()
            self._log.debug(f'Projectors current: {current}A')

            sma_sum += current
            sma_values.append(current)

            # We have filled the SMA window size
            if len(sma_values) > CURRENT_SMA_WINDOW:
                sma_sum -= sma_values.pop(0)

            current_sma = sma_sum / CURRENT_SMA_WINDOW

            if self._projector_on and current_sma < settings.PROJECTOR_CURRENT_TURNED_ON:
                self._log.info("Projector turned off")
                self._projector_on = False
                # self._cabinet.close()
            elif not self._projector_on and current_sma >= settings.PROJECTOR_CURRENT_TURNED_ON:
                self._log.info("Projector turned on")
                self._projector_on = True
                # self._cabinet.close()

            await asyncio.sleep_ms(READING_INTERVAL_MS)
