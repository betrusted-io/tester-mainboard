import time
from luma.core.render import canvas
import RPi.GPIO as GPIO

from tests.BaseTest import BaseTest
from gpiodefs import *
from adc128 import *

class Test(BaseTest):
    def __init__(self, vbus_min_limit=4.5, vbus_max_limit=5.5):
        BaseTest.__init__(self, name="Vbus On", shortname="VbusOn")
        self.vbus_min_limit = vbus_min_limit
        self.vbus_max_limit = vbus_max_limit

    def run(self, oled):
        self.passing = True
        
        # turn on the power
        GPIO.output(GPIO_VBUS, 1)
        time.sleep(0.5) # wait for power to stabilize

        vbus = read_vbus()

        ###############################
        if vbus_min < 4.5:
            self.passing = False
            self.add_reason("VBUS too low: {:.3f}V".format(vbus_min))
        if vbus_max > 5.5:
            self.passing = False
            self.add_reason("VBUS too high: {:3.f}V".format(vbus_max))
        ###############################
        
        with canvas(oled) as draw:
            line = 0
            draw.text((0, FONT_HEIGHT * line), "VBUS: {:.3f}V".format(vbus))
            line += 1
            draw.text((0, FONT_HEIGHT * line), "IBUS: {:.3f}mA".format(ibus * 1000))
            line += 1
            draw.text((0, FONT_HEIGHT * line), "IBAT: {:.3f}mA".format(ibat * 1000))
            #line += 1
            #draw.text((0, FONT_HEIGHT * line), "Press START to continue")

        #while GPIO.input(GPIO_START) == GPIO.LOW:
        #    time.sleep(0.1)
        time.sleep(1.0)

        self.has_run = True
        return self.passing
        
