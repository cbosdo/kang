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
