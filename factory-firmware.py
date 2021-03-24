#!/usr/bin/python3

"""
Factory test script for the firmware-only burning station
"""

import time
import subprocess
from luma.core.render import canvas
from luma.core.interface.serial import bitbang
import RPi.GPIO as GPIO
from luma.oled.device import ssd1322
import luma.oled.device

from gpiodefs import *
from adc128 import *

oled=None  # global placeholder for the OLED device handle

from tests import *
from tests.BaseTest import BaseTest

def get_tests():
    tests = []
    tests.append(BattOn.Test())
    tests.append(VbusOn.Test())
    
    tests.append(Current.Test())
    
    tests.append(VbusOff.Test())
    tests.append(BattOff.Test())
    return tests

def makeint(i, base=10):
    try:
        return int(i, base=base)
    except:
        return 0
            
def get_gitver():
    major = 0
    minor = 0
    rev = 0
    gitrev = 0
    gitextra = 0
    dirty = 0

    def decode_version(v):
        version = v.split(".")
        major = 0
        minor = 0
        rev = 0
        if len(version) >= 3:
            rev = makeint(version[2])
        if len(version) >= 2:
            minor = makeint(version[1])
        if len(version) >= 1:
            major = makeint(version[0])
        return (major, minor, rev)
    git_rev_cmd = subprocess.Popen(["git", "describe", "--tags", "--long", "--dirty=+", "--abbrev=8"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
    (git_stdout, _) = git_rev_cmd.communicate()
    if git_rev_cmd.wait() != 0:
        print('unable to get git version')
        return (major, minor, rev, gitrev, gitextra, dirty)
    raw_git_rev = git_stdout.decode().strip()

    if raw_git_rev[-1] == "+":
        raw_git_rev = raw_git_rev[:-1]
        dirty = 1

    parts = raw_git_rev.split("-")

    if len(parts) >= 3:
        if parts[0].startswith("v"):
            version = parts[0]
            if version.startswith("v"):
                version = parts[0][1:]
            (major, minor, rev) = decode_version(version)
        gitextra = makeint(parts[1])
        if parts[2].startswith("g"):
            gitrev = makeint(parts[2][1:], base=16)
    elif len(parts) >= 2:
        if parts[1].startswith("g"):
            gitrev = makeint(parts[1][1:], base=16)
        version = parts[0]
        if version.startswith("v"):
            version = parts[0][1:]
        (major, minor, rev) = decode_version(version)
    elif len(parts) >= 1:
        version = parts[0]
        if version.startswith("v"):
            version = parts[0][1:]
        (major, minor, rev) = decode_version(version)

    return (major, minor, rev, gitrev, gitextra, dirty)

def wait_start():
    while GPIO.input(GPIO_START) == GPIO.LOW:
        time.sleep(0.1)
    while GPIO.input(GPIO_START) == GPIO.HIGH:
        time.sleep(0.1)
    
def abort_callback(channel):
    reset_tester_outputs()
    # this should cause the loop to restart from the top, for now, we use it to exit
    print("Abort button pressed, quitting!".format(channel))
    oled.clear()
    time.sleep(0.2)
    (major, minor, rev, gitrev, gitextra, dirty) = get_gitver()
    with canvas(oled) as draw:
       draw.text((0, FONT_HEIGHT * 0), "Tester version {}.{} {:x}+{}".format(major, minor, gitrev, gitextra), fill="white")
       draw.text((0, FONT_HEIGHT * 2), "Quit pressed, no program running.", fill="white")
    time.sleep(0.2)
    GPIO.cleanup()
    exit(0)

def reset_tester_outputs():
    GPIO.output(GPIO_VBUS, 0)
    GPIO.output(GPIO_BSIM, 0)
    GPIO.output(GPIO_ISENSE, 1)
    GPIO.output(GPIO_UART_SOC, 1)
    GPIO.output(GPIO_PROG_B, 1)
    GPIO.output(GPIO_AUD_HPR, 0)
    GPIO.output(GPIO_AUD_HPL, 0)
    GPIO.output(GPIO_AUD_SPK, 0)

# tests is a list of tests
def run_tests(tests):
    global oled

    # reset the test state before running it
    for test in tests:
        test.reset()
        
    # run phase -- each test runs, and can draw onto the screen for status updates
    # they return a simple pass/fail result, and if not passing, the full sequence aborts
    for test in tests:
        passed = test.run(oled)
        if passed != True:
            break

    # print a summary screen
    maxlines = 4
    colwidth = 64
    row = 0
    col = 0
    passing = True
    with canvas(oled) as draw:
        oled.clear()
        for test in tests:
            draw.text((col * colwidth, FONT_HEIGHT * row), test.short_status())
            if test.is_passing() != True:
                passing = False
            row += 1
            if row >= maxlines:
                row = 0
                col += 1

        if passing:
            draw.text((0, FONT_HEIGHT * 4), "Board is PASSING. Press START to continue.")
        else:
            draw.text((0, FONT_HEIGHT * 4), "Board has FAILED. Press START to continue.")

    wait_start()
    
    if passing != True:
        with canvas(oled) as draw:
            for test in tests:
                if test.is_passing() != True:
                    reasons = test.fail_reasons()
                    line = 0
                    for reason in reasons:
                        draw.text((0, FONT_HEIGHT * line), reason)
                        line += 1
                        if line >= maxlines:
                            break
            draw.text((0, FONT_HEIGHT * 4), "Details listed. Press START to continue.")
                        
    wait_start()

    
def main():
    global FONT_HEIGHT
    global GPIO_START, GPIO_FUNC, GPIO_BSIM, GPIO_ISENSE, GPIO_VBUS, GPIO_UART_SOC
    global GPIO_PROG_B, GPIO_AUD_HPR, GPIO_AUD_HPL, GPIO_AUD_SPK
    global oled
    global ADC128_REG, ADC128_DEV0, ADC128_DEV1, ADC_CH

    GPIO.setmode(GPIO.BCM)
    
    GPIO.setup(GPIO_START, GPIO.IN)
    GPIO.setup(GPIO_FUNC, GPIO.IN)
    
    GPIO.setup(GPIO_VBUS, GPIO.OUT)
    GPIO.setup(GPIO_BSIM, GPIO.OUT)
    GPIO.setup(GPIO_ISENSE, GPIO.OUT)
    GPIO.setup(GPIO_UART_SOC, GPIO.OUT)
    GPIO.setup(GPIO_PROG_B, GPIO.OUT)
    GPIO.setup(GPIO_AUD_HPR, GPIO.OUT)
    GPIO.setup(GPIO_AUD_HPL, GPIO.OUT)
    GPIO.setup(GPIO_AUD_SPK, GPIO.OUT)
    reset_tester_outputs()

    init_adc128(oled)
    
    GPIO.add_event_detect(GPIO_FUNC, GPIO.FALLING, callback=abort_callback)

    tests = get_tests()
    
    loops = 0
    oled.show()

    while True:
       reset_tester_outputs()
       oled.clear()
       (major, minor, rev, gitrev, gitextra, dirty) = get_gitver()
       with canvas(oled) as draw:
          draw.text((0, FONT_HEIGHT * 0), "Tester version {}.{} {:x}+{}".format(major, minor, gitrev, gitextra), fill="white")
          draw.text((0, FONT_HEIGHT * 1), "Tests run since last abort/restart: {}".format(loops), fill="white")
          draw.text((0, FONT_HEIGHT * 2), "Press START to continue...", fill="white")

       wait_start()
       loops += 1
       
       run_tests(tests)
    
if __name__ == "__main__":
    try:
        print("Tester main loop starting...")
        oled = ssd1322(bitbang(SCLK=11, SDA=10, CE=7, DC=1, RST=12))
        main()
    except KeyboardInterrupt:
        pass
        
    GPIO.cleanup()