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
""" Power

    - Contains the power object representing a power in the game
"""
from copy import deepcopy
from diplomacy.utils import parsing, strings
from diplomacy.utils.exceptions import DiplomacyException
from diplomacy.utils.jsonable import Jsonable
from diplomacy.utils.sorted_dict import SortedDict
from diplomacy.utils import common, constants
from diplomacy.utils.constants import OrderSettings

class Power(Jsonable):
    """ Power Class

        Properties:

        - **abbrev** - Contains the abbrev of the power (i.e. the first letter of the power name) (e.g. 'F' for FRANCE)
        - **adjust** - List of pending adjustment orders
          (e.g. ['A PAR B', 'A PAR R MAR', 'A MAR D', 'WAIVE'])
        - **centers** - Contains the list of supply centers currently controlled by the power ['MOS', 'SEV', 'STP']
        - **civil_disorder** - Bool flag to indicate that the power has been put in CIVIL_DISORDER (e.g. True or False)
        - **controller** - Sorted dictionary mapping timestamp to controller (either dummy or a user ID) who takes
          control of power at this timestamp.
        - **game** - Contains a reference to the game object
        - **goner** - Boolean to indicate that this power doesn't control any SCs any more (e.g. True or False)
        - **homes** - Contains a list of homes supply centers (where you can build)
          e.g. ['PAR', 'MAR', ... ] or None if empty
        - **influence** - Contains a list of locations influenced by this power
          Note: To influence a location, the power must have visited it last.
          e.g ['PAR', 'MAR', ... ]
        - **name** - Contains the name of the power (e.g. 'FRANCE')
        - **orders** - Contains a dictionary of units and their orders.
          For NO_CHECK games, unit is 'ORDER 1', 'ORDER 2', ...

          - e.g. {'A PAR': '- MAR' } or {'ORDER 1': 'A PAR - MAR', 'ORDER 2': '...', ... }
          - Can also be {'REORDER 1': 'A PAR - MAR', 'INVALID 1': 'A PAR - MAR', ... } after validation

        - **retreats** - Contains the list of units that need to retreat with their possible retreat locations
          (e.g. {'A PAR': ['MAR', 'BER']})
        - **role** - Power type (observer, omniscient, player or server power).
          Either the power name (for a player power) or a value in diplomacy.utils.strings.ALL_ROLE_TYPES
        - **tokens** - Only for server power: set of tokens of current power controlled (if not None).
        - **units** - Contains the list of units (e.g. ['A PAR', 'A MAR', ...]
        - **vote** - Only for omniscient, player and server power: power vote ('yes', 'no' or 'neutral').
    """
    __slots__ = ['game', 'name', 'abbrev', 'adjust', 'centers', 'units', 'influence', 'homes',
                 'retreats', 'goner', 'civil_disorder', 'orders', 'role', 'controller', 'vote',
                 'order_is_set', 'wait', 'tokens']
    model = {
        strings.ABBREV: parsing.OptionalValueType(str),
        strings.ADJUST: parsing.DefaultValueType(parsing.SequenceType(str), []),
        strings.CENTERS: parsing.DefaultValueType(parsing.SequenceType(str), []),
        strings.CIVIL_DISORDER: parsing.DefaultValueType(int, 0),
        strings.CONTROLLER: parsing.DefaultValueType(parsing.DictType(int, str, SortedDict.builder(int, str)), {}),
        strings.HOMES: parsing.OptionalValueType(parsing.SequenceType(str)),
        strings.INFLUENCE: parsing.DefaultValueType(parsing.SequenceType(str), []),
        strings.NAME: parsing.PrimitiveType(str),
        strings.ORDER_IS_SET: parsing.DefaultValueType(OrderSettings.ALL_SETTINGS, OrderSettings.ORDER_NOT_SET),
        strings.ORDERS: parsing.DefaultValueType(parsing.DictType(str, str), {}),
        strings.RETREATS: parsing.DefaultValueType(parsing.DictType(str, parsing.SequenceType(str)), {}),
        strings.ROLE: parsing.DefaultValueType(str, strings.SERVER_TYPE),
        strings.TOKENS: parsing.DefaultValueType(parsing.SequenceType(str, set), ()),
        strings.UNITS: parsing.DefaultValueType(parsing.SequenceType(str), []),
        strings.VOTE: parsing.DefaultValueType(parsing.EnumerationType(strings.ALL_VOTE_DECISIONS), strings.NEUTRAL),
        strings.WAIT: parsing.DefaultValueType(bool, True),
    }

    def __init__(self, game=None, name=None, **kwargs):
        """ Constructor """
        self.game = game
        self.abbrev = None
        self.adjust, self.centers, self.units, self.influence = [], [], [], []
        self.homes = None
        self.retreats = {}
        self.goner = self.civil_disorder = 0
        self.orders = {}

        self.name = ''
        self.role = ''
        self.controller = SortedDict(int, str)
        self.vote = ''
        self.order_is_set = 0
        self.wait = False
        self.tokens = set()
        super(Power, self).__init__(name=name, **kwargs)
        assert self.role in strings.ALL_ROLE_TYPES or self.role == self.name
        if not self.controller:
            self.controller.put(common.timestamp_microseconds(), strings.DUMMY)

    def __str__(self):
        """ Returns a representation of the power instance """
        show_cd = self.civil_disorder
        show_inhabits = self.homes is not None
        show_owns = self.centers
        show_retreats = len(self.retreats) > 0

        text = ''
        text += '\n%s (%s)' % (self.name, self.role)
        text += '\nPLAYER %s' % self.controller.last_value()
        text += '\nCD' if show_cd else ''
        text += '\nINHABITS %s' % ' '.join(self.homes) if show_inhabits else ''
        text += '\nOWNS %s' % ' '.join(self.centers) if show_owns else ''
        if show_retreats:
            text += '\n'.join([''] + [' '.join([unit, '-->'] + places) for unit, places in self.retreats.items()])
        text = '\n'.join([text] + self.units + self.adjust)

        # Orders - RIO is for REORDER, INVALID, ORDER (in NO_CHECK games)
        text_order = '\nORDERS\n'
        for unit, order in self.orders.items():
            if unit[0] not in 'RIO':
                text_order += '%s ' % unit
            text_order += order + '\n'

        text += text_order if self.orders else ''
        return text

    def __deepcopy__(self, memo):
        """ Fast deep copy implementation (**not setting the game object**) """
        cls = self.__class__
        result = cls.__new__(cls)

        # Deep copying
        for key in self.__slots__:
            if key not in ['game']:
                setattr(result, key, deepcopy(getattr(self, key)))

        # Game
        setattr(result, 'game', None)
        return result

    def reinit(self, include_flags=6):
        """ Performs a reinitialization of some of the parameters

            :param include_flags: Bit mask to indicate which params to reset
                                 (bit 1 = orders, 2 = persistent, 4 = transient)
            :return: None
        """
        reinit_persistent = include_flags & 2
        reinit_transient = include_flags & 4
        reinit_orders = include_flags & 1

        # Initialize the persistent parameters
        if reinit_persistent:
            self.abbrev = None

        # Initialize the transient parameters
        if reinit_transient:
            for home in self.homes:
                self.game.update_hash(self.name, loc=home, is_home=True)
            for center in self.centers:
                self.game.update_hash(self.name, loc=center, is_center=True)
            for unit in self.units:
                self.game.update_hash(self.name, unit_type=unit[0], loc=unit[2:])
            for dis_unit in self.retreats:
                self.game.update_hash(self.name, unit_type=dis_unit[0], loc=dis_unit[2:], is_dislodged=True)
            self.homes = None
            self.centers, self.units, self.influence = [], [], []
            self.retreats = {}

        # Initialize the order-related parameters
        if reinit_orders:
            self.civil_disorder = 0
            self.adjust = []
            self.orders = {}
            if self.is_eliminated():
                self.order_is_set = OrderSettings.ORDER_SET_EMPTY
                self.wait = False
            else:
                self.order_is_set = OrderSettings.ORDER_NOT_SET
                self.wait = True if self.is_dummy() else (not self.game.real_time)
        self.goner = 0

    @staticmethod
    def compare(power_1, power_2):
        """ Comparator object - Compares two Power objects

            :param power_1: The first Power object to compare
            :param power_2: The second Power object to compare
            :return: 1 if self is greater, -1 if other is greater, 0 if they are equal
        """
        cmp = lambda power_1, power_2: ((power_1 > power_2) - (power_1 < power_2))
        xstr = lambda string: string or ''                      # To avoid comparing with None
        cmp_type = cmp(xstr(power_1.role), xstr(power_2.role))
        cmp_name = cmp(xstr(power_1.name), xstr(power_2.name))
        return cmp_type or cmp_name

    def initialize(self, game):
        """  Initializes a game and resets home, centers and units

            :param game: The game to use for initialization
            :type game: diplomacy.Game
        """

        # Not initializing observers and monitors
        assert self.is_server_power()

        self.game = game
        self.order_is_set = OrderSettings.ORDER_NOT_SET
        self.wait = True if self.is_dummy() else (not self.game.real_time)

        # Get power abbreviation.
        self.abbrev = self.game.map.abbrev.get(self.name, self.name[0])

        # Resets homes
        if self.homes is None:
            self.homes = []
            for home in game.map.homes.get(self.name, []):
                self.game.update_hash(self.name, loc=home, is_home=True)
                self.homes.append(home)

        # Resets the centers and units
        if not self.centers:
            for center in game.map.centers.get(self.name, []):
                game.update_hash(self.name, loc=center, is_center=True)
                self.centers.append(center)
        if not self.units:
            for unit in game.map.units.get(self.name, []):
                game.update_hash(self.name, unit_type=unit[0], loc=unit[2:])
                self.units.append(unit)
                self.influence.append(unit[2:5])

    def merge(self, other_power):
        """ Transfer all units, centers, and homes of the other_power to this power

            :param other_power: The other power (will be empty after the merge)
        """
        # Regular units
        for unit in list(other_power.units):
            self.units.append(unit)
            other_power.units.remove(unit)
            self.game.update_hash(self.name, unit_type=unit[0], loc=unit[2:])
            self.game.update_hash(other_power.name, unit_type=unit[0], loc=unit[2:])

        # Dislodged units
        for unit in list(other_power.retreats.keys()):
            self.retreats[unit] = other_power.retreats[unit]
            del other_power.retreats[unit]
            self.game.update_hash(self.name, unit_type=unit[0], loc=unit[2:], is_dislodged=True)
            self.game.update_hash(other_power.name, unit_type=unit[0], loc=unit[2:], is_dislodged=True)

        # Influence
        for loc in list(other_power.influence):
            self.influence.append(loc)
            other_power.influence.remove(loc)

        # Supply centers
        for center in list(other_power.centers):
            self.centers.append(center)
            other_power.centers.remove(center)
            self.game.update_hash(self.name, loc=center, is_center=True)
            self.game.update_hash(other_power.name, loc=center, is_center=True)

        # Homes
        for home in list(other_power.homes):
            self.homes.append(home)
            other_power.homes.remove(home)
            self.game.update_hash(self.name, loc=home, is_home=True)
            self.game.update_hash(other_power.name, loc=home, is_home=True)

        # Clearing state cache
        self.game.clear_cache()

    def clear_units(self):
        """ Removes all units from the map """
        for unit in self.units:
            self.game.update_hash(self.name, unit_type=unit[0], loc=unit[2:])
        for unit in self.retreats:
            self.game.update_hash(self.name, unit_type=unit[0], loc=unit[2:], is_dislodged=True)
        self.units = []
        self.retreats = {}
        self.influence = []
        self.game.clear_cache()

    def clear_centers(self):
        """ Removes ownership of all supply centers """
        for center in self.centers:
            self.game.update_hash(self.name, loc=center, is_center=True)
        self.centers = []
        self.game.clear_cache()

    def is_dummy(self):
        """ Indicates if the power is a dummy

            :return: Boolean flag to indicate if the power is a dummy
        """
        return self.controller.last_value() == strings.DUMMY

    def is_eliminated(self):
        """ Returns a flag to show if player is eliminated

            :return: If the current power is eliminated
        """
        # Not eliminated if has units left
        if self.units or self.centers or self.retreats:
            return False
        return True

    def clear_orders(self):
        """ Clears the power's orders """
        self.reinit(include_flags=1)

    def moves_submitted(self):
        """  Returns a boolean to indicate if moves has been submitted

            :return: 1 if not in Movement phase, or orders submitted, or no more units lefts
        """
        if self.game.phase_type != 'M':
            return 1
        return self.orders or not self.units

    # ==============================================================
    # Application/network methods (mainly used for connected games).
    # ==============================================================

    def is_observer_power(self):
        """ (Network Method) Return True if this power is an observer power. """
        return self.role == strings.OBSERVER_TYPE

    def is_omniscient_power(self):
        """ (Network Method) Return True if this power is an omniscient power. """
        return self.role == strings.OMNISCIENT_TYPE

    def is_player_power(self):
        """ (Network Method) Return True if this power is a player power. """
        return self.role == self.name

    def is_server_power(self):
        """ (Network Method) Return True if this power is a server power. """
        return self.role == strings.SERVER_TYPE

    def is_controlled(self):
        """ (Network Method) Return True if this power is controlled. """
        return self.controller.last_value() != strings.DUMMY

    def does_not_wait(self):
        """ (Network Method) Return True if this power does not wait
            (ie. if we could already process orders of this power).
        """
        return self.order_is_set and not self.wait

    def update_controller(self, username, timestamp):
        """ (Network Method) Update controller with given username and timestamp. """
        self.controller.put(timestamp, username)

    def set_controlled(self, username):
        """ (Network Method) Control power with given username. Username may be None (meaning no controller). """
        if username is None or username == strings.DUMMY:
            if self.controller.last_value() != strings.DUMMY:
                self.controller.put(common.timestamp_microseconds(), strings.DUMMY)
                self.tokens.clear()
                self.wait = True
                self.vote = strings.NEUTRAL
        elif self.controller.last_value() == strings.DUMMY:
            self.controller.put(common.timestamp_microseconds(), username)
            self.wait = not self.game.real_time
        elif self.controller.last_value() != username:
            raise DiplomacyException('Power already controlled by someone else. Kick previous controller before.')

    def get_controller(self):
        """ (Network Method) Return current power controller name ('dummy' if power is not controlled). """
        return self.controller.last_value()

    def get_controller_timestamp(self):
        """ (Network Method) Return timestamp when current controller took control of this power. """
        return self.controller.last_key()

    def is_controlled_by(self, username):
        """ (Network Method) Return True if this power is controlled by given username. """
        if username == constants.PRIVATE_BOT_USERNAME:
            # Bot is connected if power is dummy and has some associated tokens.
            return self.is_dummy() and bool(self.tokens)
        return self.controller.last_value() == username

    # Server-only methods.

    def has_token(self, token):
        """ (Server Method) Return True if this power has given token. """
        assert self.is_server_power()
        return token in self.tokens

    def add_token(self, token):
        """ (Server Method) Add given token to this power. """
        assert self.is_server_power()
        self.tokens.add(token)

    def remove_tokens(self, tokens):
        """ (Server Method) Remove sequence of tokens from this power. """
        assert self.is_server_power()
        self.tokens.difference_update(tokens)
