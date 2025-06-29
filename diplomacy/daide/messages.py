# ==============================================================================
# Copyright (C) 2019 - Philip Paquette
#
#  This program is free software: you can redistribute it and/or modify it under
#  the terms of the GNU Affero General Public License as published by the Free
#  Software Foundation, either version 3 of the License, or (at your option) any
#  later version.
#
#  This program is distributed in the hope that it will be useful, but WITHOUT
#  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
#  FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
#  details.
#
#  You should have received a copy of the GNU Affero General Public License along
#  with this program.  If not, see <https://www.gnu.org/licenses/>.
# ==============================================================================
""" Implements the low-level messages sent over a stream """
from abc import ABCMeta, abstractmethod
from enum import Enum
import logging
from tornado import gen

# Constants
DAIDE_VERSION = 1
LOGGER = logging.getLogger(__name__)

class MessageType(Enum):
    """ Enumeration of message types """
    INITIAL = 0
    REPRESENTATION = 1
    DIPLOMACY = 2
    FINAL = 3
    ERROR = 4

class ErrorCode(Enum):
    """ Enumeration of error codes for error messages """
    IM_TIMER_POPPED = 0x01
    IM_NOT_FIRST_MESSAGE = 0x02
    IM_WRONG_ENDIAN = 0x03
    IM_WRONG_MAGIC_NUMBER = 0x04
    VERSION_INCOMPATIBILITY = 0x05
    MORE_THAN_1_IM_SENT = 0x06
    IM_SENT_BY_SERVER = 0x07
    UNKNOWN_MESSAGE = 0x08
    MESSAGE_SHORTER_THAN_EXPECTED = 0x09
    DM_SENT_BEFORE_RM = 0x0A
    RM_NOT_FIRST_MSG_BY_SERVER = 0x0B
    MORE_THAN_1_RM_SENT = 0x0C
    RM_SENT_BY_CLIENT = 0x0D
    INVALID_TOKEN_DM = 0x0E

class DaideMessage(metaclass=ABCMeta):
    """ Low-level DAIDE Message (Sent or Received) """

    def __init__(self, message_type):
        """ Constructor """
        self.message_type = message_type
        self.is_valid = True
        self.error_code = None                      # type: ErrorCode
        self.content = b''

    @abstractmethod
    @gen.coroutine
    def build(self, stream, remaining_length):
        """ Builds a message from a stream and its declared length """
        raise NotImplementedError()

    @staticmethod
    @gen.coroutine
    def from_stream(stream):
        """ Builds a message from the stream

            :param stream: An opened Tornado stream.
            :type stream: tornado.iostream.BaseIOStream
        """
        if stream.reading():
            return None

        data = yield stream.read_bytes(4)                               # Message type, Pad, Remaining Length (2x)

        # Parsing data
        message_type = data[0]
        remaining_length = data[2] * 256 + data[3]

        # Creating message
        message_cls = {MessageType.INITIAL.value: InitialMessage,
                       MessageType.REPRESENTATION.value: RepresentationMessage,
                       MessageType.DIPLOMACY.value: DiplomacyMessage,
                       MessageType.FINAL.value: FinalMessage,
                       MessageType.ERROR.value: ErrorMessage}.get(message_type, None)

        # Invalid message type
        if message_cls is None:
            raise ValueError('Unknown Message Type %d' % message_type)

        # Otherwise, return message
        message = message_cls()
        yield message.build(stream, remaining_length)
        return message

class InitialMessage(DaideMessage):
    """ Initial message sent from a client """

    def __init__(self):
        """ Constructor """
        super(InitialMessage, self).__init__(MessageType.INITIAL)

    def __bytes__(self):
        """ Converts message to byte array """
        return bytes([MessageType.INITIAL.value,                # Message Type
                      0,                                        # Padding
                      0, 4,                                     # Remaining length (2 bytes)
                      0, DAIDE_VERSION,                         # Daide version (2 bytes)
                      0xDA, 0x10])                              # Magic Number (2 bytes)

    @gen.coroutine
    def build(self, stream, remaining_length):
        """ Builds a message from a stream and its declared length """
        # Checking length
        if remaining_length != 4:
            LOGGER.error('Expected 4 bytes remaining in initial message. Got %d. Aborting.', remaining_length)
            self.is_valid = False
            return

        # Getting data and validating version
        data = yield stream.read_bytes(remaining_length)        # Version (x2) - Magic Number (x2)
        version = data[0] * 256 + data[1]
        magic_number = data[2] * 256 + data[3]

        # Wrong version
        if version != DAIDE_VERSION:
            self.is_valid = False
            self.error_code = ErrorCode.VERSION_INCOMPATIBILITY
            LOGGER.error('Client sent version %d. Server version is %d', version, DAIDE_VERSION)
            return

        # Wrong Endian / Magic Number
        if magic_number == 0x10DA:
            self.is_valid = False
            self.error_code = ErrorCode.IM_WRONG_ENDIAN
        elif magic_number != 0xDA10:
            self.is_valid = False
            self.error_code = ErrorCode.IM_WRONG_MAGIC_NUMBER

class RepresentationMessage(DaideMessage):
    """ Representation message sent from the server """

    def __init__(self):
        """ Constructor """
        super(RepresentationMessage, self).__init__(MessageType.REPRESENTATION)

    def __bytes__(self):
        """ Converts message to byte array """
        return bytes([MessageType.REPRESENTATION.value,         # Message Type
                      0,                                        # Padding
                      0, 0])                                    # Remaining length (2 bytes)

    @gen.coroutine
    def build(self, stream, remaining_length):
        """ Builds a message from a stream and its declared length """
        if remaining_length:
            yield stream.read_bytes(remaining_length)
        self.is_valid = False
        self.error_code = ErrorCode.RM_SENT_BY_CLIENT

class DiplomacyMessage(DaideMessage):
    """ Diplomacy message sent/received by/from the server """

    def __init__(self):
        """ Constructor """
        super(DiplomacyMessage, self).__init__(MessageType.DIPLOMACY)

    def __bytes__(self):
        """ Converts message to byte array """
        if not self.is_valid:
            return bytes()

        header = bytes([MessageType.DIPLOMACY.value,                            # Message Type
                        0,                                                      # Padding
                        len(self.content) // 256, len(self.content) % 256])     # Remaining length

        return header + self.content

    @gen.coroutine
    def build(self, stream, remaining_length):
        """ Builds a message from a stream and its declared length """
        if remaining_length < 2 or remaining_length % 2 == 1:
            self.is_valid = False
            if remaining_length:
                yield stream.read_bytes(remaining_length)
            LOGGER.warning('Got a diplomacy message of length %d. Ignoring.', remaining_length)

        # Getting data
        self.content = yield stream.read_bytes(remaining_length)

class FinalMessage(DaideMessage):
    """ Final message sent/received by/from the server """

    def __init__(self):
        """ Constructor """
        super(FinalMessage, self).__init__(MessageType.FINAL)

    def __bytes__(self):
        """ Converts message to byte array """
        return bytes([MessageType.FINAL.value,                  # Message Type
                      0,                                        # Padding
                      0, 0])                                    # Remaining length (2 bytes)

    @gen.coroutine
    def build(self, stream, remaining_length):
        """ Builds a message from a stream and its declared length """
        if remaining_length:
            yield stream.read_bytes(remaining_length)

class ErrorMessage(DaideMessage):
    """ Error message sent/received by/from the server """

    def __init__(self):
        """ Constructor """
        super(ErrorMessage, self).__init__(MessageType.ERROR)

    def __bytes__(self):
        """ Converts message to byte array """
        error_code = 0 if self.error_code is None else self.error_code.value
        return bytes([MessageType.ERROR.value,                  # Message Type
                      0,                                        # Padding
                      0, 2,                                     # Remaining length (2 bytes)
                      0, error_code])                           # Error code (2 bytes)

    @gen.coroutine
    def build(self, stream, remaining_length):
        """ Builds a message from a stream and its declared length """
        if remaining_length != 2:
            self.is_valid = False
            yield stream.read_bytes(remaining_length)
            return

        # Parsing error
        data = yield stream.read_bytes(remaining_length)
        self.error_code = ErrorCode(data[1])
