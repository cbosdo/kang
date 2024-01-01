"""
# Raspberry Pi setup

See https://stackoverflow.com/questions/49292130/raspberry-pi-python-send-sms-using-sim800l
for the raspberry pi setup to get the Serial bus working
"""

import datetime
import logging
import re
import serial
import time

log = logging.getLogger(__name__)

def fireATCommand(sim, command):
    """
    @param sim: the SIM serial handle
    @param command: the AT command to send as a string without the newline
    """
    sim.write(b'%s\n' % command.encode('ascii'))

    # Reading empty line and status
    sim.readline()
    return sim.readline().strip() == b'OK'

def getTime(sim):
    """
    Get the network time

    @param sim: the SIM serial handle
    """
    sim.write(b'AT+CCLK?\n')
    line = sim.readline()
    res = None
    while not line.endswith(b'OK\r\n'):
        time.sleep(0.5)
        matcher = re.match(br'^\+CCLK: "([^+]+)\+[0-9]+"\r\n', line)
        if matcher:
            ts = matcher.group(1).decode('ascii')
            res = datetime.datetime.strptime(ts[:ts.find('+')], "%y/%m/%d,%H:%M:%S")
        line = sim.readline()
    return res

def ucs2tostring(ucs2):
    """
    @param ucs2: the bytes array in ucs2 as provided by the SIM module
    @return: the decoded string
    """
    return bytes.fromhex(ucs2.decode('ascii')).decode('utf_16_be')

def stringtoucs2(string):
    """
    @param string: the string to encode in UCS2
    @return: the UCS2-encoded bytes value
    """
    return string.encode('utf_16_be').hex().encode('ascii')


def get_error(line):
    """
    @param line: line to check for error feedback
    @return: the error code or None
    """
    error_header = b'+CMS ERROR:'
    if line.startswith(error_header):
        return line[len(error_header):].strip().decode('ascii')
    return None


class Sms:
    def __init__(self, dest=None, message=None):
        """
        @param dest: the destination phone number
        @param message: the message
        """
        self.number = dest
        self.message = message

    def send(self, sim):
        """
        @param sim: the SIM serial handle
        """
        log.debug('Sending SMS to %s: %s', self.number, self.message)
        sim.write(b'AT+CMGS="%s"\n' % stringtoucs2(self.number))
        sim.write(stringtoucs2(self.message))
        sim.write(b'\x1A')

        # Discard the output lines
        line = sim.readline()
        while not line.endswith(b'OK\r\n'):
            error = get_error(line)
            if error:
                log.error("Failed to send SMS to %s: %s", self.number, error) 
                return
            line = sim.readline()
        log.debug('Sent')

    @staticmethod
    def read(sim, idx):
        """
        @param sim: the SIM serial handle
        @param idx: the SMS internal index
        @return: an SMS object
        """
        sim.write(b'AT+CMGR=%s\n' % idx.encode('ascii'))
        msg = b''
        line = None
        while not line or not line.endswith(b'OK\r\n'):
            line = sim.readline()
            error = get_error(line)
            if error:
                raise Exception("Failed to read SMS: " + error)
            if line != b'\r\n' and line != b'OK\r\n':
                msg = msg + line

        try:
            log.debug('Parsing received SMS: %s', msg.decode('ascii'))
        except:
            log.error('Message encoding error')
        matcher = re.search(br'\+CMGR: "[^"]*","([^"]+)","[^"]*","([^"]+)"\r\n([0-9A-Fa-f]+)', msg)
        if not matcher:
            raise Exception("Failed to parse SMS: " + msg.decode('ascii'))

        sender = ucs2tostring(matcher.group(1))
        content = ucs2tostring(matcher.group(3))

        log.debug('Parsed received SMS from %s: %s', sender, content)

        return Sms(sender, content)

    @staticmethod
    def delete(sim, idx):
        fireATCommand(sim, 'AT+CMGD=%s' % idx)

def getAllSmsIds(sim):
    """
    @param sim: the SIM serial handle
    @return: the list of identifiers for the available messages
    """
    sim.write(b'AT+CMGL="ALL"\n')
    messages = []
    time.sleep(0.5)
    line = sim.readline()
    while not line.endswith(b'OK\r\n'):
        time.sleep(0.5)
        matcher = re.match(br'^\+CMGL: ([^,]+),"[^"]*","[^"]+","[^"]*","[^"]+"\r\n', line)
        if matcher:
            messages.append(matcher.group(1).decode('ascii'))
        line = sim.readline()
    return messages

def setup(dev='/dev/ttyAMA0'):
    """
    Run the AT initialization commands

    @param dev: the serial device path. /dev/ttyAMA0 as default should work fine
    @return: the initialized sim handle
    """
    sim = serial.Serial(dev, 9600, timeout=5)
    fireATCommand(sim, 'AT')
    fireATCommand(sim, 'ATE0') # Disable echo
    fireATCommand(sim, 'AT+CLTS=1')  # Enable auto network time sync
    fireATCommand(sim, 'AT+CMGF=1')  # Setting text mode
    fireATCommand(sim, 'AT+CNMI=1,0,0,0,0')  # Don't get the unsolicited notifications
    fireATCommand(sim, 'AT+CSCS="UCS2"')  # Receive all data at UCS2
    fireATCommand(sim, 'AT+CSMP=17,168,0,8') # Change SMS Data Coding Scheme to 8 for Unicode
    fireATCommand(sim, 'AT&W')  # Save parameters for next restart

    logging.info('SIM800 ready to be used')
    return sim
