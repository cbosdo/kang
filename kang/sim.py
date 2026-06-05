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
from smspdu import SMS_SUBMIT
from io import StringIO
from smspdudecoder.easy import read_incoming_sms


from kang.cms_error import CmsError

log = logging.getLogger(__name__)


def fireATCommand(sim, command):
    """
    @param sim: the SIM serial handle
    @param command: the AT command to send as a string without the newline
    """
    sim.write(b"%s\r\n" % command.encode("ascii"))

    # Reading empty line and status
    sim.readline()
    return sim.readline().strip() == b"OK"


def getTime(sim):
    """
    Get the network time

    @param sim: the SIM serial handle
    """
    sim.write(b"AT+CCLK?\r\n")
    line = sim.readline()
    res = None
    while not line.endswith(b"OK\r\n"):
        time.sleep(0.5)
        matcher = re.match(rb'^\+CCLK: "([^+]+)\+[0-9]+"\r\n', line)
        if matcher:
            ts = matcher.group(1).decode("ascii")
            res = datetime.datetime.strptime(ts[: ts.find("+")], "%y/%m/%d,%H:%M:%S")
        line = sim.readline()
    return res


def get_error(line):
    """
    @param line: line to check for error feedback
    @return: the error code or None
    """
    error_header = b"+CMS ERROR:"
    if line.startswith(error_header):
        return CmsError(line[len(error_header) :].strip().decode("ascii"))
    if b"ERROR" in line:
        return CmsError("-1")
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
        log.debug("Sending SMS: %s", self.message)
        sim.reset_input_buffer()

        pdu_objects = []
        chunks = [self.message[i : i + 160] for i in range(0, len(self.message), 160)]
        for chunk in chunks:
            pdu_objects.append(SMS_SUBMIT.create(None, self.number, chunk))

        log.debug("Message split into %s PDU segments.", len(pdu_objects))

        # Transmit each segment sequentially
        for index, pdu_obj in enumerate(pdu_objects, start=1):
            # Convert the PDU binary map into a clean uppercase Hex string
            pdu_hex = pdu_obj.toPDU().upper()
            pdu_len = len(pdu_hex) // 2

            # Prepend a 00 byte to tell the modem to use the SIM's default SMSC profile
            pdu_hex = "00" + pdu_hex

            log.debug(
                "Sending segment %s/%s (Length: %s): %s",
                index,
                len(pdu_objects),
                pdu_len,
                pdu_hex,
            )

            # Initiate the write pipeline using \r\n line endings
            sim.write(f"AT+CMGS={pdu_len}\r\n".encode("ascii"))

            # Wait for the modem prompt indicating readiness
            prompt = sim.read_until(b"> ")
            if b"> " not in prompt:
                remainder = prompt + sim.readline()
                log.error(
                    "Modem rejected PDU initiation prompt. Response: %s", remainder
                )
                raise Exception(
                    "Modem failed to open PDU prompt: "
                    + remainder.decode("ascii", errors="replace")
                )

            # Push the hex PDU string followed immediately by Ctrl+Z (\x1a)
            sim.write(f"{pdu_hex}\x1a".encode("ascii"))

            # Keep processing responses until this fragment is confirmed by the cell tower
            line = sim.readline()
            while not line.endswith(b"OK\r\n"):
                error = get_error(line)
                if error:
                    raise error
                line = sim.readline()

        log.info("All segments sent successfully.")

    @staticmethod
    def read(sim, idx):
        """
        @param sim: the SIM serial handle
        @param idx: the SMS internal index
        @return: an SMS object
        """
        log.debug("Reading SMS %s", idx)
        sim.reset_input_buffer()
        sim.write(b"AT+CMGR=%s\r\n" % idx.encode("ascii"))
        msg = b""
        line = None
        while not line or not line.endswith(b"OK\r\n"):
            line = sim.readline()
            error = get_error(line)
            if error:
                raise error
            if line != b"\r\n" and line != b"OK\r\n" and not line.startswith(b"+CMGR:"):
                msg = msg + line

        # Decode the PDU hex string using smspdudecoder
        try:
            parsed = read_incoming_sms(msg.decode("ascii"))
            log.debug("parsed sms: %s", parsed["content"])
            return Sms(parsed["sender"], parsed["content"])

        except Exception as e:
            log.error("Failed parsing PDU string %s: %s", msg, e)
            raise e

    @staticmethod
    def delete(sim, idx):
        fireATCommand(sim, "AT+CMGD=%s" % idx)


def getAllSmsIds(sim):
    """
    @param sim: the SIM serial handle
    @return: the list of identifiers for the available messages
    """
    sim.write(b"AT+CMGL=4\r\n")
    messages = []
    time.sleep(0.5)
    line = sim.readline()
    while not line.endswith(b"OK\r\n"):
        time.sleep(0.5)
        matcher = re.match(rb"^\+CMGL:\s*([0-9]+),", line)
        log.debug("Listed message: %s", line)
        if matcher:
            messages.append(matcher.group(1).decode("ascii"))
        line = sim.readline()
    return messages


def setup(dev="/dev/ttyAMA0"):
    """
    Run the AT initialization commands

    @param dev: the serial device path. /dev/ttyAMA0 as default should work fine
    @return: the initialized sim handle
    """
    sim = serial.Serial(dev, 115200, timeout=5)
    fireATCommand(sim, "AT")
    fireATCommand(sim, "ATE0")  # Disable echo

    # Enable automatic local network time zone report
    fireATCommand(sim, "AT+CTZU=1")

    # Force a quick toggle of network functionality to grab the NITZ time packet immediately
    fireATCommand(sim, "AT+CFUN=0")
    time.sleep(2)
    fireATCommand(sim, "AT+CFUN=1")

    # Wait a few seconds for network re-attachment before proceeding
    time.sleep(5)

    fireATCommand(sim, "AT+CMGF=0")  # Setting PDU mode
    fireATCommand(sim, "AT+CNMI=1,0,0,0,0")  # Don't get the unsolicited notifications
    fireATCommand(sim, 'AT+CSCS="UCS2"')  # Receive all data as UCS2
    fireATCommand(
        sim, "AT+CSMP=17,168,0,8"
    )  # Change SMS Data Coding Scheme to 8 for Unicode
    fireATCommand(sim, "AT&W")  # Save parameters for next restart

    logging.info("SIM7600 ready and network time synchronized")
    return sim
