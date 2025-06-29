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
"""Server -> Client notifications."""
import inspect

from diplomacy.engine.game import Game
from diplomacy.engine.message import Message
from diplomacy.utils import common, exceptions, parsing, strings
from diplomacy.utils.network_data import NetworkData
from diplomacy.utils.constants import OrderSettings
from diplomacy.utils.game_phase_data import GamePhaseData

class _AbstractNotification(NetworkData):
    """ Base notification object """
    __slots__ = ['notification_id', 'token']
    header = {
        strings.NOTIFICATION_ID: str,
        strings.NAME: str,
        strings.TOKEN: str,
    }
    params = {}
    id_field = strings.NOTIFICATION_ID
    level = None

    def __init__(self, **kwargs):
        self.notification_id = None  # type: str
        self.token = None  # type: str
        super(_AbstractNotification, self).__init__(**kwargs)

    @classmethod
    def validate_params(cls):
        """ Hack: we just use it to validate level. """
        assert cls.level in strings.ALL_COMM_LEVELS

class _ChannelNotification(_AbstractNotification):
    """ Channel notification (intended to be sent to a channel). """
    __slots__ = []
    level = strings.CHANNEL

class _GameNotification(_AbstractNotification):
    """ Game notification (intended to be sent to a game). """
    __slots__ = ['game_id', 'game_role', 'power_name']
    header = parsing.update_model(_AbstractNotification.header, {
        strings.GAME_ID: str,
        strings.GAME_ROLE: str,
        strings.POWER_NAME: parsing.OptionalValueType(str),
    })

    level = strings.GAME

    def __init__(self, **kwargs):
        self.game_id = None  # type: str
        self.game_role = None  # type: str
        self.power_name = None  # type: str
        super(_GameNotification, self).__init__(**kwargs)

class AccountDeleted(_ChannelNotification):
    """ Notification about an account deleted. """
    __slots__ = []

class OmniscientUpdated(_GameNotification):
    """ Notification about a grade updated. Sent at channel level.

        Properties:

            - **grade_update**: :class:`str` One of 'promote' or 'demote'.
            - **game**: :class:`parsing.JsonableClassType(Game)` a :class:`diplomacy.engine.game.Game` object.
    """
    __slots__ = ['grade_update', 'game']
    params = {
        strings.GRADE_UPDATE: parsing.EnumerationType(strings.ALL_GRADE_UPDATES),
        strings.GAME: parsing.JsonableClassType(Game)
    }

    def __init__(self, **kwargs):
        self.grade_update = ''
        self.game = None  # type: Game
        super(OmniscientUpdated, self).__init__(**kwargs)

class ClearedCenters(_GameNotification):
    """ Notification about centers cleared. """
    __slots__ = []

class ClearedOrders(_GameNotification):
    """ Notification about orders cleared. """
    __slots__ = []

class ClearedUnits(_GameNotification):
    """ Notification about units cleared. """
    __slots__ = []

class VoteCountUpdated(_GameNotification):
    """ Notification about new count of draw votes for a game (for observers).

        Properties:

            - **count_voted**: :class:`int` number of powers that have voted.
            - **count_expected**: :class:`int` number of powers to be expected to vote.
    """
    __slots__ = ['count_voted', 'count_expected']
    params = {
        strings.COUNT_VOTED: int,
        strings.COUNT_EXPECTED: int,
    }

    def __init__(self, **kwargs):
        self.count_voted = None  # type: int
        self.count_expected = None  # type: int
        super(VoteCountUpdated, self).__init__(**kwargs)

class VoteUpdated(_GameNotification):
    """ Notification about votes updated for a game (for omniscient observers).

        Properties:

            - **vote**: :class:`Dict` mapping a power name to a Vote (:class:`str`) object representing power vote.
              Possible votes are: yes, no, neutral.
    """
    __slots__ = ['vote']
    params = {
        strings.VOTE: parsing.DictType(str, parsing.EnumerationType(strings.ALL_VOTE_DECISIONS))
    }

    def __init__(self, **kwargs):
        self.vote = None  # type: dict{str, str}
        super(VoteUpdated, self).__init__(**kwargs)

class PowerVoteUpdated(VoteCountUpdated):
    """ Notification about a new vote for a specific game power (for player games).

        Properties:

            - **vote**: :class:`str` vote object representing associated power vote. Can be yes, no, neutral.
    """
    __slots__ = ['vote']
    params = parsing.extend_model(VoteCountUpdated.params, {
        strings.VOTE: parsing.EnumerationType(strings.ALL_VOTE_DECISIONS)
    })

    def __init__(self, **kwargs):
        self.vote = None  # type: str
        super(PowerVoteUpdated, self).__init__(**kwargs)

class PowersControllers(_GameNotification):
    """ Notification about current controller for each power in a game.

        Properties:

            - **powers**: A :class:`Dict` that maps a power_name to a controller_name :class:`str`.
            - **timestamps**: A :class:`Dict` that maps a power_name to timestamp where the controller took over.
    """
    __slots__ = ['powers', 'timestamps']
    params = {
        # {power_name => controller_name}
        strings.POWERS: parsing.DictType(str, parsing.OptionalValueType(str)),
        # {power_name => controller timestamp}
        strings.TIMESTAMPS: parsing.DictType(str, int)
    }

    def __init__(self, **kwargs):
        self.powers = {}
        self.timestamps = {}
        super(PowersControllers, self).__init__(**kwargs)

class GameDeleted(_GameNotification):
    """ Notification about a game deleted. """
    __slots__ = []

class GameProcessed(_GameNotification):
    """ Notification about a game phase update. Sent after game has processed a phase.

        Properties:

            - **previous_phase_data**: :class:`diplomacy.utils.game_phase_data.GamePhaseData` of the previous phase
            - **current_phase_data**: :class:`diplomacy.utils.game_phase_data.GamePhaseData` of the current phase
    """
    __slots__ = ['previous_phase_data', 'current_phase_data']
    params = {
        strings.PREVIOUS_PHASE_DATA: parsing.JsonableClassType(GamePhaseData),
        strings.CURRENT_PHASE_DATA: parsing.JsonableClassType(GamePhaseData),
    }

    def __init__(self, **kwargs):
        self.previous_phase_data = None  # type: GamePhaseData
        self.current_phase_data = None  # type: GamePhaseData
        super(GameProcessed, self).__init__(**kwargs)

class GamePhaseUpdate(_GameNotification):
    """ Notification about a game phase update.

        Properties:

            - **phase_data**: :class:`diplomacy.utils.game_phase_data.GamePhaseData` of the updated phase
            - **phase_data_type**: :class:`str`. One of 'state_history', 'state', 'phase'
    """
    __slots__ = ['phase_data', 'phase_data_type']
    params = {
        strings.PHASE_DATA: parsing.JsonableClassType(GamePhaseData),
        strings.PHASE_DATA_TYPE: strings.ALL_STATE_TYPES
    }

    def __init__(self, **kwargs):
        self.phase_data = None  # type: GamePhaseData
        self.phase_data_type = None  # type: str
        super(GamePhaseUpdate, self).__init__(**kwargs)

class GameStatusUpdate(_GameNotification):
    """ Notification about a game status update.

        Properties:

            -**status**: :class:`str`. One of 'forming', 'active', 'paused', 'completed', 'canceled'
    """
    __slots__ = ['status']
    params = {
        strings.STATUS: parsing.EnumerationType(strings.ALL_GAME_STATUSES),
    }

    def __init__(self, **kwargs):
        self.status = None
        super(GameStatusUpdate, self).__init__(**kwargs)

class GameMessageReceived(_GameNotification):
    """ Notification about a game message received.

        Properties:

            - **message**: :class:`diplomacy.engine.message.Message` received.
    """
    __slots__ = ['message']
    params = {
        strings.MESSAGE: parsing.JsonableClassType(Message),
    }

    def __init__(self, **kwargs):
        self.message = None  # type: Message
        super(GameMessageReceived, self).__init__(**kwargs)

class PowerOrdersUpdate(_GameNotification):
    """ Notification about a power order update.

        Properties:

            - **orders**: List of updated orders (i.e. :class:`str`)
    """
    __slots__ = ['orders']
    params = {
        strings.ORDERS: parsing.OptionalValueType(parsing.SequenceType(str)),
    }

    def __init__(self, **kwargs):
        self.orders = None  # type: set
        super(PowerOrdersUpdate, self).__init__(**kwargs)

class PowerOrdersFlag(_GameNotification):
    """ Notification about a power order flag update.

        Properties:

            - **order_is_set**: :class:`int`. O = ORDER_NOT_SET, 1 = ORDER_SET_EMPTY, 2 = ORDER_SET.
    """
    __slots__ = ['order_is_set']
    params = {
        strings.ORDER_IS_SET: parsing.EnumerationType(OrderSettings.ALL_SETTINGS),
    }

    def __init__(self, **kwargs):
        self.order_is_set = 0
        super(PowerOrdersFlag, self).__init__(**kwargs)

class PowerWaitFlag(_GameNotification):
    """ Notification about a power wait flag update.

        Properties:

            - **wait**: :class:`bool` that indicates to wait until the deadline is reached before proceeding. Otherwise
              if all powers are not waiting, the game is processed as soon as all non-eliminated powers have submitted
              their orders.
    """
    __slots__ = ['wait']
    params = {
        strings.WAIT: bool,
    }

    def __init__(self, **kwargs):
        self.wait = None  # type: bool
        super(PowerWaitFlag, self).__init__(**kwargs)

def parse_dict(json_notification):
    """ Parse a JSON expected to represent a notification. Raise an exception if parsing failed.

        :param json_notification: JSON dictionary.
        :return: a notification class instance.
    """
    assert isinstance(json_notification, dict), 'Notification parser expects a dict.'
    name = json_notification.get(strings.NAME, None)
    if name is None:
        raise exceptions.NotificationException()
    expected_class_name = common.snake_case_to_upper_camel_case(name)
    notification_class = globals()[expected_class_name]
    assert inspect.isclass(notification_class) and issubclass(notification_class, _AbstractNotification)
    return notification_class.from_dict(json_notification)
