# ==============================================================================
# Copyright 2019 - Philip Paquette. All Rights Reserved.
#
# NOTICE:  All information contained herein is, and remains the property of the authors
#   listed above. The intellectual and technical concepts contained herein are proprietary
#   and may be covered by U.S. and Foreign Patents, patents in process, and are protected
#   by trade secret or copyright law. Dissemination of this information or reproduction of
#   this material is strictly forbidden unless prior written permission is obtained.
# ==============================================================================
""" Utility to convert a webdiplomacy.net game state to a game object """
import logging
from diplomacy import Game
from diplomacy.integration.webdiplomacy_net.orders import Order
from diplomacy.integration.webdiplomacy_net.utils import CACHE

# Constants
LOGGER = logging.getLogger(__name__)


def turn_to_phase(turn, phase):
    """ Converts a turn and phase to a short phase name e.g. turn 1 - phase 'Retreats' to 'F1901R' """
    year = 1901 + turn // 2
    season = 'S' if turn % 2 == 0 else 'F'
    if phase == 'Builds':
        season = 'W'
    phase_type = {'Diplomacy': 'M', 'Retreats': 'R', 'Builds': 'A'}[phase]
    return season + str(year) + phase_type


# Format:
# {'unitType':   'Army'/'Fleet',
#  'terrID':     integer,
#  'countryId':  integer,
#  'retreating': 'Yes'/'No'}
def unit_dict_to_str(unit_dict, map_id=1):
    """ Converts a unit from the dictionary format to the string format
        e.g. ``{'unitType': 'Army', 'terrID': 6, 'countryId': 1, 'retreating': 'No'}``
        to ``'ENGLAND', 'A LON'``

        :param unit_dict: The unit in dictionary format from webdiplomacy.net
        :return: A tuple consisting of:

            #. The power owning the unit (e.g. 'FRANCE')
            #. The unit in string format (with a leading ``*`` when dislodged) (e.g. ``'*A PAR'``)
    """
    req_fields = ('unitType', 'terrID', 'countryID', 'retreating')
    if [1 for field in req_fields if field not in unit_dict]:
        LOGGER.error('The required fields for unit dict are %s. Cannot translate %s', req_fields, unit_dict)
        return '', ''

    # Extracting information
    unit_type = str(unit_dict['unitType'])
    terr_id = int(unit_dict['terrID'])
    country_id = int(unit_dict['countryID'])
    retreating = str(unit_dict['retreating'])

    # Validating
    if unit_type not in ('Army', 'Fleet'):
        LOGGER.error('Unknown unitType "%s". Expected "Army" or "Fleet".', unit_type)
        return '', ''
    if terr_id not in CACHE[map_id]['ix_to_loc']:
        LOGGER.error('Unknown terrID "%s" for mapID "%s".', terr_id, map_id)
        return '', ''
    if country_id not in CACHE[map_id]['ix_to_power']:
        LOGGER.error('Unknown countryID "%s" for mapID "%s".', country_id, map_id)
        return '', ''
    if retreating not in ('Yes', 'No'):
        LOGGER.error('Unknown retreating "%s". Expected "Yes" or "No".', retreating)
        return '', ''

    # Translating names
    loc_name = CACHE[map_id]['ix_to_loc'][terr_id]
    power_name = CACHE[map_id]['ix_to_power'][country_id]
    is_dislodged = bool(retreating == 'Yes')

    # Building unit and returning
    unit = '%s%s %s' % ('*' if is_dislodged else '', unit_type[0], loc_name)
    return power_name, unit


# Format:
# {'terrID':     integer,
#  'countryId':  integer}
def center_dict_to_str(center_dict, map_id=1):
    """ Converts a supply center from the dictionary format to the string format
        e.g. ``{'terrID': 6, 'countryId': 1}`` to ``'ENGLAND', 'LON'``

        :param center_dict: The center in dictionary format from webdiplomacy.net
        :return: A tuple consisting of:

            #. The power owning the center (e.g. 'FRANCE')
            #. The location where the supply center is (e.g. 'PAR')
    """
    req_fields = ('terrID', 'countryID')
    if [1 for field in req_fields if field not in center_dict]:
        LOGGER.error('The required fields for center dict are %s. Cannot translate %s', req_fields, center_dict)
        return '', ''

    # Extracting information
    terr_id = int(center_dict['terrID'])
    country_id = int(center_dict['countryID'])

    # Validating
    if terr_id not in CACHE[map_id]['ix_to_loc']:
        LOGGER.error('Unknown terrID "%s" for mapID "%s".', terr_id, map_id)
        return '', ''
    if country_id not in CACHE[map_id]['ix_to_power']:
        LOGGER.error('Unknown countryID "%s" for mapID "%s".', country_id, map_id)
        return '', ''

    # Translating names
    loc_name = CACHE[map_id]['ix_to_loc'][terr_id]
    power_name = CACHE[map_id]['ix_to_power'][country_id]

    # Returning
    return power_name, loc_name


# Format:
# {'turn':       integer,
#  'phase':      'Diplomacy', 'Retreats', 'Builds',
#  'countryID':  integer,
#  'terrID':     integer,
#  'unitType':   'Army', 'Fleet',
#  'type':       'Hold', 'Move', 'Support hold', 'Support move', 'Convoy',
#                'Retreat', 'Disband',
#                'Build Army', 'Build Fleet', 'Wait', 'Destroy'
#  'toTerrID':   integer,
#  'fromTerrID': integer,
#  'viaConvoy':  'Yes', 'No',
#  'success':    'Yes', 'No',
#  'dislodged':  'Yes', 'No'}
def order_dict_to_str(order_dict, phase, map_id=1):
    """ Converts an order from the dictionary format to the string format

        :param order_dict: The order in dictionary format from webdiplomacy.net
        :param phase: The current phase ('Diplomacy', 'Retreats', 'Builds')
        :return: A tuple consisting of:

            #. The power who submitted the order (e.g. 'FRANCE')
            #. The order in string format (e.g. 'A PAR H')
    """
    req_fields = ('countryID',)
    if [1 for field in req_fields if field not in order_dict]:
        LOGGER.error('The required fields for order dict are %s. Cannot translate %s', req_fields, order_dict)
        return '', '', ''

    # Extracting information
    country_id = int(order_dict['countryID'])

    # Validating
    if country_id not in CACHE[map_id]['ix_to_power']:
        LOGGER.error('Unknown countryID "%s" for mapID "%s".', country_id, map_id)
        return '', ''

    # Getting power name and phase_type
    power_name = CACHE[map_id]['ix_to_power'][country_id]
    phase_type = {'Diplomacy': 'M', 'Retreats': 'R', 'Builds': 'A'}[phase]

    # Getting order in string format
    order = Order(order_dict, map_id=map_id, phase_type=phase_type)
    if not order:
        return '', ''

    # Returning
    return power_name, order.to_string()


# Format:
# {'turn':       integer,
#  'phase':      'Diplomacy', 'Retreats', 'Builds',
#  'units':      [],
#  'centers':    [],
#  'orders':     []}
def process_phase_dict(phase_dict, map_id=1):
    """ Converts a phase dict to its string representation """
    phase = turn_to_phase(phase_dict.get('turn', 0), phase_dict.get('phase', 'Diplomacy'))

    # Processing units
    units_per_power = {}
    for unit_dict in phase_dict.get('units', []):
        power_name, unit = unit_dict_to_str(unit_dict, map_id=map_id)
        if not power_name:
            continue
        if power_name not in units_per_power:
            units_per_power[power_name] = []
        units_per_power[power_name].append(unit)

    # Processing centers
    centers_per_power = {}
    for center_dict in phase_dict.get('centers', []):
        power_name, loc = center_dict_to_str(center_dict, map_id=map_id)
        if not power_name:
            continue
        if power_name not in centers_per_power:
            centers_per_power[power_name] = []
        centers_per_power[power_name].append(loc)

    # Processing orders
    orders_per_power = {}
    for order_dict in phase_dict.get('orders', []):
        power_name, order = order_dict_to_str(order_dict,
                                              phase=phase_dict.get('phase', 'Diplomacy'),
                                              map_id=map_id)
        if not power_name:
            continue
        if power_name not in orders_per_power:
            orders_per_power[power_name] = []
        orders_per_power[power_name].append(order)

    # Returning
    return {'name': phase,
            'units': units_per_power,
            'centers': centers_per_power,
            'orders': orders_per_power}


# Format:
# {'gameID':      integer,
#  'variantID':   integer,
#  'turn':        integer,
#  'phase':       'Pre-Game', 'Diplomacy', 'Retreats', 'Builds', 'Finished',
#  'gameOver':    'No, 'Won', 'Drawn',
#  'phases':      [],
#  'standoffs':   []}
def state_dict_to_game_and_power(state_dict, country_id, max_phases=None):
    """ Converts a game state from the dictionary format to an actual diplomacy.Game object with the related power.

        :param state_dict: The game state in dictionary format from webdiplomacy.net
        :param country_id: The country id we want to convert.
        :param max_phases: Optional. If set, improve speed by only keeping the last 'x' phases to regenerate the game.
        :return: A tuple of

            #. None, None       - on error or if the conversion is not possible, or game is invalid / not-started / done
            #. game, power_name - on successful conversion
    """
    if state_dict is None:
        return None, None

    req_fields = ('gameID', 'variantID', 'turn', 'phase', 'gameOver', 'phases', 'standoffs', 'occupiedFrom')
    if [1 for field in req_fields if field not in state_dict]:
        LOGGER.error('The required fields for state dict are %s. Cannot translate %s', req_fields, state_dict)
        return None, None

    # Extracting information
    game_id = str(state_dict['gameID'])
    map_id = int(state_dict['variantID'])
    standoffs = state_dict['standoffs']
    occupied_from = state_dict['occupiedFrom']

    # Parsing all phases
    state_dict_phases = state_dict.get('phases', [])
    if max_phases is not None and isinstance(max_phases, int):
        state_dict_phases = state_dict_phases[-1 * max_phases:]
    all_phases = [process_phase_dict(phase_dict, map_id=map_id) for phase_dict in state_dict_phases]

    # Building game - Replaying the last phases
    game = Game(game_id=game_id, map_name=CACHE['ix_to_map'][map_id])

    for phase_to_replay in all_phases[:-1]:
        game.set_current_phase(phase_to_replay['name'])

        # Units
        game.clear_units()
        for power_name, power_units in phase_to_replay['units'].items():
            if power_name == 'GLOBAL':
                continue
            game.set_units(power_name, power_units)

        # Centers
        game.clear_centers()
        for power_name, power_centers in phase_to_replay['centers'].items():
            if power_name == 'GLOBAL':
                continue
            game.set_centers(power_name, power_centers)

        # Orders
        for power_name, power_orders in phase_to_replay['orders'].items():
            if power_name == 'GLOBAL':
                continue
            game.set_orders(power_name, power_orders)

        # Processing
        game.process()

    # Setting the current phase
    current_phase = all_phases[-1]
    game.set_current_phase(current_phase['name'])

    # Units
    game.clear_units()
    for power_name, power_units in current_phase['units'].items():
        if power_name == 'GLOBAL':
            continue
        game.set_units(power_name, power_units)

    # Centers
    game.clear_centers()
    for power_name, power_centers in current_phase['centers'].items():
        if power_name == 'GLOBAL':
            continue
        game.set_centers(power_name, power_centers)

    # Setting retreat locs
    if current_phase['name'][-1] == 'R':
        invalid_retreat_locs = set()
        attack_source = {}

        # Loc is occupied
        for power in game.powers.values():
            for unit in power.units:
                invalid_retreat_locs.add(unit[2:5])

        # Loc was in standoff
        if standoffs:
            for loc_dict in standoffs:
                _, loc = center_dict_to_str(loc_dict, map_id=map_id)
                invalid_retreat_locs.add(loc[:3])

        # Loc was attacked from
        if occupied_from:
            for loc_id, occupied_from_id in occupied_from.items():
                loc_name = CACHE[map_id]['ix_to_loc'][int(loc_id)][:3]
                from_loc_name = CACHE[map_id]['ix_to_loc'][int(occupied_from_id)][:3]
                attack_source[loc_name] = from_loc_name

        # Removing invalid retreat locs
        for power in game.powers.values():
            for retreat_unit in power.retreats:
                power.retreats[retreat_unit] = [loc for loc in power.retreats[retreat_unit]
                                                if loc[:3] not in invalid_retreat_locs
                                                and loc[:3] != attack_source.get(retreat_unit[2:5], '')]

    # Returning
    power_name = CACHE[map_id]['ix_to_power'][country_id]
    return game, power_name
