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
""" Daide Requests - Contains a list of requests sent by client to server """
from diplomacy.communication.requests import _AbstractGameRequest
from diplomacy.daide.clauses import String, Number, Power, Order, Turn, SingleToken, strip_parentheses, \
    break_next_group, parse_bytes
from diplomacy.daide import tokens
from diplomacy.daide.tokens import Token, is_ascii_token
from diplomacy.utils import parsing, strings

class RequestBuilder:
    """ Builds DaideRequest from bytes or tokens """
    @staticmethod
    def from_bytes(daide_bytes, **kwargs):
        """ Builds a request from DAIDE bytes

            :param daide_bytes: The bytes representation of a request
            :return: The DaideRequest built from the bytes
        """
        if len(daide_bytes) < 2:
            return None
        initial_bytes = daide_bytes[:2]
        if initial_bytes not in __REQUEST_CONSTRUCTORS__:
            raise ValueError('Unable to find a constructor for %s' % str(Token(from_bytes=initial_bytes)))
        request = __REQUEST_CONSTRUCTORS__[initial_bytes](**kwargs)             # type: DaideRequest
        request.parse_bytes(daide_bytes)
        return request

class DaideRequest(_AbstractGameRequest):
    """ Represents a DAIDE request. """
    def __init__(self, **kwargs):
        """ Constructor """
        self._bytes = b''
        self._str = ''
        super(DaideRequest, self).__init__(token='',
                                           game_id='',
                                           game_role='',
                                           phase='',
                                           **kwargs)

    def __bytes__(self):
        """ Returning the bytes representation of the request """
        return self._bytes

    def __str__(self):
        """ Returning the string representation of the request """
        return self._str

    def parse_bytes(self, daide_bytes):
        """ Builds the request from DAIDE bytes """
        assert len(daide_bytes) % 2 == 0, 'Expected request to have an even number of bytes. Got %d' % len(daide_bytes)
        self._bytes = daide_bytes

        # Building str representation
        while daide_bytes:
            token = Token(from_bytes=(daide_bytes[0], daide_bytes[1]))
            new_str = str(token)
            daide_bytes = daide_bytes[2:]
            pad = '' if (not self._str
                         or self._str[-1] == '('
                         or new_str == ')'
                         or (is_ascii_token(token) and new_str != '(')) else ' '
            self._str = self._str + pad + new_str


# ====================
# Connection requests
# ====================

class NameRequest(DaideRequest):
    """ Represents a NME DAIDE request. Can be sent by the client as soon as it connects to the server.

        Syntax: ::

            NME ('name') ('version')
    """
    __slots__ = ['client_name', 'client_version']
    params = {
        strings.CLIENT_NAME: str,
        strings.CLIENT_VERSION: str
    }

    def __init__(self, **kwargs):
        """ Constructor """
        self.client_name = ''
        self.client_version = ''
        super(NameRequest, self).__init__(client_name='', client_version='', **kwargs)

    def parse_bytes(self, daide_bytes):
        """ Builds the request from DAIDE bytes """
        super(NameRequest, self).parse_bytes(daide_bytes)

        # Parsing
        lead_token, daide_bytes = parse_bytes(SingleToken, daide_bytes)
        client_name, daide_bytes = parse_bytes(String, daide_bytes)
        client_version, daide_bytes = parse_bytes(String, daide_bytes)
        assert str(lead_token) == 'NME', 'Expected NME request'
        assert not daide_bytes, '%s bytes remaining. Request is malformed' % len(daide_bytes)

        # Setting properties
        self.client_name = str(client_name)
        self.client_version = str(client_version)

class ObserverRequest(DaideRequest):
    """ Represents a NME DAIDE request. Can be sent by the client as soon as it connects to the server.

        Syntax: ::

            OBS
    """
    __slots__ = []
    params = {}

    def parse_bytes(self, daide_bytes):
        """ Builds the request from DAIDE bytes """
        super(ObserverRequest, self).parse_bytes(daide_bytes)

        # Parsing
        lead_token, daide_bytes = parse_bytes(SingleToken, daide_bytes)
        assert str(lead_token) == 'OBS', 'Expected OBS request'
        assert not daide_bytes, '%s bytes remaining. Request is malformed' % len(daide_bytes)

class IAmRequest(DaideRequest):
    """ Represents a IAM DAIDE request. Can be sent by the client at anytime to rejoin the game.

        Syntax: ::

            IAM (power) (passcode)
    """
    __slots__ = ['power_name', 'passcode']
    params = {
        strings.POWER_NAME: str,
        strings.PASSCODE: parsing.OptionalValueType(int)
    }

    def __init__(self, **kwargs):
        """ Constructor """
        self.power_name = ''
        self.passcode = 0
        super(IAmRequest, self).__init__(power_name='', passcode=0, **kwargs)

    def parse_bytes(self, daide_bytes):
        """ Builds the request from DAIDE bytes """
        super(IAmRequest, self).parse_bytes(daide_bytes)

        # Parsing
        lead_token, daide_bytes = parse_bytes(SingleToken, daide_bytes)
        assert str(lead_token) == 'IAM', 'Expected IAM request'

        # Power
        power_group_bytes, daide_bytes = break_next_group(daide_bytes)
        power_group_bytes = strip_parentheses(power_group_bytes)
        power, power_group_bytes = parse_bytes(Power, power_group_bytes)
        assert not power_group_bytes, '%s bytes remaining in power group. Request is malformed' % len(power_group_bytes)

        # Passcode
        passcode_group_bytes, daide_bytes = break_next_group(daide_bytes)
        passcode_group_bytes = strip_parentheses(passcode_group_bytes)
        passcode, passcode_group_bytes = parse_bytes(SingleToken, passcode_group_bytes)
        assert not passcode_group_bytes, '%s bytes remaining in passcode group. Req. error' % len(passcode_group_bytes)
        assert not daide_bytes, '%s bytes remaining. Request is malformed' % len(daide_bytes)

        # Setting properties
        self.power_name = str(power)
        self.passcode = str(passcode)

class HelloRequest(DaideRequest):
    """ Represents a HLO DAIDE request. Sent by the client to request a copy of the HLO message.

        Syntax: ::

            HLO
    """
    __slots__ = []
    params = {}

    def parse_bytes(self, daide_bytes):
        """ Builds the request from DAIDE bytes """
        super(HelloRequest, self).parse_bytes(daide_bytes)

        # Parsing
        lead_token, daide_bytes = parse_bytes(SingleToken, daide_bytes)
        assert str(lead_token) == 'HLO', 'Expected HLO request'
        assert not daide_bytes, '%s bytes remaining. Request is malformed' % len(daide_bytes)

class MapRequest(DaideRequest):
    """ Represents a MAP DAIDE request. Sent by the client to request a copy of the MAP message.

        Syntax: ::

            MAP
    """
    __slots__ = []
    params = {}

    def parse_bytes(self, daide_bytes):
        """ Builds the request from DAIDE bytes """
        super(MapRequest, self).parse_bytes(daide_bytes)

        # Parsing
        lead_token, daide_bytes = parse_bytes(SingleToken, daide_bytes)
        assert str(lead_token) == 'MAP', 'Expected MAP request'
        assert not daide_bytes, '%s bytes remaining. Request is malformed' % len(daide_bytes)

class MapDefinitionRequest(DaideRequest):
    """ Represents a MDF DAIDE request. Sent by the client to request the map definition of the game.

        Syntax: ::

            MDF
    """
    __slots__ = []
    params = {}

    def parse_bytes(self, daide_bytes):
        """ Builds the request from DAIDE bytes """
        super(MapDefinitionRequest, self).parse_bytes(daide_bytes)

        # Parsing
        lead_token, daide_bytes = parse_bytes(SingleToken, daide_bytes)
        assert str(lead_token) == 'MDF', 'Expected MDF request'
        assert not daide_bytes, '%s bytes remaining. Request is malformed' % len(daide_bytes)


# ====================
# Game updates
# ====================

class SupplyCentreOwnershipRequest(DaideRequest):
    """ Represents a SCO DAIDE request. Sent by the client to request a copy of the last SCO message.

        Syntax: ::

            SCO
    """
    __slots__ = []
    params = {}

    def parse_bytes(self, daide_bytes):
        """ Builds the request from DAIDE bytes """
        super(SupplyCentreOwnershipRequest, self).parse_bytes(daide_bytes)

        # Parsing
        lead_token, daide_bytes = parse_bytes(SingleToken, daide_bytes)
        assert str(lead_token) == 'SCO', 'Expected SCO request'
        assert not daide_bytes, '%s bytes remaining. Request is malformed' % len(daide_bytes)

class CurrentPositionRequest(DaideRequest):
    """ Represents a NOW DAIDE request. Sent by the client to request a copy of the last NOW message.

        Syntax: ::

            NOW
    """
    __slots__ = []
    params = {}

    def parse_bytes(self, daide_bytes):
        """ Builds the request from DAIDE bytes """
        super(CurrentPositionRequest, self).parse_bytes(daide_bytes)

        # Parsing
        lead_token, daide_bytes = parse_bytes(SingleToken, daide_bytes)
        assert str(lead_token) == 'NOW', 'Expected NOW request'
        assert not daide_bytes, '%s bytes remaining. Request is malformed' % len(daide_bytes)

class HistoryRequest(DaideRequest):
    """ Represents a HST DAIDE request. Sent by the client to request a copy of a previous ORD, SCO and NOW messages.

        Syntax: ::

            HST (turn)
    """
    def __init__(self, **kwargs):
        """ Constructor """
        self.phase = ''
        super(HistoryRequest, self).__init__(**kwargs)

    def parse_bytes(self, daide_bytes):
        """ Builds the request from DAIDE bytes """
        super(HistoryRequest, self).parse_bytes(daide_bytes)

        # Parsing
        lead_token, daide_bytes = parse_bytes(SingleToken, daide_bytes)
        assert str(lead_token) == 'HST', 'Expected HST request'

        # Turn
        turn, daide_bytes = parse_bytes(Turn, daide_bytes)
        assert not daide_bytes, '%s bytes remaining. Request is malformed' % len(daide_bytes)

        # Setting properties
        self.phase = str(turn)


# ====================
# Orders
# ====================

class SubmitOrdersRequest(DaideRequest):
    """ Represents a SUB DAIDE request. Sent by the client to submit orders.

        Syntax: ::

            SUB (order) (order) ...
            SUB (turn) (order) (order) ...

        order syntax: ::

            (unit) HLD                                       # Hold
            (unit) MTO province                              # Move to
            (unit) SUP (unit)                                # Support
            (unit) SUP (unit) MTO (prov_no_coast)            # Support to move
            (unit) CVY (unit) CTO province                   # Convoy
            (unit) CTO province VIA (sea_prov sea_prov ...)  # Convoy to via provinces
            (unit) RTO province                              # Retreat to
            (unit) DSB                                       # Disband (R phase)
            (unit) BLD                                       # Build
            (unit) REM                                       # Remove (A phase)
            (unit) WVE                                       # Waive
    """
    __slots__ = ['power_name', 'orders']
    params = {
        strings.POWER_NAME: parsing.OptionalValueType(str),
        strings.ORDERS: parsing.SequenceType(str)
    }

    def __init__(self, **kwargs):
        """ Constructor """
        self.power_name = None
        self.phase = ''
        self.orders = []
        super(SubmitOrdersRequest, self).__init__(power_name='', orders=[], **kwargs)

    def parse_bytes(self, daide_bytes):
        """ Builds the request from DAIDE bytes """
        super(SubmitOrdersRequest, self).parse_bytes(daide_bytes)
        orders = []

        # Parsing
        lead_token, daide_bytes = parse_bytes(SingleToken, daide_bytes)
        turn, daide_bytes = parse_bytes(Turn, daide_bytes, on_error='ignore')
        while daide_bytes:
            order, daide_bytes = parse_bytes(Order, daide_bytes)
            orders += [order]
        assert str(lead_token) == 'SUB', 'Expected SUB request'
        assert not daide_bytes, '%s bytes remaining. Request is malformed' % len(daide_bytes)

        # Setting properties
        self.phase = '' if not turn else str(turn)
        self.power_name = None if not orders or not orders[0].power_name else str(orders[0].power_name)
        self.orders = [str(order) for order in orders]

class MissingOrdersRequest(DaideRequest):
    """ Represents a MIS DAIDE request. Sent by the client to request a copy of the current MIS message.

        Syntax: ::

            MIS
    """
    __slots__ = []
    params = {}

    def parse_bytes(self, daide_bytes):
        """ Builds the request from DAIDE bytes """
        super(MissingOrdersRequest, self).parse_bytes(daide_bytes)

        # Parsing
        lead_token, daide_bytes = parse_bytes(SingleToken, daide_bytes)
        assert str(lead_token) == 'MIS', 'Expected MIS request'
        assert not daide_bytes, '%s bytes remaining. Request is malformed' % len(daide_bytes)

class GoFlagRequest(DaideRequest):
    """ Represents a GOF DAIDE request. Sent by the client to notify that the client is ready to process the turn.

        Syntax: ::

            GOF
    """
    __slots__ = []
    params = {}

    def parse_bytes(self, daide_bytes):
        """ Builds the request from DAIDE bytes """
        super(GoFlagRequest, self).parse_bytes(daide_bytes)

        # Parsing
        lead_token, daide_bytes = parse_bytes(SingleToken, daide_bytes)
        assert str(lead_token) == 'GOF', 'Expected GOF request'
        assert not daide_bytes, '%s bytes remaining. Request is malformed' % len(daide_bytes)


# ====================
# Deadline
# ====================

class TimeToDeadlineRequest(DaideRequest):
    """ Represents a TME DAIDE request. Sent by the client to request a TME message or to request it at a later time.

        Syntax: ::

            TME
            TME (seconds)
    """
    __slots__ = ['seconds']
    params = {
        strings.SECONDS: parsing.OptionalValueType(int)
    }

    def __init__(self, **kwargs):
        """ Constructor """
        self.seconds = None
        super(TimeToDeadlineRequest, self).__init__(seconds=0, **kwargs)

    def parse_bytes(self, daide_bytes):
        """ Builds the request from DAIDE bytes """
        super(TimeToDeadlineRequest, self).parse_bytes(daide_bytes)

        # Parsing
        lead_token, daide_bytes = parse_bytes(SingleToken, daide_bytes)
        seconds_group_bytes, daide_bytes = break_next_group(daide_bytes)
        assert str(lead_token) == 'TME', 'Expected TME request'

        # Seconds
        if seconds_group_bytes:
            seconds_group_bytes = strip_parentheses(seconds_group_bytes)
            seconds, daide_bytes = parse_bytes(Number, seconds_group_bytes)
        assert not daide_bytes, '%s bytes remaining. Request is malformed' % len(daide_bytes)

        # Setting properties
        self.seconds = None if not seconds_group_bytes else int(seconds)


# ====================
# End of the game
# ====================

class DrawRequest(DaideRequest):
    """ Represents a DRW DAIDE request. Sent by the client to notify that the client would accept a draw.

        Syntax: ::

            DRW

        LVL 10: ::

            DRW (power power ...)
    """
    __slots__ = ['powers']
    params = {
        strings.POWERS: parsing.SequenceType(str)
    }

    def __init__(self, **kwargs):
        """ Constructor """
        self.powers = []
        super(DrawRequest, self).__init__(powers=[], **kwargs)

    def parse_bytes(self, daide_bytes):
        """ Builds the request from DAIDE bytes """
        super(DrawRequest, self).parse_bytes(daide_bytes)
        powers = []

        # Parsing
        lead_token, daide_bytes = parse_bytes(SingleToken, daide_bytes)
        assert str(lead_token) == 'DRW', 'Expected DRW request'

        # Powers
        powers_group_bytes, daide_bytes = break_next_group(daide_bytes)
        if powers_group_bytes:
            powers_group_bytes = strip_parentheses(powers_group_bytes)
            while powers_group_bytes:
                power, powers_group_bytes = parse_bytes(Power, powers_group_bytes)
                powers += [power]

        assert not daide_bytes, '%s bytes remaining. Request is malformed' % len(daide_bytes)

        # Setting properties
        self.powers = [str(power) for power in powers]


# ====================
# Messaging
# ====================

class SendMessageRequest(DaideRequest):
    """ Represents a SND DAIDE request

        Syntax: ::

            SND (power ...) (press_message)
            SND (power ...) (reply)
            SND (turn) (power ...) (press_message)
            SND (turn) (power ...) (reply)

        Press message syntax: ::

            PRP (arrangement)
            CCL (press_message)
            FCT (arrangement)
            TRY (tokens)

        Reply syntax: ::

            YES (press_message)
            REJ (press_message)
            BWX (press_message)
            HUH (press_message)
    """
    __slots__ = ['powers', 'message_bytes']
    params = {
        strings.POWERS: parsing.SequenceType(str),
        strings.MESSAGE_BYTES: parsing.OptionalValueType(str),
    }

    def __init__(self, **kwargs):
        """ Constructor """
        self.phase = ''
        self.powers = []
        self.message_bytes = None
        super(SendMessageRequest, self).__init__(powers=[], press_message='', reply='', **kwargs)

    def parse_bytes(self, daide_bytes):
        """ Builds the request from DAIDE bytes """
        super(SendMessageRequest, self).parse_bytes(daide_bytes)

        # Parsing
        lead_token, daide_bytes = parse_bytes(SingleToken, daide_bytes)
        assert str(lead_token) == 'SND', 'Expected SND request'

        # Turn
        turn, daide_bytes = parse_bytes(Turn, daide_bytes, on_error='ignore')

        # Powers
        powers = []
        powers_group_bytes, daide_bytes = break_next_group(daide_bytes)
        powers_group_bytes = strip_parentheses(powers_group_bytes)
        while powers_group_bytes:
            power, powers_group_bytes = parse_bytes(Power, powers_group_bytes)
            powers += [power]
        assert powers, 'Expected a group of `power`. Request is malformed'

        # Press message or reply
        message_group_bytes, daide_bytes = break_next_group(daide_bytes)
        message_group_bytes = strip_parentheses(message_group_bytes)
        assert message_group_bytes, 'Expected a `press_message` or a `reply`. Request is malformed'
        assert not daide_bytes, '%s bytes remaining. Request is malformed' % len(daide_bytes)

        # Setting properties
        self.phase = '' if not turn else str(turn)
        self.powers = [str(power) for power in powers]
        self.message_bytes = message_group_bytes

# ====================
# Cancel Request
# ====================

class NotRequest(DaideRequest):
    """ Represents a NOT DAIDE request. Sent by the client to cancel a previous request.

        Syntax: ::

            NOT (SUB)                       # Cancel all submitted orders
            NOT (SUB (order))               # Cancel specific submitted order
            NOT (GOF)                       # Do not process orders until the deadline
            NOT (TME)                       # Cancel all requested time messages
            NOT (TME (seconds))             # Cancel specific requested time message
            NOT (DRW)                       # Cancel all draw requests
    """
    __slots__ = ['request']
    params = {
        strings.REQUEST: parsing.JsonableClassType(DaideRequest)
    }

    def __init__(self, **kwargs):
        """ Constructor """
        self.request = None                             # type: DaideRequest
        super(NotRequest, self).__init__(request=DaideRequest(), **kwargs)

    def parse_bytes(self, daide_bytes):
        """ Builds the request from DAIDE bytes """
        super(NotRequest, self).parse_bytes(daide_bytes)

        # Parsing
        lead_token, daide_bytes = parse_bytes(SingleToken, daide_bytes)
        request_group_bytes, daide_bytes = break_next_group(daide_bytes)
        assert str(lead_token) == 'NOT', 'Expected NOT request'

        # Request
        request_group_bytes = strip_parentheses(request_group_bytes)
        request = RequestBuilder.from_bytes(request_group_bytes)
        assert not daide_bytes, '%s bytes remaining. Request is malformed' % len(daide_bytes)

        # Setting properties
        self.request = request

# ========================
# Accept / Reject Response
# ========================

class AcceptRequest(DaideRequest):
    """ Represents a YES DAIDE request.

        Syntax: ::

            YES (MAP ('name'))
            YES (SVE ('gamename'))
    """
    __slots__ = ['response_bytes']
    params = {
        strings.RESPONSE_BYTES: bytes
    }

    def __init__(self, **kwargs):
        """ Constructor """
        self.response_bytes = b''
        super(AcceptRequest, self).__init__(response_bytes=b'', **kwargs)

    def parse_bytes(self, daide_bytes):
        """ Builds the request from DAIDE bytes """
        super(AcceptRequest, self).parse_bytes(daide_bytes)

        # Parsing
        lead_token, daide_bytes = parse_bytes(SingleToken, daide_bytes)
        response_bytes, daide_bytes = break_next_group(daide_bytes)
        response_bytes = strip_parentheses(response_bytes)
        assert str(lead_token) == 'YES', 'Expected YES request'
        assert not daide_bytes, '%s bytes remaining. Request is malformed' % len(daide_bytes)

        # Setting properties
        self.response_bytes = response_bytes

class RejectRequest(DaideRequest):
    """ Represents a REJ DAIDE request.

        Syntax: ::

            REJ (SVE ('gamename'))
    """
    __slots__ = ['response_bytes']
    params = {
        strings.RESPONSE_BYTES: bytes
    }

    def __init__(self, **kwargs):
        """ Constructor """
        self.response_bytes = b''
        super(RejectRequest, self).__init__(response_bytes=b'', **kwargs)

    def parse_bytes(self, daide_bytes):
        """ Builds the request from DAIDE bytes """
        super(RejectRequest, self).parse_bytes(daide_bytes)

        # Parsing
        lead_token, daide_bytes = parse_bytes(SingleToken, daide_bytes)
        response_bytes, daide_bytes = break_next_group(daide_bytes)
        response_bytes = strip_parentheses(response_bytes)
        assert str(lead_token) == 'REJ', 'Expected REJ request'
        assert not daide_bytes, '%s bytes remaining. Request is malformed' % len(daide_bytes)

        # Setting properties
        self.response_bytes = response_bytes

# ====================
# Errors
# ====================

class ParenthesisErrorRequest(DaideRequest):
    """ Represents a PRN DAIDE request. Sent by the client to specify an error in the set of parenthesis.

        Syntax: ::

            PRN (message)
    """
    __slots__ = ['message_bytes']
    params = {
        strings.MESSAGE_BYTES: bytes
    }

    def __init__(self, **kwargs):
        """ Constructor """
        self.message_bytes = b''
        super(ParenthesisErrorRequest, self).__init__(message_bytes=b'', **kwargs)

    def parse_bytes(self, daide_bytes):
        """ Builds the request from DAIDE bytes """
        super(ParenthesisErrorRequest, self).parse_bytes(daide_bytes)

        # Parsing
        lead_token, daide_bytes = parse_bytes(SingleToken, daide_bytes)
        message_bytes, daide_bytes = break_next_group(daide_bytes)
        if message_bytes:
            message_bytes = strip_parentheses(message_bytes)
        else:
            message_bytes = strip_parentheses(daide_bytes)
            daide_bytes = b''
        assert str(lead_token) == 'PRN', 'Expected PRN request'
        assert not daide_bytes, '%s bytes remaining. Request is malformed' % len(daide_bytes)

        # Setting properties
        self.message_bytes = message_bytes

class SyntaxErrorRequest(DaideRequest):
    """ Represents a HUH DAIDE request. Sent by the client to specify an error in a message.

        Syntax: ::

            HUH (message)
    """
    __slots__ = ['message_bytes']
    params = {
        strings.MESSAGE_BYTES: bytes
    }

    def __init__(self, **kwargs):
        """ Constructor """
        self.message_bytes = b''
        super(SyntaxErrorRequest, self).__init__(message_bytes=b'', **kwargs)

    def parse_bytes(self, daide_bytes):
        """ Builds the request from DAIDE bytes """
        super(SyntaxErrorRequest, self).parse_bytes(daide_bytes)

        # Parsing
        lead_token, daide_bytes = parse_bytes(SingleToken, daide_bytes)
        message_bytes, daide_bytes = break_next_group(daide_bytes)
        message_bytes = strip_parentheses(message_bytes)
        assert str(lead_token) == 'HUH', 'Expected HUH request'
        assert not daide_bytes, '%s bytes remaining. Request is malformed' % len(daide_bytes)

        # Setting properties
        self.message_bytes = message_bytes


# ====================
# Admin Messages
# ====================

class AdminMessageRequest(DaideRequest):
    """ Represents a ADM DAIDE request. Can be sent by the client to send a message to all clients.
        Should not be used for negotiation.

        Syntax: ::

            ADM ('message')
    """
    __slots__ = ['adm_message']
    params = {
        strings.ADM_MESSAGE: str
    }

    def __init__(self, **kwargs):
        """ Constructor """
        self.adm_message = ''
        super(AdminMessageRequest, self).__init__(adm_message='', **kwargs)

    def parse_bytes(self, daide_bytes):
        """ Builds the request from DAIDE bytes """
        super(AdminMessageRequest, self).parse_bytes(daide_bytes)

        # Parsing
        lead_token, daide_bytes = parse_bytes(SingleToken, daide_bytes)
        adm_message, daide_bytes = parse_bytes(String, daide_bytes)
        assert str(lead_token) == 'ADM', 'Expected ADM request'
        assert not daide_bytes, '%s bytes remaining. Request is malformed' % len(daide_bytes)

        # Setting properties
        self.adm_message = str(adm_message)

# =====================
# Constants and aliases
# =====================
NME = NameRequest
OBS = ObserverRequest
IAM = IAmRequest
HLO = HelloRequest
MAP = MapRequest
MDF = MapDefinitionRequest
SCO = SupplyCentreOwnershipRequest
NOW = CurrentPositionRequest
HST = HistoryRequest
SUB = SubmitOrdersRequest
MIS = MissingOrdersRequest
GOF = GoFlagRequest
TME = TimeToDeadlineRequest
DRW = DrawRequest
SND = SendMessageRequest
NOT = NotRequest
YES = AcceptRequest
REJ = RejectRequest
PRN = ParenthesisErrorRequest
HUH = SyntaxErrorRequest
ADM = AdminMessageRequest

# Constants
__REQUEST_CONSTRUCTORS__ = {bytes(tokens.NME): NME,
                            bytes(tokens.OBS): OBS,
                            bytes(tokens.IAM): IAM,
                            bytes(tokens.HLO): HLO,
                            bytes(tokens.MAP): MAP,
                            bytes(tokens.MDF): MDF,
                            bytes(tokens.SCO): SCO,
                            bytes(tokens.NOW): NOW,
                            bytes(tokens.HST): HST,
                            bytes(tokens.SUB): SUB,
                            bytes(tokens.MIS): MIS,
                            bytes(tokens.GOF): GOF,
                            bytes(tokens.TME): TME,
                            bytes(tokens.DRW): DRW,
                            bytes(tokens.SND): SND,
                            bytes(tokens.NOT): NOT,
                            bytes(tokens.YES): YES,
                            bytes(tokens.REJ): REJ,
                            bytes(tokens.PRN): PRN,
                            bytes(tokens.HUH): HUH,
                            bytes(tokens.ADM): ADM}
