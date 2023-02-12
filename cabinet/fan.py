import machine

PWM_FREQ = 5000
MAX_DUTY_VALUE = pow(2, 16)


class Fan:
    def __init__(self, pwm_pin):
        # self.relay_pin = relay_pin
        self.pwm = machine.PWM(pwm_pin, freq=PWM_FREQ)
        self.full_speed = True

    def toggle_speed(self):
        self.pwm.duty_u16(MAX_DUTY_VALUE if self.full_speed else MAX_DUTY_VALUE / 2)
        self.full_speed = not self.full_speed
