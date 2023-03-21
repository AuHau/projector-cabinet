import ujson
import os
from utils import singleton

# Pins settings
TRIGGER_PIN = 32
ACTUATOR_IN1_PIN = 26
ACTUATOR_IN2_PIN = 27
ACTUATOR_PWM_PIN = 25
POSITION_ADC_PIN = 36
ACTUATOR_CURRENT_SCL_PIN = 22
ACTUATOR_CURRENT_SDA_PIN = 21
FAN_PWM_PIN = 14

"""
Defines the maximal extension of the actuator's arm.
In millimeters.
"""
ACTUATOR_LENGTH = 200

"""
The limit current that when actuator reaches it is most likely that there
is some obstacle. Therefore the actuator will stop and reverse a bit. 
"""
ACTUATOR_OBSTACLE_CURRENT = 450

"""
When obstacle is detected then how much actuator should reverse in millimeters.
"""
ACTUATOR_OBSTACLE_REVERSE_DISTANCE = 12

PERSISTENT_SETTINGS_PATH = '/data/setting.json'


@singleton
class PersistentSettings:
    actuator_target = 100
    """
    Target to where the actuator will go when Cabinet is turned on. 
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

        if self._booting or key == '_booting':
            return

        try:
            os.mkdir('/data')
        except OSError:
            pass

        with open(PERSISTENT_SETTINGS_PATH, mode='w') as f:
            ujson.dump(self.__dict__, f)
