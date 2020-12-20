from unittest.mock import MagicMock
import textwrap

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
