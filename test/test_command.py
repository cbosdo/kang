# -*- coding: utf-8 -*-

import kang.kang
from unittest.mock import MagicMock, call, patch

def test_start(make_sms):
    '''
    Test the processing of command Démarrer
    '''
    mock_sim = MagicMock()
    mock_sms = make_sms("+33123456789", "Démarrer")

    with patch('kang.relays') as mock_relays:
        kang.kang.process_command(mock_sms, mock_sim)
        mock_relays.start.assert_any_call(mock_relays.CHURCH)
        mock_relays.start.assert_called_with(mock_relays.HALL)

def test_command_lenient(make_sms):
    '''
    Test the processing of commands with variations of accents, added spaces, different caps
    '''
    mock_sim = MagicMock()
    mock_sms = make_sms("+33123456789", " demarrer  ")

    with patch('kang.relays') as mock_relays:
        kang.kang.process_command(mock_sms, mock_sim)
        mock_relays.start.assert_any_call(mock_relays.CHURCH)
        mock_relays.start.assert_called_with(mock_relays.HALL)
