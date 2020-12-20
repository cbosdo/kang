# -*- coding: utf-8 -*-

import kang.kang
from unittest.mock import MagicMock, call, patch

@patch('kang.sim800')
@patch('kang.relays')
def test_start(mock_relays, mock_sim800, make_sms):
    '''
    Test the processing of command Démarrer
    '''
    mock_sim = MagicMock()
    mock_sms = make_sms("+33123456789", "Démarrer")

    kang.kang.process_command(mock_sms, mock_sim)

    # Test that the relays are actioned
    mock_relays.start.assert_any_call(mock_relays.CHURCH)
    mock_relays.start.assert_called_with(mock_relays.HALL)

    # Test that the confirmation SMS is sent back
    mock_sim800.Sms.assert_called_with("+33123456789", "Démarré dans l'église, le hall")
    mock_sim800.Sms.return_value.send.assert_called_with(mock_sim)


@patch('kang.sim800')
@patch('kang.relays')
def test_start_place(mock_relays, mock_sim800, make_sms, place):
    '''
    Test the processing of the command Démarrer in specific places
    '''
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
    mock_sim800.Sms.assert_called_with("+33123456789", "Démarré dans " + place)
    mock_sim800.Sms.return_value.send.assert_called_with(mock_sim)


@patch('kang.sim800')
@patch('kang.relays')
def test_stop(mock_relays, mock_sim800, make_sms):
    '''
    Test the processing of command Arrêter
    '''
    mock_sim = MagicMock()
    mock_sms = make_sms("+33123456789", "Arrêter")

    kang.kang.process_command(mock_sms, mock_sim)

    # Test that the relays are actioned
    mock_relays.stop.assert_any_call(mock_relays.CHURCH)
    mock_relays.stop.assert_called_with(mock_relays.HALL)

    # Test that the confirmation SMS is sent back
    mock_sim800.Sms.assert_called_with("+33123456789", "Arrêté dans l'église, le hall")
    mock_sim800.Sms.return_value.send.assert_called_with(mock_sim)


@patch('kang.sim800')
@patch('kang.relays')
def test_stop_place(mock_relays, mock_sim800, make_sms, place):
    '''
    Test the processing of the command Arrêter in specific places
    '''
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


@patch('kang.sim800')
@patch('kang.relays')
def test_command_lenient(mock_relays, mock_sim800, make_sms):
    '''
    Test the processing of commands with variations of accents, added spaces, different caps
    '''
    mock_sim = MagicMock()
    mock_sms = make_sms("+33123456789", " demarrer  ")

    kang.kang.process_command(mock_sms, mock_sim)

    # Test that the relays are actioned
    mock_relays.start.assert_any_call(mock_relays.CHURCH)
    mock_relays.start.assert_called_with(mock_relays.HALL)

    # Test that the confirmation SMS is sent back
    mock_sim800.Sms.assert_called_with("+33123456789", "Démarré dans l'église, le hall")
    mock_sim800.Sms.return_value.send.assert_called_with(mock_sim)
