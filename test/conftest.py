import kang.scheduler

import os
import pytest
import sys
from unittest.mock import MagicMock


mock_GPIO_obj = MagicMock()
rpi_module = type(sys)("RPi")
rpi_module.GPIO = mock_GPIO_obj
sys.modules["RPi"] = rpi_module
sys.modules["RPi.GPIO"] = type(sys)("RPi.GPIO")

mock_serial_obj = MagicMock()
sys.modules["serial"] = mock_serial_obj

def start():
    '''
    Fake start function to test the scheduler
    '''

def stop():
    '''
    Fake stop function to test the scheduler
    '''


@pytest.fixture
def mock_GPIO():
    return mock_GPIO_obj


@pytest.fixture
def mock_serial():
    return mock_serial_obj


@pytest.fixture
def make_sms():
    """
    Mock SMS object factory fixture
    """

    def _make_sms(number, message):
        mock = MagicMock()
        mock.number = number
        mock.message = message
        return mock

    return _make_sms


@pytest.fixture(params=["l'église", "le hall"])
def place(request):
    return request.param


EVENTS_FILE = "events.txt"


@pytest.fixture
def make_scheduler_thread():
    """
    Convenience fixture to easily create a scheduler thread with data
    """
    scheduler_thread = None
    def _make_scheduler(data):
        nonlocal scheduler_thread
        with open(EVENTS_FILE, "w") as fd:
            fd.write(data)

        scheduler_thread = kang.scheduler.SchedulerThread(EVENTS_FILE, [start, stop])
        scheduler_thread.start()
        return scheduler_thread

    yield _make_scheduler

    scheduler_thread.stop()
    scheduler_thread.join()

    os.remove(EVENTS_FILE)
