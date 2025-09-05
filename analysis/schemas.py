""" separate module for constants"""
import re
__all__ = ["ALL_PROVINCES", "ALL_SUPPLY_CENTERS", "COASTAL_SCs", "COUNTRIES", "PHASE_REGEX", "PLACE_IDENTIFIER", "UNIT_IDENTIFIER", "UNIT_MOVE", "POSSIBLE_COMMANDS", "POSSIBLE_COMMAND_RESULTS", "COUNTRY_RE", "PHASE_RE", "UNIT_RE", "PLACE_RE", "COMMAND_PATTERNS", "ALLOWED_RESULTS", "ALLOWED_COUNTRIES"]

ALL_PROVINCES = ['BRE', 'PAR', 'MAR', 'PIC', 'BUR', 'GAS', 'SPA', 'POR', 'NAF',
       'TUN', 'LON', 'WAL', 'LVP', 'YOR', 'EDI', 'CLY', 'NWY', 'SWE',
       'DEN', 'FIN', 'STP', 'STP/NC', 'STP/SC', 'MOS', 'SEV', 'UKR',
       'WAR', 'LVN', 'BER', 'PRU', 'SIL', 'MUN', 'RUH', 'KIE', 'HOL',
       'BEL', 'VIE', 'BOH', 'GAL', 'TYR', 'TRI', 'BUD', 'SER', 'RUM',
       'BUL', 'BUL/EC', 'BUL/SC', 'GRE', 'ALB', 'CON', 'ANK', 'SMY',
       'ARM', 'SYR', 'VEN', 'PIE', 'TUS', 'ROM', 'NAP', 'APU', 'NTH',
       'ENG', 'IRI', 'MAO', 'WES', 'LYO', 'TYS', 'ION', 'ADR', 'AEG',
       'EAS', 'BLA', 'BAL', 'BOT', 'SKA', 'BAR', 'NWG', 'NAO']

ALL_SUPPLY_CENTERS = [
    "ANK", "ARM", "BEL", "BER", "BUD", "BUL", "CON", "DEN", "EDI", "GRE",
    "HOL", "KIE", "LON", "LVP", "MAR", "MOS", "MUN", "NAP", "PAR", "POR",
    "ROM", "RUM", "SER", "SEV", "SMY", "SWE", "TRI", "TUN",
    "VEN", "VIE", "WAR", 
    "SPA", "STP",  # coastal provinces
]

COASTAL_SCs = ["SPA/SC", "SPA/NC",
    "STP/SC", "STP/NC", 'BUL/EC',
       'BUL/SC',]

COUNTRIES = ['AUSTRIA', 'ENGLAND', 'FRANCE', 'GERMANY', 'ITALY', 'RUSSIA', 'TURKEY']

PHASE_REGEX = r"^[A-Z]\d{4}[MRA]$"

PLACE_IDENTIFIER = r"[A-Z]{3}(?:/[A-Z]{2})?"
PLACE_CAPTURING_REGEX = r"([A-Z]{3})"
UNIT_IDENTIFIER = rf"[AF] {PLACE_IDENTIFIER}"
UNIT_MOVE = rf"{UNIT_IDENTIFIER} . {PLACE_IDENTIFIER}"

POSSIBLE_COMMANDS = {
    "Move": f"^"+UNIT_MOVE, # distinguishing this from support
    "Support Move": f"{UNIT_IDENTIFIER} S {UNIT_MOVE}",
    "Support Hold": fr"{UNIT_IDENTIFIER} S {UNIT_IDENTIFIER}(?!\s+[.\-]\s+{PLACE_IDENTIFIER})",
    "Convoy": f"F {PLACE_IDENTIFIER} C {UNIT_MOVE}", # No convoys in here? 
    "Hold": f"{UNIT_IDENTIFIER} H",
    "Build": f"{UNIT_IDENTIFIER} B",
    "Disband": f"{UNIT_IDENTIFIER} D",
    "Retreat": f"{UNIT_IDENTIFIER} R",
}

POSSIBLE_COMMAND_RESULTS = [
"void", "bounce", "cut", "dislodged", "disband", "no convoy"]

COUNTRY_RE = re.compile(r"^[A-Z][A-Z]+$")
PHASE_RE   = re.compile(PHASE_REGEX)
UNIT_RE    = re.compile(rf"^(?P<ut>A|F) (?P<ter>[A-Z]{{3}}(?:/(?:NC|SC|EC|WC))?)$")  # allow coasts
PLACE_RE   = re.compile(rf"^{PLACE_IDENTIFIER}$")

COMMAND_PATTERNS = [(name, re.compile(p)) for name, p in POSSIBLE_COMMANDS.items()]
ALLOWED_RESULTS  = set(POSSIBLE_COMMAND_RESULTS)
ALLOWED_COUNTRIES = set(COUNTRIES)