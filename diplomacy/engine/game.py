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
# -*- coding: utf-8 -*-
""" Game

    - Contains the game engine
"""
# pylint: disable=too-many-lines
import base64
import os
import logging
import sys
import time
import random
from copy import deepcopy

from diplomacy import settings
import diplomacy.utils.errors as err
from diplomacy.utils.order_results import OK, NO_CONVOY, BOUNCE, VOID, CUT, DISLODGED, DISRUPTED, DISBAND, MAYBE
from diplomacy.engine.map import Map
from diplomacy.engine.message import Message, GLOBAL
from diplomacy.engine.power import Power
from diplomacy.engine.renderer import Renderer
from diplomacy.utils import PriorityDict, common, exceptions, parsing, strings
from diplomacy.utils.jsonable import Jsonable
from diplomacy.utils.sorted_dict import SortedDict
from diplomacy.utils.constants import OrderSettings, DEFAULT_GAME_RULES
from diplomacy.utils.game_phase_data import GamePhaseData, MESSAGES_TYPE

# Constants
UNDETERMINED, POWER, UNIT, LOCATION, COAST, ORDER, MOVE_SEP, OTHER = 0, 1, 2, 3, 4, 5, 6, 7
LOGGER = logging.getLogger(__name__)

class Game(Jsonable):
    """ Game class.

        Properties:

        - **combat**:

          - Dictionary of dictionaries containing the strength of every attack on a location (including units
            who don't count toward dislodgment)
          - Format: {loc: attack_strength: [ ['src loc', [support loc] ]}
          - e.g. ``{ 'MUN': { 1 : [ ['A MUN', [] ], ['A RUH', [] ] ], 2 : [ ['A SIL', ['A BOH'] ] ] } }``.
            MUN is holding, being attack without support from RUH and being attacked with support from SIL (S from BOH)

        - **command**: contains the list of finalized orders to be processed
          (same format as orders, but without .order). e.g. {'A PAR': '- A MAR'}
        - **controlled_powers**: *(for client games only)*. List of powers currently controlled
          by associated client user.
        - **convoy_paths**:

          - Contains the list of remaining convoys path for each convoyed unit to reach their destination
          - Note: This is used to see if there are still active convoy paths remaining.
          - Note: This also include the start and ending location
          - e.g. {'A PAR': [ ['PAR', 'ION','NAO', 'MAR], ['PAR', 'ION', 'MAR'] ], ... }

        - **convoy_paths_possible**:

          - Contains the list of possible convoy paths given the current fleet locations or None
          - e.g. [(START_LOC, {Fleets Req}, {possible dest}), ...]

        - **convoy_paths_dest**:

          - Contains a dictionary of possible paths to reach destination from start or None
          - e.g. {start_loc: {dest_loc_1: [{fleets}, {fleets}, {fleets}], dest_loc_2: [{fleets, fleets}]}

        - **daide_port**: *(for client games only)*. Port when a DAIDE bot can connect, to play with this game.
        - **deadline**: integer: game deadline in seconds.
        - **dislodged**: contains a dictionary of dislodged units (and the site that dislodged them').
          e.g. { 'A PAR': 'MAR' }
        - **error**: contains a list of errors that the game generated. e.g. ['NO MASTER SPECIFIED']
        - **fixed_state**:

          - used when game is a context of a with-block.
          - Store values that define the game state when entered in with-statement.
          - Compared to actual fixed state to detect any changes in methods where changes are not allowed.
          - Reset to None when exited from with-statement.

        - **game_id**: String that contains the current game's ID. e.g. '123456'
        - **lost**:

          - Contains a dictionary of centers that have been lost during the term
          - e.g. {'PAR': 'FRANCE'}  to indicate that PAR was lost by France (previous owner)

        - **map**: Contains a reference to the current map (Map instance). e.g. map = Map('standard')
        - **map_name**: Contains a reference to the name of the map that was loaded (or a path to a custom map file)
          e.g. map_name = 'standard' or map_name = '/some/path/to/file.map'
        - **messages** *(for non-observer games only)*:

          - history of messages exchanged inside this game.
          - Sorted dict mapping message timestamps to message objects (instances of diplomacy.Message).
          - Format: {message.time_sent => message}

        - **message_history**:

          - history of messages through all played phases.
          - Sorted dict mapping a short phase name to a message dict
            (with same format as field `message` describe above).
          - Format: {short phase name => {message.time_sent => message}}
          - Wrapped in a sorted dict at runtime, see method __init__().

        - **meta_rules**: contains the rules that have been processed as directives. e.g. ['NO_PRESS']
        - **n_controls**: integer:

          - exact number of controlled powers allowed for this game.
          - If game start mode is not START_MASTER, then game starts as soon as
            this number of powers are controlled.

        - **no_rules**: contains the list of rules that have been disabled (prefixed with '!').
          e.g ['NO_PRESS']
        - **note**: a note to display on the rendering. e.g. 'Winner: FRANCE'
        - **observer_level** *(for client games only)*:

          - Highest observation level allowed for associated client user.
          - Either "master_type", "omniscient_type" or "observer_type".

        - **orders**: contains the list of current orders (not yet processed). e.g. {'A PAR': '- A MAR'}
        - **ordered_units**:

          - Contains a dictionary of the units ordered by each power in the last phase
          - e.g. {'FRANCE': ['A PAR', 'A MAR'], 'ENGLAND': ... }

        - **order_history**:

          - Contains the history of orders from each player from the beginning of the game.
          - Sorted dict mapping  a short phase name to a dictionary of orders
            (powers names as keys, powers orders as values).
          - Format: {short phase name => {power name => [orders]}}
          - Wrapped in a sorted dict at runtime, see method __init__().

        - **outcome**: contains the game outcome. e.g. [lastPhase, victor1, victor2, victor3]
        - **phase**: string that contains a long representation of the current phase.
          e.g. 'SPRING 1901 MOVEMENT'
        - **phase_type**: indicates the current phase type.
          e.g. 'M' for Movement, 'R' for Retreats, 'A' for Adjustment, '-' for non-playing phase
        - **popped**: contains a list of all retreaters who didn't make it. e.g. ['A PAR', 'A MAR']
        - **powers**:

          - Contains a dictionary mapping power names to power instances in the game
          - e.g. {'FRANCE': FrancePower, 'ENGLAND': EnglishPower, ...}

        - **registration_password**: ** hashed ** version of password to be sent by a player to join this game.
        - **renderer**: contains the object in charge of rendering the map. e.g. Renderer()
        - **result**:

          - Contains the result of the action for each unit.
          - In Movement Phase, result can be 'no convoy', 'bounce', 'void', 'cut', 'dislodged', 'disrupted'.
            e.g. { 'A PAR': ['cut', 'void'] }
          - In Retreats phase, result can be 'bounce', 'disband', 'void'.
            e.g. { 'A PAR': ['cut', 'void'] }
          - In Adjustments phase, result can be 'void' or ''.
            e.g. { 'A PAR': ['', 'void'] }      # e.g. to indicate a successful build, and a void build.

        - **result_history**:

          - Contains the history of orders results for all played phases.
          - Sorted dict mapping a short phase name to a dictionary of order results for this phase.
          - Dictionary of order results maps a unit to a list of results. See field result for more details.
          - Format: {short phase name => {unit => [results]}}
          - Wrapped in a sorted dict at runtime, see method __init__().

        - **role**: Either a power name (for player game) or a value in diplomacy.utils.strings.ALL_ROLE_TYPES.
        - **rules**: Contains a list of active rules. e.g. ['NO_PRESS', ...]. Default is
          :const:`diplomacy.utils.constants.DEFAULT_GAME_RULES`.
        - **state_history**:

          - history of previous game states (returned by method get_state()) for this game.
          - Sorted dict mapping a short phase name to a game state.
          - Each game state is associated to a timestamp generated
            when state is created by method get_state().
          - State timestamp then represents the "end" time of the state,
            ie. time when this state was saved and archived in state history.
          - Format: {short phase name => state}
          - Wrapped in a sorted dict at runtime, see method __init__().

        - **status**: game status (forming, active, paused, completed or canceled).
          Possible values in diplomacy.utils.strings.ALL_GAME_STATUSES.
        - **supports**:

          - Contains a dictionary of support for each unit
          - Format: { 'unit': [nb_of_support, [list of supporting units]] }
          - e.g. { 'A PAR': [2, ['A MAR']] }. 2 support, but the Marseille support
            does NOT count toward dislodgment

        - **timestamp_created**: timestamp in microseconds when game object was created on server side.
        - **victory**:

          - Indicates the number of SUPPLY [default] centers one power must control to win the game
          - Format: [reqFirstYear, reqSecondYear, ..., reqAllFurtherYears]
          - e.g. [10,10,18]     for 10 the 1st year, 10 the 2nd year, 18 year 3+

        - **win** - Indicates the minimum number of centers required to win. e.g. 3
        - **zobrist_hash** - Contains the zobrist hash representing the current state of this game.
          e.g. 12545212418541325
        - **phase_summaries**:

          - Contains a dictionary of phase summaries for all of the actions taken in that phase, each turn will have a single

        Cache properties:

        - **unit_owner_cache**:

          - Contains a dictionary with (unit, coast_required) as key and owner as value
          - Set to Note when the cache is not built
          - e.g. {('A PAR', True): <FRANCE>, ('A PAR', False): <FRANCE>), ...}

    """
    # pylint: disable=too-many-instance-attributes
    __slots__ = ['victory', 'no_rules', 'meta_rules', 'phase', 'note', 'map', 'powers', 'outcome', 'error', 'popped',
                 'messages', 'order_history', 'orders', 'ordered_units', 'phase_type', 'win', 'combat', 'command',
                 'result', 'supports', 'dislodged', 'lost', 'convoy_paths', 'convoy_paths_possible',
                 'convoy_paths_dest', 'zobrist_hash', 'renderer', 'game_id', 'map_name', 'role', 'rules',
                 'message_history', 'state_history', 'result_history', 'status', 'timestamp_created', 'n_controls',
                 'deadline', 'registration_password', 'observer_level', 'controlled_powers', '_phase_wrapper_type',
                 'phase_abbr', '_unit_owner_cache', 'daide_port', 'fixed_state', 'power_model_map', 'phase_summaries']
    zobrist_tables = {}
    rule_cache = ()
    model = {
        strings.CONTROLLED_POWERS: parsing.OptionalValueType(parsing.SequenceType(str)),
        strings.DAIDE_PORT: parsing.OptionalValueType(int),
        strings.DEADLINE: parsing.DefaultValueType(int, 300),
        strings.ERROR: parsing.DefaultValueType(parsing.SequenceType(parsing.StringableType(err.Error)), []),
        strings.GAME_ID: parsing.OptionalValueType(str),
        strings.MAP_NAME: parsing.DefaultValueType(str, 'standard'),
        strings.MESSAGE_HISTORY: parsing.DefaultValueType(parsing.DictType(str, MESSAGES_TYPE), {}),
        strings.MESSAGES: parsing.DefaultValueType(MESSAGES_TYPE, []),
        strings.META_RULES: parsing.DefaultValueType(parsing.SequenceType(str), []),
        strings.N_CONTROLS: parsing.OptionalValueType(int),
        strings.NO_RULES: parsing.DefaultValueType(parsing.SequenceType(str, set), []),
        strings.NOTE: parsing.DefaultValueType(str, ''),
        strings.OBSERVER_LEVEL: parsing.OptionalValueType(
            parsing.EnumerationType((strings.MASTER_TYPE, strings.OMNISCIENT_TYPE, strings.OBSERVER_TYPE))),
        strings.ORDER_HISTORY: parsing.DefaultValueType(
            parsing.DictType(str, parsing.DictType(str, parsing.SequenceType(str))), {}),
        strings.OUTCOME: parsing.DefaultValueType(parsing.SequenceType(str), []),
        strings.PHASE: parsing.DefaultValueType(str, ''),
        strings.PHASE_ABBR: parsing.DefaultValueType(str, ''),
        strings.PHASE_SUMMARIES: parsing.DefaultValueType(parsing.DictType(str, str), {}),
        strings.POWERS: parsing.DefaultValueType(parsing.DictType(str, parsing.JsonableClassType(Power)), {}),
        strings.REGISTRATION_PASSWORD: parsing.OptionalValueType(str),
        strings.RESULT_HISTORY: parsing.DefaultValueType(parsing.DictType(str, parsing.DictType(
            str, parsing.SequenceType(parsing.StringableType(common.StringableCode)))), {}),
        strings.ROLE: parsing.DefaultValueType(str, strings.SERVER_TYPE),
        strings.RULES: parsing.DefaultValueType(parsing.SequenceType(str, sequence_builder=list), ()),
        strings.STATE_HISTORY: parsing.DefaultValueType(parsing.DictType(str, dict), {}),
        strings.STATUS: parsing.DefaultValueType(parsing.EnumerationType(strings.ALL_GAME_STATUSES), strings.FORMING),
        strings.TIMESTAMP_CREATED: parsing.OptionalValueType(int),
        strings.VICTORY: parsing.DefaultValueType(parsing.SequenceType(int), []),
        strings.WIN: parsing.DefaultValueType(int, 0),
        strings.ZOBRIST_HASH: parsing.DefaultValueType(int, 0),
    }

    def __init__(self, game_id=None, **kwargs):
        """ Constructor """
        self.victory = None
        self.no_rules = set()
        self.meta_rules = []
        self.phase, self.note = '', ''
        self.map = None  # type: Map
        self.powers = {}
        self.outcome, self.error, self.popped = [], [], []
        self.orders, self.ordered_units = {}, {}
        self.phase_type = None
        self.win = None
        self.combat, self.command, self.result = {}, {}, {}
        self.supports, self.dislodged, self.lost = {}, {}, {}
        self.convoy_paths, self.convoy_paths_possible, self.convoy_paths_dest = {}, None, None
        self.zobrist_hash = 0
        self.renderer = None
        self.game_id = None  # type: str
        self.map_name = None  # type: str
        self.messages = None  # type: SortedDict
        self.role = None  # type: str
        self.rules = []
        self.state_history, self.order_history, self.result_history, self.message_history = {}, {}, {}, {}
        self.status = None  # type: str
        self.timestamp_created = None  # type: int
        self.n_controls = None
        self.deadline = 0
        self.registration_password = None
        self.observer_level = None
        self.controlled_powers = None
        self.daide_port = None
        self.fixed_state = None
        self.power_model_map = {}
        self.phase_summaries = {}
        # Caches
        self._unit_owner_cache = None               # {(unit, coast_required): owner}

        # Remove rules from kwargs (if present), as we want to add them manually using self.add_rule().
        rules = kwargs.pop(strings.RULES, None)

        # Update rules with game ID.
        kwargs[strings.GAME_ID] = game_id

        # Initialize game with kwargs.
        super(Game, self).__init__(**kwargs)

        # Check settings.
        if self.registration_password is not None and self.registration_password == '':
            raise exceptions.DiplomacyException('Registration password must be None or non-empty string.')
        if self.n_controls is not None and self.n_controls < 0:
            raise exceptions.NaturalIntegerException('n_controls must be a natural integer.')
        if self.deadline < 0:
            raise exceptions.NaturalIntegerException('Deadline must be a natural integer.')

        # Check rules.
        if rules is None:
            rules = list(DEFAULT_GAME_RULES)

        # Set game rules.
        for rule in rules:
            self.add_rule(rule)

        # Check settings about rule NO_DEADLINE.
        if 'NO_DEADLINE' in self.rules:
            self.deadline = 0

        # Check settings about rule SOLITAIRE.
        if 'SOLITAIRE' in self.rules:
            self.n_controls = 0
        elif self.n_controls == 0:
            # If number of allowed players is 0, the game can only be solitaire.
            self.add_rule('SOLITAIRE')

        # Check timestamp_created.
        if self.timestamp_created is None:
            self.timestamp_created = common.timestamp_microseconds()

        # Check game ID.
        if self.game_id is None:
            self.game_id = base64.b64encode(os.urandom(12), b'-_').decode('utf-8')

        # Validating status
        self._validate_status(reinit_powers=(self.timestamp_created is None))

        if self.powers:
            # Game loaded with powers.
            # Associate loaded powers with this game.
            for power in self.powers.values():
                power.game = self
        else:
            # Begin game.
            self._begin()

        # Game loaded.

        # Check map powers.
        assert all(self.has_power(power_name) for power_name in self.map.powers)

        # Check role and consistency between all power roles and game role.
        if self.has_power(self.role):
            # It's a power game. Each power must be a player power.
            assert all(power.role == power.name for power in self.powers.values())
        else:
            # We should have a non-power game and each power must have same role as game role.
            assert self.role in strings.ALL_ROLE_TYPES
            assert all(power.role == self.role for power in self.powers.values())

        # Wrap history fields into runtime sorted dictionaries.
        # This is necessary to sort history fields by phase name.

        self._phase_wrapper_type = common.str_cmp_class(self.map.compare_phases)

        self.order_history = SortedDict(self._phase_wrapper_type, dict,
                                        {self._phase_wrapper_type(key): value
                                         for key, value in self.order_history.items()})
        self.message_history = SortedDict(self._phase_wrapper_type, SortedDict,
                                          {self._phase_wrapper_type(key): value
                                           for key, value in self.message_history.items()})
        self.state_history = SortedDict(self._phase_wrapper_type, dict,
                                        {self._phase_wrapper_type(key): value
                                         for key, value in self.state_history.items()})
        self.result_history = SortedDict(self._phase_wrapper_type, dict,
                                         {self._phase_wrapper_type(key): value
                                          for key, value in self.result_history.items()})

    def __str__(self):
        """ Returns a string representation of the game instance """
        show_map = self.map
        show_result = self.outcome

        text = ''
        text += 'GAME %s%s%s' % (self.game_id, '\nPHASE ', self.phase)
        text += '\nMAP %s' % self.map_name if show_map else ''
        text += '\nRESULT %s' % ' '.join(self.outcome) if show_result else ''
        text += '\nRULE '.join([''] + [rule for rule in self.rules if rule not in self.meta_rules])
        text += '\nRULE !'.join([''] + [no_rule for no_rule in self.no_rules])
        return text

    def __deepcopy__(self, memo):
        """ Fast deep copy implementation """
        cls = self.__class__
        result = cls.__new__(cls)

        # Deep copying
        for key in self._slots:
            if key in ['map', 'renderer', 'powers']:
                continue
            setattr(result, key, deepcopy(getattr(self, key)))
        setattr(result, 'map', self.map)
        setattr(result, 'powers', {})
        for power in self.powers.values():
            result.powers[power.name] = deepcopy(power)
            setattr(result.powers[power.name], 'game', result)
        return result

    # ====================================================================
    #   Public Interface
    # ====================================================================

    @property
    def _slots(self):
        """ Return an iterable of all attributes of this object.
            Should be used in place of "self.__slots__" to be sure to retrieve all
            attribute names from a derived class (including parent slots).
        """
        return (name for cls in type(self).__mro__ for name in getattr(cls, '__slots__', ()))

    @property
    def power(self):
        """ (only for player games) Return client power associated to this game.

            :return: a Power object.
            :rtype: diplomacy.engine.power.Power
        """
        return self.powers[self.role] if self.is_player_game() else None

    @property
    def is_game_done(self):
        """ Returns a boolean flag that indicates if the game is done """
        return self.phase == 'COMPLETED'

    is_game_forming = property(lambda self: self.status == strings.FORMING)
    is_game_active = property(lambda self: self.status == strings.ACTIVE)
    is_game_paused = property(lambda self: self.status == strings.PAUSED)
    is_game_canceled = property(lambda self: self.status == strings.CANCELED)
    is_game_completed = property(lambda self: self.status == strings.COMPLETED)
    current_short_phase = property(lambda self: self.map.phase_abbr(self.phase, self.phase))

    civil_disorder = property(lambda self: 'CIVIL_DISORDER' in self.rules)
    multiple_powers_per_player = property(lambda self: 'MULTIPLE_POWERS_PER_PLAYER' in self.rules)
    no_observations = property(lambda self: 'NO_OBSERVATIONS' in self.rules)
    no_press = property(lambda self: 'NO_PRESS' in self.rules)
    power_choice = property(lambda self: 'POWER_CHOICE' in self.rules)
    public_press = property(lambda self: 'PUBLIC_PRESS' in self.rules)
    real_time = property(lambda self: 'REAL_TIME' in self.rules)
    start_master = property(lambda self: 'START_MASTER' in self.rules)
    solitaire = property(lambda self: 'SOLITAIRE' in self.rules)

    # ==============================================================
    # Application/network methods (mainly used for connected games).
    # ==============================================================

    def current_state(self):
        """ Returns the game object. To be used with the following syntax:

            .. code-block:: python

                    with game.current_state():
                        orders = players.get_orders(game, power_name)
                        game.set_orders(power_name, orders)
        """
        return self

    def __enter__(self):
        """ Enter into game context. Initialize fixed state.
            Raise an exception if fixed state is already initialized to a different state,
            to prevent using the game into multiple contexts at same time.
        """
        current_state = (self.get_current_phase(), self.get_hash())
        if self.fixed_state and self.fixed_state != current_state:
            raise RuntimeError('Game already used in a different context.')
        self.fixed_state = current_state
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """ Exit from game context. Reset fixed state to None. """
        self.fixed_state = None

    def is_fixed_state_unchanged(self, log_error=True):
        """ Check if actual state matches saved fixed state, if game is used as context of a with-block.

            :param log_error: Boolean that indicates to log an error if state has changed
            :return: boolean that indicates if the state has changed.
        """
        current_state = (self.get_current_phase(), self.get_hash())
        if self.fixed_state and current_state != self.fixed_state:
            if log_error:
                LOGGER.error('State has changed from: %s to %s', self.fixed_state, current_state)
            return False
        return True

    def is_player_game(self):
        """ Return True if this game is a player game. """
        return self.has_power(self.role)

    def is_observer_game(self):
        """ Return True if this game is an observer game. """
        return self.role == strings.OBSERVER_TYPE

    def is_omniscient_game(self):
        """ Return True if this game is an omniscient game. """
        return self.role == strings.OMNISCIENT_TYPE

    def is_server_game(self):
        """ Return True if this game is a server game. """
        return self.role == strings.SERVER_TYPE

    def is_valid_password(self, registration_password):
        """ Return True if given plain password matches registration password. """
        if self.registration_password is None:
            return registration_password is None
        if registration_password is None:
            return False
        return common.is_valid_password(registration_password, self.registration_password)

    def is_controlled(self, power_name):
        """ Return True if given power name is currently controlled.

            :param power_name: power name
            :type power_name: str
            :rtype: bool
        """
        return self.get_power(power_name).is_controlled()

    def is_dummy(self, power_name):
        """ Return True if given power name is not currently controlled. """
        return not self.is_controlled(power_name)

    def does_not_wait(self):
        """ Return True if the game does not wait anything to process its current phase.
            The game is not waiting is all **controlled** powers have defined orders and wait flag set to False.
            If it's a solitaire game (with no controlled powers), all (dummy, not eliminated) powers must have defined
            orders and wait flag set to False. By default, wait flag for a dummy power is True.
            Note that an empty orders set is considered as a defined order as long as it was
            explicitly set by the power controller.
        """
        return all(power.is_eliminated() or power.does_not_wait() for power in self.powers.values())

    def has_power(self, power_name):
        """ Return True if this game has given power name. """
        return power_name in self.map.powers

    def has_expected_controls_count(self):
        """ Return True if game has expected number of map powers to be controlled.
            If True, the game can start (if not yet started).
        """
        return self.count_controlled_powers() == self.get_expected_controls_count()

    def count_controlled_powers(self):
        """ Return the number of controlled map powers. """
        return sum(1 for power_name in self.get_map_power_names() if self.is_controlled(power_name))

    def get_controlled_power_names(self, username):
        """ Return the list of power names currently controlled by given user name. """
        return [power.name for power in self.powers.values() if power.is_controlled_by(username)]

    def get_expected_controls_count(self):
        """ Return the number of map powers expected to be controlled in this game.
            This number is either specified in settings or the number of map powers.
        """
        expected_count = self.n_controls
        if expected_count is None:
            expected_count = len(self.powers)
        return expected_count

    def get_dummy_power_names(self):
        """ Return sequence of not eliminated dummy power names. """
        return set(power_name for power_name in self.get_map_power_names()
                   if self.is_dummy(power_name) and not self.get_power(power_name).is_eliminated())

    def get_dummy_unordered_power_names(self):
        """ Return a sequence of playable dummy power names
            without orders but still orderable and with orderable locations.
        """
        return [power_name for power_name in self.get_map_power_names() if
                # power must not be controlled by a user
                self.is_dummy(power_name)
                # power must be still playable
                and not self.get_power(power_name).is_eliminated()
                # power must not have yet orders
                and not self.get_orders(power_name)
                # power must have orderable locations
                and self.get_orderable_locations(power_name)
                # power must be waiting
                and self.get_power(power_name).wait]

    def get_controllers(self):
        """ Return a dictionary mapping each power name to its current controller name."""
        return {power.name: power.get_controller() for power in self.powers.values()}

    def get_controllers_timestamps(self):
        """ Return a dictionary mapping each power name to its controller timestamp. """
        return {power.name: power.get_controller_timestamp() for power in self.powers.values()}

    def get_random_power_name(self):
        """ Return a random power name from remaining dummy power names.
            Raise an exception if there are no dummy power names.
        """
        playable_power_names = list(self.get_dummy_power_names())
        if not playable_power_names:
            raise exceptions.RandomPowerException(1, len(playable_power_names))
        playable_power_names.sort()
        return playable_power_names[random.randint(0, len(playable_power_names) - 1)]

    def get_latest_timestamp(self):
        """ Return timestamp of latest data saved into this game
            (either current state, archived state or message).

            :return: a timestamp
            :rtype: int
        """
        timestamp = self.timestamp_created
        if self.state_history:
            timestamp = max(self.state_history.last_value()['timestamp'], timestamp)
        if self.messages:
            timestamp = max(self.messages.last_key(), timestamp)
        return timestamp

    @classmethod
    def filter_messages(cls, messages, game_role, timestamp_from=None, timestamp_to=None):
        """ Filter given messages based on given game role between given timestamps (bounds included).
            See method diplomacy.utils.SortedDict.sub() about bound rules.

            :param messages: a sorted dictionary of messages to filter.
            :param game_role: game role requiring messages. Either a special power name
                (PowerName.OBSERVER or PowerName.OMNISCIENT), a power name, or a list of power names.
            :param timestamp_from: lower timestamp (included) for required messages.
            :param timestamp_to: upper timestamp (included) for required messages.
            :return: a dict of corresponding messages (empty if no corresponding messages found),
                mapping messages timestamps to messages.
            :type messages: diplomacy.utils.sorted_dict.SortedDict
        """

        # Observer can see global messages and system messages sent to observers.
        if isinstance(game_role, str) and game_role == strings.OBSERVER_TYPE:
            return {message.time_sent: message
                    for message in messages.sub(timestamp_from, timestamp_to)
                    if message.is_global() or message.for_observer()}

        # Omniscient observer can see all messages.
        if isinstance(game_role, str) and game_role == strings.OMNISCIENT_TYPE:
            return {message.time_sent: message
                    for message in messages.sub(timestamp_from, timestamp_to)}

        # Power can see global messages and all messages she sent or received.
        if isinstance(game_role, str):
            game_role = [game_role]
        elif not isinstance(game_role, list):
            game_role = list(game_role)
        return {message.time_sent: message
                for message in messages.sub(timestamp_from, timestamp_to)
                if message.is_global() or message.recipient in game_role or message.sender in game_role}

    def get_phase_history(self, from_phase=None, to_phase=None, game_role=None):
        """ Return a list of game phase data from game history between given phases (bounds included).
            Each GamePhaseData object contains game state, messages, orders and order results for a phase.

            :param from_phase: either:

                - a string: phase name
                - an integer: index of phase in game history
                - None (default): lowest phase stored in game history

            :param to_phase: either:

                - a string: phase name
                - an integer: index of phase in game history
                - None (default): latest phase stored in game history

            :param game_role: (optional) role of game for which phase history is retrieved.
                If none, messages in game history will not be filtered.

            :return: a list of GamePhaseHistory objects
        """
        if isinstance(from_phase, int):
            from_phase = self.state_history.key_from_index(from_phase)
        elif isinstance(from_phase, str):
            from_phase = self._phase_wrapper_type(from_phase)
        if isinstance(to_phase, int):
            to_phase = self.state_history.key_from_index(to_phase)
        elif isinstance(to_phase, str):
            to_phase = self._phase_wrapper_type(to_phase)
        phases = self.state_history.sub_keys(from_phase, to_phase)
        states = self.state_history.sub(from_phase, to_phase)
        orders = self.order_history.sub(from_phase, to_phase)
        messages = self.message_history.sub(from_phase, to_phase)
        results = self.result_history.sub(from_phase, to_phase)
        if game_role:
            messages = [self.filter_messages(msg_dict, game_role) for msg_dict in messages]
        assert len(phases) == len(states) == len(orders) == len(messages) == len(results), (
            len(phases), len(states), len(orders), len(messages), len(results))
        return [
            GamePhaseData(
                name=str(phases[i]),
                state=states[i],
                orders=orders[i],
                messages=messages[i],
                results=results[i],
                # NEW: fetch summary from self.phase_summaries:
                summary=self.phase_summaries.get(str(phases[i]), "")
            )
            for i in range(len(phases))
        ]

    def get_phase_from_history(self, short_phase_name, game_role=None):
        """ Return a game phase data corresponding to given phase from phase history. """
        return self.get_phase_history(short_phase_name, short_phase_name, game_role)[0]

    def phase_history_from_timestamp(self, timestamp):
        """ Return list of game phase data from game history for which state timestamp >= given timestamp. """
        earliest_phase = ''
        for state in self.state_history.reversed_values():
            if state['timestamp'] < timestamp:
                break
            earliest_phase = state['name']
        return self.get_phase_history(from_phase=earliest_phase) if earliest_phase else []

    def extend_phase_history(self, game_phase_data):
        """ Add data from a game phase to game history.

            :param game_phase_data: a GamePhaseData object.
            :type game_phase_data: GamePhaseData
        """
        phase = self._phase_wrapper_type(game_phase_data.name)
        assert phase not in self.state_history
        assert phase not in self.message_history
        assert phase not in self.order_history
        assert phase not in self.result_history
        self.state_history.put(phase, game_phase_data.state)
        self.message_history.put(phase, game_phase_data.messages)
        self.order_history.put(phase, game_phase_data.orders)
        self.result_history.put(phase, game_phase_data.results)

    def set_status(self, status):
        """ Set game status with given status (should be in diplomacy.utils.strings.ALL_GAME_STATUSES). """
        assert status in strings.ALL_GAME_STATUSES
        self.status = status

    def draw(self, winners=None):
        """ Force a draw for this game, set status as COMPLETED and finish the game.

            :param winners: (optional) either None (all powers remaining to map are considered winners)
                or a sequence of required power names to be considered as winners.
            :return: a couple (previous state, current state)
                with game state before the draw and game state after the draw.
        """
        if winners is None:
            # Draw with all powers which still have units in map.
            winners = [power.name for power in self.powers.values() if power.units]

        # No orders will be processed when drawing, so clear current orders.
        self.clear_orders()

        # Collect data about current phase before drawing.
        previous_phase = self._phase_wrapper_type(self.current_short_phase)
        previous_orders = self.get_orders()
        previous_messages = self.messages.copy()
        previous_state = self.get_state()

        # Finish the game.
        self._finish(winners)

        # Then clear game and save previous phase.
        self.clear_vote()
        self.clear_orders()
        self.messages.clear()
        self.order_history.put(previous_phase, previous_orders)
        self.message_history.put(previous_phase, previous_messages)
        self.state_history.put(previous_phase, previous_state)
        self.result_history.put(previous_phase, {})

        # There are no expected results for orders, as there are no orders processed.

        previous_phase_data = GamePhaseData(name=str(previous_phase),
                                            state=previous_state,
                                            orders=previous_orders,
                                            messages=previous_messages,
                                            results={})
        current_phase_data = GamePhaseData(name=self.current_short_phase,
                                           state=self.get_state(),
                                           orders={},
                                           messages={},
                                           results={})

        return previous_phase_data, current_phase_data

    def set_controlled(self, power_name, username):
        """ Control power with given username (may be None to set dummy power).
            See method diplomacy.Power#set_controlled.
        """
        self.get_power(power_name).set_controlled(username)

    def update_dummy_powers(self, dummy_power_names):
        """ Force all power associated to given dummy power names to be uncontrolled.

            :param dummy_power_names: Sequence of required dummy power names.
        """
        for dummy_power_name in dummy_power_names:
            if self.has_power(dummy_power_name):
                self.set_controlled(dummy_power_name, None)

    def update_powers_controllers(self, powers_controllers, timestamps):
        """ Update powers controllers.

            :param powers_controllers: a dictionary mapping a power name to a controller name.
            :param timestamps: a dictionary mapping a power name to timestamp when related controller
                (in powers_controllers) was associated to power.
            :type powers_controllers: dict
        """
        for power_name, controller in powers_controllers.items():
            self.get_power(power_name).update_controller(controller, timestamps[power_name])

    def new_power_message(self, recipient, body):
        """ Create a undated (without timestamp) power message to be sent from a power to another via server.
            Server will answer with timestamp, and message will be updated
            and added to local game messages.

            :param recipient: recipient power name (string).
            :param body: message body (string).
            :return: a new GameMessage object.
            :rtype: GameMessage
        """
        assert self.is_player_game()
        if not self.has_power(recipient):
            raise exceptions.MapPowerException(recipient)
        return Message(phase=self.current_short_phase, sender=self.role, recipient=recipient, message=body)

    def new_global_message(self, body):
        """ Create an undated (without timestamp) global message to be sent from a power via server.
            Server will answer with timestamp, and message will be updated and added to local game messages.

            :param body: message body (string).
            :return: a new GameMessage object.
            :rtype: Message
        """
        assert self.is_player_game()
        return Message(phase=self.current_short_phase, sender=self.role, recipient=GLOBAL, message=body)

    def add_message(self, message):
        """ Add message to current game data.
            Only a server game can add a message with no timestamp:
            game will auto-generate a timestamp for the message.

            :param message: a GameMessage object to add.
            :return: message timestamp.
            :rtype: int
        """
        assert isinstance(message, Message)
        if self.is_player_game():
            assert message.is_global() or self.power.name in (message.sender, message.recipient)

        if message.time_sent is None:
            # This instance must be a server game.
            # Message should be a new message matching current game phase.
            # There should not be any more recent message in message history (as we are adding a new message).
            # We must generate a timestamp for this message.
            assert self.is_server_game()
            if message.phase != self.current_short_phase:
                raise exceptions.GamePhaseException(self.current_short_phase, message.phase)
            assert not self.messages or common.timestamp_microseconds() >= self.messages.last_key()
            time.sleep(1e-6)
            message.time_sent = common.timestamp_microseconds()

        self.messages.put(message.time_sent, message)
        return message.time_sent

    # Vote methods. For server and omniscient games only.
    # Observer game should not see votes.
    # Power game should know only vote of related power (votes for all other power should be 'neutral' in a power game).

    def has_draw_vote(self):
        """ Return True if all controlled non-eliminated powers have voted YES to draw game at current phase. """
        assert self.is_server_game() or self.is_omniscient_game()
        return all(
            power.vote == strings.YES
            for power in self.powers.values()
            if not power.is_eliminated()
        )

    def count_voted(self):
        """ Return the count of controlled powers who already voted for a draw for current phase. """
        assert self.is_server_game() or self.is_omniscient_game()
        return sum(1 for power in self.powers.values()
                   if not power.is_eliminated() and power.vote != strings.NEUTRAL)

    def clear_vote(self):
        """ Clear current vote. """
        for power in self.powers.values():
            power.vote = strings.NEUTRAL

    # ==============
    # Basic methods.
    # ==============

    def get_map_power_names(self):
        """ Return sequence of map power names. """
        return self.powers.keys()

    def get_current_phase(self):
        """ Returns the current phase (format 'S1901M' or 'FORMING' or 'COMPLETED') """
        return self._phase_abbr()

    def get_units(self, power_name=None):
        """ Retrieves the list of units for a power or for all powers

            :param power_name: Optional. The name of the power (e.g. ``'FRANCE'``) or None for all powers
            :return: A list of units (e.g. ``['A PAR', 'A MAR']``) if a power name is provided
                or a dictionary of powers with their units if None is provided
                (e.g. ``{'FRANCE': [...], ...}``)

            Note: Dislodged units will appear with a leading asterisk (e.g. ``'*A PAR'``)
        """
        if power_name is not None:
            power_name = power_name.upper()
        power = self.get_power(power_name)
        if power_name is not None:
            return power.units[:] + ['*{}'.format(unit) for unit in power.retreats]
        if power_name is None:
            units = {}
            for power in self.powers.values():
                units[power.name] = self.get_units(power.name)
            return units
        return []

    def get_centers(self, power_name=None):
        """ Retrieves the list of owned supply centers for a power or for all powers

            :param power_name: Optional. The name of the power (e.g. 'FRANCE') or None for all powers
            :return: A list of supply centers (e.g. ['PAR', 'MAR']) if a power name is provided
                or a dictionary of powers with their supply centers if None is provided
                (e.g. {'FRANCE': [...], ...}
        """
        if power_name is not None:
            power_name = power_name.upper()
        power = self.get_power(power_name)
        if power_name is not None:
            return power.centers[:]
        if power_name is None:
            centers = {}
            for power in self.powers.values():
                centers[power.name] = self.get_centers(power.name)
            return centers
        return []

    def get_orders(self, power_name=None):
        """ Retrieves the orders submitted by a specific power, or by all powers

            :param power_name: Optional. The name of the power (e.g. 'FRANCE') or None for all powers
            :return: A list of orders (e.g. ['A PAR H', 'A MAR - BUR']) if a power name is provided
                or a dictionary of powers with their orders if None is provided
                (e.g. {'FRANCE': ['A PAR H', 'A MAR - BUR', ...], ...}
        """
        if power_name is not None:
            power_name = power_name.upper()
        power = self.get_power(power_name)

        # Getting orders for a particular power
        # Skipping VOID and WAIVE orders in Adjustment/Retreats phase
        if power_name is not None:
            if self.get_current_phase()[-1] == 'M':
                if 'NO_CHECK' in self.rules:
                    power_orders = [power.orders[order] for order in power.orders if power.orders[order]]
                else:
                    power_orders = ['{} {}'.format(unit, unit_order) for unit, unit_order in power.orders.items()]
            else:
                power_orders = [order for order in power.adjust
                                if order and order != 'WAIVE' and order.split()[0] != 'VOID']
            return power_orders

        # Recursively calling itself to get all powers
        if power_name is None:
            orders = {}
            for power in self.powers.values():
                orders[power.name] = self.get_orders(power.name)
            return orders
        return []

    def get_orderable_locations(self, power_name=None):
        """ Find the location requiring an order for a power (or for all powers)

            :param power_name: Optionally, the name of the power (e.g. 'FRANCE') or None for all powers
            :return: A list of orderable locations (e.g. ['PAR', 'MAR']) if a power name is provided
                or a dictionary of powers with their orderable locations if None is not provided
                (e.g. {'FRANCE': [...], ...}
        """
        if power_name is not None:
            power_name = power_name.upper()
        power = self.get_power(power_name)

        # Single power
        if power_name is not None:
            current_phase_type = self.get_current_phase()[-1]

            # Adjustment
            if current_phase_type == 'A':
                build_count = len(power.centers) - len(power.units)

                # Building - All unoccupied homes
                if build_count > 0:
                    orderable_locs = self._build_sites(power)

                # Nothing can be built.
                elif build_count == 0:
                    orderable_locs = []

                # Disbanding - All units location
                else:
                    orderable_locs = [unit[2:5] for unit in power.units]

            # Retreating
            elif current_phase_type == 'R':
                orderable_locs = [unit[2:5] for unit in power.retreats]

            # Movement
            else:
                orderable_locs = [unit[2:5] for unit in power.units]

            # Returning and sorting for deterministic output
            return sorted(orderable_locs)

        # All powers
        return {power.name: self.get_orderable_locations(power.name) for power in self.powers.values()}

    def get_order_status(self, power_name=None, unit=None, loc=None):
        """ Returns a list or a dict representing the order status ('', 'no convoy', 'bounce', 'void', 'cut',
            'dislodged', 'disrupted') for orders submitted in the last phase

            :param power_name: Optional. If provided (e.g. 'FRANCE') will only return the order status of that
                power's orders
            :param unit: Optional. If provided (e.g. 'A PAR') will only return that specific unit order status.
            :param loc: Optional. If provided (e.g. 'PAR') will only return that specific loc order status.
                Mutually exclusive with unit
            :param phase_type: Optional. Returns the results of a specific phase type (e.g. 'M', 'R', or 'A')
            :return:

                - If unit is provided a list (e.g. [] or ['void', 'dislodged'])
                - If loc is provided, a couple of unit and list (e.g. ('A PAR', ['void', 'dislodged'])),
                  or (loc, []) if unit not found.
                - If power is provided a dict (e.g. {'A PAR': ['void'], 'A MAR': []})
                - Otherwise a 2-level dict
                  (e.g. {'FRANCE: {'A PAR': ['void'], 'A MAR': []}, 'ENGLAND': {}, ... }

        """
        # Specific location
        if unit or loc:
            assert bool(unit) != bool(loc), 'Required either a unit or a location, not both.'
            result_dict = self.result_history.last_value() if self.result_history else {}
            if unit:
                # Unit given, return list of order status
                return result_dict[unit][:] if unit in result_dict else []
            # Loc given, return a couple (unit found, list of order status)
            for result_unit, result_list in result_dict.items():
                if result_unit[2:5] == loc[:3]:
                    return result_unit, result_list[:]
            return loc, []

        # Specific power, returning dictionary
        if power_name is not None:
            power_name = power_name.upper()
        if power_name is not None:
            order_status = {}
            if self.state_history:
                state_history = self.state_history.last_value()
                for ordered_unit in state_history['units'][power_name]:
                    ordered_unit = ordered_unit.replace('*', '')
                    order_status[ordered_unit] = self.get_order_status(power_name, ordered_unit)
            return order_status

        # All powers
        if power_name is None:
            order_status = {}
            for power in self.powers.values():
                order_status[power.name] = self.get_order_status(power.name)
            return order_status
        return {}

    def get_power(self, power_name):
        """ Retrieves a power instance from given power name.

            :param power_name: name of power instance to retrieve. Power name must be as given
                in map file.
            :return: the power instance, or None if power name is not found.
            :rtype: diplomacy.engine.power.Power
        """
        return self.powers.get(power_name, None)

    def set_units(self, power_name, units, reset=False):
        """ Sets units directly on the map

            :param power_name: The name of the power who will own the units (e.g. 'FRANCE')
            :param units: An unit (e.g. 'A PAR') or a list of units (e.g. ['A PAR', 'A MAR']) to set
                          Note units starting with a '*' will be set as dislodged
            :param reset: Boolean. If, clear all units of the power before setting them
            :return: Nothing
        """
        power_name = power_name.upper()
        if not isinstance(units, list):
            units = [units]
        if power_name not in self.powers:
            return

        # Clearing old units if reset is true
        if reset and power_name in self.powers:
            self.powers[power_name].clear_units()

        regular_units = [unit for unit in units if unit[0] != '*']
        dislodged_units = [unit[1:] for unit in units if unit[0] == '*']
        influence = [unit[2:5] for unit in regular_units + dislodged_units]

        # Removing units that are already there
        for power in self.powers.values():
            for unit in regular_units:
                unit_loc = unit[2:5]
                for unit_to_remove in {p_unit for p_unit in power.units if p_unit[2:5] == unit_loc}:
                    self.update_hash(power.name, unit_type=unit_to_remove[0], loc=unit_to_remove[2:])
                    power.units.remove(unit_to_remove)
            for unit in dislodged_units:
                unit_loc = unit[2:5]
                for unit_to_remove in {p_unit for p_unit in power.retreats if p_unit[2:5] == unit_loc}:
                    self.update_hash(power.name, unit_type=unit_to_remove[0], loc=unit_to_remove[2:], is_dislodged=True)
                    del power.retreats[unit_to_remove]
            for loc in influence:
                if loc in power.influence:
                    power.influence.remove(loc)

        # Retrieving the target power
        power = self.get_power(power_name)

        # Re-adding normal units to the new power
        for unit in regular_units:
            word = unit.upper().split()
            if len(word) != 2:
                continue
            unit_type, unit_loc = word
            if unit_type in ('A', 'F') \
                    and unit_loc in [loc.upper() for loc in self.map.locs] \
                    and self.map.is_valid_unit(unit):
                if power and unit not in power.units:
                    self.update_hash(power_name, unit_type=unit_type, loc=unit_loc)
                    power.units.append(unit)
                    power.influence.append(unit[2:5])
            else:
                self.error += [err.MAP_INVALID_UNIT % unit]

        # Re-adding dislodged units to the new power
        for unit in dislodged_units:
            word = unit.upper().split()
            if len(word) != 2:
                continue
            unit_type, unit_loc = word
            if unit_type in ('A', 'F') and unit_loc in [loc.upper() for loc in self.map.locs]:
                if power and unit not in power.retreats:
                    self.update_hash(power_name, unit_type=unit_type, loc=unit_loc, is_dislodged=True)
                    power.retreats[unit] = []

        # Set retreats locations for all powers
        if self.get_current_phase()[-1] == 'R':
            for power in self.powers.values():
                for unit in power.retreats:
                    word = unit.upper().split()
                    if len(word) != 2:
                        continue
                    unit_type, unit_loc = word
                    abuts = [abut.upper() for abut in self.map.abut_list(unit_loc, incl_no_coast=True)
                             if self._abuts(unit_type, unit_loc, '-', abut.upper()) and not self._occupant(abut)]
                    power.retreats[unit] = abuts

        # Clearing cache
        self.clear_cache()

    def set_centers(self, power_name, centers, reset=False):
        """ Transfers supply centers ownership

            :param power_name: The name of the power who will control the supply centers (e.g. 'FRANCE')
            :param centers: A loc (e.g. 'PAR') or a list of locations (e.g. ['PAR', 'MAR']) to transfer
            :param reset: Boolean. If, removes ownership of all power's SC before transferring ownership of the new SC
            :return: Nothing
        """
        power_name = power_name.upper()
        if not isinstance(centers, list):
            centers = [centers]
        if power_name not in self.powers:
            return

        # Clearing old centers if reset is true
        if reset and power_name in self.powers:
            self.powers[power_name].clear_centers()

        # Removing centers that are already controlled by another power
        for power in self.powers.values():
            for center in centers:
                if center in power.centers:
                    self.update_hash(power.name, loc=center, is_center=True)
                    power.centers.remove(center)

        # Transferring center to power_name
        power = self.get_power(power_name)
        if power:
            for center in centers:
                if center in self.map.scs and center not in power.centers:
                    self.update_hash(power_name, loc=center, is_center=True)
                    power.centers += [center]

        # Clearing cache
        self.clear_cache()

    def set_orders(self, power_name, orders, expand=True, replace=True):
        """ Sets the current orders for a power

            :param power_name: The name of the power (e.g. 'FRANCE')
            :param orders: The list of orders (e.g. ['A MAR - PAR', 'A PAR - BER', ...])
            :param expand: Boolean. If set, performs order expansion and reformatting (e.g. adding unit type, etc.)
                If false, expect orders in the following format. False gives a performance improvement.
            :param replace: Boolean. If set, replace previous orders on same units, otherwise prevents re-orders.
            :return: Nothing

            Expected format: ::

                A LON H, F IRI - MAO, A IRI - MAO VIA, A WAL S F LON, A WAL S F MAO - IRI,
                F NWG C A NWY - EDI, A IRO R MAO, A IRO D, A LON B, F LIV B
        """
        if not self.is_fixed_state_unchanged(log_error=bool(orders)):
            return
        power_name = power_name.upper()

        if not self.has_power(power_name):
            raise exceptions.MapPowerException('Unknown power %s' % power_name)

        if self.is_player_game() and self.role != power_name:
            raise exceptions.GameRoleException('Player game for %s only accepts orders for this power.' % self.role)

        power = self.get_power(power_name)

        if not isinstance(orders, list):
            orders = [orders]

        # Remove any empty string from orders.
        orders = [order for order in orders if order]

        # Setting orders depending on phase type
        if self.phase_type == 'R':
            self._update_retreat_orders(power, orders, expand=expand, replace=replace)
        elif self.phase_type == 'A':
            self._update_adjust_orders(power, orders, expand=expand, replace=replace)
        else:
            self._update_orders(power, orders, expand=expand, replace=replace)
        power.order_is_set = (OrderSettings.ORDER_SET
                              if self.get_orders(power.name)
                              else OrderSettings.ORDER_SET_EMPTY)

    def set_wait(self, power_name, wait):
        """ Set wait flag for a power.

            :param power_name: name of power to set wait flag.
            :param wait: wait flag (boolean).
        """
        if not self.is_fixed_state_unchanged(log_error=False):
            return
        power_name = power_name.upper()

        if not self.has_power(power_name):
            return

        power = self.get_power(power_name.upper())          # type: diplomacy.engine.power.Power
        power.wait = wait

    def clear_units(self, power_name=None):
        """ Clear the power's units

            :param power_name: Optional. The name of the power whose units will be cleared (e.g. 'FRANCE'),
                otherwise all units on the map will be cleared
            :return: Nothing
        """
        for power in self.powers.values():
            if power_name is None or power.name == power_name:
                power.clear_units()
        self.clear_cache()

    def clear_centers(self, power_name=None):
        """ Removes ownership of supply centers

            :param power_name:  Optional. The name of the power whose centers will be cleared (e.g. 'FRANCE'),
                otherwise all centers on the map will lose ownership.
            :return: Nothing
        """
        for power in self.powers.values():
            if power_name is None or power.name == power_name:
                power.clear_centers()
        self.clear_cache()

    def clear_orders(self, power_name=None):
        """  Clears the power's orders

            :param power_name:  Optional. The name of the power to clear (e.g. 'FRANCE') or will clear orders for
                all powers if None.
            :return: Nothing
        """
        if not self.is_fixed_state_unchanged():
            return
        if power_name is not None:
            power = self.get_power(power_name.upper())
            power.clear_orders()
        else:
            for power in self.powers.values():
                power.clear_orders()

    def clear_cache(self):
        """ Clears all caches """
        self.convoy_paths_possible, self.convoy_paths_dest = None, None
        self._unit_owner_cache = None

    def set_current_phase(self, new_phase):
        """ Changes the phase to the specified new phase (e.g. 'S1901M') """
        if new_phase in ('FORMING', 'COMPLETED'):
            self.phase = new_phase
            self.phase_type = None
        else:
            self.phase = self.map.phase_long(new_phase)
            self.phase_type = self.phase.split()[-1][0]

    def render(self, incl_orders=True, incl_abbrev=False, output_format='svg', output_path=None):
        """ Renders the current game and returns its image representation

            :param incl_orders:  Optional. Flag to indicate we also want to render orders.
            :param incl_abbrev: Optional. Flag to indicate we also want to display the provinces abbreviations.
            :param output_format: The desired output format. Currently, only 'svg' is supported.
            :param output_path: Optional. The full path where to save the rendering on disk.
            :type incl_orders: bool, optional
            :type incl_abbrev: bool, optional
            :type output_format: str, optional
            :type output_path: str | None, optional
            :return: The rendered image in the specified format.
        """
        if not self.renderer:
            self.renderer = Renderer(self)
        return self.renderer.render(incl_orders=incl_orders,
                                    incl_abbrev=incl_abbrev,
                                    output_format=output_format,
                                    output_path=output_path)

    def add_rule(self, rule):
        """ Adds a rule to the current rule list

            :param rule: Name of rule to add (e.g. 'NO_PRESS')
            :return: Nothing
        """
        if not self.__class__.rule_cache:
            self._load_rules()
        valid_rules = {valid_rule for valid_rule in self.__class__.rule_cache[0]}

        if rule not in valid_rules or rule in self.no_rules:
            return

        forbidden_rules = self.__class__.rule_cache[0].get(rule, {}).get('!', [])
        rules_to_add = self.__class__.rule_cache[0].get(rule, {}).get('+', [])
        rules_to_remove = self.__class__.rule_cache[0].get(rule, {}).get('-', [])

        # Making sure we don't already have a forbidden rule
        for forbidden in forbidden_rules:
            if forbidden in self.rules:
                self.error += [err.GAME_FORBIDDEN_RULE % (forbidden, rule)]
                return
            if forbidden not in self.no_rules:
                self.no_rules.add(forbidden)

        # Adding rules
        for rule_to_add in rules_to_add:
            if rule_to_add not in self.rules:
                self.rules.append(rule_to_add)

        # Removing rules
        for rule_to_remove in rules_to_remove:
            if rule_to_remove in self.rules:
                self.rules.remove(rule_to_remove)

        # Adding main rule
        if rule not in self.rules:
            self.rules.append(rule)

    def remove_rule(self, rule):
        """ Removes a rule from the current rule list

            :param rule: Name of rule to remove (e.g. 'NO_PRESS')
            :return: Nothing
        """
        if rule in self.rules:
            self.rules.remove(rule)

    def load_map(self, reinit_powers=True):
        """ Load a map and process directives

            :param reinit_powers: Boolean. If true, empty powers dict.
            :return: Nothing, but stores the map in self.map
        """
        # Create a map, and check for errors
        self.map = Map(self.map_name)
        if self.map_name != self.map.name:
            raise RuntimeError('Invalid Map loaded. Expected %s - Got %s' % (self.map_name, self.map.name))

        # Adding map rules
        for rule in self.map.rules:
            self.add_rule(rule)

        # Build Zobrist tables
        self._build_hash_table()

        self.error += self.map.error

        # Sets the current phase to the long version
        if self.phase and ' ' not in self.phase and self.phase not in ('FORMING', 'COMPLETED'):
            self.phase = self.map.phase_long(self.phase)

        # Have the Game process all lines in the map file that were in DIRECTIVES clauses (this includes any RULE lines)
        # Do this for all directives given without a variant and for those specific for this Game's variant.
        if self.phase == 'FORMING':
            return

        # Resetting powers
        if reinit_powers:
            self.powers = {}

    def process(self, phase_summary_callback=None):
        """
        Process the current phase of the game, optionally providing
        a `phase_summary_callback(system_prompt, user_prompt) -> str` that generates
        a summary with an external LLM or similar approach.
        """
        previous_phase = self._phase_wrapper_type(self.current_short_phase)
        previous_orders = self.get_orders()
        previous_messages = self.messages.copy()
        previous_state = self.get_state()

        if self.error:
            if 'IGNORE_ERRORS' not in self.rules:
                print('The following errors were encountered and were cleared before processing.')
                for error in self.error:
                    print('-- %s' % error)
                print('-' * 32)
            self.error = []

        # ---- Process the game (e.g. movement, retreats, or adjustments).
        self._process()

        # Clean up or finalize for next phase
        self.clear_vote()
        self.clear_orders()
        self.messages.clear()

        # Archive prior data
        self.order_history.put(previous_phase, previous_orders)
        self.message_history.put(previous_phase, previous_messages)
        self.state_history.put(previous_phase, previous_state)

        # Generate a text summary (if a callback is provided)
        phase_summary_text = self._generate_phase_summary(
            previous_phase,
            summary_callback=phase_summary_callback
        )
        self.phase_summaries[str(previous_phase)] = phase_summary_text

        # Now build the GamePhaseData to return. (This is the new object that your `lm_game.py` receives.)
        # IMPORTANT: copy the summary we just generated so that `phase_data.summary` is not empty.
        phase_data = GamePhaseData(
            name=str(previous_phase),
            state=previous_state,
            orders=previous_orders,
            messages=previous_messages,
            results=self.result_history[previous_phase],
            summary=phase_summary_text  # <--- add this line
        )

        if not self.is_game_done:
            # Possibly set orders = [] for unorderable powers, etc.
            orderable_locations = self.get_orderable_locations()
            for power_name, locs in orderable_locations.items():
                if not locs and not self.get_power(power_name).is_eliminated():
                    self.set_orders(power_name, [])
                    self.set_wait(power_name, False)

        return phase_data

    def build_caches(self):
        """ Rebuilds the various caches """
        self.clear_cache()
        self._build_list_possible_convoys()
        self._build_unit_owner_cache()

    def rebuild_hash(self):
        """ Completely recalculate the Zobrist hash

            :return: The updated hash value
        """
        self.zobrist_hash = 0
        if self.map is None:
            return 0

        # Recalculating for each power
        for power in self.powers.values():
            for unit in power.units:
                self.update_hash(power.name, unit_type=unit[0], loc=unit[2:])
            for dis_unit in power.retreats:
                self.update_hash(power.name, unit_type=dis_unit[0], loc=dis_unit[2:], is_dislodged=True)
            for center in power.centers:
                self.update_hash(power.name, loc=center, is_center=True)
            for home in power.homes:
                self.update_hash(power.name, loc=home, is_home=True)

        # Clearing cache
        self.clear_cache()

        # Returning the new hash
        return self.get_hash()

    def get_hash(self):
        """ Returns the zobrist hash for the current game """
        # Needs to be a string, otherwise json.dumps overflows
        return str(self.zobrist_hash)

    def update_hash(self, power, unit_type='', loc='', is_dislodged=False, is_center=False, is_home=False):
        """ Updates the zobrist hash for the current game

            :param power: The name of the power owning the unit, supply center or home
            :param unit_type: Contains the unit type of the unit being added or remove from the board ('A' or 'F')
            :param loc:  Contains the location of the unit, supply center, of home being added or remove
            :param is_dislodged: Indicates that the unit being added/removed is dislodged
            :param is_center: Indicates that the location being added/removed is a supply center
            :param is_home: Indicates that the location being added/removed is a home
            :return: Nothing
        """
        if self.map is None:
            return
        zobrist = self.__class__.zobrist_tables[self.map_name]
        loc = loc[:3].upper() if is_center or is_home else loc.upper()
        power = power.upper()

        power_ix = zobrist['map_powers'].index(power)
        loc_ix = zobrist['map_locs'].index(loc)
        unit_type_ix = ['A', 'F'].index(unit_type) if unit_type in ['A', 'F'] else -1

        # Dislodged
        if is_dislodged:
            self.zobrist_hash ^= zobrist['dis_unit_type'][unit_type_ix][loc_ix]
            self.zobrist_hash ^= zobrist['dis_units'][power_ix][loc_ix]

        # Supply Center
        elif is_center:
            self.zobrist_hash ^= zobrist['centers'][power_ix][loc_ix]

        # Home
        elif is_home:
            self.zobrist_hash ^= zobrist['homes'][power_ix][loc_ix]

        # Regular unit
        else:
            self.zobrist_hash ^= zobrist['unit_type'][unit_type_ix][loc_ix]
            self.zobrist_hash ^= zobrist['units'][power_ix][loc_ix]

    def get_phase_data(self):
        """ Return a GamePhaseData object representing current game. """
        # Associate each power name to power orders, or None if order ist not set for the power.
        # This is done to make distinction between voluntary empty orders ([]) and unset orders (None).
        current_orders = {power.name: (self.get_orders(power.name) if power.order_is_set else None)
                          for power in self.powers.values()}
        # Game does not have results for current orders (until orders are processed and game phase is updated).
        return GamePhaseData(
            name=self.current_short_phase,
            state=self.get_state(),
            orders=current_orders,
            messages=self.messages.copy(),
            results={},
            # NEW: include summary from self.phase_summaries:
            summary=self.phase_summaries.get(self.current_short_phase, "")
        )

    def set_phase_data(self, phase_data, clear_history=True):
        """ Set game from phase data.

            :param phase_data: either a GamePhaseData or a list of GamePhaseData.
                If phase_data is a GamePhaseData, it will be treated as a list of GamePhaseData with 1 element.
                Last phase data in given list will be used to set current game internal state.
                Previous phase data in given list will replace current game history.
            :param clear_history: Indicate if we must clear game history fields before update.
        """
        # In the following code, we use Game.method instead of self.method to make sure
        # game internal state is correctly set without calling any asynchronous
        # overriden method from a derived class (especially NetworkGame class).

        if not phase_data:
            return
        if isinstance(phase_data, GamePhaseData):
            phase_data = [phase_data]
        elif not isinstance(phase_data, list):
            phase_data = list(phase_data)

        if clear_history:
            self._clear_history()
        else:
            # Clear orders and vote - Messages will be totally overwritten below.
            Game.clear_vote(self)
            Game.clear_orders(self)

        for game_phase_data in phase_data[:-1]:  # type: GamePhaseData
            Game.extend_phase_history(self, game_phase_data)

        current_phase_data = phase_data[-1]  # type: GamePhaseData
        Game.set_state(self, current_phase_data.state, clear_history=False)
        for power_name, power_orders in current_phase_data.orders.items():
            if power_orders is not None:
                Game.set_orders(self, power_name, power_orders)
        self.messages = current_phase_data.messages.copy()
        # We ignore 'results' for current phase data.

    def get_state(self):
        """ Gets the internal saved state of the game.
            This state is intended to represent current game view
            (powers states, orders results for previous phase, and few more info).
            See field message_history to get messages from previous phases.
            See field order_history to get orders from previous phases.
            To get a complete state of all data in this game object, consider using method Game.to_dict().

            :param make_copy: Boolean. If true, a deep copy of the game state is returned,
                otherwise the attributes are returned directly.
            :return: The internal saved state (dict) of the game
        """
        state = {}
        state['timestamp'] = common.timestamp_microseconds()
        state['zobrist_hash'] = self.get_hash()
        state['note'] = self.note
        state['name'] = self._phase_abbr()
        state['units'] = {}
        state['retreats'] = {}
        state['centers'] = {}
        state['homes'] = {}
        state['influence'] = {}
        state['civil_disorder'] = {}
        state['builds'] = {}

        # Setting powers data: units, centers, homes, influence and civil disorder.
        for power in self.powers.values():
            state['units'][power.name] = list(power.units) + ['*{}'.format(d) for d in power.retreats]
            state['retreats'][power.name] = power.retreats.copy()
            state['centers'][power.name] = list(power.centers)
            state['homes'][power.name] = list(power.homes)
            state['influence'][power.name] = list(power.influence)
            state['civil_disorder'][power.name] = power.civil_disorder
            # Setting build
            state['builds'][power.name] = {}
            if self.phase_type != 'A':
                state['builds'][power.name]['count'] = 0
            else:
                state['builds'][power.name]['count'] = len(power.centers) - len(power.units)
            state['builds'][power.name]['homes'] = []
            if state['builds'][power.name].get('count', 0) > 0:
                build_sites = self._build_sites(power)
                state['builds'][power.name]['count'] = min(len(build_sites), state['builds'][power.name]['count'])
                state['builds'][power.name]['homes'] = build_sites

        # Returning state
        state["phase"] = self.get_current_phase()
        return state

    def set_state(self, state, clear_history=True):
        """ Sets the game from a saved internal state

            :param state: The saved state (dict)
            :param clear_history: Boolean. If true, all game histories are cleared.
            :return: Nothing
        """
        if clear_history:
            self._clear_history()

        if 'map' in state and self.map.name != state['map']:
            raise RuntimeError('Inconsistent state map (state: %s, game: %s)' % (state['map'], self.map.name))
        if 'rules' in state:
            self.rules = []
            for rule in state['rules']:
                self.add_rule(rule)

        if 'note' in state:
            self.note = state['note']
        if 'name' in state and state['name']:
            self.set_current_phase(state['name'])
        if 'units' in state:
            for power_name, units in state['units'].items():
                self.set_units(power_name, units, reset=True)
        if 'retreats' in state:
            for power in self.powers.values():
                for unit in power.retreats:
                    if power.name in state['retreats'] and unit in state['retreats'][power.name]:
                        power.retreats[unit] = state['retreats'][power.name][unit]
        if 'centers' in state:
            for power_name, centers in state['centers'].items():
                self.set_centers(power_name, centers, reset=True)
        for power in self.powers.values():
            if 'homes' in state and power.name in state['homes']:
                power.homes = list(state['homes'][power.name])
            else:
                power.homes = list(self.map.homes[power.name])
        if 'influence' in state:
            for power_name, influence in state['influence'].items():
                power = self.get_power(power_name)
                power.influence = deepcopy(influence)
        if 'civil_disorder' in state:
            for power_name, civil_disorder in state['civil_disorder'].items():
                power = self.get_power(power_name)
                power.civil_disorder = civil_disorder

        # Rebuilding hash and returning
        self.rebuild_hash()
        self.build_caches()

    def get_all_possible_orders(self):
        """ Computes a list of all possible orders for all locations

            :return: A dictionary with locations as keys, and their respective list of possible orders as values
        """
        # pylint: disable=too-many-branches,too-many-nested-blocks
        possible_orders = {loc.upper(): set() for loc in self.map.locs}

        # Game is completed
        if self.get_current_phase() == 'COMPLETED':
            return {loc: list(possible_orders[loc]) for loc in possible_orders}

        # Building a dict of (unit, is_dislodged, retreat_list, duplicate) for each power
        # duplicate is to indicate that the real unit has a coast, and that was added a duplicate unit without the coast
        unit_dict = {}
        for power in self.powers.values():

            # Regular units
            for unit in power.units:
                unit_loc = unit[2:]
                unit_dict[unit_loc] = (unit, False, [], False)
                if '/' in unit_loc:
                    unit_dict[unit_loc[:3]] = (unit, False, [], True)

            # Dislodged units
            for unit, retreat_list in power.retreats.items():
                unit_loc = unit[2:]
                unit_dict['*' + unit_loc] = (unit, True, retreat_list, False)

        # Building a list of build counts and build_sites
        build_counts = {power_name: len(power.centers) - len(power.units) if self.phase_type == 'A' else 0
                        for power_name, power in self.powers.items()}
        build_sites = {power_name: self._build_sites(power) if self.phase_type == 'A' else []
                       for power_name, power in self.powers.items()}

        # Movement phase
        if self.phase_type == 'M':

            # Building a list of units and homes for each power
            power_units = {power_name: power.units[:] for power_name, power in self.powers.items()}

            # Hold
            for power_name in self.powers:
                for unit in power_units[power_name]:
                    order = unit + ' H'
                    possible_orders[unit[2:]].add(order)
                    if '/' in unit:
                        possible_orders[unit[2:5]].add(order)

            # Move, Support, Convoy
            for power_name in self.powers:
                for unit in power_units[power_name]:
                    unit_type, unit_loc = unit[0], unit[2:]
                    unit_on_coast = '/' in unit_loc
                    for dest in self.map.dest_with_coasts[unit_loc]:

                        # Move (Regular)
                        if self._abuts(unit_type, unit_loc, '-', dest):
                            order = unit + ' - ' + dest
                            possible_orders[unit_loc].add(order)
                            if unit_on_coast:
                                possible_orders[unit_loc[:3]].add(order)

                        # Support (Hold)
                        if self._abuts(unit_type, unit_loc, 'S', dest):
                            if dest in unit_dict:
                                other_unit, _, _, duplicate = unit_dict[dest]
                                if not duplicate:
                                    order = unit + ' S ' + other_unit[0] + ' ' + dest
                                    possible_orders[unit_loc].add(order)
                                    if unit_on_coast:
                                        possible_orders[unit_loc[:3]].add(order)

                        # Support (Move)
                        # Computing src of move (both from adjacent provinces and possible convoys)
                        # We can't support a unit that needs us to convoy it to its destination
                        abut_srcs = self.map.abut_list(dest, incl_no_coast=True)
                        convoy_srcs = self._get_convoy_destinations('A', dest, exclude_convoy_locs=[unit_loc])

                        # Computing coasts for source
                        src_with_coasts = [self.map.find_coasts(src) for src in abut_srcs + convoy_srcs]
                        src_with_coasts = {val for sublist in src_with_coasts for val in sublist}

                        for src in src_with_coasts:
                            if src not in unit_dict:
                                continue
                            src_unit, _, _, duplicate = unit_dict[src]
                            if duplicate:
                                continue

                            # Checking if src unit can move to dest (through adj or convoy), and that we can support it
                            # Only armies can move through convoy
                            if src[:3] != unit_loc[:3] \
                                    and self._abuts(unit_type, unit_loc, 'S', dest) \
                                    and ((src in convoy_srcs and src_unit[0] == 'A')
                                         or self._abuts(src_unit[0], src, '-', dest)):

                                # Adding with coast
                                order = unit + ' S ' + src_unit[0] + ' ' + src + ' - ' + dest
                                possible_orders[unit_loc].add(order)
                                if unit_on_coast:
                                    possible_orders[unit_loc[:3]].add(order)

                                # Adding without coasts
                                if '/' in dest:
                                    order = unit + ' S ' + src_unit[0] + ' ' + src + ' - ' + dest[:3]
                                    possible_orders[unit_loc].add(order)
                                    if unit_on_coast:
                                        possible_orders[unit_loc[:3]].add(order)

                    # Move Via Convoy
                    for dest in self._get_convoy_destinations(unit_type, unit_loc):
                        order = unit + ' - ' + dest + ' VIA'
                        possible_orders[unit_loc].add(order)

                    # Convoy
                    if unit_type == 'F':
                        convoy_srcs = self._get_convoy_destinations(unit_type, unit_loc, unit_is_convoyer=True)
                        for src in convoy_srcs:

                            # Making sure there is an army at the source location
                            if src not in unit_dict:
                                continue
                            src_unit, _, _, _ = unit_dict[src]
                            if src_unit[0] != 'A':
                                continue

                            # Checking where the src unit can actually go
                            convoy_dests = self._get_convoy_destinations('A', src, unit_is_convoyer=False)

                            # Adding them as possible moves
                            for dest in convoy_dests:
                                if self._has_convoy_path('A', src, dest, convoying_loc=unit_loc):
                                    order = unit + ' C A ' + src + ' - ' + dest
                                    possible_orders[unit_loc].add(order)

        # Retreat phase
        if self.phase_type == 'R':

            # Finding all dislodged units
            for unit_loc, (unit, is_dislodged, retreat_list, duplicate) in unit_dict.items():
                if not is_dislodged or duplicate:
                    continue
                unit_loc = unit_loc[1:]                 # Removing the leading *
                unit_on_coast = '/' in unit_loc

                # Disband
                order = unit + ' D'
                possible_orders[unit_loc].add(order)
                if unit_on_coast:
                    possible_orders[unit_loc[:3]].add(order)

                # Retreat
                for dest in retreat_list:
                    if dest[:3] not in unit_dict:
                        order = unit + ' R ' + dest
                        possible_orders[unit_loc].add(order)
                        if unit_on_coast:
                            possible_orders[unit_loc[:3]].add(order)

        # Adjustment phase
        if self.phase_type == 'A':

            # Building a list of units for each power
            power_units = {power_name: power.units[:] for power_name, power in self.powers.items()}

            for power_name in self.powers:
                power_build_count = build_counts[power_name]
                power_build_sites = build_sites[power_name]

                # Disband
                if power_build_count < 0:
                    for unit in power_units[power_name]:
                        unit_on_coast = '/' in unit
                        order = unit + ' D'
                        possible_orders[unit[2:]].add(order)
                        if unit_on_coast:
                            possible_orders[unit[2:5]].add(order)

                # Build
                if power_build_count > 0:
                    for site in power_build_sites:
                        for loc in self.map.find_coasts(site):
                            unit_on_coast = '/' in loc
                            if self.map.is_valid_unit('A ' + loc):
                                possible_orders[loc].add('A ' + loc + ' B')
                            if self.map.is_valid_unit('F ' + loc):
                                possible_orders[loc].add('F ' + loc + ' B')
                                if unit_on_coast:
                                    possible_orders[loc[:3]].add('F ' + loc + ' B')

                # Waive
                if power_build_count > 0:
                    for site in power_build_sites:
                        for loc in self.map.find_coasts(site):
                            possible_orders[loc].add('WAIVE')

        # Returning
        return {loc: list(possible_orders[loc]) for loc in possible_orders}

    # ====================================================================
    #   Private Interface - CONVOYS Methods
    # ====================================================================
    def _build_list_possible_convoys(self):
        """ Regenerates the list of possible convoy paths given the current fleet locations """
        # Already generated
        if self.convoy_paths_possible is not None:
            return
        self.convoy_paths_possible = []
        self.convoy_paths_dest = {}

        # Finding fleets on water
        convoying_locs = []
        for power in self.powers.values():
            for unit in power.units:
                if unit[0] == 'F' and self.map.area_type(unit[2:]) in ['WATER', 'PORT']:
                    convoying_locs += [unit[2:]]
        convoying_locs = set(convoying_locs)

        # Finding all possible convoy paths
        for nb_fleets in range(1, len(convoying_locs) + 1):
            for start, fleets, dests in self.map.convoy_paths[nb_fleets]:
                if fleets.issubset(convoying_locs):
                    self.convoy_paths_possible += [(start, fleets, dests)]

                    # Marking path to dest
                    self.convoy_paths_dest.setdefault(start, {})
                    for dest in dests:
                        self.convoy_paths_dest[start].setdefault(dest, [])
                        self.convoy_paths_dest[start][dest] += [fleets]

    def _is_convoyer(self, army, loc):
        """ Detects if there is a convoyer at thru location for army/fleet (e.g. can an army be convoyed through PAR)

            :param army: Boolean to indicate if unit being convoyed is army (1) or fleet (0)
            :param loc: Location we are checking (e.g. 'STP/SC')
            :return: Boolean to indicate if unit can be convoyed through location
        """
        # Armies can't convoy fleet, so if unit being convoyed is not an army, convoy not possible
        if not army:
            return False

        # Army can convoy through water, all units can convoy through port
        area_type = self.map.area_type(loc)
        area_type_cond = ((area_type == 'WATER') == army or area_type == 'PORT')

        # Making sure there is a valid unit on thru location to perform convoy
        unit_type_cond = self._unit_owner('F %s' % loc, coast_required=0)
        return area_type_cond and unit_type_cond

    def _is_moving_via_convoy(self, unit):
        """ Determines if a unit is moving via a convoy or through land

            :param unit: The name of the unit (e.g. 'A PAR')
            :return: A boolean (True, False) to indicate if the unit is moving via convoy
        """
        # Not moving or no paths
        if unit not in self.command or self.command[unit][0] != '-':
            return False
        if unit not in self.convoy_paths or not self.convoy_paths[unit]:
            return False

        # Otherwise, convoying since there is still an active valid path
        return True

    def _has_convoy_path(self, unit, start, end, convoying_loc=None):
        """ Determines if there is a convoy path for unit

            :param unit: The unit BEING convoyed (e.g. 'A' or 'F')
            :param start: The start location of the unit (e.g. 'LON')
            :param end: The destination of the unit (e.g. 'MAR')
            :param convoying_loc: Optional. If set, the convoying location must be in one of the paths
            :return: A boolean flag to indicate if the convoy is possible (if all units cooperate)
        """
        if unit != 'A':
            return False

        # Checking in table if there is a valid path and optionally if the convoying loc is in the path
        self._build_list_possible_convoys()
        active_paths = self.convoy_paths_dest.get(start, {}).get(end, [])
        return active_paths and (convoying_loc is None or [1 for path in active_paths if convoying_loc in path])

    def _get_convoying_units_for_path(self, unit, start, end):
        """ Returns a list of units who have submitted orders to convoy 'unit' from 'start' to 'end'

            :param unit: The unit BEING convoyed (e.g. 'A' or 'F')
            :param start: The start location of the unit (e.g. 'LON')
            :param end: The destination of the unit (e.g. 'MAR')
            :return: A list of convoying units (e.g. ['F NAO', 'F MAO']) having current orders to convoy path
        """
        convoying_units = []
        army = unit != 'F'
        expected_order = 'C %s %s - %s' % (unit, start[:3], end[:3])
        for unit_loc, unit_order in list(self.command.items()):
            if unit_order == expected_order and self._is_convoyer(army, unit_loc[2:]):
                convoying_units += [unit_loc]
        return convoying_units

    def _get_convoy_destinations(self, unit, start, unit_is_convoyer=False, exclude_convoy_locs=None):
        """ Returns a list of possible convoy destinations for a unit

            :param unit: The unit BEING convoyed (e.g. 'A' or 'F')
            :param start: The start location of the unit (e.g. 'LON')
            :param unit_is_convoyer: Boolean flag. If true, list all the dests that an unit being convoyed by unit
                could reach
            :param exclude_convoy_locs: Optional. A list of convoying location that needs to be excluded from all paths.
            :return: A list of convoying destinations (e.g. ['PAR', 'MAR']) that can be reached from start
        """
        if unit == 'A' and unit_is_convoyer:
            return []
        if unit == 'F' and not unit_is_convoyer:
            return []

        # Building cache
        self._build_list_possible_convoys()

        # If we are moving via convoy, we just read the destinations from the table
        if not unit_is_convoyer:
            if not exclude_convoy_locs:
                return list(self.convoy_paths_dest.get(start, {}).keys())

            # We need to loop to make sure there is a path without the excluded convoyer
            dests = []
            for dest, paths in self.convoy_paths_dest.get(start, {}).items():
                for path in paths:
                    if not [1 for excluded_loc in exclude_convoy_locs if excluded_loc in path]:
                        dests += [dest]
                        break
            return dests

        # If we are convoying, we need to loop through the possible convoy paths
        valid_dests = set([])
        for _, fleets, dests in self.convoy_paths_possible:
            if start in fleets and (exclude_convoy_locs is None
                                    or not [1 for excluded_loc in exclude_convoy_locs if excluded_loc in fleets]):
                valid_dests |= dests
        return list(valid_dests)

    def _get_convoy_paths(self, unit_type, start, end, via, convoying_units):
        """ Return a list of all possible convoy paths (using convoying units) from start to end

            :param unit_type: The unit type BEING convoyed (e.g. 'A' or 'F')
            :param start: The start location of the unit (e.g. 'LON')
            :param end: The destination of the unit (e.g. 'MAR')
            :param via: Boolean flag (0 or 1) to indicate if we want only paths with a local convoyer, or also paths
                including only foreign convoyers
            :param convoying_units: The list of units who can convoy the unit
            :return: A list of paths from start to end using convoying_units
        """
        if unit_type != 'A' or not convoying_units:
            return []

        # Building cache and finding possible paths with convoying units
        # Adding start and end location to every path
        self._build_list_possible_convoys()
        fleets = {loc[2:] for loc in convoying_units}
        paths = [path for path in self.convoy_paths_dest.get(start, {}).get(end, set([])) if path.issubset(fleets)]
        paths = [[start] + list(path) + [end] for path in paths]
        paths.sort(key=len)

        # No paths found
        if not paths:
            return []

        # We have intent to convoy, so we can use all paths
        if via:
            return paths

        # Assuming intent if end is not reachable from start (i.e. a convoy is required)
        if not self._abuts(unit_type, start, 'S', end):
            return paths

        # Otherwise, detecting if we intended to convoy
        unit_owner = self._unit_owner('%s %s' % (unit_type, start), coast_required=0)
        for convoyer in convoying_units:
            convoy_owner = self._unit_owner(convoyer, coast_required=1)

            # We have intent if one of the power's fleet issued a convoyed order
            # and there was a path using that fleet to move from start to end
            if unit_owner == convoy_owner and \
                    self._has_convoy_path(unit_type, start, end, convoying_loc=convoyer[2:]):
                return paths

        # We could not detect intent
        return []

    def _get_distance_to_home(self, unit_type, start, homes):
        """ Calculate the distance from unit to one of its homes
            Armies can move over water (4.D.8 choice d)

            :param unit_type: The unit type to calculate distance (e.g. 'A' or 'F')
            :param start: The start location of the unit (e.g. 'LON')
            :param homes: The list of homes (first one reached calculates the distance)
            :return: The minimum distance from unit to one of the homes
        """
        visited = []
        if not homes:
            return 99999

        # Modified Djikstra
        to_check = PriorityDict()
        to_check[start] = 0
        while to_check:
            distance, current = to_check.smallest()
            del to_check[current]

            # Found smallest distance
            if current[:3] in homes:
                return distance

            # Marking visited
            if current in visited:
                continue
            visited += [current]

            # Finding neighbors and updating distance
            for loc in self.map.abut_list(current, incl_no_coast=True):
                loc = loc.upper()
                if loc in visited:
                    continue

                # Calculating distance for armies over LAND/WATER/COAST and for Fleet over WATER/COAST
                if unit_type == 'A' or self._abuts(unit_type, current, '-', loc):
                    loc_distance = to_check[loc] if loc in to_check else 99999
                    to_check[loc] = min(distance + 1, loc_distance)

        # Could not find destination
        return 99999

    # ====================================================================
    #   Private Interface - ORDER Validation Methods
    # ====================================================================
    def _valid_order(self, power, unit, order, report=1):
        """ Determines if an order is valid

            :param power: The power submitting the order
            :param unit: The unit being affected by the order (e.g. 'A PAR')
            :param order: The actual order (e.g. 'H' or 'S A MAR')
            :param report: Boolean to report errors in self.errors
            :return: One of the following:

                * None -  The order is NOT valid at all
                * -1   -  It is NOT valid, BUT it does not get reported because it may be used to signal support
                * 0    -  It is valid, BUT some unit mentioned does not exist
                * 1    -  It is completed valid
        """
        # pylint: disable=too-many-return-statements,too-many-branches,too-many-statements
        # No order
        if not order:
            return None
        word = order.split()
        owner = self._unit_owner(unit)

        # No order
        if not word:
            return None

        status = 1 if owner is not None else 0
        unit_type = unit[0]
        unit_loc = unit[2:]
        order_type = word[0]

        # Make sure the unit exists (or if the player is in a game in which he can't necessarily know) could exist.
        # Also make sure any mentioned (supported or conveyed) unit could exists and could reach the listed destination
        if not self.map.is_valid_unit(unit):
            if report:
                self.error.append(err.GAME_ORDER_TO_INVALID_UNIT % unit)
            return None

        # Support / Convoy - 'S A/F XXX - YYY'
        if order_type in ('S', 'C') and word[1:]:
            if word[1] in ('A', 'F'):
                alter, other = word[1:3]
            else:
                alter, other = '?', word[1]

            # Checks if A/F XXX is a valid unit for loc (source)
            other = alter + ' ' + other
            if not self.map.is_valid_unit(other, no_coast_ok=1):
                if report:
                    self.error.append(err.GAME_ORDER_INCLUDES_INVALID_UNIT % other)
                return None

            # S [A/F] XXX - YYY
            # Checks if A/F YYY is a valid unit for loc (dest)
            if len(word) == 5 - (alter == '?'):
                other = alter + ' ' + word[-1]
                if not self.map.is_valid_unit(other, no_coast_ok=1):
                    if report:
                        self.error.append(err.GAME_ORDER_INCLUDES_INVALID_DEST % other)
                    return None

        # Check if unit exists
        # Status - 1 if unit has owner, 0 otherwise (Non-existent unit)
        if not status:
            if report:
                self.error.append(err.GAME_ORDER_NON_EXISTENT_UNIT % unit)
            return None
        if power is not owner:
            if report:
                self.error.append(err.GAME_ORDER_TO_FOREIGN_UNIT % unit)
            return None

        # Validate that anything in a SHUT location is only ordered to HOLD
        if self.map.area_type(unit_loc) == 'SHUT' and order_type != 'H':
            if report:
                self.error.append(err.GAME_UNIT_MAY_ONLY_HOLD % unit)
            return None

        # Validate support and convoy orders
        # Triggers error if Army trying to convoys
        if order_type == 'C' and (unit_type != 'F' or (self.map.area_type(unit_loc) not in ('WATER', 'PORT'))):
            if report:
                self.error.append(err.GAME_CONVOY_IMPROPER_UNIT % (unit, order))
            return None

        # -------------------------------------------------------------
        # SUPPORT OR CONVOY ORDER
        if order_type in ('C', 'S'):

            # Add the unit type (or '?') if not specified.
            # Note that the unit type is NOT added to the actual order -- just used during checking.
            order_text = 'CONVOY' if order_type == 'C' else 'SUPPORT'
            if len(word) > 1 and word[1] not in ('A', 'F'):
                terrain = self.map.area_type(word[1])
                if order_type == 'C':
                    word[1:1] = ['AF'[unit_type == 'A']]  # Convoying the opposite unit type A-F and F-A
                elif terrain == 'WATER':
                    word[1:1] = ['F']
                elif terrain == 'LAND':
                    word[1:1] = ['A']
                elif terrain:  # Other terrain, trying to determine if XXX exist
                    its_unit_type = [unit_type for unit_type in 'AF' if self._unit_owner(unit_type + ' ' + word[1])]
                    if its_unit_type:
                        word[1:1] = its_unit_type
                    else:
                        if report:
                            self.error.append(err.GAME_INVALID_ORDER_NON_EXISTENT_UNIT % (order_text, unit, order))
                        return None
                else:
                    if report:
                        self.error.append(err.GAME_INVALID_ORDER_RECIPIENT % (order_text, unit, order))
                    return None

            # Make sure we have enough to work with
            # e.g. syntax S A XXX - YYY or at least S XXX YYY
            if len(word) < 3:
                if report:
                    self.error.append(err.GAME_BAD_ORDER_SYNTAX % (order_text, unit, order))
                return None

            # Check that the recipient of the support or convoy exists
            rcvr, dest = ' '.join(word[1:3]), word[2]
            if not self._unit_owner(rcvr, 0):
                if report:
                    self.error.append(err.GAME_ORDER_RECIPIENT_DOES_NOT_EXIST % (order_text, unit, order))
                return None

            # Check that the recipient is not the same unit as the supporter
            if unit_loc == dest:
                if report:
                    self.error.append(err.GAME_UNIT_CANT_SUPPORT_ITSELF % (unit, order))
                return None

            # Only units on coasts can be convoyed, or invalid units convoying
            if order_type == 'C' \
                    and (word[1] != 'AF'[unit_type == 'A'] or self.map.area_type(dest) not in ('COAST', 'PORT')):
                if report:
                    self.error.append(err.GAME_UNIT_CANT_BE_CONVOYED % (unit, order))
                return None

            # Handle orders of the form C U xxx - xxx and S U xxx - xxx
            if len(word) == 5:
                if word[3] != '-':
                    if report:
                        self.error.append(err.GAME_BAD_ORDER_SYNTAX % (order_text, unit, order))
                    return None
                dest = word[4]

                # Coast is specified in the move, but ignored in the support and convoy order
                # DATC 6.B.4
                if '/' in dest:
                    dest = dest[:dest.find('/')]

                # Making sure the dest is COAST,PORT and that the convoyed order can land there
                if order_type == 'C':
                    if not (self.map.area_type(dest) in ('COAST', 'PORT')
                            and self.map.is_valid_unit(word[1] + ' ' + dest, unit[0] < 'F')):
                        if report:
                            self.error.append(err.GAME_BAD_CONVOY_DESTINATION % (unit, order))
                        return None

                # Checking that support can reach destination...
                elif (not self._abuts(word[1], word[2], order_type, dest)
                      and (rcvr[0] == 'F'
                           or not self._has_convoy_path(word[1], word[2][:3], dest))):
                    if report:
                        self.error.append(err.GAME_SUPPORTED_UNIT_CANT_REACH_DESTINATION % (unit, order))
                    return None

            # Make sure that a convoy order was formatted as above
            elif order_type == 'C':
                if report:
                    self.error.append(err.GAME_IMPROPER_CONVOY_ORDER % (unit, order))
                return None

            # Make sure a support order was either as above or as S U xxx or as S U xxx H
            elif len(word) != 3 and (len(word) != 4 or word[-1] != 'H'):
                if report:
                    self.error.append(err.GAME_IMPROPER_SUPPORT_ORDER % (unit, order))
                return None

            # Make sure the support destination can be reached...
            if order_type == 'S':
                if not self._abuts(unit_type, unit_loc, order_type, dest):
                    if report:
                        self.error.append(err.GAME_UNIT_CANT_PROVIDE_SUPPORT_TO_DEST % (unit, order))
                    return None

            # ... or that the fleet can perform the described convoy
            elif not self._has_convoy_path(rcvr[0], rcvr[2:5], dest, convoying_loc=unit_loc):
                if report:
                    self.error.append(err.GAME_IMPOSSIBLE_CONVOY_ORDER % (unit, order))
                return None

        # -------------------------------------------------------------
        # MOVE order
        elif order_type == '-':
            # Expected format '- xxx' or '- xxx VIA'
            if (len(word) & 1 and word[-1] != 'VIA') or (len(word[:-1]) & 1 and word[-1] == 'VIA'):
                if report:
                    self.error.append(err.GAME_BAD_MOVE_ORDER % (unit, order))
                return None

            # Only a convoying army can give a path
            if len(word) > 2 and unit_type != 'A' and self.map.area_type(unit_loc) not in ('COAST', 'PORT'):
                if report:
                    self.error.append(err.GAME_UNIT_CANT_CONVOY % (unit, order))
                return None

            # Step through "- xxx" in the order and ensure the unit can get there
            src = unit_loc
            offset = 1 if word[-1] == 'VIA' else 0
            to_loc = word[-1 - offset]

            # Making sure that the syntax is '- xxx'
            # The old syntax 'A XXX - YYY - ZZZ' is deprecated
            if len(word) - offset > 2 or word[0] != '-':
                if report:
                    self.error.append(err.GAME_BAD_MOVE_ORDER % (unit, order))
                return None

            # Checking that unit is not returning back where it started ...
            if to_loc == unit_loc:
                if report:
                    self.error.append(err.GAME_MOVING_UNIT_CANT_RETURN % (unit, order))
                return None

            # Move only possible through convoy
            if not self._abuts(unit_type, src, order_type, to_loc) or word[-1] == 'VIA':

                # Checking that destination is a COAST or PORT ...
                if self.map.area_type(to_loc) not in ('COAST', 'PORT'):
                    if report:
                        self.error.append(err.GAME_CONVOYING_UNIT_MUST_REACH_COST % (unit, order))
                    return None

                # Making sure that army is not having a specific coast as destination ...
                if unit_type == 'A' and '/' in to_loc:
                    if report:
                        self.error.append(err.GAME_ARMY_CANT_CONVOY_TO_COAST % (unit, order))
                    return None

                # Make sure there is at least a possible path
                if not self._has_convoy_path(unit_type, unit_loc, to_loc):
                    if report:
                        self.error.append(err.GAME_UNIT_CANT_MOVE_VIA_CONVOY_INTO_DEST % (unit, order))
                    return None

        # -------------------------------------------------------------
        # HOLD order
        elif order_type == 'H':
            if len(word) != 1:
                if report:
                    self.error.append(err.GAME_INVALID_HOLD_ORDER % (unit, order))
                return None

        else:
            if report:
                self.error.append(err.GAME_UNRECOGNIZED_ORDER_TYPE % (unit, order))
            return None

        # All done
        return status

    def _expand_order(self, word):
        """ Detects errors in order, convert to short version, and expand the default coast if necessary

            :param word: The words (e.g. order.split()) for an order
                (e.g. ['England:', 'Army', 'Rumania', 'SUPPORT', 'German', 'Army', 'Bulgaria']).
            :return: The compacted and expanded order (e.g. ['A', 'RUM', 'S', 'A', 'BUL'])
        """
        if not word:
            return word

        result = self.map.compact(' '.join(word))
        result = self.map.vet(self.map.rearrange(result), 1)

        # If multiple move seps '-' are present, skipping locs after each move separator except the last one
        count_move_seps = 0
        total_move_seps = len([1 for x in word if x == '-'])
        add_via_flag = total_move_seps >= 2

        # Removing errors (Negative values)
        final, order = [], ''
        for result_ix, (token, token_type) in enumerate(result):
            if token_type < 1:
                if token_type == -1 * POWER:
                    self.error.append(err.GAME_UNKNOWN_POWER % token)
                    continue
                elif token_type == -1 * UNIT:
                    self.error.append(err.GAME_UNKNOWN_UNIT_TYPE % token)
                    continue
                elif token_type == -1 * LOCATION:
                    self.error.append(err.GAME_UNKNOWN_LOCATION % token)
                elif token_type == -1 * COAST:
                    token_without_coast = token.split('/')[0]
                    if token_without_coast in self.map.aliases.values():
                        self.error.append(err.GAME_UNKNOWN_COAST % token)
                        result[result_ix] = token_without_coast, -1 * LOCATION
                    else:
                        self.error.append(err.GAME_UNKNOWN_LOCATION % token)
                elif token_type == -1 * ORDER:
                    self.error.append(err.GAME_UNKNOWN_ORDER_TYPE % token)
                    continue
                else:
                    self.error.append(err.GAME_UNRECOGNIZED_ORDER_DATA % token)
                    continue
                token_type = -1 * token_type

            # Remove power names. Checking ownership of the unit might be better
            if token_type == POWER:
                continue

            # Remove the "H" from any order having the form "u xxx S xxx H"
            # Otherwise storing order
            elif token_type == ORDER:
                if order == 'S' and token == 'H':
                    continue
                order += token

            # Skip locations except after the last move separator
            elif token_type == LOCATION and 0 < count_move_seps < total_move_seps:
                continue

            # Only keeping the first move separator. Others are discarded.
            elif token_type == MOVE_SEP:
                count_move_seps += 1
                if count_move_seps >= 2:
                    continue
                result[result_ix] = '-', token_type
                order += '-'

            elif token_type == OTHER:
                order = ''

            # Spot ambiguous place names and coasts in support and convoy orders
            if 'NO_CHECK' in self.rules:
                if token_type == LOCATION and token in self.map.unclear:
                    self.error.append(err.GAME_AMBIGUOUS_PLACE_NAME % token)
                if token_type == COAST and token.split('/')[0] in self.map.unclear:
                    self.error.append(err.GAME_AMBIGUOUS_PLACE_NAME % token)

            final += [token]

        # If we detected multiple move separated - Adding a final VIA flag
        if add_via_flag and final[-1] != 'VIA':
            final += ['VIA']

        # Default any fleet move's coastal destination, then we're done
        return self.map.default_coast(final)

    def _expand_coast(self, word):
        """ Makes sure the correct coast is specified (if any) is specified.
            For Fleets: Adjust to correct coast if wrong coast is specified
            For Armies: Removes coast if coast is specified
            (e.g. if F is on SPA/SC but the order is F SPA/NC - LYO, the coast will be added or corrected)

            :param word: A list of tokens (e.g. ['F', 'GRE', '-', 'BUL'])
            :return: The updated list of tokens (e.g. ['F', 'GRE', '-', 'BUL/SC'])
        """
        if not word:
            return word

        unit_type = word[0]
        loc = word[1]
        loc_without_coast = loc[:loc.find('/')] if '/' in loc else loc

        # For armies: Removing coast if specified
        if unit_type == 'A':
            if '/' in loc:
                word[1] = loc_without_coast
            if len(word) == 4 and '/' in word[3]:
                word[3] = word[3][:word[3].find('/')]

        # For fleets: If there is a unit in the country, but not on the specified coast, we need to correct the coast
        elif self._unit_owner('%s %s' % (unit_type, loc), coast_required=1) is None \
                and self._unit_owner('%s %s' % (unit_type, loc_without_coast), coast_required=0) is not None:

            # Finding the correct coast
            for loc in [l for l in self.map.locs if l[:3] == loc_without_coast]:
                if self._unit_owner('%s %s' % (word[0], loc), coast_required=1) is not None:
                    word[1] = loc
                    break

        # Removing cost if unit is supporting an army moving to coast
        # F WES S A MAR - SPA/SC -> F WES S A MAR - SPA
        if len(word) == 7 and '/' in word[-1] and word[2] == 'S' and word[3] == 'A':
            dest = word[-1]
            word[-1] = dest[:dest.find('/')]

        # Adjusting the coast if a fleet is supporting a move to the wrong coast
        # F WES S F GAS - SPA/SC -> F WES S F GAS - SPA/NC
        if len(word) == 7 and word[0] == 'F' and word[2] == 'S' and word[3] == 'F' and '/' in word[-1]:
            word = word[:3] + self.map.default_coast(word[3:6] + [word[6][:3]])

        # Returning with coasts fixed
        return word

    def _add_unit_types(self, item):
        """ Adds any missing "A" and "F" designations and (current) coastal locations for fleets.

            :param item: The words for expand_order() (e.g. ['A', 'RUM', 'S', 'BUL'])
            :return: The list of items with A/F and coasts added (e.g. ['A', 'RUM', 'S', 'A', 'BUL'])
        """
        # dependent is set when A/F is expected afterwards (so at start and after C/S)
        # had_type indicates that A/F was found
        word, dependent, had_type = [], 1, 0
        for token in item:
            if not dependent:
                dependent = token in 'CS'
            elif token in 'AF':
                had_type = 1
            elif token in ('RETREAT', 'DISBAND', 'BUILD', 'REMOVE'):
                pass
            else:
                try:
                    # We have a location
                    # Try to find an active or retreating unit at current location
                    unit = [unit for power in self.powers.values()
                            for unit in (power.units, power.retreats.keys())[self.phase_type == 'R']
                            if unit[2:].startswith(token)][0]

                    # If A/F is missing, add it
                    if not had_type:
                        word += [unit[0]]

                    # Trying to detect if coast is specified in retrieved unit location
                    # If yes, update the token, so it incorporates coastal information
                    if self.map.is_valid_unit(word[-1] + unit[1:]):
                        token = unit[2:]
                except IndexError:
                    pass
                dependent = had_type = 0

            # Add token to final list
            word += [token]
        return word

    def _add_coasts(self):
        """ This method adds the matching coast to orders supporting or (portage)
            convoying a fleet to a multi-coast province.

            :return: Nothing
        """
        # converting to unique format
        orders = {}
        for unit, order in self.orders.items():
            orders[unit] = order

        # Add coasts to support and (portage) convoy orders for fleets moving to a specific coast
        for unit, order in orders.items():
            # Only rewriting 'S F XXX - YYY' and 'C F XXX - YYY'
            if order[:3] not in ('S F', 'C F'):
                continue
            word = order.split()

            # rcvr is the unit receiving the support or convoy (e.g. F XXX in S F XXX - BER)
            # Making sure rcvr has also submitted orders (e.g. F XXX - YYY)
            rcvr = ' '.join(word[1:3])
            try:
                rcvr = [x for x in orders if x.startswith(rcvr)][0]
            except IndexError:
                # No orders found
                continue

            # Updating order to include rcvr full starting position (with coasts)
            orders[unit] = ' '.join([order[0], rcvr] + word[3:]).strip()

            # Checking if coast is specified in destination position
            if '-' in order:
                # his -> '- dest/coast'
                # updating order if coast is specified in his dest, but not ours
                his = ' '.join(orders.get(rcvr, '').split()[-2:])
                if his[0] == '-' and his.split('/')[0] == ' '.join(word[3:]):
                    orders[unit] = order[:2] + rcvr + ' ' + his

            # Updating game.orders object
            self.orders[unit] = orders[unit]

    def _validate_status(self, reinit_powers=True):
        """ Validates the status of the game object"""
        # Loading map and setting victory condition
        if not self.map:
            self.load_map(reinit_powers=reinit_powers)
        self.victory = self.map.victory

        # By default, 50% +1 of the scs
        # Or for victory homes, half the average number of home centers belonging to other powers plus one
        if not self.victory:
            self.victory = [len(self.map.scs) // 2 + 1]

        # Ensure game phase was set
        if not self.phase:
            self.phase = self.map.phase
        apart = self.phase.split()
        if len(apart) == 3:
            if '%s %s' % (apart[0], apart[2]) not in self.map.seq:
                self.error += [err.GAME_BAD_PHASE_NOT_IN_FLOW]
            self.phase_type = apart[2][0]
        else:
            self.phase_type = '-'

        # Validate the BEGIN phase (if one was given)
        if self.phase == 'FORMING':
            apart = self.map.phase.split()
            try:
                int(apart[1])
                del apart[1]
                if ' '.join(apart) not in self.map.seq:
                    raise Exception()
            except ValueError:
                self.error += [err.GAME_BAD_BEGIN_PHASE]

        # Set victory condition
        if self.phase not in ('FORMING', 'COMPLETED'):
            try:
                year = abs(int(self.phase.split()[1]) - self.map.first_year)
                win = self.victory[:]
                self.win = win[min(year, len(win) - 1)]
            except ValueError:
                self.error += [err.GAME_BAD_YEAR_GAME_PHASE]

        # Initialize power data
        for power in self.powers.values():

            # Initialize homes if needed
            if power.homes is None:
                power.homes = []
                for home in self.map.homes.get(power.name, []):
                    self.update_hash(power.name, loc=home, is_home=True)
                    power.homes.append(home)

    # ====================================================================
    #   Private Interface - Generic methods
    # ====================================================================
    def _load_rules(self):
        """ Loads the list of rules and their forced (+) and denied (!) corresponding rules

            :return: A tuple of dictionaries: rules, forced, and denied ::

                rules = {'NO_CHECK':
                             { 'group': '3 Movement Order',
                               'variant': 'standard',
                               '!': ['RULE_1', 'RULE_2'],
                               '+': ['RULE_3'] } }
                forced = {'payola': 'RULE_4'}
                denied = {'payola': 'RULE_5'}
        """
        if self.__class__.rule_cache:
            return self.__class__.rule_cache
        group = variant = ''
        data, forced, denied = {}, {}, {}
        file_path = os.path.join(settings.PACKAGE_DIR, 'README_RULES.txt')

        if not os.path.exists(file_path):
            self.error.append(err.GAME_UNABLE_TO_FIND_RULES)
            return data, forced, denied

        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                word = line.strip().split()

                # Rules are in the format <!-- RULE NAME !RULE_1 +RULE_2 -->
                # Where ! indicates a denied rule, and + indicates a forced rule
                if word[:2] == ['<!--', 'RULE'] and word[-1][-1] == '>':

                    # <!-- RULE GROUP 6 Secrecy -->
                    # group would be '6 Secrecy'
                    if word[2] == 'GROUP':
                        group = ' '.join(word[3:-1])

                    # <!-- RULE VARIANT standard -->
                    elif word[2] == 'VARIANT':
                        variant = word[3]
                        forced[variant] = [x[1:] for x in word[4:-1] if x[0] == '+']
                        denied[variant] = [x[1:] for x in word[4:-1] if x[0] == '!']

                    # <!-- RULE NAME !RULE_1 +RULE_2 -->
                    elif word[2] != 'END':
                        rule = word[2]
                        if rule not in data:
                            data[rule] = {'group': group, 'variant': variant}
                        for control in word[3:-1]:
                            if control[0] in '-=+!':
                                data[rule].setdefault(control[0], []).append(control[1:])

        self.__class__.rule_cache = (data, forced, denied)
        return data, forced, denied

    def _build_hash_table(self):
        """ Builds the Zobrist hash tables """
        if not self.map or self.map_name in self.__class__.zobrist_tables:
            return

        # Finding powers and locations
        map_powers = sorted([power_name for power_name in self.map.powers])
        map_locs = sorted([loc.upper() for loc in self.map.locs if self.map.area_type(loc) != 'SHUT'])
        nb_powers = len(map_powers)
        nb_locs = len(map_locs)
        sorted_concat_scs = '-'.join(sorted([scs.upper() for scs in self.map.scs]))

        # Generating a standardized seed
        # Map derivations (e.g. 'standard_age_of_empires') should have the same initial seed as their parent
        random_state = random.getstate()
        map_seed = (12345 + nb_locs + sum([ord(x) * 7 ** ix for ix, x in enumerate(sorted_concat_scs)])) % 2 ** 32
        random.seed(map_seed)
        self.__class__.zobrist_tables[self.map_name] = {
            'unit_type': [[random.randint(1, sys.maxsize) for _ in range(nb_locs)] for _ in range(2)],
            'units': [[random.randint(1, sys.maxsize) for _ in range(nb_locs)] for _ in range(nb_powers)],
            'dis_unit_type': [[random.randint(1, sys.maxsize) for _ in range(nb_locs)] for _ in range(2)],
            'dis_units': [[random.randint(1, sys.maxsize) for _ in range(nb_locs)] for _ in range(nb_powers)],
            'centers': [[random.randint(1, sys.maxsize) for _ in range(nb_locs)] for _ in range(nb_powers)],
            'homes': [[random.randint(1, sys.maxsize) for _ in range(nb_locs)] for _ in range(nb_powers)],
            'map_powers': map_powers,
            'map_locs': map_locs
        }
        random.setstate(random_state)

    # ====================================================================
    #   Private Interface - PROCESSING and phase change methods
    # ====================================================================
    def _begin(self):
        """ Called to begin the game and move to the start phase

            :return: Nothing
        """
        self._move_to_start_phase()
        self.note = ''
        self.win = self.victory[0]

        # Create dummy power objects for non-loaded powers.
        for power_name in self.map.powers:
            if power_name not in self.powers:
                self.powers[power_name] = Power(self, power_name, role=self.role)

        # Initialize all powers - Starter having type won't be initialized.
        for starter in self.powers.values():
            starter.initialize(self)

        # Build caches
        self.build_caches()

    def _process(self):
        """ Processes the current phase of the game """
        # Convert all raw movement phase "ORDER"s in a NO_CHECK game to standard orders before calling
        # Game.process(). All "INVALID" and "REORDER" orders are left raw -- the Game.move_results() method
        # knows how to detect and report them
        if 'NO_CHECK' in self.rules and self.phase_type == 'M':
            for power in self.powers.values():
                orders, power.orders, civil_disorder = power.orders, {}, power.civil_disorder
                for status, order in orders.items():
                    if status[:5] != 'ORDER':
                        power.orders[status] = order
                    elif order:
                        self._add_order(power, order.split())
                power.civil_disorder = civil_disorder

        # Processing the game
        if self.phase_type == 'M':
            self._determine_orders()
            self._add_coasts()

        # Resolving orders
        self._resolve()

    def _advance_phase(self):
        """ Advance the game to the next phase (skipping phases with no actions)

            :return: A list of lines to put in the results
        """

        # Save results for current phase.
        # NB: result_history is updated here, neither in process() nor in draw(),
        # unlike order_history, message_history and state_history.
        self.result_history.put(self._phase_wrapper_type(self.current_short_phase), self.result)
        self.result = {}

        # For each possible phase
        for _ in self.map.seq:

            # If game is not yet started, or completed can't advance
            if self.phase in (None, 'FORMING', 'COMPLETED'):
                break

            # Finding next phase and setting variables
            self.phase = self._find_next_phase()
            self.phase_type = self.phase.split()[-1][0]

            # Check phase determines if we need to process phase (0) or can skip it (1)
            if not self._check_phase():
                break
        else:
            raise Exception("FailedToAdvancePhase")

        # Rebuilding the caches
        self.build_caches()

        # Returning
        return []

    def _move_to_start_phase(self):
        """ Moves to the map's start phase

            :return: Nothing, but sets the self.phase and self.phase_type settings
        """
        # Retrieve the beginning phase and phase type from the map
        self.phase = self.map.phase
        self.phase_type = self.phase.split()[-1][0]

    def _find_next_phase(self, phase_type=None, skip=0):
        """ Returns the long name of the phase coming immediately after the current phase

            :param phase_type: The type of phase we are looking for
                (e.g. 'M' for Movement, 'R' for Retreats, 'A' for Adjust.)
            :param skip: The number of match to skip (e.g. 1 to find not the next phase, but the one after)
            :return: The long name of the next phase (e.g. FALL 1905 MOVEMENT)
        """
        return self.map.find_next_phase(self.phase, phase_type, skip)

    def _find_previous_phase(self, phase_type=None, skip=0):
        """ Returns the long name of the phase coming immediately before the current phase

            :param phase_type: The type of phase we are looking for
                (e.g. 'M' for Movement, 'R' for Retreats, 'A' for Adjust.)
            :param skip: The number of match to skip (e.g. 1 to find not the next phase, but the one after)
            :return: The long name of the previous phase (e.g. SPRING 1905 MOVEMENT)
        """
        return self.map.find_previous_phase(self.phase, phase_type, skip)

    def _get_start_phase(self):
        """ Returns the name of the start phase"""
        cur_phase, cur_phase_type = self.phase, self.phase_type
        self._move_to_start_phase()
        phase = self.phase
        self.phase, self.phase_type = cur_phase, cur_phase_type
        return phase

    def _check_phase(self):
        """ Checks if we need to process a phase, or if we can skip it if there are no actions

            :return: Boolean (0 or 1) - 0 if we need to process phase, 1 if we can skip it
        """
        # pylint: disable=too-many-return-statements
        # Beginning / End of game - Can't skip
        if self.phase in (None, 'FORMING', 'COMPLETED'):
            return 0

        # When changing phases, clearing all caches
        self.clear_cache()

        # Movement phase - Always need to process
        if self.phase_type == 'M':
            return 0

        # Retreats phase
        if self.phase_type == 'R':
            # We need to process if there are retreats
            if [1 for x in self.powers.values() if x.retreats]:
                return 0

            # Otherwise, clearing flags and skipping phase
            for power in self.powers.values():
                for dis_unit in power.retreats:
                    self.update_hash(power.name, unit_type=dis_unit[0], loc=dis_unit[2:], is_dislodged=True)
                power.retreats, power.adjust, power.civil_disorder = {}, [], 0
            self.result = {}
            if 'DONT_SKIP_PHASES' in self.rules:
                return 0
            return 1

        # Adjustments phase
        if self.phase_type == 'A':
            # Capturing supply centers
            self._capture_centers()

            # If completed, can't skip
            if self.phase == 'COMPLETED':
                return 0

            # If we have units to remove or to build, we need to process
            for power in self.powers.values():
                units, centers = len(power.units), len(power.centers)
                if [x for x in power.centers if x in power.homes]:
                    centers += (0 + min(0, len([0 for x in power.units if x[2:5] in power.homes])))
                if units > centers or (units < centers and self._build_limit(power)):
                    return 0

            # Otherwise, skipping
            self.result = {}
            if 'DONT_SKIP_PHASES' in self.rules:
                return 0
            return 1

        # Other phases. We need to process manually.
        return 0

    def _post_move_update(self):
        """ Deletes orders and removes CD flag after moves """
        for power in self.powers.values():
            power.orders, power.civil_disorder = {}, 0

    def _build_sites(self, power):
        """ Returns a list of sites where power can build units

            :param power: The power instance to check
            :return: A list of build sites
        """

        # Retrieving the list of homes (build sites) for the power, and the list of active powers
        homes = power.homes

        # Can build on any of his centers
        # -- BUILD_ANY: Powers may build new units at any owned supply center, not simply at their home supply centers.
        if 'BUILD_ANY' in self.rules:
            homes = power.centers

        # Updating homes to only include homes if they are unoccupied,
        homes = [h for h in homes if h in power.centers and h not in
                 [u[2:5] for p in self.powers.values() for u in p.units]]
        return homes

    def _build_limit(self, power, sites=None):
        """ Determines the maximum number of builds a power can do in an adjustment phase

            Note:

            - This function assumes that one unit can be built per build sites + alternative sites.
            - The actual maximum build limit would be less if units are built on alternative sites.

            :param power: The power instance to check
            :param sites: The power's build sites (or None to compute them)
            :return: An integer representing the maximum number of simultaneous builds
        """
        # Computing build_sites if not provided
        if sites is None:
            sites = self._build_sites(power)

        # Returning number of sites
        return len(sites)

    def _calculate_victory_score(self):
        """ Calculates the score to determine win for each power

            :return: A dict containing the score for each power (e.g. {'FRANCE': 10, 'ENGLAND': 2})
        """
        score = {}

        # Score is the number of supply centers owned
        for power in self.powers.values():
            score[power] = len(power.centers)
        return score

    def _determine_win(self, last_year):
        """ Determine if we have a win.

            :param last_year: A dict containing the score for each power (e.g. {'FRANCE': 10, 'ENGLAND': 2})
                (from the previous year)
            :return: Nothing
        """
        victors, this_year = [], self._calculate_victory_score()
        year_centers = list(this_year.values())

        # Determining win
        for power in self.powers.values():
            centers = this_year[power]

            # 1) you must have enough centers to win
            if (centers >= self.win

                    # 2) and you must grow or, if "HOLD_WIN", must have had a win
                    and (centers > last_year[power], last_year[power] >= self.win)['HOLD_WIN' in self.rules]

                    # 3) and you must be alone in the lead (not required in case of SHARED_VICTORY)
                    and ('SHARED_VICTORY' in self.rules
                         or (centers, year_centers.count(centers)) == (max(year_centers), 1))):
                victors += [power]

        # We have a winner!
        if victors:
            self._finish([victor.name for victor in victors])

        # DRAW if 100 years
        elif int(self.phase.split()[1]) - self.map.first_year + 1 == 100:
            self.draw()

    def _capture_centers(self):
        """ In Adjustment Phase, proceed with the capture of occupied supply centers

            :return: Nothing
        """
        victory_score_prev_year = self._calculate_victory_score()

        # If no power owns centers, initialize them
        if not [1 for x in self.powers.values() if x.centers]:
            for power in self.powers.values():
                for center in power.centers:
                    self.update_hash(power.name, loc=center, is_center=True)
                power.centers = []
                for center in power.homes:
                    self.update_hash(power.name, loc=center, is_center=True)
                    power.centers.append(center)

        # Remember the current center count for the various powers, for use in victory condition check,
        # then go through and see if any centers have been taken over
        unowned = self.map.scs[:]
        for power in self.powers.values():
            for center in power.centers:
                if center in unowned:
                    unowned.remove(center)

        # Keep track of scs lost
        self.lost = {}
        for power in list(self.powers.values()) + [None]:
            # Centers before takover
            if power:
                centers = power.centers
            else:
                centers = unowned

            # For each center, check if we took ownership
            for center in centers[:]:
                for owner in self.powers.values():

                    # 1) If center is unowned, or 2) owned by someone else and that we have a unit on it
                    # Proceed with transfer, and record lost
                    if (not power or owner is not power) and center in [x[2:5] for x in owner.units]:
                        self._transfer_center(power, owner, center)
                        if not power:
                            unowned.remove(center)
                        else:
                            self.lost[center] = power
                        break

        # Determining if we have a winner
        self._determine_win(victory_score_prev_year)

    def _transfer_center(self, from_power, to_power, center):
        """ Transfers a supply center from a power to another

            :param from_power: The power instance from whom the supply center is transfered
            :param to_power: The power instance to whom the supply center is transferred
            :param center: The supply center location (e.g. 'PAR')
            :return: Nothing
        """
        if from_power:
            self.update_hash(from_power.name, loc=center, is_center=True)
            from_power.centers.remove(center)
        if center not in to_power.centers:
            self.update_hash(to_power.name, loc=center, is_center=True)
            to_power.centers += [center]

    def _finish(self, victors):
        """ Indicates that a game is finished and has been won by 'victors'

            :param victors: The list of victors (e.g. ['FRANCE', 'GERMANY'])
            :return: Nothing
        """
        # Setting outcome, and end date. Clearing orders and saving.
        self.outcome = [self._phase_abbr()] + victors
        self.note = 'Victory by: ' + ', '.join([vic[:3] for vic in victors])
        self.phase = 'COMPLETED'
        self.set_status(strings.COMPLETED)
        for power in self.powers.values():
            for dis_unit in power.retreats:
                self.update_hash(power.name, unit_type=dis_unit[0], loc=dis_unit[2:], is_dislodged=True)
            power.retreats, power.adjust, power.civil_disorder = {}, [], 0

    def _phase_abbr(self, phase=None):
        """ Constructs a 5 character representation (S1901M) from a phase (SPRING 1901 MOVEMENT)

            :param phase: The full phase (e.g. SPRING 1901 MOVEMENT)
            :return: A 5 character representation of the phase
        """
        return self.map.phase_abbr(phase or self.phase)

    # ====================================================================
    #   Private Interface - ORDER Submission methods
    # ====================================================================
    def _add_order(self, power, word, expand=True, replace=True):
        """ Adds an order for a power
            :param power: The power instance issuing the order
            :param word: The order (e.g. ['A', 'PAR', '-', 'MAR'])
            :param expand: Boolean. If set, performs order expansion and reformatting (e.g. adding unit type, etc.).
               If false, expect orders in the following format. False gives a performance improvement.
            :param replace: Boolean. If set, replace previous orders on same units, otherwise prevents re-orders.
            :return: Nothing, but adds error to self.error

            Expected format: ::

                A LON H, F IRI - MAO, A IRI - MAO VIA, A WAL S F LON, A WAL S F MAO - IRI,
                F NWG C A NWY - EDI, A IRO R MAO, A IRO D, A LON B, F LIV B
        """
        if not word:
            return None

        raw_word = word

        if expand:
            # Check that the order is valid. If not, self.error will say why.
            word = self._expand_order(word)
            word = self._expand_coast(word)
            word = self._add_unit_types(word)
            word = self.map.default_coast(word)

            # Last word is '?' - Removing it
            if word and len(word[-1]) == 1 and not word[-1].isalpha():
                word = word[:-1]
            if len(word) < 2:
                return self.error.append(err.STD_GAME_BAD_ORDER % ' '.join(word))

        # Checking if we can order unit
        unit, order = ' '.join(word[:2]), ' '.join(word[2:])
        owner = self._unit_owner(unit)
        if not owner or owner is not power:
            self.error += [err.STD_GAME_UNORDERABLE_UNIT % ' '.join(word)]

        # Validating order
        elif order:
            valid = self._valid_order(power, unit, order)

            # Valid order. But is it to a unit already ordered? This is okay in a NO_CHECK game, and
            # we HOLD the unit. If not, pack it back into the power's order list.
            if valid is not None:
                power.civil_disorder = 0
                if valid == -1:
                    order += ' ?'
                if unit not in power.orders or (replace and 'NO_CHECK' not in self.rules):
                    power.orders[unit] = order
                elif 'NO_CHECK' in self.rules:
                    count = len(power.orders)
                    if power.orders[unit] not in ('H', order):
                        power.orders['REORDER %d' % count] = power.orders[unit]
                        count += 1
                        power.orders[unit] = 'H'
                    power.orders['REORDER %d' % count] = ' '.join(word)
                else:
                    self.error += [err.STD_GAME_UNIT_REORDERED % unit]

            # Invalid order in NO_CHECK game
            elif 'NO_CHECK' in self.rules:
                count = len(power.orders)
                power.orders['INVALID %d' % count] = ' '.join(raw_word)

        # Returning nothing
        return None

    def _update_orders(self, power, orders, expand=True, replace=True):
        """ Updates the orders of a power

            :param power: The power instance (or None if updating multiple instances)
            :param orders: The updated list of orders
                e.g. ['A MAR - PAR', 'A PAR - BER', ...]
            :param expand: Boolean. If set, performs order expansion and reformatting (e.g. adding unit type, etc.)
                If false, expect orders in the following format. False gives a performance improvement.
            :param replace: Boolean. If set, replace previous orders on same units, otherwise prevents re-orders.
            :return: Nothing

            Expected format: ::

                A LON H, F IRI - MAO, A IRI - MAO VIA, A WAL S F LON, A WAL S F MAO - IRI, F NWG C A NWY - EDI
                A IRO R MAO, A IRO D, A LON B, F LIV B
        """
        cur_power, has_orders, powers = power, [], []

        # For each order
        for line in orders:

            word = line.strip().split()
            who = cur_power

            if not word:
                continue

            if who not in powers:
                powers += [who]

            # Adds orders
            if 'NO_CHECK' in self.rules:
                data = self._expand_order(word)
                if len(data) < 3 and (len(data) == 1 or data[1] != 'H'):
                    self.error.append(err.STD_GAME_BAD_ORDER % line.upper())
                    continue

                # Voiding previous order on same unit
                if replace:
                    for order in who.orders:
                        order_parts = who.orders[order].split()
                        if len(order_parts) >= 2 and order_parts[1][:3] == word[1][:3]:
                            who.orders[order] = ''

                # Adding new order
                who.orders['ORDER %d' % (len(who.orders) + 1)] = ' '.join(word)
            else:
                self._add_order(who, word, expand=expand, replace=replace)
            if who.orders and who not in has_orders:
                has_orders += [who]

        # Make sure the player can update his orders
        if not powers:
            return 1
        if self.error:
            return self.error

        # Clear CD flag, even if orders were cleared
        for who in powers:
            who.civil_disorder = 0

        # Returning nothing
        return None

    def _add_retreat_orders(self, power, orders, expand=True, replace=True):
        """ Adds a retreat order (Retreats Phase)

            :param power: The power instance who is submitting orders (or None if power is in the orders)
            :param orders: The list of adjustment orders
                (format can be [Country: order], [Country, order, order], or [order,order])
            :param expand: Boolean. If set, performs order expansion and reformatting (e.g. adding unit type, etc.)
                If false, expect orders in the following format. False gives a performance improvement.
            :param replace: Boolean. If set, replace previous orders on same units, otherwise prevents re-orders.
            :return: Nothing, but adds error to self.error

            Expected format: ::

                A LON H, F IRI - MAO, A IRI - MAO VIA, A WAL S F LON, A WAL S F MAO - IRI, F NWG C A NWY - EDI
                A IRO R MAO, A IRO D, A LON B, F LIV B
        """
        # No orders, returning
        if not orders:
            power.adjust, power.civil_disorder = [], 0
            return

        # Processing each order
        adjust, retreated = [], []
        for order in orders:
            word = order.split()
            if not word or len(word) < 2:
                continue

            # Expanding and adding unit types
            if expand:
                word = self._expand_order([order])
                word = self._add_unit_types(word)

                # Add 'R' as order type for Retreat, 'D' for Disband
                if word[0] == 'R' and len(word) > 3:
                    del word[0]
                if word[0] in 'RD':
                    word = word[1:] + word[:1]

            # Checking if unit can retreat
            unit = ' '.join(word[:2])
            try:
                unit = [r_unit for r_unit in power.retreats if r_unit == unit or r_unit.startswith(unit + '/')][0]
            except IndexError:
                adjust += ['VOID ' + order]
                self.error.append(err.GAME_UNIT_NOT_IN_RETREAT % unit)
                continue

            # Checking if unit already retreated
            if unit in retreated:
                adjust += ['VOID ' + order]
                self.error.append(err.GAME_TWO_ORDERS_FOR_RETREATING_UNIT % unit)
                continue
            word[1] = unit[2:]

            # Adding Disband for retreats with no destination
            if len(word) == 3 and word[2] in 'RD':
                word[2] = 'D'

            # Checking if retreat destination is valid
            elif len(word) == 4 and word[2] in 'R-':
                word[2] = 'R'
                if word[3] not in power.retreats[unit]\
                        or self._unit_owner('A {}'.format(word[3][:3]), coast_required=0) \
                        or self._unit_owner('F {}'.format(word[3][:3]), coast_required=0):
                    self.error.append(err.GAME_INVALID_RETREAT_DEST % ' '.join(word))
                    adjust += ['VOID ' + order]
                    continue

            # Invalid retreat order - Voiding
            else:
                self.error.append(err.GAME_BAD_RETREAT_ORDER % ' '.join(word))
                adjust += ['VOID ' + order]
                continue

            # Adding retreat order and marking unit as retreated
            retreated += [unit]
            adjust += [' '.join(word)]

        # Replacing previous orders
        if replace:
            for order in adjust:
                word = order.split()
                if len(word) >= 2 and word[0] != 'VOID':
                    power.adjust = [adj_order for adj_order in power.adjust if adj_order.split()[1] != word[1]]

        # Otherwise, marking re-orders as invalid
        else:
            ordered_locs = [adj_order.split()[1] for adj_order in power.adjust]
            for order in adjust[:]:
                word = order.split()
                if len(word) >= 2 and word[1] in ordered_locs:
                    self.error += [err.GAME_MULTIPLE_ORDERS_FOR_UNIT % ' '.join(word[:2])]
                    adjust.remove(order)

        # Finalizing orders
        power.adjust += adjust
        power.civil_disorder = 0

    def _update_retreat_orders(self, power, orders, expand=True, replace=True):
        """ Updates order for Retreats phase

            :param power: The power instance submitting the orders
            :param orders: The updated orders
            :param expand: Boolean. If set, performs order expansion and reformatting (e.g. adding unit type, etc.)
                If false, expect orders in the following format. False gives a performance improvement.
            :param replace: Boolean. If set, replace previous orders on same units, otherwise prevents re-orders.
            :return: List of processing errors

            Expected format: ::

                A LON H, F IRI - MAO, A IRI - MAO VIA, A WAL S F LON, A WAL S F MAO - IRI, F NWG C A NWY - EDI
                A IRO R MAO, A IRO D, A LON B, F LIV B
        """
        self._add_retreat_orders(power, orders, expand=expand, replace=replace)
        return self.error

    def _add_adjust_orders(self, power, orders, expand=True, replace=True):
        """ Adds an adjustment order (Adjustment Phase)

            :param power: The power instance who is submitting orders (or None if power is in the orders)
            :param orders: The list of adjustment orders (format can be [Country: order],
                [Country, order, order], or [order,order])
            :param expand: Boolean. If set, performs order expansion and reformatting (e.g. adding unit type, etc.)
                If false, expect orders in the following format. False gives a performance improvement.
            :param replace: Boolean. If set, replace previous orders on same units, otherwise prevents re-orders.
            :return: Nothing, but adds error to self.error

            Expected format: ::

                A LON H, F IRI - MAO, A IRI - MAO VIA, A WAL S F LON, A WAL S F MAO - IRI, F NWG C A NWY - EDI
                A IRO R MAO, A IRO D, A LON B, F LIV B
        """
        # pylint: disable=too-many-branches
        # No orders submitted, returning
        if not orders:
            power.adjust, power.civil_disorder = [], 0
            return

        # Calculating if the power can build or remove units
        adjust, places = [], []
        need, sites = len(power.centers) - len(power.units), []
        order_type = 'D' if need < 0 else 'B'

        # If we can build, calculating list of possible build locations
        if need > 0:
            sites = self._build_sites(power)
            need = min(need, self._build_limit(power, sites))

        # Processing each order
        for order in orders:
            order = order.strip()

            if order == 'WAIVE':
                # Check WAIVE order immediately and continue to next loop step.
                if need >= 0:
                    adjust += [order]
                else:
                    adjust += ['VOID ' + order]
                    self.error += [err.GAME_NO_WAIVE_WITH_DISBAND]
                continue

            if not order or len(order.split()) < 2:
                continue
            word = self._expand_order([order]) if expand else order.split()

            # Checking if unit can Build/Disband, otherwise voiding order
            if word[-1] == order_type:
                pass
            elif word[-1] in 'BD':
                adjust += ['VOID ' + order]
                self.error += [err.GAME_ORDER_NOT_ALLOWED % order]
                continue

            # Adding unit type
            if word[-1] == 'D' and expand:
                word = self._add_unit_types(word)

            # Checking for 'Disband'
            order = ' '.join(word)
            if word[-1] == 'D':
                if len(word) == 3:
                    unit = ' '.join(word[:2])

                    # Invalid unit, voiding order
                    if unit not in power.units:
                        adjust += ['VOID ' + order]
                        self.error += [err.GAME_NO_SUCH_UNIT % unit]

                    # Order to remove unit
                    elif order not in adjust:
                        adjust += [order]

                    # Invalid order, voiding
                    else:
                        adjust += ['VOID ' + order]
                        self.error += [err.GAME_MULTIPLE_ORDERS_FOR_UNIT % unit]
                else:
                    adjust += ['VOID ' + order]
                    self.error += [err.GAME_BAD_ADJUSTMENT_ORDER % order]

            # Checking for BUILD
            elif len(word) == 3:
                site = word[1][:3]

                # Invalid build site
                if site not in sites:
                    adjust += ['VOID ' + order]
                    self.error += [err.GAME_INVALID_BUILD_SITE % order]

                # Site already used
                elif site in places:
                    adjust += ['VOID ' + order]
                    self.error += [err.GAME_MULT_BUILDS_IN_SITE % order]

                # Unit can't be built there
                elif not self.map.is_valid_unit(' '.join(word[:2])):
                    adjust += ['VOID ' + order]
                    self.error += [err.GAME_INVALID_BUILD_ORDER % order]

                # Valid build sites
                else:
                    adjust += [order]
                    places += [site]

            # Otherwise, unknown order - Voiding
            else:
                adjust += ['VOID ' + order]
                self.error += [err.GAME_BAD_ADJUSTMENT_ORDER % order]

        # NB: We skip WAIVE orders when checking for replacements.
        # We will check them later.

        # Replacing previous orders
        if replace:
            for order in adjust:
                word = order.split()
                if len(word) >= 2 and word[0] != 'VOID':
                    power.adjust = [adj_order for adj_order in power.adjust
                                    if adj_order == 'WAIVE' or adj_order.split()[1] != word[1]]

        # Otherwise, marking re-orders as invalid
        else:
            ordered_locs = [adj_order.split()[1] for adj_order in power.adjust if adj_order != 'WAIVE']
            for order in adjust[:]:
                word = order.split()
                if len(word) >= 2 and word[1] in ordered_locs:
                    self.error += [err.GAME_MULTIPLE_ORDERS_FOR_UNIT % ' '.join(word[:2])]
                    adjust.remove(order)

        # Finalizing orders
        power.adjust += adjust
        power.civil_disorder = 0

        # We check WAIVE orders in power.adjust after updating power.adjust,
        # as WAIVE orders depend on variable `need`, whom computation is relative to power
        # (ie. not relative to orders being currently adjusted).

        # Removing extra waive orders
        while 0 < need < len(power.adjust):
            if 'WAIVE' in power.adjust:
                power.adjust.remove('WAIVE')
            else:
                break

        # Adding missing waive orders
        if 'WAIVE' in power.adjust or power.is_dummy():
            power.adjust.extend(['WAIVE'] * (need - len(power.adjust)))

    def _update_adjust_orders(self, power, orders, expand=True, replace=True):
        """ Updates order for Adjustment phase

            :param power: The power instance submitting the orders
            :param orders: The updated orders
            :param expand: Boolean. If set, performs order expansion and reformatting (e.g. adding unit type, etc.)
                If false, expect orders in the following format. False gives a performance improvement.
            :param replace: Boolean. If set, replace previous orders on same units, otherwise prevents re-orders.
            :return: List of processing errors

            Expected format: ::

                A LON H, F IRI - MAO, A IRI - MAO VIA, A WAL S F LON, A WAL S F MAO - IRI, F NWG C A NWY - EDI
                A IRO R MAO, A IRO D, A LON B, F LIV B
        """
        self._add_adjust_orders(power, orders, expand=expand, replace=replace)
        return self.error

    def _determine_orders(self):
        """ Builds the self.orders dictionary (i.e. makes sure all orders are legitimate). """
        self.orders = {}

        # Determine the orders to be issued to each unit, based on unit ownership
        for power in self.powers.values():
            for unit, order in power.orders.items():
                if power is self._unit_owner(unit):
                    self.orders[unit] = order

        # In NO_CHECK games, ensure that orders to other player's units are reported as invalid
        # if no proxy was given
        if 'NO_CHECK' in self.rules:
            for power in self.powers.values():
                for unit, order in power.orders.items():
                    if unit[0] not in 'RI' and power is not self._unit_owner(unit):
                        order = unit + ' ' + order
                        power.orders['INVALID %d' % len(power.orders)] = order

    def _default_orders(self, power):
        """ Issues default orders for a power (HOLD)

            :param power: The power instance
            :return: Nothing
        """
        # Power has no units
        if not power.units:
            return

        # Power has not submitted all his orders, checking if we default to HOLD
        if not [x for x in power.units if self.orders.get(x)]:
            power.civil_disorder = 1
        for unit in power.units:
            self.orders.setdefault(unit, 'H')

    # ====================================================================
    #   Private Interface - ADJUDICATION Methods
    # ====================================================================
    def _abuts(self, unit_type, unit_loc, order_type, other_loc):
        """ Determines if a order for unit_type from unit_loc to other_loc is adjacent (Support and convoy only)

            :param unit_type: The type of unit ('A' or 'F')
            :param unit_loc: The location of the unit ('BUR', 'BUL/EC')
            :param order_type: The type of order ('S' for Support, 'C' for Convoy', '-' for move)
            :param other_loc: The location of the other unit
            :return: 1 if the locations are adjacent for the move, 0 otherwise
        """
        # Check if the map says the adjacency is good
        if not self.map.abuts(unit_type, unit_loc, order_type, other_loc):
            return 0
        return 1

    def _build_unit_owner_cache(self):
        """ Builds the unit_owner cache """
        if self._unit_owner_cache is not None:
            return
        self._unit_owner_cache = {}
        for owner in self.powers.values():
            for unit in owner.units:
                self._unit_owner_cache[(unit, True)] = owner                    # (unit, coast_required): owner
                self._unit_owner_cache[(unit, False)] = owner
                if '/' in unit:
                    self._unit_owner_cache[(unit.split('/')[0], False)] = owner

    def _unit_owner(self, unit, coast_required=1):
        """ Finds the power who owns a unit

            :param unit: The name of the unit to find (e.g. 'A PAR')
            :param coast_required: Indicates that the coast is in the unit
                (if 0, you can search for 'F STP' for example, but if 1, you must specify 'F STP/SC')
            :return: The power instance who owns the unit or None
        """
        # If coast_required is 0 and unit does not contain a '/'
        # return the owner if we find a unit that starts with unit
        # Don't count the unit if it needs to retreat (i.e. it has been dislodged)
        self._build_unit_owner_cache()
        return self._unit_owner_cache.get((unit, bool(coast_required)), None)

    def _occupant(self, site, any_coast=0):
        """ Finds the occupant of a site

            :param site: The site name (e.g. "STP")
            :param any_coast: Boolean to indicate to return unit on any coast
            :return: The unit (e.g. "A STP", "F STP/NC") occupying the site, None otherwise
        """
        if any_coast:
            site = site[:3]
        for power in self.powers.values():
            for unit in power.units:
                if unit[2:].startswith(site):
                    return unit
        return None

    def _strengths(self):
        """ This function sets self.combat to a dictionary of dictionaries, specifying each potential destination
            for every piece, with the strengths of each unit's attempt to get (or stay) there, and with the givers
            of supports that DON'T country dislodgement. (i.e. supports given by the power owning the occupying unit).

            :return: Nothing, but sets self.combat
        """
        # For example, the following orders, all by the same power:
        # A MUN H, A SIL - MUN, A BOH S A SIL - MUN, A RUH - MUN would result in:
        # e.g. { 'MUN': { 1 : [ ['A MUN', [] ], ['A RUH', [] ] ], 2 : [ ['A SIL', ['A BOH'] ] ] } }
        # MUN is holding, being attack without support from RUH and being attacked with support from SIL (S from BOH)
        self.combat = {}

        # For each order
        for unit, order in self.command.items():
            word = order.split()

            # Strength of a non-move or failed move is 1 + support
            if word[0] != '-' or self.result[unit]:
                place, strength = unit[2:5], 1

            # Strength of move depends on * and ~ in adjacency list
            else:
                offset = 1 if word[-1] == 'VIA' else 0
                place = word[-1 - offset][:3]
                strength = 1

            # Adds the list of supporting units
            # Only adding the support that DOES NOT count toward dislodgment
            self.combat \
                .setdefault(place, {}) \
                .setdefault(strength + self.supports[unit][0], []) \
                .append([unit, self.supports[unit][1]])

    def _detect_paradox(self, starting_node, paradox_action, paradox_last_words):
        """ Paradox detection algorithm. Start at starting node and move chain to see if node if performing
            paradox action

            :param starting_node: The location (e.g. PAR) where to start the paradox chain
            :param paradox_action: The action that would cause a paradox in the chain (e.g. 'S')
            :param paradox_last_words: The last words to detect in a order to cause a paradox (e.g. ['F', 'NTH'])
            :return: Boolean (1 or 0) to indicate if a paradox action was detected in the chain
        """
        visited_units = []
        current_node = starting_node
        current_unit = self._occupant(current_node)
        while current_unit is not None and current_unit not in visited_units:
            visited_units += [current_unit]
            current_order = self.command.get(current_unit, 'H')

            # Action and last words detected
            if (current_order[0] == paradox_action
                    and current_order.split()[-1 * len(paradox_last_words):] == paradox_last_words):
                return True

            # Continuing chain only if order is Support or Convoy
            if current_order.split()[0] not in 'SC':
                break
            current_node = current_order.split()[-1]
            current_unit = self._occupant(current_node)

        # No paradox detected
        return False

    def _check_disruptions(self, may_convoy, result, coresult=None):
        """ Determines convoy disruptions.

            :param may_convoy: Contains the dictionary of all convoys that have a chance to succeed
                (e.g. {'A PAR': ['BER', 'MUN']}
            :param result: Result to set for the unit if the convoying fleet would be dislodged
                (e.g. 'maybe', 'no convoy')
            :param coresult: Result to set for the convoyer if the convoying fleet would be dislodged (e.g. 'dislodged')
            :return: Nothing
        """
        for unit, word in may_convoy.items():

            # Removing '-'
            word = [w for w in word if w != '-']

            # Checking order of unit at dest
            offset = 1 if self.command.get(unit, []).split()[-1] == 'VIA' else 0
            convoy_dest = self.command.get(unit, 'H').split()[-1 - offset]
            unit_at_dest = self._occupant(convoy_dest)
            order_unit_at_dest = self.command.get(unit_at_dest, 'H')

            # Looping over all areas where convoys will take place (including destination)
            for place in word:
                area, convoyer = place[:3], 'AF'[unit[0] == 'A'] + ' ' + place
                strongest = self.combat[area][max(self.combat[area])]

                # Checking if the convoy is under attack
                for strong_unit in strongest:
                    if self._unit_owner(convoyer) != self._unit_owner(strong_unit[0]):
                        break
                else:
                    continue

                # Paradox Detection #1
                # [1st and 2nd order] Checking that we are not attacking a chain, with the last unit supporting
                # the convoy
                paradox = self._detect_paradox(convoy_dest, 'S', ['S', 'F', area])

                # Checking if the convoy can withstand the attack and there is not active paradox
                if convoyer in [x[0] for x in strongest] and not paradox:
                    continue

                # For a beleaguered garrison, checking if the destination is attacking / supporting an attack
                # against convoy
                if len(strongest) >= 2 and not paradox:
                    if order_unit_at_dest.split()[0] not in '-S' or order_unit_at_dest.split()[-1][:3] != area:
                        continue

                # Removing paths using place
                self.convoy_paths.setdefault(unit, [])
                for path in self.convoy_paths[unit]:
                    if place in path:
                        self.convoy_paths[unit].remove(path)

                # Paradox Detection #2 - Can convoyed unit use land route to cut support necessary to attack convoy
                paradox = False
                if self._abuts(unit[0], unit[2:], '-', convoy_dest):
                    paradox = self._detect_paradox(convoy_dest, 'S', ['-', area])

                # Setting the result if there is no convoy paths left, and
                #   1) there is no land route (or there is a paradox through the land route)
                #   or 2) the unit specified 'VIA' and doesn't want to try the land route (4.A.3)
                if not self.convoy_paths[unit] and (paradox
                                                    or not self._abuts(unit[0], unit[2:], '-', convoy_dest)
                                                    or (self._abuts(unit[0], unit[2:], '-', convoy_dest)
                                                        and self.command[unit].split()[-1] == 'VIA')):
                    self.result[unit] = [result]

                # Setting the result for a would-be dislodged fleet
                if coresult:
                    self.result[convoyer] = [coresult]

    def _boing(self, unit):
        """ Mark a unit bounced, and update the combat table to show the unit as
            having strength one at its current location

            :param unit: The unit to bounce (e.g. 'A PAR')
            :return: 1
        """
        self.result[unit] += [BOUNCE]
        self.combat \
            .setdefault(unit[2:5], {}) \
            .setdefault(1, []) \
            .append([unit, []])
        return 1

    def _bounce(self):
        """ This methods marks all units that can't get where they're going as bounced.
            It loops to handle bounce-chains.
        """
        # pylint: disable=too-many-nested-blocks
        bounced = 1
        while bounced:
            bounced = 0

            # STEP 6. MARK (non-convoyed) PLACE-SWAP BOUNCERS
            for unit, order in self.command.items():
                word = order.split()
                if self.result[unit] or word[0] != '-' or self._is_moving_via_convoy(unit):
                    continue
                crawl_ok, site = False, '- ' + unit[2:]
                swap = self._occupant(word[1], any_coast=not crawl_ok)
                if self._is_moving_via_convoy(swap):
                    continue
                if not (crawl_ok and swap and swap[0] == unit[0] == 'F'):
                    site = site.split('/')[0]
                if not (self.command.get(swap, '').find(site) or self.result[swap]):
                    my_strength = self.supports[unit][0] - len(self.supports[unit][1])
                    his_strength = self.supports[swap][0] - len(self.supports[swap][1])
                    our_strength = (self._unit_owner(unit) is self._unit_owner(swap)
                                    or self.supports[unit][0] == self.supports[swap][0])
                    if our_strength or my_strength <= his_strength:
                        self._boing(unit)
                    if our_strength or his_strength <= my_strength:
                        self._boing(swap)

                    # Marking support used for self-dislodgement as void
                    for supporting_unit in self.supports[unit][1]:
                        self.result[supporting_unit] += [VOID]
                    for supporting_unit in self.supports[swap][1]:
                        self.result[supporting_unit] += [VOID]
                    bounced = 1
            if bounced:
                continue
            # No (more) swap-bouncers

            # STEP 7. MARK OUTGUNNED BOUNCERS
            for place, conflicts in list(self.combat.items()):
                strength = sorted(conflicts.keys())
                for key in strength:
                    if key != strength[-1] or len(conflicts[key]) != 1:
                        for unit, no_help in conflicts[key]:
                            if not self.result[unit] and self.command[unit][0] == '-':
                                bounced = self._boing(unit)
            if bounced:
                continue
            # No (more) outgunned bouncers

            # STEP 8. MARK SELF-DISLODGE BOUNCERS
            for place, conflicts in list(self.combat.items()):
                strength = sorted(conflicts.keys())
                if len(conflicts[strength[-1]]) != 1:
                    continue
                strongest = conflicts[strength[-1]][0][0]
                if self.command[strongest][0] != '-' or self.result[strongest]:
                    continue
                no_help = len(conflicts[strength[-1]][0][1])
                guy = self._occupant(place)
                if guy:
                    owner = self._unit_owner(guy)
                    if ((self.command[guy][0] != '-' or self.result[guy])
                            and (owner is self._unit_owner(strongest)
                                 or (len(strength) > 1 and strength[-1] - no_help <= strength[-2]))):
                        bounced = self._boing(strongest)
                        for supporting_unit in conflicts[strength[-1]][0][1]:
                            if VOID not in self.result[supporting_unit]:
                                self.result[supporting_unit] += [VOID]

            # No (more) self-dislodge bouncers

    def _cut_support(self, unit, direct=0):
        """ See if the order made by the unit cuts a support. If so, cut it.

            :param unit: The unit who is attacking (and cutting support)
            :param direct: Boolean Flag - If set, the order must not only be a move, but also a non-convoyed move.
            :return: Nothing
        """
        order = self.command[unit]
        word = order.split()
        if word[0] != '-' or (direct and self._is_moving_via_convoy(unit)):
            return
        dest = word[-1] if word[-1] != 'VIA' else word[-2]
        other_unit = self._occupant(dest, any_coast=1)
        coord = self.command.get(other_unit, 'no unit at dest').split()
        support_target = 'F ' + coord[-1][:3]

        # pylint: disable=too-many-boolean-expressions
        if (coord[0] == 'S'
                and CUT not in self.result[other_unit]
                and VOID not in self.result[other_unit]

                # EXCEPTION A: CANNOT CUT SUPPORT YOU YOURSELF ARE GIVING
                and (self._unit_owner(unit) is not self._unit_owner(other_unit))

                # EXCEPTION B: CANNOT CUT SUPPORT FOR A MOVE AGAINST YOUR LOCATION
                and coord[-1][:3] != unit[2:5]

                # EXCEPTION C: OR (IF CONVOYED) FOR OR AGAINST ANY CONVOYING FLEET
                and (not self._is_moving_via_convoy(unit)
                     or self.command.get(support_target, 'H')[0] != 'C'
                     or VOID in self.result.get(support_target, [])
                     # EXCEPTION TO EXCEPTION C: IF THERE IS A ALTERNATIVE CONVOY ROUTE
                     or [1 for path in self.convoy_paths[unit] if support_target[2:] not in path])):

            # Okay, the support is cut.
            self.result[other_unit] += [CUT]
            affected = ' '.join(coord[1:3])  # Unit being supported
            self.supports[affected][0] -= 1
            if other_unit in self.supports[affected][1]:
                self.supports[affected][1].remove(other_unit)

    def _no_effect(self, unit, site):
        """ Removes a unit from the combat list of an attack site

            :param unit: The unit attacking the site (e.g. ['A PAR', []])
            :param site: The site being attacked (e.g. 'MAR')
            :return: Nothing
        """
        sups = [strength for strength, attack_unit in self.combat[site].items() if unit in attack_unit][0]
        self.combat[site][sups].remove(unit)
        if not self.combat[site][sups]:
            del self.combat[site][sups]
            if not self.combat[site]:
                del self.combat[site]

    def _unbounce(self, site):
        """ Unbounce any powerful-enough move that can now take the spot being vacated by the dislodger.

            :param site: The site being attacked
            :return: Nothing
        """
        # Detecting if there is only one attack winning at site
        most = max(self.combat[site])
        if len(self.combat[site][most]) > 1:
            return None

        # Unbouncing the winner of the attack at site
        unbouncer = self.combat[site][most][0][0]
        if BOUNCE in self.result[unbouncer]:
            self.result[unbouncer].remove(BOUNCE)
            if unbouncer in self.dislodged:
                del self.dislodged[unbouncer]
                return self.result[unbouncer].remove(DISLODGED)

            next_site = unbouncer[2:5]
            self._no_effect([unbouncer, []], next_site)
            if next_site in self.combat:
                self._unbounce(next_site)
        return None

    def _resolve_moves(self):
        """ Resolves the list of orders """
        # pylint: disable=too-many-statements,too-many-branches

        # -----------------------------------------------------------
        # STEP 0: DECLARE ALL RESULTS AS YET UNKNOWN
        self.result, self.supports, self.convoy_paths, may_convoy = {}, {}, {}, {}

        # Fill self.command from the self.orders dictionary
        # Fill self.ordered_units from the powers.units list
        # Default order is to hold
        self.command = {}
        self.ordered_units = {}
        for power in self.powers.values():
            self.ordered_units[power.name] = [unit for unit in power.units if unit in self.orders]
            for unit in power.units:
                self.command[unit] = self.orders.get(unit, 'H')
            if 'NO_CHECK' in self.rules:
                for order in [order for key, order in power.orders.items() if key.startswith('INVALID')]:
                    unit = ' '.join(order.split()[:2])
                    self.ordered_units[power.name] += [unit]
                    self.command[unit] = 'H'
                    self.result[unit] = [VOID]
            self._default_orders(power)

        for unit in self.command:
            self.result.setdefault(unit, [])
            self.supports.setdefault(unit, [0, []])

        # -----------------------------------------------------------
        # STEP 1A. CANCEL ALL INVALID ORDERS GIVEN TO UNITS ATTEMPTING TO MOVE BY CONVOY
        for unit, order in list(self.command.items()):
            word = order.split()
            if word[0] != '-':
                continue

            offset = 1 if word[-1] == 'VIA' else 0
            def flatten(nested_list):
                """ Flattens a sublist """
                return [list_item for sublist in nested_list for list_item in sublist]

            has_via_convoy_flag = 1 if word[-1] == 'VIA' else 0
            convoying_units = self._get_convoying_units_for_path(unit[0], unit[2:], word[1])
            possible_paths = self._get_convoy_paths(unit[0],
                                                    unit[2:],
                                                    word[1],
                                                    has_via_convoy_flag,
                                                    convoying_units)

            # No convoy path - Removing VIA and checking if adjacent
            if not possible_paths:
                if has_via_convoy_flag:
                    self.command[unit] = ' '.join(word[:-1])
                if not self._abuts(unit[0], unit[2:], 'S', word[1]):
                    self.result[unit] += [NO_CONVOY]

            # There is a convoy path, remembering the convoyers
            else:
                self.convoy_paths[unit] = possible_paths
                may_convoy.setdefault(unit, [])
                for convoyer in convoying_units:
                    if convoyer[2:] in flatten(possible_paths) and convoyer[2:] not in may_convoy[unit]:
                        may_convoy[unit] += [convoyer[2:]]

            # Marking all convoys that are not in any path
            invalid_convoys = convoying_units[:]
            all_path_locs = list(set(flatten(possible_paths)))
            for convoy in convoying_units:
                if convoy[2:] in all_path_locs:
                    invalid_convoys.remove(convoy)
            for convoy in invalid_convoys:
                self.result[convoy] = [NO_CONVOY]

        # -----------------------------------------------------------
        # STEP 1B. CANCEL ALL INVALID CONVOY ORDERS
        for unit, order in self.command.items():
            if order[0] != 'C':
                continue
            # word = ['C', 'PAR', 'MAR'] -> ['C', 'A', 'PAR', 'MAR']
            word, mover_type = order.split(), 'AF'[unit[0] == 'A']
            if word[1] != mover_type:
                word[1:1] = [mover_type]
            mover = '%s %s' % (mover_type, word[2])
            if self._unit_owner(mover):
                convoyer = may_convoy.get(mover, [])
                offset = 1 if self.command.get(mover, '').split()[-1] == 'VIA' else 0
                mover_dest = self.command.get(mover, '').split()[-1 - offset]
                if unit[2:] not in convoyer or word[-1] != mover_dest:
                    self.result[unit] += [VOID]
            else:
                self.command[unit] = 'H'

        # -----------------------------------------------------------
        # STEP 2. CANCEL INCONSISTENT SUPPORT ORDERS AND COUNT OTHERS
        for unit, order in self.command.items():
            if order[0] != 'S':
                continue
            word, signal = order.split(), 0

            # Remove any trailing "H" from a support-in-place order.
            if word[-1] == 'H':
                del word[-1]
                self.command[unit] = ' '.join(word)

            # Stick the proper unit type (A or F) into the order;
            # All supports will have it from here on
            where = 1 + (word[1] in 'AF')
            guy = self._occupant(word[where])

            # See if there is a unit to receive the support
            if not guy:
                self.command[unit] = 'H'
                if not signal:
                    self.result[unit] += [VOID]
                continue
            word[1:where + 1] = guy.split()
            self.command[unit] = ' '.join(word)

            # See if the unit's order matches the supported order
            if signal:
                continue
            coord = self.command[guy].split()

            # 1) Void if support is for hold and guy is moving
            if len(word) < 5 and coord[0] == '-':
                self.result[unit] += [VOID]
                continue

            # 2) Void if support is for move and guy isn't going where support is given
            offset = 1 if coord[-1] == 'VIA' else 0
            if len(word) > 4 and (coord[0], coord[-1 - offset]) != ('-', word[4]):
                self.result[unit] += [VOID]
                continue

            # 3) Void if support is giving for army moving via convoy, but move over convoy failed
            if NO_CONVOY in self.result[guy] and guy[0] == 'A':
                self.result[unit] += [VOID]
                continue

            # Okay, the support is valid
            self.supports[guy][0] += 1

            # If the unit is owned by the owner of the piece being attacked, add the unit to those
            # whose supports are not counted toward dislodgment.
            if coord[0] != '-':
                continue
            owner = self._unit_owner(unit)
            other = self._unit_owner(self._occupant(coord[-1], any_coast=1))
            if owner is other:
                self.supports[guy][1] += [unit]

        # -----------------------------------------------------------
        # STEP 3. LET DIRECT (NON-CONVOYED) ATTACKS CUT SUPPORTS
        for unit in self.command:
            if not self.result[unit]:
                self._cut_support(unit, direct=1)

        # -----------------------------------------------------------
        # STEPS 4 AND 5. DETERMINE CONVOY DISRUPTIONS
        cut, cutters = 1, []
        while cut:
            cut = 0
            self._strengths()

            # STEP 4. CUT SUPPORTS MADE BY (non-maybe) CONVOYED ATTACKS
            self._check_disruptions(may_convoy, MAYBE)
            for unit in may_convoy:
                if self.result[unit] or unit in cutters:
                    continue
                self._cut_support(unit)
                cutters += [unit]
                cut = 1
            if cut:
                continue

            # STEP 5. LOCATE NOW-DEFINITE CONVOY DISRUPTIONS, VOID SUPPORTS
            #         THESE CONVOYERS WERE GIVEN, AND ALLOW CONVOYING UNITS TO CUT SUPPORT
            self._check_disruptions(may_convoy, NO_CONVOY, DISRUPTED)
            for unit in may_convoy:
                if NO_CONVOY in self.result[unit]:
                    for sup, help_unit in self.command.items():
                        if not (help_unit.find('S %s' % unit) or self.result[sup]):
                            self.result[sup] = [NO_CONVOY]
                        if not (help_unit.find('C %s' % unit) or self.result[sup]):
                            self.result[sup] = [NO_CONVOY]
                    self.supports[unit] = [0, []]
                elif MAYBE in self.result[unit] and unit not in cutters:
                    self.result[unit], cut = [], 1
                    self._cut_support(unit)
                    cutters += [unit]

        # Recalculate strengths now that some are reduced by cuts
        self._strengths()

        # Mark bounces, then dislodges, and if any dislodges caused a cut
        # loop over this whole kaboodle again
        self.dislodged, cut = {}, 1
        while cut:  # pylint: disable=too-many-nested-blocks
            # -----------------------------------------------------------
            # STEPS 6-8. MARK BOUNCERS
            self._bounce()

            # STEP 9. MARK SUPPORTS CUT BY DISLODGES
            cut = 0
            for unit, order in self.command.items():
                if order[0] != '-' or self.result[unit]:
                    continue
                attack_order = order.split()
                offset = 1 if attack_order[-1] == 'VIA' else 0
                victim = self._occupant(attack_order[-1 - offset], any_coast=1)
                if victim and self.command[victim][0] == 'S' and not self.result[victim]:
                    word = self.command[victim].split()
                    supported, sup_site = self._occupant(word[2]), word[-1][:3]

                    # This next line is the key. Convoyed attacks can dislodge, but even when doing so, they cannot cut
                    # supports offered for or against a convoying fleet
                    # (They can cut supports directed against the original position of the army, though.)
                    if len(attack_order) > 2 and sup_site != unit[2:5]:
                        continue
                    self.result[victim] += [CUT]
                    cut = 1
                    for sups in self.combat.get(sup_site, {}):
                        for guy, no_help in self.combat[sup_site][sups]:
                            if guy != supported:
                                continue
                            self.combat[sup_site][sups].remove([guy, no_help])
                            if not self.combat[sup_site][sups]:
                                del self.combat[sup_site][sups]
                            sups -= 1
                            if victim in no_help:
                                no_help.remove(victim)
                            self.combat[sup_site].setdefault(sups, []).append([guy, no_help])
                            break
                        else:
                            continue
                        break

        # -----------------------------------------------------------
        # STEP 10. MARK DISLODGEMENTS AND UNBOUNCE ALL MOVES THAT LEAD TO DISLODGING UNITS
        for unit, order in self.command.items():
            if order[0] != '-' or self.result[unit]:
                continue
            site = unit[2:5]
            offset = 1 if order.split()[-1] == 'VIA' else 0
            loser = self._occupant(order.split()[-1 - offset], any_coast=1)
            if loser and (self.command[loser][0] != '-' or self.result[loser]):
                self.result[loser] = [res for res in self.result[loser] if res != DISRUPTED] + [DISLODGED]
                self.dislodged[loser] = site

                # Check for a dislodged swapper (attacker and dislodged units must not be convoyed.)
                # If found, remove the swapper from the combat list of the attacker's space
                head_to_head_battle = not self._is_moving_via_convoy(unit) and not self._is_moving_via_convoy(loser)
                if self.command[loser][2:5] == site and head_to_head_battle:
                    for sups, items in self.combat.get(site, {}).items():
                        item = [x for x in items if x[0] == loser]
                        if item:
                            self._no_effect(item[0], site)
                            break

                # Marking support for self-dislodgement as void
                for supporting_unit in self.supports[unit][1]:
                    self.result[supporting_unit] += [VOID]

            # Unbounce any powerful-enough move that can now take the spot being vacated by the dislodger.
            if site in self.combat:
                self._unbounce(site)

        # Done :-)

    def _move_results(self):
        """ Resolves moves (Movement phase) and returns a list of messages explaining what happened

            :return: A list of lines for the results file explaining what happened during the phase
        """
        # Resolving moves
        self._resolve_moves()

        # Determine any retreats
        for power in self.powers.values():
            for unit in [u for u in power.units if u in self.dislodged]:
                if unit not in power.retreats:
                    self.update_hash(power.name, unit_type=unit[0], loc=unit[2:], is_dislodged=True)
                power.retreats.setdefault(unit, [])
                attacker_site, site = self.dislodged[unit], unit[2:]
                attacker = self._occupant(attacker_site)
                if self.map.loc_abut.get(site):
                    pushee = site
                else:
                    pushee = site.lower()
                for abut in self.map.loc_abut[pushee]:
                    abut = abut.upper()
                    where = abut[:3]
                    if ((self._abuts(unit[0], site, '-', abut) or self._abuts(unit[0], site, '-', where))
                            and (not self.combat.get(where)
                                 and where != attacker_site or self._is_moving_via_convoy(attacker))):

                        # Armies cannot retreat to specific coasts
                        if unit[0] == 'F':
                            power.retreats[unit] += [abut]
                        elif where not in power.retreats[unit]:
                            power.retreats[unit] += [where]

        # List all possible retreats
        destroyed, self.popped = {}, []
        if self.dislodged:
            for power in self.powers.values():
                for unit in [u for u in power.units if u in self.dislodged]:

                    # Removing unit
                    self.update_hash(power.name, unit_type=unit[0], loc=unit[2:])
                    power.units.remove(unit)
                    to_where = power.retreats.get(unit)

                    # Describing what it can do
                    if to_where:
                        pass
                    else:
                        destroyed[unit] = power
                        self.popped += [unit]

        # Now (finally) actually move the units that succeeded in moving
        for power in self.powers.values():
            for unit in power.units[:]:
                if self.command[unit][0] == '-' and not self.result[unit]:
                    offset = 1 if self.command[unit].split()[-1] == 'VIA' else 0

                    # Removing
                    self.update_hash(power.name, unit_type=unit[0], loc=unit[2:])
                    power.units.remove(unit)

                    # Adding
                    new_unit = unit[:2] + self.command[unit].split()[-1 - offset]
                    self.update_hash(power.name, unit_type=new_unit[0], loc=new_unit[2:])
                    power.units += [new_unit]

                    # Setting influence
                    for influence_power in self.powers.values():
                        if new_unit[2:5] in influence_power.influence:
                            influence_power.influence.remove(new_unit[2:5])
                    power.influence.append(new_unit[2:5])

        # If units were destroyed, other units may go out of sight
        if destroyed:
            for unit, power in destroyed.items():
                if unit in power.retreats:
                    self.update_hash(power.name, unit_type=unit[0], loc=unit[2:], is_dislodged=True)
                    del power.retreats[unit]

        # All finished
        self._post_move_update()
        return []

    def _other_results(self):
        """ Resolves moves (Retreat and Adjustment phase) and returns a list of messages explaining what happened

            :return: A list of lines for the results file explaining what happened during the phase
        """
        # pylint: disable=too-many-statements,too-many-branches,too-many-nested-blocks
        self.command = {}
        self.ordered_units = {}
        conflicts = {}
        disbanded_units = set()

        # Adjustments
        if self.phase_type == 'A':
            self.result = {}

            # Emptying the results for the Adjustments Phase
            for power in self.powers.values():
                self.ordered_units.setdefault(power.name, [])
                for order in power.adjust[:]:

                    # Void order - Marking it as such in results
                    if order.split()[0] == 'VOID':
                        word = order.split()[1:]
                        unit = ' '.join(word[:2])
                        self.result.setdefault(unit, []).append(VOID)
                        power.adjust.remove(order)
                        if unit not in self.ordered_units[power.name]:
                            self.ordered_units[power.name] += [unit]

                    # Valid order - Marking as unprocessed
                    else:
                        word = order.split()
                        unit = ' '.join(word[:2])
                        self.result.setdefault(unit, [])
                        if unit not in self.ordered_units[power.name]:
                            self.ordered_units[power.name] += [unit]

            # CIVIL DISORDER
            for power in self.powers.values():
                diff = len(power.units) - len(power.centers)

                # Detecting missing orders
                for order in power.adjust[:]:
                    if diff == 0:
                        word = order.split()
                        unit = ' '.join(word[:2])
                        self.result.setdefault(unit, []).append(VOID)
                        power.adjust.remove(order)

                    # Looking for builds
                    elif diff < 0:
                        word = order.split()
                        unit = ' '.join(word[:2])
                        if word[-1] == 'B':
                            diff += 1
                        else:
                            self.result.setdefault(unit, []).append(VOID)
                            power.adjust.remove(order)

                    # Looking for removes
                    else:
                        word = order.split()
                        unit = ' '.join(word[:2])
                        if word[-1] == 'D':
                            diff -= 1
                            disbanded_units.add(unit)
                        else:
                            self.result.setdefault(unit, []).append(VOID)
                            power.adjust.remove(order)

                if not diff:
                    continue

                power.civil_disorder = 1

                # Need to remove units
                if diff > 0:
                    fleets = PriorityDict()
                    armies = PriorityDict()

                    # Calculating distance to home
                    for unit in power.units:
                        if unit in disbanded_units:
                            continue
                        distance = self._get_distance_to_home(unit[0], unit[2:], power.homes)
                        if unit[0] == 'F':
                            fleets[unit] = -1 * distance
                        else:
                            armies[unit] = -1 * distance

                    # Removing units
                    for unit in range(diff):
                        goner_distance, goner = 99999, None

                        # Removing units with largest distance (using fleets if they are equal)
                        # (using alpha name if multiple units)
                        if fleets:
                            goner_distance, goner = fleets.smallest()
                        if armies and armies.smallest()[0] < goner_distance:
                            goner_distance, goner = armies.smallest()
                        if goner is None:
                            break
                        if goner[0] == 'F':
                            del fleets[goner]
                        else:
                            del armies[goner]
                        power.adjust += ['%s D' % goner]
                        self.result.setdefault(goner, [])

                # Need to build units
                else:
                    sites = self._build_sites(power)
                    need = min(self._build_limit(power, sites), -diff)
                    power.adjust += ['WAIVE'] * need

        # Retreats phase
        elif self.phase_type == 'R':
            self.result = {}

            # Emptying the results for the Retreats Phase
            for power in self.powers.values():
                self.ordered_units.setdefault(power.name, [])
                for retreats in power.retreats:
                    self.result[retreats] = []

            # Emptying void orders - And marking them as such
            for power in self.powers.values():
                for order in power.adjust[:]:
                    if order.split()[0] == 'VOID':
                        word = order.split()[1:]
                        unit = ' '.join(word[:2])
                        self.result[unit] = [VOID]
                        if unit not in self.ordered_units[power.name]:
                            self.ordered_units[power.name] += [unit]
                        power.adjust.remove(order)

            # Disband units with no retreats
            for power in self.powers.values():
                if power.retreats and not power.adjust:
                    power.civil_disorder = 1
                    power.adjust = ['%s D' % r_unit for r_unit in power.retreats]

        # Determine multiple retreats to the same location.
        for power in self.powers.values():
            for order in power.adjust or []:
                word = order.split()
                if len(word) == 4:
                    conflicts.setdefault(word[3][:3], []).append(' '.join(word[:2]))

        # Determine retreat conflict (*bounce, destroyed*)
        # When finished, "self.popped" will be a list of all retreaters who didn't make it.
        for retreaters in conflicts.values():
            if len(retreaters) > 1:
                for retreater in retreaters:
                    if VOID in self.result[retreater]:
                        self.result[retreater].remove(VOID)
                    self.result[retreater] += [BOUNCE, DISBAND]
                self.popped += retreaters

        # Processing Build and Disband
        for power in self.powers.values():
            diff = len(power.units) - len(power.centers)

            # For each order
            for order in power.adjust or []:
                word = order.split()
                unit = ' '.join(word[:2])

                # Build
                if word[-1] == 'B' and len(word) > 2:
                    if diff < 0:
                        self.update_hash(power.name, unit_type=unit[0], loc=unit[2:])
                        power.units += [' '.join(word[:2])]
                        diff += 1
                        self.result[unit] += [OK]
                    else:
                        self.result[unit] += [VOID]
                    if unit not in self.ordered_units[power.name]:
                        self.ordered_units[power.name] += [unit]

                # Disband
                elif word[-1] == 'D' and self.phase_type == 'A':
                    if diff > 0 and ' '.join(word[:2]) in power.units:
                        self.update_hash(power.name, unit_type=unit[0], loc=unit[2:])
                        power.units.remove(' '.join(word[:2]))
                        diff -= 1
                        self.result[unit] += [OK]
                    else:
                        self.result[unit] += [VOID]
                    if unit not in self.ordered_units[power.name]:
                        self.ordered_units[power.name] += [unit]

                # Retreat
                elif len(word) == 4:
                    if unit not in self.popped:
                        self.update_hash(power.name, unit_type=word[0], loc=word[-1])
                        power.units += [word[0] + ' ' + word[-1]]
                        if unit in self.dislodged:
                            del self.dislodged[unit]

                        # Update influence
                        for influence_power in self.powers.values():
                            if word[-1] in influence_power.influence:
                                influence_power.influence.remove(word[-1])
                        power.influence.append(word[-1])

                    if unit not in self.ordered_units[power.name]:
                        self.ordered_units[power.name] += [unit]

            for dis_unit in power.retreats:
                self.update_hash(power.name, unit_type=dis_unit[0], loc=dis_unit[2:], is_dislodged=True)
            power.adjust, power.retreats, power.civil_disorder = [], {}, 0

        # Disbanding
        for unit in [u for u in self.dislodged]:
            self.result.setdefault(unit, [])
            if DISBAND not in self.result[unit]:
                self.result[unit] += [DISBAND]
            del self.dislodged[unit]
            if unit not in self.popped:
                self.popped += [unit]

        return []

    def _resolve(self):
        """ Resolve the current phase

            :return: A list of strings for the results file explaining how the phase was resolved.
        """
        this_phase = self.phase_type

        # This method knows how to process movement, retreat, and adjustment phases.
        # For others, implement resolve_phase()
        if this_phase == 'M':
            self._move_results()
        elif this_phase in 'RA':
            self._other_results()
        self._advance_phase()

    def _clear_history(self):
        """ Clear all game history fields. """
        self.state_history.clear()
        self.order_history.clear()
        self.result_history.clear()
        self.message_history.clear()
        self.clear_orders()
        self.clear_vote()

    def _generate_phase_summary(self, phase_key, summary_callback=None):
        """
        A comprehensive private method to generate a summary for the specified `phase_key`
        (e.g. "S1901M"), including a comparison with the previous phase.

        Steps:
        1) Retrieve the current phase data (GamePhaseData) for `phase_key`.
        2) Retrieve the *previous* phase data if it exists, so we can see what changed.
        3) Gather all relevant info: orders, results, plus state['units'], ['centers'],
            ['retreats'], ['homes'], ['influence'], ['civil_disorder'] for each power.
        4) Build a robust user prompt that includes both current data and any differences from previous.
        5) Call an OpenAI (or other) model using something like `_openai_generate_response(...)`.
        6) Store the resulting text into phase_data.summary and `self.phase_summaries`.
        7) Return the summary text for convenience.
        """

        # 1) Get the GamePhaseData for the current phase key. If none, bail.
        try:
            current_phase_data = self.get_phase_from_history(str(phase_key))
        except (IndexError, KeyError):
            return f"[_generate_phase_summary] No GamePhaseData found for {phase_key}"

        # 2) Attempt to retrieve the PREVIOUS phase data to highlight differences
        #    We'll do this by checking the index of `phase_key` in `self.state_history`.
        #    If there's a previous index, we'll fetch that phase_data for comparison.
        prev_phase_data = None
        all_phases = list(self.state_history.keys())
        if str(phase_key) in all_phases:
            idx = all_phases.index(str(phase_key))
            if idx > 0:
                prev_phase_key = all_phases[idx - 1]
                try:
                    prev_phase_data = self.get_phase_from_history(prev_phase_key)
                except:
                    pass

        # 3) Gather the big data from current_phase_data
        #    (We assume you have stored them in current_phase_data.state the usual way.)
        cur_state = current_phase_data.state
        # Typically these keys exist if your get_state() populates them:
        cur_units   = cur_state.get('units', {})
        cur_centers = cur_state.get('centers', {})
        cur_retreats = cur_state.get('retreats', {})
        cur_homes   = cur_state.get('homes', {})
        cur_influence = cur_state.get('influence', {})
        cur_cd      = cur_state.get('civil_disorder', {})

        cur_orders_dict  = current_phase_data.orders  # {power_name: list_of_orders}
        cur_results_dict = current_phase_data.results # {unit_name: list_of_outcomes}

        # 4) If we have a previous phase, gather the old state's data so we can do some diffs
        prev_units = prev_centers = prev_retreats = prev_homes = prev_influence = prev_cd = {}
        if prev_phase_data:
            prev_state = prev_phase_data.state
            prev_units   = prev_state.get('units', {})
            prev_centers = prev_state.get('centers', {})
            prev_retreats= prev_state.get('retreats', {})
            prev_homes   = prev_state.get('homes', {})
            prev_influence= prev_state.get('influence', {})
            prev_cd      = prev_state.get('civil_disorder', {})

        # 5) Build a user prompt. We can do it in sections:

        # 5a) Orders:
        orders_text = []
        for power, orders in cur_orders_dict.items():
            if orders:
                orders_text.append(f"{power} => {', '.join(orders)}")
            else:
                orders_text.append(f"{power} => [No orders]")
        orders_block = "\n".join(orders_text) if orders_text else "[No orders found]"

        # 5b) Results:
        results_text = []
        for unit_name, outcomes in cur_results_dict.items():
            # old code: results_text.append(f"{unit_name}: {', '.join(outcomes)}")
            outcome_strs = [str(item) for item in outcomes]
            results_text.append(f"{unit_name}: {', '.join(outcome_strs)}")

        results_block = "\n".join(results_text) if results_text else "[No results found]"
        # 5c) Current state (units, centers, etc.) - all powers
        # We'll just do a short textual listing. You can format it more carefully as you see fit.
        def dict_of_lists_to_str(title, dct):
            # Helper to turn e.g. {"FRANCE": ["A MAR", "F BRE"], "ENGLAND": ["A LVP"]} into lines
            lines = []
            for key, val in dct.items():
                lines.append(f"  {key}: {val}")
            return f"{title}:\n" + "\n".join(lines) if lines else f"{title}: [None]"

        current_state_text = []
        current_state_text.append(dict_of_lists_to_str("Units",   cur_units))
        current_state_text.append(dict_of_lists_to_str("Centers", cur_centers))
        current_state_text.append(dict_of_lists_to_str("Retreats",cur_retreats))
        current_state_text.append(dict_of_lists_to_str("Homes",   cur_homes))
        current_state_text.append(dict_of_lists_to_str("Influence", cur_influence))
        current_state_text.append(dict_of_lists_to_str("Civil Disorder", cur_cd))
        current_state_block = "\n\n".join(current_state_text)

        # 5d) Differences from previous (if any)
        # We'll do an extremely simple approach: check if the set of items changed in each dict.
        # This is purely an example. You can do more advanced diff logic if you want.

        differences_info = []
        if prev_phase_data:
            # For each of units, centers, etc. do a quick set compare for each power
            # We'll focus on e.g. newly acquired centers, newly lost centers, etc.
            for power in cur_units.keys():
                # (1) Units difference:
                old_units = set(prev_units.get(power, []))
                new_units = set(cur_units.get(power, []))
                if old_units != new_units:
                    gained = new_units - old_units
                    lost   = old_units - new_units
                    if gained:
                        differences_info.append(f"{power} gained units: {list(gained)}")
                    if lost:
                        differences_info.append(f"{power} lost units:  {list(lost)}")

                # (2) Centers difference:
                old_centers = set(prev_centers.get(power, []))
                new_centers = set(cur_centers.get(power, []))
                if old_centers != new_centers:
                    gained = new_centers - old_centers
                    lost   = old_centers - new_centers
                    if gained:
                        differences_info.append(f"{power} gained centers: {list(gained)}")
                    if lost:
                        differences_info.append(f"{power} lost centers:  {list(lost)}")
            
            # You can do the same for retreats, homes, influence, etc. if you want,
            # or just skip them. We'll skip for brevity here.
        else:
            differences_info.append("No previous phase data found, so no direct diffs to report.")

        differences_block = "\n".join(differences_info) or "[No changes detected from previous phase]"

        # 5e) Put it all together in the final user prompt for the LLM:
        user_prompt = (
            f"PHASE SUMMARY REQUEST.\n\n"
            f"PHASE: {phase_key}\n\n"
            f"ORDERS:\n{orders_block}\n\n"
            f"RESULTS:\n{results_block}\n\n"
            f"CURRENT BOARD STATE:\n{current_state_block}\n\n"
            f"CHANGES FROM PREVIOUS PHASE:\n{differences_block}\n\n"
            "Below is the final board state after the latest phase, along with the moves each power submitted and the engine’s adjudication results. Please create a summary in JSON, explaining:"
            "- Each successful move,"
            "- Each bounce or voided order, with reasons (e.g. equal force, no valid route, contradictory support),"
            "- Key changes in supply centers,"
            "- Potential strategic ramifications if relevant."

            "Return ONLY JSON:"

            "PARSABLE OUTPUT:"
            "{{"
            "'summary': ... your text ..."
            "}}"
        )

        # We might also have a system prompt to guide the AI, e.g.:
        system_prompt = (
            """
                You are a Diplomacy expert, summarizing the results of the latest phase.
                Your tasks:
                1) Provide a concise summary of how the board changed.
                2) Specifically list each voided or bounced order, and *why* it occurred.
                3) If possible, describe which moves or supports succeeded and how that affected centers.

                Format:
                - Must return a JSON with the top-level key "summary" or "orders" or similar.
                - Possibly:

                PARSABLE OUTPUT:
                {
                    "summary": "...(your textual summary)..."
                }

                Ensure the summary clarifies reasons for bounces, e.g., "F TRI -> VEN bounced because Italy also moved A VEN -> TRI with equal force."

                No extra text outside the JSON block.
            """
        )

        if summary_callback:
            summary_text = summary_callback(system_prompt, user_prompt)
        else:
            summary_text = "(No LLM callback provided.)"

        # 7) Store the text in the current GamePhaseData and in self.phase_summaries
        current_phase_data.summary = summary_text
        self.phase_summaries[str(phase_key)] = summary_text

        return summary_text