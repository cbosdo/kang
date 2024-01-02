from unittest.mock import MagicMock, call
import pytest

from kang.cms_error import CmsError

import kang.sim800


def test_readsms_unsolicited():
    '''
    In some cases we get unsolicited messages when reading the message.
    Ensure that the message is parsed properly even in those cases.
    '''
    data = [
        b'+CTZV: +4,0\r\n',
        b'*PSUTTZ: 2020,12,16,18,3,45,"+4",0\r\n',
        b'DST: 0\r\n',
        b'+CIEV: 10,"20801","Orange F","Orange F", 0, 0\r\n',
        b'+CMGR: "REC READ","002B0031003200330034003500360037003800390030","","20/12/16,19:03:40+04"\r\n',
        b'00410072007200EA007400650072\r\n',
        b'OK\r\n',
    ]
    mock_sim = MagicMock()
    mock_sim.readline.side_effect = data
    sms = kang.sim800.Sms.read(mock_sim, '0')
    assert "+1234567890" == sms.number
    assert "Arrêter" == sms.message


def test_readsms_error():
    '''
    Test reading an SMS with a failure
    '''
    data = [
        b'+CMS ERROR: 29\r\n',
    ]
    mock_sim = MagicMock()
    mock_sim.readline.side_effect = data
    
    with pytest.raises(CmsError) as excinfo:
        kang.sim800.Sms.read(mock_sim, '0')
      
    assert excinfo.type is CmsError
    assert '29' == excinfo.value.code
    assert 'Facility rejected' in f"Error: {excinfo.value}"

    expected_writes = [
        call(b'AT+CMGR=0\n'),
    ]

    assert expected_writes == mock_sim.write.call_args_list


def test_sendsms_errors():
    '''
    Test sending an SMS with a failure
    '''
    data = [
        b'+CMS ERROR: 29\r\n',
    ]
    mock_sim = MagicMock()
    mock_sim.readline.side_effect = data
    sms = kang.sim800.Sms('+1234567890', 'Test message')
    
    with pytest.raises(CmsError) as excinfo:
        sms.send(mock_sim)
       
    assert excinfo.type is CmsError
    assert '29' == excinfo.value.code
    assert 'Facility rejected' in f"Error: {excinfo.value}"


def test_sendsms_valid():
    '''
    Test successfully sending an SMS
    '''
    data = [
        b'\r\n',
        b'OK\r\n',
    ] 
    mock_sim = MagicMock()
    mock_sim.readline.side_effect = data
    sms = kang.sim800.Sms('+1234567890', 'Test message')
    
    sms.send(mock_sim)

    expected_writes = [
        call(b'AT+CMGS="002b0031003200330034003500360037003800390030"\n'),
        call(b'00540065007300740020006d006500730073006100670065'),
        call(b'\x1A')
    ]

    assert expected_writes == mock_sim.write.call_args_list
