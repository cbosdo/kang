import pytest
import sys
from unittest.mock import MagicMock


mock_GPIO = MagicMock()
rpi_module = type(sys)('RPi')
rpi_module.GPIO = mock_GPIO
sys.modules['RPi'] = rpi_module
sys.modules['RPi.GPIO'] = type(sys)('RPi.GPIO')

mock_serial = MagicMock()
sys.modules['serial'] = mock_serial


@pytest.fixture
def mock_GPIO():
    return mock_GPIO


@pytest.fixture
def mock_serial():
    return mock_serial


@pytest.fixture
def make_sms():
    '''
    Mock SMS object factory fixture
    '''
    def _make_sms(number, message):
        mock = MagicMock()
        mock.number = number
        mock.message = message
        return mock
    return _make_sms
