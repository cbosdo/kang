import logging
import RPi.GPIO as GPIO
import time

CHURCH = 22  # ON: 22, OFF: 23
HALL   = 24  # ON: 24, OFF: 25

_PLACES = [CHURCH, HALL]

log = logging.getLogger(__name__)

def setup():
    """
    Initiliaze the GPIO pins for the relay board
    """
    GPIO.setmode(GPIO.BCM)
    for pin in [CHURCH, CHURCH + 1, HALL, HALL + 1]:
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)

def clean():
    """
    Reset the GPIO pins
    """
    GPIO.cleanup()

def start(place):
    """
    Start the heating
    @param place: place to start the heating in. Value is one of CHURCH or HALL
    """
    if place not in _PLACES:
        raise ValueError
    log.info('start: %s', 'Church' if place == CHURCH else 'Hall')
    GPIO.output(place, GPIO.LOW)
    time.sleep(0.2)
    GPIO.output(place, GPIO.HIGH)

def stop(place):
    """
    Stop the heating
    @param place: place to stop the heating in. Value is one of CHURCH or HALL
    """
    if place not in _PLACES:
        raise ValueError
    log.info('stop: %s', 'Church' if place == CHURCH else 'Hall')
    GPIO.output(place + 1, GPIO.LOW)
    time.sleep(0.2)
    GPIO.output(place + 1, GPIO.HIGH)
