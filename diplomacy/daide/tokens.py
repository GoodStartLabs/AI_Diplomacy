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
""" Contains the list of valid tokens and their byte representation """

# Constants
BYTES_TO_STR = {}         # (0x46, 0x04) -> 'ECS'
STR_TO_BYTES = {}         # 'ECS' -> (0x46, 0x04)
ASCII_BYTE = 0x4B         # Byte identifying an ASCII char

# Utilities
class Token:
    """ Contains the representation of a token """

    def __init__(self, from_str=None, from_int=None, from_bytes=None):
        """ Initialize a token from its string representation, or from its bytes representation

            :param from_str: The string representation of the token
            :param from_int: The integer representation of the token
            :param from_bytes: The byte representation of the token
        """
        self.repr_str = ''
        self.repr_int = None
        self.repr_bytes = b''

        # From string
        if from_str is not None:
            assert from_int is None, 'Cannot provide both a string and an integer'
            assert from_bytes is None, 'Cannot provide both a string and bytes'
            self._load_from_str(str(from_str))

        # From integer
        elif from_int is not None:
            assert from_bytes is None, 'Cannot provide both an integer and bytes'
            self._load_from_int(int(from_int))

        # From bytes
        elif from_bytes is not None:
            self._load_from_bytes(from_bytes)

        else:
            raise ValueError('You must provide a string, integer, or bytes representation')

    def _load_from_str(self, from_str):
        """ Creates a token from a DAIDE string representation"""
        assert isinstance(from_str, str), 'Expected a string'

        # 1) Known token
        # 2) ASCII Text
        if from_str in STR_TO_BYTES:
            self.repr_str = BYTES_TO_STR[STR_TO_BYTES[from_str]]
            self.repr_bytes = STR_TO_BYTES[from_str]
        elif len(from_str) == 1 and ord(from_str[0]) <= 255:
            self.repr_str = from_str
            self.repr_bytes = bytes((ASCII_BYTE, ord(from_str[0])))
        else:
            raise ValueError('Unable to parse %s as a token' % from_str)

    def _load_from_int(self, from_int):
        """ Creates a token from an integer representation """
        assert isinstance(from_int, int), 'Expected an integer'

        # Integers - Encoded as 14 bits
        if from_int > 8191 or from_int < -8192:
            raise ValueError('Valid values for strings are -8192 to +8191.')

        # Negative numbers start with a 1
        prefix = '0'
        if from_int < 0:
            prefix = '1'
            from_int += 8192

        # Encoding the number as 14 bit. + a prefix of '00' for a total of 16 bit
        bit_encoding = bin(from_int)[2:]
        bit_encoding = '00' + prefix + '0' * (13 - len(bit_encoding)) + bit_encoding
        self.repr_str = str(from_int)
        self.repr_int = from_int
        self.repr_bytes = bytes((int(bit_encoding[0:8], 2), int(bit_encoding[8:16], 2)))

    def _load_from_bytes(self, from_bytes):
        """ Creates a token from its bytes representation """
        if isinstance(from_bytes, tuple):
            from_bytes = bytes(from_bytes)
        if len(from_bytes) != 2:
            raise ValueError('Expected a couple of 2 bytes 0x000xFF. Got [{}]' \
                             .format(''.join([hex(b) for b in from_bytes])))

        # Known token
        if from_bytes in BYTES_TO_STR:
            self.repr_str = BYTES_TO_STR[from_bytes]
            self.repr_bytes = from_bytes

        # Ascii text
        elif from_bytes[0] == ASCII_BYTE:
            self.repr_str = chr(from_bytes[1])
            self.repr_bytes = from_bytes

        # Integer
        elif from_bytes[0] < 64:
            bin_0, bin_1 = bin(from_bytes[0])[2:], bin(from_bytes[1])[2:]
            from_binary = '0' * (6 - len(bin_0)) + bin_0 + '0' * (8 - len(bin_1)) + bin_1
            is_negative = int(from_binary[0] == '1')
            self.repr_int = is_negative * -8192 + int(from_binary[1:14], 2)
            self.repr_str = str(self.repr_int)
            self.repr_bytes = from_bytes

        else:
            # Unknown value
            raise ValueError('Unable to parse bytes %s as a token' % (from_bytes,))

    def __bytes__(self):
        """ Returns bytes representation """
        return self.repr_bytes

    def __int__(self):
        """ Returns integer representation """
        return self.repr_int

    def __str__(self):
        """ Returns string representation """
        return self.repr_str

    def __eq__(self, other):
        """ Define the equal """
        return isinstance(other, Token) and ((self.repr_int and self.repr_int == other.repr_int)
                                             or self.repr_str == other.repr_str)

def is_ascii_token(token):
    """ Check if the token is an ascii token

        :param token: An instance of Token
        :return: True if `token` is an acsii token. False otherwise
    """
    return isinstance(token, Token) and \
           len(token.repr_bytes) == 2 and token.repr_bytes[0] == ASCII_BYTE

def is_integer_token(token):
    """ Check if the token is an integer token

        :param token: An instance of Token
        :return: True if `token` is an integer token. False otherwise
    """
    return isinstance(token, Token) and \
           len(token.repr_bytes) == 2 and token.repr_bytes[0] < 64

def register_token(str_repr, bytes_repr):
    """ Registers a token in the registry

        :param str_repr: The DAIDE string representation of the token (e.g. 'ECS')
        :param bytes_repr: The bytes representation of the token (i.e. bytes of length 2)
        :return: The token that has been registered
    """
    if str_repr in STR_TO_BYTES:
        raise ValueError('String %s has already been registered.' % str_repr)
    if bytes_repr in BYTES_TO_STR:
        raise ValueError('Bytes %s have already been registered.' % bytes_repr)
    STR_TO_BYTES[str_repr] = bytes_repr
    BYTES_TO_STR[bytes_repr] = str_repr
    return Token(from_str=str_repr)


# ------------------------
# Registering tokens
# Coasts
ECS = register_token('ECS', b'\x46\x04')                       # ECS Coast East Coast
NCS = register_token('NCS', b'\x46\x00')                       # NCS Coast North Coast
NEC = register_token('NEC', b'\x46\x02')                       # NEC Coast North East Coast
NWC = register_token('NWC', b'\x46\x0E')                       # NWC Coast North West Coast
SCS = register_token('SCS', b'\x46\x08')                       # SCS Coast South Coast
SEC = register_token('SEC', b'\x46\x06')                       # SEC Coast South East Coast
SWC = register_token('SWC', b'\x46\x0A')                       # SWC Coast South West Coast
WCS = register_token('WCS', b'\x46\x0C')                       # WCS Coast West Coast
COAST_TOKENS = [ECS, NCS, NEC, NWC, SCS, SEC, SWC, WCS]

# Orders
BLD = register_token('BLD', b'\x43\x80')                       # BLD Order Build Phase Build
CTO = register_token('CTO', b'\x43\x20')                       # CTO Order Movement Phase Move by Convoy to
CVY = register_token('CVY', b'\x43\x21')                       # CVY Order Movement Phase Convoy
DSB = register_token('DSB', b'\x43\x40')                       # DSB Order Retreat Phase Disband
HLD = register_token('HLD', b'\x43\x22')                       # HLD Order Movement Phase Hold
MTO = register_token('MTO', b'\x43\x23')                       # MTO Order Movement Phase Move To
REM = register_token('REM', b'\x43\x81')                       # REM Order Build Phase Remove
RTO = register_token('RTO', b'\x43\x41')                       # RTO Order Retreat Phase Retreat to
SUP = register_token('SUP', b'\x43\x24')                       # SUP Order Movement Phase Support
VIA = register_token('VIA', b'\x43\x25')                       # VIA Order Movement Phase Move via
WVE = register_token('WVE', b'\x43\x82')                       # WVE Order Build Phase Waive
ORDER_TOKENS = [BLD, CTO, CVY, DSB, HLD, MTO, REM, RTO, SUP, VIA, WVE]
MOVEMENT_ORDER_TOKENS = [CTO, CVY, HLD, MTO, SUP]
RETREAT_ORDER_TOKENS = [RTO, DSB]
BUILD_ORDER_TOKENS = [BLD, REM, WVE]

# Seasons
AUT = register_token('AUT', b'\x47\x03')                       # AUT Phase Fall Retreats
FAL = register_token('FAL', b'\x47\x02')                       # FAL Phase Fall Movements
SPR = register_token('SPR', b'\x47\x00')                       # SPR Phase Spring Movement
SUM = register_token('SUM', b'\x47\x01')                       # SUM Phase Spring Retreats
WIN = register_token('WIN', b'\x47\x04')                       # WIN Phase Fall Builds
SEASON_TOKENS = [AUT, FAL, SPR, SUM, WIN]

# Powers
AUS = register_token('AUS', b'\x41\x00')                       # AUS Power Austria
ENG = register_token('ENG', b'\x41\x01')                       # ENG Power England
FRA = register_token('FRA', b'\x41\x02')                       # FRA Power France
GER = register_token('GER', b'\x41\x03')                       # GER Power Germany
ITA = register_token('ITA', b'\x41\x04')                       # ITA Power Italy
RUS = register_token('RUS', b'\x41\x05')                       # RUS Power Russia
TUR = register_token('TUR', b'\x41\x06')                       # TUR Power Turkey
POWER_TOKENS = [AUS, ENG, FRA, GER, ITA, RUS, TUR]

# Units
AMY = register_token('AMY', b'\x42\x00')                       # AMY Unit Type Army
FLT = register_token('FLT', b'\x42\x01')                       # FLT Unit Type Fleet

# Symbols
OPE_PAR = register_token('(', b'\x40\x00')                     # BRA - ( - Opening Bracket
CLO_PAR = register_token(')', b'\x40\x01')                     # KET - ) - Closing Bracket

# Provinces
ADR = register_token('ADR', b'\x52\x0E')                       # ADR Province Sea Adriatic Sea
AEG = register_token('AEG', b'\x52\x0F')                       # AEG Province Sea Aegean Sea
ALB = register_token('ALB', b'\x54\x21')                       # ALB Province Coastal Albania
ANK = register_token('ANK', b'\x55\x30')                       # ANK Province Coastal Supply Center Ankara
APU = register_token('APU', b'\x54\x22')                       # APU Province Coastal Apulia
ARM = register_token('ARM', b'\x54\x23')                       # ARM Province Coastal Armenia
BAL = register_token('BAL', b'\x52\x10')                       # BAL Province Sea Baltic Sea
BAR = register_token('BAR', b'\x52\x11')                       # BAR Province Sea Barents Sea
BEL = register_token('BEL', b'\x55\x31')                       # BEL Province Coastal Supply Center Belgium
BER = register_token('BER', b'\x55\x32')                       # BER Province Coastal Supply Center Berlin
BLA = register_token('BLA', b'\x52\x12')                       # BLA Province Sea Black Sea
BOH = register_token('BOH', b'\x50\x00')                       # BOH Province Inland Bohemia
BRE = register_token('BRE', b'\x55\x33')                       # BRE Province Coastal Supply Center Brest
BUD = register_token('BUD', b'\x51\x07')                       # BUD Province Inland Supply Center Budapest
BUL = register_token('BUL', b'\x57\x48')                       # BUL Province Bicoastal Supply Center Bulgaria
BUR = register_token('BUR', b'\x50\x01')                       # BUR Province Inland Burgundy
CLY = register_token('CLY', b'\x54\x24')                       # CLY Province Coastal Clyde
CON = register_token('CON', b'\x55\x34')                       # CON Province Coastal Supply Center Constantinople
DEN = register_token('DEN', b'\x55\x35')                       # DEN Province Coastal Supply Center Denmark
EAS = register_token('EAS', b'\x52\x13')                       # EAS Province Sea Eastern Mediterranean Sea
ECH = register_token('ECH', b'\x52\x14')                       # ECH Province Sea English Channel
EDI = register_token('EDI', b'\x55\x36')                       # EDI Province Coastal Supply Center Edinburgh
FIN = register_token('FIN', b'\x54\x25')                       # FIN Province Coastal Finland
GAL = register_token('GAL', b'\x50\x02')                       # GAL Province Inland Galecia
GAS = register_token('GAS', b'\x54\x26')                       # GAS Province Coastal Gascony
GOB = register_token('GOB', b'\x52\x15')                       # GOB Province Sea Gulf of Bothnia
GOL = register_token('GOL', b'\x52\x16')                       # GOL Province Sea Gulf of Lyons
GRE = register_token('GRE', b'\x55\x37')                       # GRE Province Coastal Supply Center Greece
HEL = register_token('HEL', b'\x52\x17')                       # HEL Province Sea Helgoland Bight
HOL = register_token('HOL', b'\x55\x38')                       # HOL Province Coastal Supply Center Holland
ION = register_token('ION', b'\x52\x18')                       # ION Province Sea Ionian Sea
IRI = register_token('IRI', b'\x52\x19')                       # IRI Province Sea Irish Sea
KIE = register_token('KIE', b'\x55\x39')                       # KIE Province Coastal Supply Center Kiel
LON = register_token('LON', b'\x55\x3A')                       # LON Province Coastal Supply Center London
LVN = register_token('LVN', b'\x54\x27')                       # LVN Province Coastal Livonia
LVP = register_token('LVP', b'\x55\x3B')                       # LVP Province Coastal Supply Center Liverpool
MAO = register_token('MAO', b'\x52\x1A')                       # MAO Province Sea Mid Atlantic Ocean
MAR = register_token('MAR', b'\x55\x3C')                       # MAR Province Coastal Supply Center Marseilles
MOS = register_token('MOS', b'\x51\x08')                       # MOS Province Inland Supply Center Moscow
MUN = register_token('MUN', b'\x51\x09')                       # MUN Province Inland Supply Center Munich
NAF = register_token('NAF', b'\x54\x28')                       # NAF Province Coastal North Africa
NAO = register_token('NAO', b'\x52\x1B')                       # NAO Province Sea North Atlantic Ocean
NAP = register_token('NAP', b'\x55\x3D')                       # NAP Province Coastal Supply Center Naples
NTH = register_token('NTH', b'\x52\x1C')                       # NTH Province Sea North Sea
NWG = register_token('NWG', b'\x52\x1D')                       # NWG Province Sea Norwegian Sea
NWY = register_token('NWY', b'\x55\x3E')                       # NWY Province Coastal Supply Center Norway
PAR = register_token('PAR', b'\x51\x0A')                       # PAR Province Inland Supply Center Paris
PIC = register_token('PIC', b'\x54\x29')                       # PIC Province Coastal Picardy
PIE = register_token('PIE', b'\x54\x2A')                       # PIE Province Coastal Piedmont
POR = register_token('POR', b'\x55\x3F')                       # POR Province Coastal Supply Center Portugal
PRU = register_token('PRU', b'\x54\x2B')                       # PRU Province Coastal Prussia
ROM = register_token('ROM', b'\x55\x40')                       # ROM Province Coastal Supply Center Rome
RUH = register_token('RUH', b'\x50\x03')                       # RUH Province Inland Ruhr
RUM = register_token('RUM', b'\x55\x41')                       # RUM Province Coastal Supply Center Rumania
SER = register_token('SER', b'\x51\x0B')                       # SER Province Inland Supply Center Serbia
SEV = register_token('SEV', b'\x55\x42')                       # SEV Province Coastal Supply Center Sevastopol
SIL = register_token('SIL', b'\x50\x04')                       # SIL Province Inland Silesia
SKA = register_token('SKA', b'\x52\x1E')                       # SKA Province Sea Skaggerack
SMY = register_token('SMY', b'\x55\x43')                       # SMY Province Coastal Supply Center Smyrna
SPA = register_token('SPA', b'\x57\x49')                       # SPA Province Bicoastal Supply Center Spain
STP = register_token('STP', b'\x57\x4A')                       # STP Province Bicoastal Supply Center St Petersburg
SWE = register_token('SWE', b'\x55\x44')                       # SWE Province Coastal Supply Center Sweden
SYR = register_token('SYR', b'\x54\x2C')                       # SYR Province Coastal Syria
TRI = register_token('TRI', b'\x55\x45')                       # TRI Province Coastal Supply Center Trieste
TUN = register_token('TUN', b'\x55\x46')                       # TUN Province Coastal Supply Center Tunis
TUS = register_token('TUS', b'\x54\x2D')                       # TUS Province Coastal Tuscany
TYR = register_token('TYR', b'\x50\x05')                       # TYR Province Inland Tyrolia
TYS = register_token('TYS', b'\x52\x1F')                       # TYS Province Sea Tyrrhenian Sea
UKR = register_token('UKR', b'\x50\x06')                       # UKR Province Inland Ukraine
VEN = register_token('VEN', b'\x55\x47')                       # VEN Province Coastal Supply Center Venice
VIE = register_token('VIE', b'\x51\x0C')                       # VIE Province Inland Supply Center Vienna
WAL = register_token('WAL', b'\x54\x2E')                       # WAL Province Coastal Wales
WAR = register_token('WAR', b'\x51\x0D')                       # WAR Province Inland Supply Center Warsaw
WES = register_token('WES', b'\x52\x20')                       # WES Province Sea Western Mediterranean Sea
YOR = register_token('YOR', b'\x54\x2F')                       # YOR Province Coastal Yorkshire
PROVINCE_TOKENS = [ADR, AEG, ALB, ANK, APU, ARM, BAL, BAR,
                   BEL, BER, BLA, BOH, BRE, BUD, BUL, BUR,
                   CLY, CON, DEN, EAS, ECH, EDI, FIN, GAL,
                   GAS, GOB, GOL, GRE, HEL, HOL, ION, IRI,
                   KIE, LON, LVN, LVP, MAO, MAR, MOS, MUN,
                   NAF, NAO, NAP, NTH, NWG, NWY, PAR, PIC,
                   PIE, POR, PRU, ROM, RUH, RUM, SER, SEV,
                   SIL, SKA, SMY, SPA, STP, SWE, SYR, TRI,
                   TUN, TUS, TYR, TYS, UKR, VEN, VIE, WAL,
                   WAR, WES, YOR]

# Commands
ADM = register_token('ADM', b'\x48\x1D')                       # AMD Command / Press Client <-> Server Admin Messages
CCD = register_token('CCD', b'\x48\x00')                       # CCD Command Server to Client Power in Civil Disorder
DRW = register_token('DRW', b'\x48\x01')                       # DRW Command / Press Client <-> Server Draw + NOT(DRW)
FRM = register_token('FRM', b'\x48\x02')                       # FRM Command / Press Server to Client Message From
GOF = register_token('GOF', b'\x48\x03')                       # GOF Command Client to Server Go Flag + NOT(GOF)
HLO = register_token('HLO', b'\x48\x04')                       # HLO Command Server to Client Hello (Start of Game)
HST = register_token('HST', b'\x48\x05')                       # HST Command Client to Server History
HUH = register_token('HUH', b'\x48\x06')                       # HUH Command / Press Server to Client Syntax Error
IAM = register_token('IAM', b'\x48\x07')                       # IAM Command Client to Server I am
LOD = register_token('LOD', b'\x48\x08')                       # LOD Command Server to Client Load Game
MAP = register_token('MAP', b'\x48\x09')                       # MAP Cmd Server to Client Map to be used for this game
MDF = register_token('MDF', b'\x48\x0A')                       # MDF Command Client <---> Server Map definition
MIS = register_token('MIS', b'\x48\x0B')                       # MIS Command Server to Client Missing Orders
NME = register_token('NME', b'\x48\x0C')                       # NME Command Client to Server Name
NOT = register_token('NOT', b'\x48\x0D')                       # NOT Command / Press Client <---> Server Logical NOT
NOW = register_token('NOW', b'\x48\x0E')                       # NOW Command Client <---> Server Current Position
OBS = register_token('OBS', b'\x48\x0F')                       # OBS Command Client to Server Observer
OFF = register_token('OFF', b'\x48\x10')                       # OFF Command Server to Client Turn Off (Exit)
ORD = register_token('ORD', b'\x48\x11')                       # ORD Command Server to Client Order Results
OUT = register_token('OUT', b'\x48\x12')                       # OUT Command Server to Client Power is Eliminated
PRN = register_token('PRN', b'\x48\x13')                       # PRN Command Server to Client Parenthesis error
REJ = register_token('REJ', b'\x48\x14')                       # REJ Command / Press Server to Client Reject
SCO = register_token('SCO', b'\x48\x15')                       # SCO Command Client <-> Server Supply Center Ownership
SLO = register_token('SLO', b'\x48\x16')                       # SLO Command Server to Client Solo
SMR = register_token('SMR', b'\x48\x1E')                       # SMR Command Server to Client Summary
SND = register_token('SND', b'\x48\x17')                       # SND Command / Press Client to Server Send Message
SUB = register_token('SUB', b'\x48\x18')                       # SUB Command Client to Server Submit Order
SVE = register_token('SVE', b'\x48\x19')                       # SVE Command Server to Client Save Game
THX = register_token('THX', b'\x48\x1A')                       # THX Command Server to Client Thanks for the order
TME = register_token('TME', b'\x48\x1B')                       # TME Command Client <---> Server Time to Deadline
YES = register_token('YES', b'\x48\x1C')                       # YES Command / Press Server to Client Accept

# Order Notes (ORD)
BNC = register_token('BNC', b'\x45\x01')                       # BNC Order Note ORD Move Bounced
CUT = register_token('CUT', b'\x45\x02')                       # CUT Order Note ORD Support Cut
DSR = register_token('DSR', b'\x45\x03')                       # DSR Order Note ORD Convoy Disrupted
FLD = register_token('FLD', b'\x45\x04')                       # FLD Order Note ORD REMOVED
NSO = register_token('NSO', b'\x45\x05')                       # NSO Order Note ORD No Such Order
RET = register_token('RET', b'\x45\x06')                       # RET Order Note ORD Unit must retreat
SUC = register_token('SUC', b'\x45\x00')                       # SUC Order Note ORD Order Succeeds
ORDER_RESULT_TOKENS = [BNC, CUT, DSR, NSO, SUC]

# Order Notes (THX)
BPR = register_token('BPR', b'\x44\x01')                       # BPR Order Note THX REMOVED
CST = register_token('CST', b'\x44\x02')                       # CST Order Note THX No Coast Specified
ESC = register_token('ESC', b'\x44\x03')                       # ESC Order Note THX Not an Empty Supply Center
FAR = register_token('FAR', b'\x44\x04')                       # FAR Order Note THX Not Adjacent
HSC = register_token('HSC', b'\x44\x05')                       # HSC Order Note THX Not a Home Supply Center
MBV = register_token('MBV', b'\x44\x00')                       # MBV Order Note THX Might Be Valid
NAS = register_token('NAS', b'\x44\x06')                       # NAS Order Note THX Not At Sea
NMB = register_token('NMB', b'\x44\x07')                       # NMB Order Note THX No More Builds Allowed
NMR = register_token('NMR', b'\x44\x08')                       # NMR Order Note THX No More Retreats Allowed
NRN = register_token('NRN', b'\x44\x09')                       # NRN Order Note THX No Retreat Needed
NRS = register_token('NRS', b'\x44\x0A')                       # NRS Order Note THX Not the Right Season
NSA = register_token('NSA', b'\x44\x0B')                       # NSA Order Note THX No Such Army
NSC = register_token('NSC', b'\x44\x0C')                       # NSC Order Note THX Not a Supply Center
NSF = register_token('NSF', b'\x44\x0D')                       # NSF Order Note THX No Such Fleet
NSP = register_token('NSP', b'\x44\x0E')                       # NSP Order Note THX No Such Province
NSU = register_token('NSU', b'\x44\x10')                       # NSU Order Note THX No Such Unit
NVR = register_token('NVR', b'\x44\x11')                       # NVR Order Note THX Not a Valid Retreat
NYU = register_token('NYU', b'\x44\x12')                       # NYU Order Note THX Not Your Unit
YSC = register_token('YSC', b'\x44\x13')                       # YSC Order Note THX Not Your Supply Center
ORDER_NOTE_TOKENS = [MBV, FAR, NSP, NSU, NAS, NSF, NSA, NYU,
                     NRN, NVR, YSC, ESC, HSC, NSC, CST, NMB,
                     NMR, NRS, FLD]

# Parameters
AOA = register_token('AOA', b'\x49\x00')                       # AOA Parameter HLO Any Orders Allowed
BTL = register_token('BTL', b'\x49\x01')                       # BTL Parameter HLO Build Time Limit
DSD = register_token('DSD', b'\x49\x0D')                       # DSD Parameter HLO Deadline stops on disconnect
ERR = register_token('ERR', b'\x49\x02')                       # ERR Parameter HUH Error location
LVL = register_token('LVL', b'\x49\x03')                       # LVL Parameter HLO Level (Language Level)
MRT = register_token('MRT', b'\x49\x04')                       # MRT Parameter NOW Must Retreat to
MTL = register_token('MTL', b'\x49\x05')                       # MTL Parameter HLO Movement Time Limit
NPB = register_token('NPB', b'\x49\x06')                       # NPB Parameter HLO No Press During Builds
NPR = register_token('NPR', b'\x49\x07')                       # NPR Parameter HLO No Press During Retreats
PDA = register_token('PDA', b'\x49\x08')                       # PDA Parameter HLO Partial Draws Allowed
PTL = register_token('PTL', b'\x49\x09')                       # PTL Parameter HLO Press Time Limit
RTL = register_token('RTL', b'\x49\x0A')                       # RTL Parameter HLO Retreat Time Limit
UNO = register_token('UNO', b'\x49\x0B')                       # UNO Parameter SCO Unowned

# Valid tokens for variant option
VARIANT_OPT_NUM_TOKENS = [LVL, MTL, RTL, BTL, PTL]
VARIANT_OPT_NO_NUM_TOKENS = [AOA, DSD, PDA, NPR, NPB]

# Press
ALY = register_token('ALY', b'\x4A\x00')                       # ALY Press Ally
AND = register_token('AND', b'\x4A\x01')                       # AND Press Logical AND
BCC = register_token('BCC', b'\x4A\x23')                       # BCC Press Request to Blind Carbon Copy
BWX = register_token('BWX', b'\x4A\x02')                       # BWX Press None of Your Business
CCL = register_token('CCL', b'\x4A\x26')                       # CCL Press Cancel
CHO = register_token('CHO', b'\x4A\x22')                       # CHO Press Choose
DMZ = register_token('DMZ', b'\x4A\x03')                       # DMZ Press Demilitarised Zone
ELS = register_token('ELS', b'\x4A\x04')                       # ELS Press IFF Else
EXP = register_token('EXP', b'\x4A\x05')                       # EXP Press Explain
FCT = register_token('FCT', b'\x4A\x06')                       # FCT Press Fact
FOR = register_token('FOR', b'\x4A\x07')                       # FOR Press For specified Turn
FWD = register_token('FWD', b'\x4A\x08')                       # FWD Press Request to Forward
HOW = register_token('HOW', b'\x4A\x09')                       # HOW Press How to attack
IDK = register_token('IDK', b'\x4A\x0A')                       # IDK Press I Do Not Know
IFF = register_token('IFF', b'\x4A\x0B')                       # IFF Press If
INS = register_token('INS', b'\x4A\x0C')                       # INS Press Insist
NAR = register_token('NAR', b'\x4A\x25')                       # NAR Press No Agreement
OCC = register_token('OCC', b'\x4A\x0E')                       # OCC Press Occupy
ORR = register_token('ORR', b'\x4A\x0F')                       # ORR Press Logical OR
PCE = register_token('PCE', b'\x4A\x10')                       # PCE Press Peace
POB = register_token('POB', b'\x4A\x11')                       # POB Press Position on Board
PRP = register_token('PRP', b'\x4A\x13')                       # PRP Press Propose
QRY = register_token('QRY', b'\x4A\x14')                       # QRY Press Query
SCD = register_token('SCD', b'\x4A\x15')                       # SCD Press Supply Center Distribution
SRY = register_token('SRY', b'\x4A\x16')                       # SRY Press Sorry
SUG = register_token('SUG', b'\x4A\x17')                       # SUG Press Suggest
THK = register_token('THK', b'\x4A\x18')                       # THK Press Think
THN = register_token('THN', b'\x4A\x19')                       # THN Press IFF Then
TRY = register_token('TRY', b'\x4A\x1A')                       # TRY Press Try the following tokens
UNT = register_token('UNT', b'\x4A\x24')                       # UNT Press OCC Unit
VSS = register_token('VSS', b'\x4A\x1C')                       # VSS Press ALY Versus
WHT = register_token('WHT', b'\x4A\x1D')                       # WHT Press What to do with
WHY = register_token('WHY', b'\x4A\x1E')                       # WHY Press Why
XDO = register_token('XDO', b'\x4A\x1F')                       # XDO Press Moves to do
XOY = register_token('XOY', b'\x4A\x20')                       # XOY Press X owes Y
YDO = register_token('YDO', b'\x4A\x21')                       # YDO Press You provide the order for these units
