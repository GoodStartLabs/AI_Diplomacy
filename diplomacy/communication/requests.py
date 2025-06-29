# ==============================================================================
# Copyright (C) 2019 - Philip Paquette, Steven Bocco
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
""" Client -> Server requests.

    This module contains the definition of request (as classes)
    that a client can send to Diplomacy server implemented in this project.

    The client -> server communication follows this procedure:

    - Client sends a request to server.
      All requests have parameters that must be filled by client before being sent.
    - Server replies with a response, which is either an error response or a valid response.
    - Client receives and handles server response.

      - If server response is an error, client converts it to a typed exception and raises it.
      - If server response is a valid response, client return either the response data directly,
        or make further treatments and return a derived data.

    Diplomacy package actually provides 2 clients: the Python client and the web front-end.

    Web front-end provides user-friendly forms to collect required request parameters,
    makes all request calls internally, and then uses them to update graphical user interface.
    So, when using front-end, you don't need to get familiar with underlying protocol, and documentation
    in this module won't be really useful for you.

    Python client consists of three classes (:class:`.Connection`, :class:`.Channel` and
    :class:`.NetworkGame`) which provide appropriate methods to automatically send requests, handle
    server response, and either raise an exception (if server returns an error) or return a client-side
    wrapped data (if server returns a valid response) where requests were called. Thus, these methods
    still need to receive request parameters, and you need to know what kind of data they can return.
    So, if you use Python client, you will need the documentation in this module, which describes, for
    each request:

    - the request parameters (important)
    - the server valid responses (less interesting)
    - the Python client returned values (important)

    All requests classes inherit from :class:`._AbstractRequest` which require parameters
    ``name`` (from parant class :class:`.NetworkData`), ``request_id`` and ``re_sent``.
    These parameters are automatically filled by the client.

    From parent class :class:`._AbstractRequest`, we get 3 types of requests:

    - public requests, which directly inherit from :class:`._AbstractRequest`.
    - channel requests, inherited from :class:`._AbstractChannelRequest`, which requires additional
      parameter ``token``. Token is retrieved by client when he connected to server using
      connection request :class:`.SignIn`, and is then used to create a :class:`.Channel` object.
      Channel object will be responsible for sending all other channel requests, automatically
      filling token field for these requests.
    - game requests, intherited from :class:`._AbstractGameRequest`, which itself inherit from
      :class:`._AbstractChannelRequest`, and requires additional parameters ``game_id``, ``game_role``
      and ``phase`` (game short phase name). Game ID, role and phase are retrieved for a specific game
      by the client when he joined a game through one of featured :class:`.Channel` methods which return
      a :class:`.NetworkGame` object. Network game will then be responsible for sending all other
      game requests, automatically filling game ID, role and phase for these requests.

    Then, all other requests derived directly from either abstract request class, abstract channel
    request class, or abstract game request class, may require additional parameters, and if so, these
    parameters will need to be filled by the user, by passing them to related client methods.

    Check :class:`.Connection` for available public request methods (and associated requests).

    Check :class:`.Channel` for available channel request methods (and associated requests).

    Check :class:`.NetworkGame` for available game request methods (and associated requests).

    Then come here to get parameters and returned values for associated requests.
"""
import inspect
import logging

from diplomacy.engine.message import Message
from diplomacy.utils import common, exceptions, parsing, strings
from diplomacy.utils.network_data import NetworkData
from diplomacy.utils.parsing import OptionalValueType
from diplomacy.utils.sorted_dict import SortedDict

LOGGER = logging.getLogger(__name__)

class _AbstractRequest(NetworkData):
    """ Abstract request class.

        Field **request_id** is auto-filled if not defined.

        Field **name** is auto-filled with snake case version of request class name.

        Field **re_sent** is False by default. It should be set to True if request is re-sent by client
        (currently done by Connection object when reconnecting).

        **Timestamp** field is auto-set with current local timestamp if not defined.
        For game request Synchronize, timestamp should be game latest timestamp instead
        (see method NetworkGame.synchronize()).
    """
    __slots__ = ['request_id', 're_sent']
    header = {
        strings.REQUEST_ID: str,
        strings.NAME: str,
        strings.RE_SENT: parsing.DefaultValueType(bool, False),
    }
    params = {}
    id_field = strings.REQUEST_ID
    level = None

    def __init__(self, **kwargs):
        """ Constructor. """
        self.request_id = None  # type: str
        self.re_sent = None  # type: bool
        super(_AbstractRequest, self).__init__(**kwargs)

    @classmethod
    def validate_params(cls):
        """ Hack: we just use it to validate level. """
        assert cls.level is None or cls.level in strings.ALL_COMM_LEVELS

class _AbstractChannelRequest(_AbstractRequest):
    """ Abstract class representing a channel request.
        Token field is automatically filled by a Channel object before sending request.
    """
    __slots__ = ['token']
    header = parsing.update_model(_AbstractRequest.header, {
        strings.TOKEN: str
    })
    level = strings.CHANNEL

    def __init__(self, **kwargs):
        self.token = None  # type: str
        super(_AbstractChannelRequest, self).__init__(**kwargs)

class _AbstractGameRequest(_AbstractChannelRequest):
    """ Abstract class representing a game request.
        Game ID, game role and phase fields are automatically filled by a NetworkGame object before sending request.
    """
    __slots__ = ['game_id', 'game_role', 'phase']

    header = parsing.extend_model(_AbstractChannelRequest.header, {
        strings.GAME_ID: str,
        strings.GAME_ROLE: str,
        strings.PHASE: str,  # Game short phase.
    })
    level = strings.GAME

    # Game request class flag to indicate if this type of game request depends on game phase.
    # If True, phase indicated in request must match current game phase.
    phase_dependent = True

    def __init__(self, **kwargs):
        self.game_id = None  # type: str
        self.game_role = None  # type: str
        self.phase = None  # type: str
        super(_AbstractGameRequest, self).__init__(**kwargs)

    # Return "address" of request sender inside related game (ie. channel token + game role).
    # Used by certain request managers to skip sender when notify related game.
    # See request managers in diplomacy.server.request_managers.
    address_in_game = property(lambda self: (self.game_role, self.token))

# ====================
# Connection requests.
# ====================

class GetDaidePort(_AbstractRequest):
    """ Public request to get DAIDE port opened for a game.

        :param game_id: ID of game for which yu want to get DAIDE port
        :type game_id: str
        :return:

            - Server: :class:`.DataPort`
            - Client: int - DAIDE port

        :raise diplomacy.utils.exceptions.DaidePortException: if there is no DAIDE port associated to given game ID.
    """
    __slots__ = ['game_id']
    params = {
        strings.GAME_ID: str
    }

    def __init__(self, **kwargs):
        self.game_id = None
        super(GetDaidePort, self).__init__(**kwargs)

class SignIn(_AbstractRequest):
    """ Connection request. Log in or sign in to server.

        :param username: account username
        :param password: account password
        :return:

            - Server: :class:`.DataToken`
            - Client: a :class:`.Channel` object presenting user connected to the server.
              If any sign in error occurs, raise an appropriate :class:`.ResponseException`.

        :type username: str
        :type password: str
    """
    __slots__ = ['username', 'password']
    params = {
        strings.USERNAME: str,
        strings.PASSWORD: str,
    }

    def __init__(self, **kwargs):
        self.username = None
        self.password = None
        super(SignIn, self).__init__(**kwargs)

# =================
# Channel requests.
# =================

class CreateGame(_AbstractChannelRequest):
    """ Channel request to create a game.

        :param game_id: game ID. If not provided, a game ID will be generated.
        :param n_controls: number of controlled powers required to start the game.
            A power becomes controlled when a player joins the game to control this power.
            Game won't start as long it does not have this number of controlled powers.
            Game will stop (to ``forming`` state) if the number of controlled powers decrease under
            this number (e.g. when powers are kicked, eliminated, or when a player controlling a power
            leaves the game). If not provided, set with the number of powers on the map (e.g. ``7``
            on standard map).
        :param deadline: (default ``300``) time (in seconds) for the game to wait before
            processing a phase. ``0`` means no deadline, ie. game won't process a phase until either
            all powers submit orders and turn off wait flag, or a game master forces game to process.
        :param registration_password: password required to join the game.
            If not provided, anyone can join the game.
        :param power_name: power to control once game is created.

            - If provided, the user who send this request will be joined to the game as a player
              controlling this power.
            - If not provided, the user who send this request will be joined to the game as an
              omniscient observer (ie. able to see everything in the game, including user messages).
              Plus, as game creator, user will also be a game master, ie. able to send master requests,
              e.g. to force game processing.

        :param state: game initial state (for expert users).
        :param map_name: (default ``'standard'``) map to play on.
            You can retrieve maps available on server by sending request :class:`GetAvailableMaps`.
        :param rules: list of strings - game rules (for expert users).
        :type game_id: str, optional
        :type n_controls: int, optional
        :type deadline: int, optional
        :type registration_password: str, optional
        :type power_name: str, optional
        :type state: dict, optional
        :type map_name: str, optional
        :type rules: list, optional
        :return:

            - Server: :class:`.DataGame`
            - Client: a :class:`.NetworkGame` object representing a client version of the
              game created and joined. Either a power game (if power name given) or an omniscient game.
    """
    __slots__ = ['game_id', 'power_name', 'state', 'map_name', 'rules', 'n_controls', 'deadline',
                 'registration_password']
    params = {
        strings.GAME_ID: parsing.OptionalValueType(str),
        strings.N_CONTROLS: parsing.OptionalValueType(int),
        strings.DEADLINE: parsing.DefaultValueType(int, 300),  # 300 seconds. Must be >= 0.
        strings.REGISTRATION_PASSWORD: parsing.OptionalValueType(str),
        strings.POWER_NAME: parsing.OptionalValueType(str),
        strings.STATE: parsing.OptionalValueType(dict),
        strings.MAP_NAME: parsing.DefaultValueType(str, 'standard'),
        strings.RULES: parsing.OptionalValueType(parsing.SequenceType(str, sequence_builder=set)),
    }

    def __init__(self, **kwargs):
        self.game_id = ''
        self.n_controls = 0
        self.deadline = 0
        self.registration_password = ''
        self.power_name = ''
        self.state = {}
        self.map_name = ''
        self.rules = set()
        super(CreateGame, self).__init__(**kwargs)

class DeleteAccount(_AbstractChannelRequest):
    """ Channel request to delete an account.

        :param username: name of user to delete account

            - if **not** given, then account to delete will be the one of user sending this request.
            - if **provided**, then user submitting this request must have administrator privileges.

        :type username: str, optional
        :return: None
    """
    __slots__ = ['username']
    params = {
        strings.USERNAME: OptionalValueType(str)
    }

    def __init__(self, **kwargs):
        self.username = None
        super(DeleteAccount, self).__init__(**kwargs)

class GetDummyWaitingPowers(_AbstractChannelRequest):
    """ Channel request to get games with dummy waiting powers.
        A dummy waiting power is a dummy (not controlled) power:

        - not yet eliminated,
        - without orders submitted (for current game phase),
        - but able to submit orders (for current game phase),
        - and who is waiting for orders.

        It's a non-controlled orderable free power, which is then best suited to be controlled
        by an automated player (e.g. a bot, or a learning algorithm).

        :param buffer_size: maximum number of powers to return.
        :type buffer_size: int
        :return:

            - Server: :class:`.DataGamesToPowerNames`
            - Client: a dictionary mapping a game ID to a list of dummy waiting power names,
              such that the total number of power names in the entire dictionary does not exceed
              given buffer size.
    """
    __slots__ = ['buffer_size']
    params = {
        strings.BUFFER_SIZE: int,
    }

    def __init__(self, **kwargs):
        self.buffer_size = 0
        super(GetDummyWaitingPowers, self).__init__(**kwargs)

class GetAvailableMaps(_AbstractChannelRequest):
    """ Channel request to get maps available on server.

        :return:

            - Server: :class:`.DataMaps`
            - Client: a dictionary associating a map name to a dictionary of information related
              to the map. You can especially check key ``'powers'`` to get the list of map power names.
    """
    __slots__ = []

class GetPlayablePowers(_AbstractChannelRequest):
    """ Channel request to get the list of playable powers for a game.
        A playable power is a dummy (uncontrolled) power not yet eliminated.

        :param game_id: ID of game to get playable powers
        :type game_id: str
        :return:

            - Server: :class:`.DataPowerNames`
            - Client: set of playable power names for given game ID.
    """
    __slots__ = ['game_id']
    params = {
        strings.GAME_ID: str
    }

    def __init__(self, **kwargs):
        self.game_id = None
        super(GetPlayablePowers, self).__init__(**kwargs)

class JoinGame(_AbstractChannelRequest):
    """ Channel request to join a game.

        :param game_id: ID of game to join
        :param power_name: if provided, name of power to control. Otherwise,
            user wants to observe game without playing.
        :param registration_password: password to join game. If omitted while
            game requires a password, server will return an error.
        :type game_id: str
        :type power_name: str, optional
        :type registration_password: str, optional
        :return:

            - Server: :class:`.DataGame`
            - Client: a :class:`.NetworkGame` object representing the client game, which is either:

              - a power game (if power name was given), meaning that this network game allows user
                to play a power
              - an observer game, if power was not given and user does not have omniscient privileges
                for this game. Observer role allows user to watch game phases changes, orders submitted
                and orders results for each phase, but he can not see user messages and he can not
                send any request that requires game master privileges.
              - an omniscient game, if power was not given and user does have game master privileges.
                Omniscient role allows user to see everything in the game, including user messages.
                If user does only have omniscient privileges for this game, he can't do anything more,
                If he does have up to game master privileges, then he can also send requests that
                require game master privileges.
    """
    __slots__ = ['game_id', 'power_name', 'registration_password']
    params = {
        strings.GAME_ID: str,
        strings.POWER_NAME: parsing.OptionalValueType(str),
        strings.REGISTRATION_PASSWORD: parsing.OptionalValueType(str)
    }

    def __init__(self, **kwargs):
        self.game_id = None
        self.power_name = None
        self.registration_password = None
        super(JoinGame, self).__init__(**kwargs)

class JoinPowers(_AbstractChannelRequest):
    """ Channel request to join many powers of a game with one request.

        This request is mostly identical to :class:`.JoinGame`, except that list of power names
        is mandatory. It's useful to allow the user to control many powers while still working
        with 1 client game instance.

        :param game_id: ID of game to join
        :param power_names: list of power names to join
        :param registration_password: password to join the game
        :type game_id: str
        :type power_names: list, optional
        :type registration_password: str, optionl
        :return: None. If request succeeds, then the user is registered as player for all
            given power names. The user can then simply join game to one of these powers (by sending
            a :class:`.JoinGame` request), and he will be able to manage all the powers through
            the client game returned by :class:`.JoinGame`.
    """
    __slots__ = ['game_id', 'power_names', 'registration_password']
    params = {
        strings.GAME_ID: str,
        strings.POWER_NAMES: parsing.SequenceType(str, sequence_builder=set),
        strings.REGISTRATION_PASSWORD: parsing.OptionalValueType(str)
    }

    def __init__(self, **kwargs):
        self.game_id = None
        self.power_names = None
        self.registration_password = None
        super(JoinPowers, self).__init__(**kwargs)

class ListGames(_AbstractChannelRequest):
    """ Channel request to find games.

        :param game_id: if provided, look for games with game ID either containing or contained into this game ID.
        :param status: if provided, look for games with this status.
        :param map_name: if provided, look for games with this map name.
        :param include_protected: (default True) tell if we must look into games protected by a password
        :param for_omniscience: (default False) tell if we look for games where request user can be at least omniscient.
        :type game_id: str, optional
        :type status: str, optional
        :type map_name: str, optional
        :type include_protected: bool optional
        :type for_omniscience: bool, optional
        :return:

            - Server: :class:`.DataGames`
            - Client: a list of :class:`.DataGameInfo` objects, each containing
              a bunch of information about a game found. If no game found, list will be empty.
    """
    __slots__ = ['game_id', 'status', 'map_name', 'include_protected', 'for_omniscience']
    params = {
        strings.STATUS: OptionalValueType(parsing.EnumerationType(strings.ALL_GAME_STATUSES)),
        strings.MAP_NAME: OptionalValueType(str),
        strings.INCLUDE_PROTECTED: parsing.DefaultValueType(bool, True),
        strings.FOR_OMNISCIENCE: parsing.DefaultValueType(bool, False),
        strings.GAME_ID: OptionalValueType(str),
    }

    def __init__(self, **kwargs):
        self.game_id = None
        self.status = None
        self.map_name = None
        self.include_protected = None
        self.for_omniscience = None
        super(ListGames, self).__init__(**kwargs)

class GetGamesInfo(_AbstractChannelRequest):
    """ Channel request to get information for a given list of game indices.

        :param games: list of game ID.
        :type games: list
        :return:

            - Server: :class:`.DataGames`
            - Client: a list of :class:`.DataGameInfo` objects.
    """
    __slots__ = ['games']
    params = {
        strings.GAMES: parsing.SequenceType(str)
    }

    def __init__(self, **kwargs):
        self.games = []
        super(GetGamesInfo, self).__init__(**kwargs)

class Logout(_AbstractChannelRequest):
    """ Channel request to logout. Returns nothing. """
    __slots__ = []

class UnknownToken(_AbstractChannelRequest):
    """ Channel request to tell server that a channel token is unknown.

        .. note::

            Client does not even wait for a server response when sending this request,
            which acts more like a "client notification" sent to server.
    """
    __slots__ = []

class SetGrade(_AbstractChannelRequest):
    """ Channel request to modify the grade of a user.
        Require admin privileges to change admin grade, and at least game master privileges
        to change omniscient or moderator grade.

        :param grade: grade to update (``'omniscient'``, ``'admin'`` or ``'moderator'``)
        :param grade_update: how to make update (``'promote'`` or ``'demote'``)
        :param username: user for which the grade must be modified
        :param game_id: ID of game for which the grade must be modified.
            Required only for ``'moderator'`` and ``'omniscient'`` grade.
        :type grade: str
        :type grade_update: str
        :type username: str
        :type game_id: str, optional
        :return: None
    """
    __slots__ = ['grade', 'grade_update', 'username', 'game_id']
    params = {
        strings.GRADE: parsing.EnumerationType(strings.ALL_GRADES),
        strings.GRADE_UPDATE: parsing.EnumerationType(strings.ALL_GRADE_UPDATES),
        strings.USERNAME: str,
        strings.GAME_ID: parsing.OptionalValueType(str),
    }

    def __init__(self, **kwargs):
        self.grade = None
        self.grade_update = None
        self.username = None
        self.game_id = None
        super(SetGrade, self).__init__(**kwargs)

# ==============
# Game requests.
# ==============

class ClearCenters(_AbstractGameRequest):
    """ Game request to clear supply centers. See method :meth:`.Game.clear_centers`.

        :param power_name: if given, clear centers for this power. Otherwise, clear centers for all powers.
        :type power_name: str, optional
        :return: None
    """
    __slots__ = ['power_name']
    params = {
        strings.POWER_NAME: parsing.OptionalValueType(str),
    }

    def __init__(self, **kwargs):
        self.power_name = None  # type: str
        super(ClearCenters, self).__init__(**kwargs)

class ClearOrders(_AbstractGameRequest):
    """ Game request to clear orders.

        :param power_name: if given, clear orders for this power. Otherwise, clear orders for all powers.
        :type power_name: str, optional
        :return: None
    """
    __slots__ = ['power_name']
    params = {
        strings.POWER_NAME: parsing.OptionalValueType(str),
    }

    def __init__(self, **kwargs):
        self.power_name = None  # type: str
        super(ClearOrders, self).__init__(**kwargs)

class ClearUnits(_AbstractGameRequest):
    """ Game request to clear units.

        :param power_name: if given, clear units for this power. Otherwise, clear units for all powers.
        :type power_name: str, optional
        :return: None
    """
    __slots__ = ['power_name']
    params = {
        strings.POWER_NAME: parsing.OptionalValueType(str),
    }

    def __init__(self, **kwargs):
        self.power_name = None  # type: str
        super(ClearUnits, self).__init__(**kwargs)

class DeleteGame(_AbstractGameRequest):
    """ Game request to delete a game. Require game master privileges. Returns nothing. """
    __slots__ = []
    phase_dependent = False

class GetAllPossibleOrders(_AbstractGameRequest):
    """ Game request to get all possible orders.
        Return (server and client) a :class:`.DataPossibleOrders` object
        containing possible orders and orderable locations.
    """
    __slots__ = []

class GetPhaseHistory(_AbstractGameRequest):
    """ Game request to get a list of game phase data from game history for given phases interval.
        A phase can be either None, a phase name (string) or a phase index (integer).
        See :meth:`.Game.get_phase_history` about how phases are used to retrieve game phase data.

        :param from_phase: phase from which to look in game history
        :param to_phase: phase up to which to look in game history
        :type from_phase: str | int, optional
        :type to_phase: str | int, optional
        :return:

            - Server: DataGamePhases
            - Client: a list of :class:`.GamePhaseData` objects corresponding to game phases
              found between ``from_phase`` and ``to_phase`` in game history.
    """
    __slots__ = ['from_phase', 'to_phase']
    params = {
        strings.FROM_PHASE: parsing.OptionalValueType(parsing.SequenceOfPrimitivesType([str, int])),
        strings.TO_PHASE: parsing.OptionalValueType(parsing.SequenceOfPrimitivesType([str, int])),
    }
    phase_dependent = False

    def __init__(self, **kwargs):
        self.from_phase = ''
        self.to_phase = ''
        super(GetPhaseHistory, self).__init__(**kwargs)

class LeaveGame(_AbstractGameRequest):
    """ Game request to leave a game (logout from game). If request power name is set
        (ie. request user was a player), then power will become uncontrolled.
        Otherwise, user will be signed out from its observer (or omniscient) role.
        Returns nothing.
    """
    __slots__ = []

class ProcessGame(_AbstractGameRequest):
    """ Game request to force a game processing. Require master privileges. Return nothing. """
    __slots__ = []

class QuerySchedule(_AbstractGameRequest):
    """ Game request to get info about current scheduling for a game in server.
        Returns (server and client) a :class:`.DataGameSchedule` object.
    """
    __slots__ = []

class SaveGame(_AbstractGameRequest):
    """ Game request to get game exported in JSON format.

        :return:

            - Server: :class:`.DataSavedGame`
            - Client: dict - the JSON dictionary.
    """
    __slots__ = []

class SendGameMessage(_AbstractGameRequest):
    """ Game message to send a user request.

        :param message: message to send. See :class:`.Message` for more info.
            message sender must be request user role (ie. power role, in such case).
            Message time sent must not be defined, it will be allocated by server.
        :type message: Message
        :return:

            - Server: :class:`.DataTimeStamp`
            - Client: nothing (returned timestamp is just used to update message locally)
    """
    __slots__ = ['message']
    params = {
        strings.MESSAGE: parsing.JsonableClassType(Message)
    }

    def __init__(self, **kwargs):
        self.message = None  # type: Message
        super(SendGameMessage, self).__init__(**kwargs)

class SetDummyPowers(_AbstractGameRequest):
    """ Game request to set dummy powers. Require game master privileges.
        If given powers are controlled, related players are kicked
        and powers become dummy (uncontrolled).

        :param power_names: list of power names to set dummy. If not provided, will be all map power names.
        :param username: if provided, only power names controlled by this user will be set dummy.
        :type power_names: list, optional
        :type user_name: str, optional
        :return: None
    """
    __slots__ = ['username', 'power_names']
    params = {
        strings.USERNAME: parsing.OptionalValueType(str),
        strings.POWER_NAMES: parsing.OptionalValueType(parsing.SequenceType(str)),
    }

    def __init__(self, **kwargs):
        self.username = None
        self.power_names = None
        super(SetDummyPowers, self).__init__(**kwargs)

class SetGameState(_AbstractGameRequest):
    """ Game request to set a game state (for exper users). Require game master privileges.

        :param state: game state
        :param orders: dictionary mapping a power name to a list of orders strings
        :param results: dictionary mapping a unit to a list of order result strings
        :param messages: dictionary mapping a timestamp to a message
        :type state: dict
        :type orders: dict
        :type results: dict
        :type messages: dict
        :return: None
    """
    __slots__ = ['state', 'orders', 'results', 'messages']
    params = {
        strings.STATE: dict,
        strings.ORDERS: parsing.DictType(str, parsing.SequenceType(str)),
        strings.RESULTS: parsing.DictType(str, parsing.SequenceType(str)),
        strings.MESSAGES: parsing.DictType(int, parsing.JsonableClassType(Message), SortedDict.builder(int, Message)),
    }

    def __init__(self, **kwargs):
        self.state = {}
        self.orders = {}
        self.results = {}
        self.messages = {}  # type: SortedDict
        super(SetGameState, self).__init__(**kwargs)

class SetGameStatus(_AbstractGameRequest):
    """ Game request to force game status (only if new status differs from previous one).
        Require game master privileges.

        :param status: game status to set.
            Either ``'forming'``, ``'active'``, ``'paused'``, ``'completed'`` or ``'canceled'``.

            - If new status is ``'completed'``, game will be forced to draw.
            - If new status is ``'active'``, game will be forced to start.
            - If new status is ``'paused'``, game will be forced to pause.
            - If new status is ``'canceled'``, game will be canceled and become invalid.
        :type status: str
        :return: None
    """
    __slots__ = ['status']
    params = {
        strings.STATUS: parsing.EnumerationType(strings.ALL_GAME_STATUSES),
    }

    def __init__(self, **kwargs):
        self.status = None
        super(SetGameStatus, self).__init__(**kwargs)

class SetOrders(_AbstractGameRequest):
    """ Game request to set orders for a power.

        :param power_name: power name. If not given, request user must be a game player,
            and power is inferred from request game role.
        :param orders: list of power orders.
        :param wait: if provided, wait flag to set for this power.
        :type power_name: str, optional
        :type orders: list
        :type wait: bool, optional
        :return: None
    """
    __slots__ = ['power_name', 'orders', 'wait']
    params = {
        strings.POWER_NAME: parsing.OptionalValueType(str),  # required only for game master.
        strings.ORDERS: parsing.SequenceType(str),
        strings.WAIT: parsing.OptionalValueType(bool)
    }

    def __init__(self, **kwargs):
        self.power_name = None
        self.orders = None
        self.wait = None
        super(SetOrders, self).__init__(**kwargs)

class SetWaitFlag(_AbstractGameRequest):
    """ Game request to set orders for a power.

        :param power_name: power name. If not given, request user must be a game player,
            and power if inferred from request game role.
        :param wait: wait flag to set.
        :type power_name: str, optional
        :type wait: bool
        :return: None
    """
    __slots__ = ['power_name', 'wait']
    params = {
        strings.POWER_NAME: parsing.OptionalValueType(str),  # required only for game master.
        strings.WAIT: bool
    }

    def __init__(self, **kwargs):
        self.power_name = None
        self.wait = None
        super(SetWaitFlag, self).__init__(**kwargs)

class Synchronize(_AbstractGameRequest):
    """ Game request to force synchronization of client game with server game.
        If necessary, server will send appropriate notifications to client game so that it can
        be up to date with server game state.

        :param timestamp: timestamp since which client game needs to synchronize.
        :type timestamp: int
        :return: (server and client) a :class:`.DataGameInfo` object.
    """
    __slots__ = ['timestamp']
    params = {
        strings.TIMESTAMP: int
    }
    phase_dependent = False

    def __init__(self, **kwargs):
        self.timestamp = None  # type: int
        super(Synchronize, self).__init__(**kwargs)

class Vote(_AbstractGameRequest):
    """ Game request to vote for draw decision.
        If number of pro-draw votes > number of con-draw votes for current phase,
        then server will automatically draw the game and send appropriate notifications.
        Votes are reset after a game processing.

        :param power_name: power name who wants to vote. If not provided, request user must be a game player,
            and power name will be inferred from request game role.
        :param vote: vote to set. Either ``'yes'`` (power votes for draw), ``'no'`` (power votes against draw),
            or ``'neutral'`` (power does not want to decide).
        :type power_name: str, optional
        :type vote: str
        :return: None
    """
    __slots__ = ['power_name', 'vote']
    params = {
        strings.POWER_NAME: parsing.OptionalValueType(str),
        strings.VOTE: strings.ALL_VOTE_DECISIONS
    }

    def __init__(self, **kwargs):
        self.power_name = ''
        self.vote = ''
        super(Vote, self).__init__(**kwargs)

def parse_dict(json_request):
    """ Parse a JSON dictionary expected to represent a request.
        Raise an exception if parsing failed.

        :param json_request: JSON dictionary.
        :return: a request class instance.
        :type json_request: dict
        :rtype: _AbstractRequest | _AbstractChannelRequest | _AbstractGameRequest
    """
    name = json_request.get(strings.NAME, None)
    if name is None:
        raise exceptions.RequestException()
    expected_class_name = common.snake_case_to_upper_camel_case(name)
    request_class = globals().get(expected_class_name, None)
    if request_class is None or not inspect.isclass(request_class) or not issubclass(request_class, _AbstractRequest):
        raise exceptions.RequestException('Unknown request name %s' % expected_class_name)
    try:
        return request_class.from_dict(json_request)
    except exceptions.DiplomacyException as exc:
        LOGGER.error('%s/%s', type(exc).__name__, exc.message)
        raise exceptions.RequestException('Wrong request format')
