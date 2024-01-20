# -*- coding: utf-8 -*-

import locale
from threading import local
from datetime import datetime, timedelta
import time
import kang.kang
from unittest.mock import MagicMock, call, patch
import pytest
from json import dumps as _dumps


@patch("kang.sim800")
@patch("kang.relays")
def test_start(mock_relays, mock_sim800, make_sms):
    """
    Test the processing of command Démarrer
    """
    mock_sim = MagicMock()
    mock_sms = make_sms("+33123456789", "Démarrer")

    kang.kang.process_command(mock_sms, mock_sim)

    # Test that the relays are actioned
    mock_relays.start.assert_any_call(mock_relays.CHURCH)
    mock_relays.start.assert_called_with(mock_relays.HALL)

    # Test that the confirmation SMS is sent back
    mock_sim800.Sms.assert_called_with("+33123456789", "Démarré dans l'église, le hall")
    mock_sim800.Sms.return_value.send.assert_called_with(mock_sim)


@patch("kang.sim800")
@patch("kang.relays")
def test_start_place(mock_relays, mock_sim800, make_sms, place):
    """
    Test the processing of the command Démarrer in specific places
    """
    mock_sim = MagicMock()
    mock_sms = make_sms("+33123456789", "Démarrer dans " + place)

    kang.kang.process_command(mock_sms, mock_sim)

    # Test that the relays are actioned
    called = mock_relays.CHURCH
    not_called = mock_relays.HALL
    if place == "le hall":
        called = mock_relays.HALL
        not_called = mock_relays.CHURCH
    mock_relays.start.assert_any_call(called)
    call(not_called) not in mock_relays.start.method_calls

    # Test that the confirmation SMS is sent back
    mock_sim800.Sms.assert_called_once_with("+33123456789", "Démarré dans " + place)
    mock_sim800.Sms.return_value.send.assert_called_with(mock_sim)


@patch("kang.sim800")
@patch("kang.relays")
def test_stop(mock_relays, mock_sim800, make_sms):
    """
    Test the processing of command Arrêter
    """
    mock_sim = MagicMock()
    mock_sms = make_sms("+33123456789", "Arrêter")

    kang.kang.process_command(mock_sms, mock_sim)

    # Test that the relays are actioned
    mock_relays.stop.assert_any_call(mock_relays.CHURCH)
    mock_relays.stop.assert_called_with(mock_relays.HALL)

    # Test that the confirmation SMS is sent back
    mock_sim800.Sms.assert_called_with("+33123456789", "Arrêté dans l'église, le hall")
    mock_sim800.Sms.return_value.send.assert_called_with(mock_sim)


@patch("kang.sim800")
@patch("kang.relays")
def test_stop_place(mock_relays, mock_sim800, make_sms, place):
    """
    Test the processing of the command Arrêter in specific places
    """
    mock_sim = MagicMock()
    mock_sms = make_sms("+33123456789", "Arrêter dans " + place)

    kang.kang.process_command(mock_sms, mock_sim)

    # Test that the relays are actioned
    called = mock_relays.CHURCH
    not_called = mock_relays.HALL
    if place == "le hall":
        called = mock_relays.HALL
        not_called = mock_relays.CHURCH
    mock_relays.stop.assert_any_call(called)
    call(not_called) not in mock_relays.stop.method_calls

    # Test that the confirmation SMS is sent back
    mock_sim800.Sms.assert_called_with("+33123456789", "Arrêté dans " + place)
    mock_sim800.Sms.return_value.send.assert_called_with(mock_sim)


@patch("kang.sim800")
@patch("kang.relays")
def test_command_lenient(mock_relays, mock_sim800, make_sms):
    """
    Test the processing of commands with variations of accents, added spaces, different caps
    """
    mock_sim = MagicMock()
    mock_sms = make_sms("+33123456789", " demarrer  ")

    kang.kang.process_command(mock_sms, mock_sim)

    # Test that the relays are actioned
    mock_relays.start.assert_any_call(mock_relays.CHURCH)
    mock_relays.start.assert_called_with(mock_relays.HALL)

    # Test that the confirmation SMS is sent back
    mock_sim800.Sms.assert_called_with("+33123456789", "Démarré dans l'église, le hall")
    mock_sim800.Sms.return_value.send.assert_called_with(mock_sim)


def dumps_wapper(*args, **kwargs):
    return _dumps(*args, **(kwargs | {"default": lambda obj: "mock"}))


@patch("kang.sim800")
@patch("kang.relays")
@patch("kang.kang.scheduler_thread")
@pytest.mark.parametrize(
    "pattern,duration",
    [
        ("Démarrer le 01/02/2023 à 12:34 pendant 1h", timedelta(hours=1)),
        (
            "Démarrer  le 1  février  2023  à  12  :  34  pendant  1 h",
            timedelta(hours=1),
        ),
        (
            "allumer le 1 février 2023 a 12h34 pendant 1:12",
            timedelta(hours=1, minutes=12),
        ),
    ],
)
def test_add_schedule(
    mock_scheduler, mock_relays, mock_sim800, make_sms, pattern, duration
):
    """
    Test the processing of start command with schedule under various forms
    """
    mock_sim = MagicMock()
    mock_sms = make_sms("+33123456789", pattern)

    current_locale = locale.setlocale(locale.LC_ALL)
    locale.setlocale(locale.LC_ALL, "fr_FR")

    mock_relays.start = MagicMock()
    mock_relays.start.__name__ = "start"
    mock_relays.stop = MagicMock()
    mock_relays.stop.__name__ = "stop"

    kang.kang.process_command(mock_sms, mock_sim)

    locale.setlocale(locale.LC_ALL, current_locale)

    # Test that the event has been scheduled
    start = datetime(2023, 2, 1, 12, 34)
    start_time = start.timestamp()
    stop_time = (start + duration).timestamp()

    mock_scheduler.enterabs.assert_any_call(
        start_time, 0, mock_relays.start, argument=(mock_relays.CHURCH,)
    )
    mock_scheduler.enterabs.assert_any_call(
        start_time, 0, mock_relays.start, argument=(mock_relays.HALL,)
    )

    mock_scheduler.enterabs.assert_any_call(
        stop_time, 0, mock_relays.stop, argument=(mock_relays.CHURCH,)
    )
    mock_scheduler.enterabs.assert_any_call(
        stop_time, 0, mock_relays.stop, argument=(mock_relays.HALL,)
    )

    # Test that the confirmation SMS is sent back
    mock_sim800.Sms.assert_called_with(
        "+33123456789", "Programmé dans l'église, le hall"
    )
    mock_sim800.Sms.return_value.send.assert_called_with(mock_sim)


@patch("kang.kang.subprocess")
@patch("kang.sim800")
def test_version(mock_sim800, mock_subprocess, make_sms):
    """
    Test the processing of command version
    """
    mock_sim = MagicMock()
    mock_sms = make_sms("+33123456789", "version")

    git_mock = MagicMock()
    git_mock.returncode = 0
    git_mock.stdout = "Fake version"
    mock_subprocess.run.return_value = git_mock

    kang.kang.process_command(mock_sms, mock_sim)

    # Test that the result SMS is sent back
    mock_sim800.Sms.assert_called_with("+33123456789", "Fake version")
    mock_sim800.Sms.return_value.send.assert_called_with(mock_sim)
