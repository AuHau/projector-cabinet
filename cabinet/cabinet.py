import machine

from cabinet import settings
from cabinet.actuator import Actuator
from cabinet.fan import Fan
from lib import btn
from lib.singleton import singleton


@singleton
class Cabinet:
    def __init__(self):
        self.moving = False
        self.target = 100
        self.actuator = Actuator()

        trigger_btn_pin = machine.Pin(settings.TRIGGER_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
        self.trigger_btn = btn.Pushbutton(trigger_btn_pin)

        # fan_pwm_pin = machine.Pin(settings.FAN_PWM_PIN)
        # self.fan = Fan(fan_pwm_pin)

    def start(self):
        # self.trigger_btn.press_func(self.fan.toggle_speed)
        self.trigger_btn.press_func(self.trigger_move)
        self.actuator.start()

    async def trigger_move(self):
        if self.moving:
            print("Actuator is still on the move!")
            return

        self.moving = True
        if self.actuator.is_extended():
            await self.actuator.go_back()
        else:
            await self.actuator.go_to(self.target)

        print("Finished moving!")
        self.moving = False
