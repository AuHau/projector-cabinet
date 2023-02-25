# WiFi settings
WIFI_SSID = "Wuhuuu"
WIFI_PASS = "Kq4admD7EJJGDjl"

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
ACTUATOR_OBSTACLE_CURRENT = 500

"""
When obstacle is detected then how much actuator should reverse in millimeters.
"""
ACTUATOR_OBSTACLE_REVERSE_DISTANCE = 12
