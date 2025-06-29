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
""" Server -> Client responses sent by server as replies to requests. """
import inspect

from diplomacy.engine.game import Game
from diplomacy.utils import common, parsing, strings
from diplomacy.utils import exceptions
from diplomacy.utils.game_phase_data import GamePhaseData
from diplomacy.utils.network_data import NetworkData
from diplomacy.utils.scheduler_event import SchedulerEvent

class _AbstractResponse(NetworkData):
    """ Base response object """
    __slots__ = ['request_id']
    header = {
        strings.REQUEST_ID: str,
        strings.NAME: str,
    }
    id_field = strings.REQUEST_ID

    def __init__(self, **kwargs):
        self.request_id = None
        super(_AbstractResponse, self).__init__(**kwargs)

class Error(_AbstractResponse):
    """ Error response sent when an error occurred on server-side while handling a request.

        Properties:

        - **error_type**: str - error type, containing the exception class name.
        - **message**: str - error message
    """
    __slots__ = ['message', 'error_type']
    params = {
        strings.MESSAGE: str,
        strings.ERROR_TYPE: str
    }

    def __init__(self, **kwargs):
        self.message = None
        self.error_type = None
        super(Error, self).__init__(**kwargs)

    def throw(self):
        """ Convert this error to an instance of a Diplomacy ResponseException class and raises it. """
        # If error type is the name of a ResponseException class,
        # convert it to related class and raise it.
        if hasattr(exceptions, self.error_type):
            symbol = getattr(exceptions, self.error_type)
            if inspect.isclass(symbol) and issubclass(symbol, exceptions.ResponseException):
                raise symbol(self.message)

        # Otherwise, raise a generic ResponseException object.
        raise exceptions.ResponseException('%s/%s' % (self.error_type, self.message))

class Ok(_AbstractResponse):
    """ Ok response sent by default after handling a request. Contains nothing. """
    __slots__ = []

class NoResponse(_AbstractResponse):
    """ Placeholder response to indicate that no responses are required """
    __slots__ = []

    def __bool__(self):
        """ This response always evaluate to false """
        return False

class DataGameSchedule(_AbstractResponse):
    """ Response with info about current scheduling for a game.

        Properties:

        - **game_id**: str - game ID
        - **phase**: str - game phase
        - **schedule**: :class:`.SchedulerEvent` - scheduling information about the game
    """
    __slots__ = ['game_id', 'phase', 'schedule']
    params = {
        'game_id': str,
        'phase': str,
        'schedule': parsing.JsonableClassType(SchedulerEvent)
    }

    def __init__(self, **kwargs):
        self.game_id = ''
        self.phase = ''
        self.schedule = None  # type: SchedulerEvent
        super(DataGameSchedule, self).__init__(**kwargs)

class DataGameInfo(_AbstractResponse):
    """ Response containing information about a game, to be used when no entire game object is required.

        Properties:

        - **game_id**: game ID
        - **phase**: game phase
        - **timestamp**: latest timestamp when data was saved into game on server
          (ie. game state or message)
        - **timestamp_created**: timestamp when game was created on server
        - **map_name**: (optional) game map name
        - **observer_level**: (optional) highest observer level allowed for the user who sends
          the request. Either ``'observer_type'``, ``'omniscient_type'`` or ``'master_type'``.
        - **controlled_powers**: (optional) list of power names controlled by the user who sends
          the request.
        - **rules**: (optional) game rules
        - **status**: (optional) game status
        - **n_players**: (optional) number of powers currently controlled in the game
        - **n_controls**: (optional) number of controlled powers required by the game to be active
        - **deadline**: (optional) game deadline - time to wait before processing a game phase
        - **registration_password**: (optional) boolean - if True, a password is required to join the game
    """
    __slots__ = ['game_id', 'phase', 'timestamp', 'map_name', 'rules', 'status', 'n_players',
                 'n_controls', 'deadline', 'registration_password', 'observer_level',
                 'controlled_powers', 'timestamp_created']
    params = {
        strings.GAME_ID: str,
        strings.PHASE: str,
        strings.TIMESTAMP: int,
        strings.TIMESTAMP_CREATED: int,
        strings.MAP_NAME: parsing.OptionalValueType(str),
        strings.OBSERVER_LEVEL: parsing.OptionalValueType(parsing.EnumerationType(
            (strings.MASTER_TYPE, strings.OMNISCIENT_TYPE, strings.OBSERVER_TYPE))),
        strings.CONTROLLED_POWERS: parsing.OptionalValueType(parsing.SequenceType(str)),
        strings.RULES: parsing.OptionalValueType(parsing.SequenceType(str)),
        strings.STATUS: parsing.OptionalValueType(parsing.EnumerationType(strings.ALL_GAME_STATUSES)),
        strings.N_PLAYERS: parsing.OptionalValueType(int),
        strings.N_CONTROLS: parsing.OptionalValueType(int),
        strings.DEADLINE: parsing.OptionalValueType(int),
        strings.REGISTRATION_PASSWORD: parsing.OptionalValueType(bool)
    }

    def __init__(self, **kwargs):
        self.game_id = None                     # type: str
        self.phase = None                       # type: str
        self.timestamp = None                   # type: int
        self.timestamp_created = None           # type: int
        self.map_name = None                    # type: str
        self.observer_level = None              # type: str
        self.controlled_powers = None           # type: list
        self.rules = None                       # type: list
        self.status = None                      # type: str
        self.n_players = None                   # type: int
        self.n_controls = None                  # type: int
        self.deadline = None                    # type: int
        self.registration_password = None       # type: bool
        super(DataGameInfo, self).__init__(**kwargs)

class DataPossibleOrders(_AbstractResponse):
    """ Response containing information about possible orders for a game at its current phase.

        Properties:

        - **possible_orders**: dictionary mapping a location short name to all possible orders here
        - **orderable_locations**: dictionary mapping a power name to its orderable locations
    """
    __slots__ = ['possible_orders', 'orderable_locations']
    params = {
        # {location => [orders]}
        strings.POSSIBLE_ORDERS: parsing.DictType(str, parsing.SequenceType(str)),
        # {power name => [locations]}
        strings.ORDERABLE_LOCATIONS: parsing.DictType(str, parsing.SequenceType(str)),
    }

    def __init__(self, **kwargs):
        self.possible_orders = {}
        self.orderable_locations = {}
        super(DataPossibleOrders, self).__init__(**kwargs)

class UniqueData(_AbstractResponse):
    """ Response containing only 1 field named ``data``. A derived class will contain
        a specific typed value in this field.
    """
    # `params` must have exactly one field named DATA.
    __slots__ = ['data']

    @classmethod
    def validate_params(cls):
        assert len(cls.params) == 1 and strings.DATA in cls.params

    def __init__(self, **kwargs):
        self.data = None
        super(UniqueData, self).__init__(**kwargs)

class DataToken(UniqueData):
    """ Unique data containing a token. """
    __slots__ = []
    params = {
        strings.DATA: str
    }

class DataMaps(UniqueData):
    """ Unique data containing maps info
        (dictionary mapping a map name to a dictionary with map information). """
    __slots__ = []
    params = {
        # {map_id => {'powers': [power names], 'supply centers' => [supply centers], 'loc_type' => {loc => type}}}
        strings.DATA: dict
    }

class DataPowerNames(UniqueData):
    """ Unique data containing a list of power names. """
    __slots__ = []
    params = {
        strings.DATA: parsing.SequenceType(str)
    }

class DataGames(UniqueData):
    """ Unique data containing a list of :class:`.DataGameInfo` objects. """
    __slots__ = []
    params = {
        # list of game info.
        strings.DATA: parsing.SequenceType(parsing.JsonableClassType(DataGameInfo))
    }

class DataPort(UniqueData):
    """ Unique data containing a DAIDE port (integer). """
    __slots__ = []
    params = {
        strings.DATA: int   # DAIDE port
    }

class DataTimeStamp(UniqueData):
    """ Unique data containing a timestamp (integer). """
    __slots__ = []
    params = {
        strings.DATA: int  # microseconds
    }

class DataGamePhases(UniqueData):
    """ Unique data containing a list of :class:`.GamePhaseData` objects. """
    __slots__ = []
    params = {
        strings.DATA: parsing.SequenceType(parsing.JsonableClassType(GamePhaseData))
    }

class DataGame(UniqueData):
    """ Unique data containing a :class:`.Game` object. """
    __slots__ = []
    params = {
        strings.DATA: parsing.JsonableClassType(Game)
    }

class DataSavedGame(UniqueData):
    """ Unique data containing a game saved in JSON dictionary. """
    __slots__ = []
    params = {
        strings.DATA: dict
    }

class DataGamesToPowerNames(UniqueData):
    """ Unique data containing a dictionary mapping a game ID to a list of power names. """
    __slots__ = []
    params = {
        strings.DATA: parsing.DictType(str, parsing.SequenceType(str))
    }

def parse_dict(json_response):
    """ Parse a JSON dictionary expected to represent a response.
        Raise an exception if either:

        - parsing failed
        - response received is an Error response. In such case, a ResponseException is raised
          with the error message.

        :param json_response: a JSON dict.
        :return: a Response class instance.
    """
    assert isinstance(json_response, dict), 'Response parser expects a dict.'
    name = json_response.get(strings.NAME, None)
    if name is None:
        raise exceptions.ResponseException()
    expected_class_name = common.snake_case_to_upper_camel_case(name)
    response_class = globals()[expected_class_name]
    assert inspect.isclass(response_class) and issubclass(response_class, _AbstractResponse)
    response_object = response_class.from_dict(json_response)
    if isinstance(response_object, Error):
        response_object.throw()
    return response_object
