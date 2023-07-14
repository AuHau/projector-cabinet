import ujson
import os
from utils import singleton

# Pins settings
TEMP_PIN = 13
USB_TRIGGER_PIN = 33
ACTUATOR_IN1_PIN = 26
ACTUATOR_IN2_PIN = 27
# ACTUATOR_PWM_PIN = 25
POSITION_ADC_PIN = 36
ACTUATOR_CURRENT_SCL_PIN = 22
ACTUATOR_CURRENT_SDA_PIN = 21
FAN_PWM_PIN = 14

"""
Defines the maximal extension of the actuator's arm.
In millimeters.
"""
ACTUATOR_LENGTH = 200

PERSISTENT_SETTINGS_PATH = '/data/setting.json'


@singleton
class PersistentSettings:
    actuator_target = 100
    """
    Target to where the actuator will go when Cabinet is turned on. 
    """

    actuator_obstacle_sma_window = 10
    """
    Number of readings for the Simple Moving Average Window for the obstacle detection of actuator
    """

    actuator_obstacle_max_value_coefficient = 1.32
    """
    Defines limit of max. values accepted to the SMA window
    as a `actuator_obstacle_current * actuator_obstacle_max_value_coefficient`
    """

    actuator_obstacle_current = 600
    """
    The limit current that when actuator reaches it is most likely that there
    is some obstacle. Therefore the actuator will stop and reverse a bit. 
    """

    actuator_obstacle_reverse_distance = 12
    """
    When obstacle is detected then how much actuator should reverse in millimeters.
    """

    actuator_current_monitoring_interval = 100

    projector_number_of_samples = 1484
    """
    Number of samples that is taken for the current reading before reaching the final value
    """

    projector_reading_interval_ms = 500
    """
    How often is current retrieved
    """

    projector_calibration = 0.0415
    """
    Calibration value of the current sensor
    """

    projector_sma_window = 4
    """
    Number of readings for the Simple Moving Average Window
    """

    def __init__(self):
        try:
            os.stat(PERSISTENT_SETTINGS_PATH)
            with open(PERSISTENT_SETTINGS_PATH) as f:
                self._booting = True
                data = dict(ujson.load(f))
                for key, value in data.items():
                    setattr(self, key, value)
                self._booting = False
                print("=> Loaded setting: ", data)
        except OSError:
            print("=> No settings loaded")

    def __setattr__(self, key, value):
        super().__setattr__(key, value)

        try:
            if self._booting or key == '_booting':
                return
        except AttributeError:
            pass

        try:
            os.mkdir('/data')
        except OSError:
            pass

        with open(PERSISTENT_SETTINGS_PATH, mode='w') as f:
            ujson.dump(self.__dict__, f)
