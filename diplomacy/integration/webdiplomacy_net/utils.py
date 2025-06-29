# ==============================================================================
# Copyright 2019 - Philip Paquette. All Rights Reserved.
#
# NOTICE:  All information contained herein is, and remains the property of the authors
#   listed above. The intellectual and technical concepts contained herein are proprietary
#   and may be covered by U.S. and Foreign Patents, patents in process, and are protected
#   by trade secret or copyright law. Dissemination of this information or reproduction of
#   this material is strictly forbidden unless prior written permission is obtained.
# ==============================================================================
""" Utilities - Builds a cache to query power_ix and loc_ix from webdiplomacy.net """
import collections

# Constants
CACHE = {'ix_to_map': {1: 'standard', 15: 'standard_france_austria', 23: 'standard_germany_italy'},
         'map_to_ix': {'standard': 1, 'standard_france_austria': 15, 'standard_germany_italy': 23}}

# Standard map
CACHE[1] = {'powers': ['GLOBAL', 'ENGLAND', 'FRANCE', 'ITALY', 'GERMANY', 'AUSTRIA', 'TURKEY', 'RUSSIA'],
            'locs': [None, 'CLY', 'EDI', 'LVP', 'YOR', 'WAL', 'LON', 'POR', 'SPA', 'NAF', 'TUN', 'NAP', 'ROM', 'TUS',
                     'PIE', 'VEN', 'APU', 'GRE', 'ALB', 'SER', 'BUL', 'RUM', 'CON', 'SMY', 'ANK', 'ARM', 'SYR', 'SEV',
                     'UKR', 'WAR', 'LVN', 'MOS', 'STP', 'FIN', 'SWE', 'NWY', 'DEN', 'KIE', 'BER', 'PRU', 'SIL', 'MUN',
                     'RUH', 'HOL', 'BEL', 'PIC', 'BRE', 'PAR', 'BUR', 'MAR', 'GAS', 'BAR', 'NWG', 'NTH', 'SKA', 'HEL',
                     'BAL', 'BOT', 'NAO', 'IRI', 'ENG', 'MAO', 'WES', 'LYO', 'TYS', 'ION', 'ADR', 'AEG', 'EAS', 'BLA',
                     'TYR', 'BOH', 'VIE', 'TRI', 'BUD', 'GAL', 'SPA/NC', 'SPA/SC', 'STP/NC', 'STP/SC', 'BUL/EC',
                     'BUL/SC']}
CACHE['standard'] = CACHE[1]

# France-Austria Map
CACHE[15] = {'powers': ['GLOBAL', 'FRANCE', 'AUSTRIA'],
             'locs': [None, 'CLY', 'EDI', 'LVP', 'YOR', 'WAL', 'LON', 'POR', 'SPA', 'SPA/NC', 'SPA/SC', 'NAF', 'TUN',
                      'NAP', 'ROM', 'TUS', 'PIE', 'VEN', 'APU', 'GRE', 'ALB', 'SER', 'BUL', 'BUL/EC', 'BUL/SC', 'RUM',
                      'CON', 'SMY', 'ANK', 'ARM', 'SYR', 'SEV', 'UKR', 'WAR', 'LVN', 'MOS', 'STP', 'STP/NC', 'STP/SC',
                      'FIN', 'SWE', 'NWY', 'DEN', 'KIE', 'BER', 'PRU', 'SIL', 'MUN', 'RUH', 'HOL', 'BEL', 'PIC', 'BRE',
                      'PAR', 'BUR', 'MAR', 'GAS', 'BAR', 'NWG', 'NTH', 'SKA', 'HEL', 'BAL', 'BOT', 'NAO', 'IRI', 'ENG',
                      'MAO', 'WES', 'LYO', 'TYS', 'ION', 'ADR', 'AEG', 'EAS', 'BLA', 'TYR', 'BOH', 'VIE', 'TRI', 'BUD',
                      'GAL']}
CACHE['standard_france_austria'] = CACHE[15]

# Germany-Italy Map
CACHE[23] = {'powers': ['GLOBAL', 'GERMANY', 'ITALY'],
             'locs': [None, 'CLY', 'EDI', 'LVP', 'YOR', 'WAL', 'LON', 'POR', 'SPA', 'SPA/NC', 'SPA/SC', 'NAF', 'TUN',
                      'NAP', 'ROM', 'TUS', 'PIE', 'VEN', 'APU', 'GRE', 'ALB', 'SER', 'BUL', 'BUL/EC', 'BUL/SC', 'RUM',
                      'CON', 'SMY', 'ANK', 'ARM', 'SYR', 'SEV', 'UKR', 'WAR', 'LVN', 'MOS', 'STP', 'STP/NC', 'STP/SC',
                      'FIN', 'SWE', 'NWY', 'DEN', 'KIE', 'BER', 'PRU', 'SIL', 'MUN', 'RUH', 'HOL', 'BEL', 'PIC', 'BRE',
                      'PAR', 'BUR', 'MAR', 'GAS', 'BAR', 'NWG', 'NTH', 'SKA', 'HEL', 'BAL', 'BOT', 'NAO', 'IRI', 'ENG',
                      'MAO', 'WES', 'LYO', 'TYS', 'ION', 'ADR', 'AEG', 'EAS', 'BLA', 'TYR', 'BOH', 'VIE', 'TRI', 'BUD',
                      'GAL']}
CACHE['standard_germany_italy'] = CACHE[23]

# Named tuples
class GameIdCountryId(
        collections.namedtuple('GameIdCountryId', ('game_id', 'country_id'))):
    """ Tuple (game_id, country_id) """


def build_cache():
    """ Computes a mapping from ix-to-power and ix-to-loc and vice-versa """
    for map_id in (1, 15, 23):
        CACHE[map_id]['ix_to_power'] = {}
        CACHE[map_id]['power_to_ix'] = {}
        CACHE[map_id]['ix_to_loc'] = {}
        CACHE[map_id]['loc_to_ix'] = {}

        for power_id, power_name in enumerate(CACHE[map_id]['powers']):
            CACHE[map_id]['ix_to_power'][power_id] = power_name
            CACHE[map_id]['power_to_ix'][power_name] = power_id

        for loc_id, loc_name in enumerate(CACHE[map_id]['locs']):
            if loc_id == 0:
                continue
            CACHE[map_id]['ix_to_loc'][loc_id] = loc_name
            CACHE[map_id]['loc_to_ix'][loc_name] = loc_id

# Building cache
build_cache()
