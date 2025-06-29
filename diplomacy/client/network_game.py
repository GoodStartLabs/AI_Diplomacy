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
""" Game object used on client side. """
import logging

from diplomacy.client.channel import Channel
from diplomacy.communication import notifications
from diplomacy.engine.game import Game
from diplomacy.utils.exceptions import DiplomacyException

LOGGER = logging.getLogger(__name__)

def _game_request_method(channel_method):
    """Create a game request method that calls channel counterpart."""

    def func(self, **kwargs):
        """ Call channel-related method to send a game request with given kwargs. """
        # NB: Channel method returns a future.
        if not self.channel:
            raise DiplomacyException('Invalid client game.')
        return channel_method(self.channel, game=self, **kwargs)

    func.__doc__ = """
    Send game request :class:`.%(request_name)s`%(with_params)s``kwargs``.
    See :class:`.%(request_name)s` about request parameters and response.
    """ % {'request_name': channel_method.__request_name__,
           'with_params': (' with forced parameters ``(%s)`` and additional request parameters '
                           % (channel_method.__request_params__
                              if channel_method.__request_params__
                              else ' with request parameters '))}
    return func

def _callback_setting_method(notification_class):
    """ Create a callback setting method for a given notification class. """

    def func(self, notification_callback):
        """ Add given callback for this game notification class. """
        self.add_notification_callback(notification_class, notification_callback)

    func.__doc__ = """
    Add callback for notification :class:`.%(notification_name)s`. Callback signature:
    ``callback(network_game, notification) -> None``.
    """ % {'notification_name' : notification_class.__name__}

    return func

def _callback_clearing_method(notification_class):
    """ Create a callback clearing method for a given notification class. """

    def func(self):
        """ Clear user callbacks for this game notification class. """
        self.clear_notification_callbacks(notification_class)

    func.__doc__ = """
    Clear callbacks for notification :class:`.%(notification_name)s`..
    """ % {'notification_name': notification_class.__name__}

    return func

class NetworkGame(Game):
    """ NetworkGame class.

        Properties:

        - **channel**: associated :class:`diplomacy.client.channel.Channel` object.
        - **notification_callbacks**: :class:`Dict` mapping a notification class name to a callback to be called
          when a corresponding game notification is received.
    """
    # pylint: disable=protected-access
    __slots__ = ['channel', 'notification_callbacks', 'data', '__weakref__']

    def __init__(self, channel, received_game):
        """ Initialize network game object with a channel and a game object sent by server.

            :param channel: a Channel object.
            :param received_game: a Game object.
            :type channel: diplomacy.client.channel.Channel
            :type received_game: diplomacy.engine.game.Game
        """
        self.channel = channel
        self.notification_callbacks = {}  # {notification_class => [callback(game, notification)]}
        self.data = None
        # Initialize parent class with Jsonable attributes from received game.
        # Received game should contain a valid `initial_state` attribute that will be used
        # to set client game state.
        super(NetworkGame, self).__init__(**{key: getattr(received_game, key) for key in received_game.get_model()})

    # ===========
    # Public API.
    # ===========

    # NB: Method get_all_possible_orders() is only local in Python code,
    # but is still a network call from web interface.
    get_phase_history = _game_request_method(Channel._get_phase_history)
    leave = _game_request_method(Channel._leave_game)
    send_game_message = _game_request_method(Channel._send_game_message)
    set_orders = _game_request_method(Channel._set_orders)

    clear_centers = _game_request_method(Channel._clear_centers)
    clear_orders = _game_request_method(Channel._clear_orders)
    clear_units = _game_request_method(Channel._clear_units)

    wait = _game_request_method(Channel._wait)
    no_wait = _game_request_method(Channel._no_wait)
    vote = _game_request_method(Channel._vote)
    save = _game_request_method(Channel._save)

    def synchronize(self):
        """ Send a :class:`.Synchronize` request to synchronize this game with associated server game. """
        if not self.channel:
            raise DiplomacyException('Invalid client game.')
        return self.channel._synchronize(game=self, timestamp=self.get_latest_timestamp())

    # Admin / Moderator API.
    delete = _game_request_method(Channel._delete_game)
    kick_powers = _game_request_method(Channel._kick_powers)
    set_state = _game_request_method(Channel._set_state)
    process = _game_request_method(Channel._process)
    query_schedule = _game_request_method(Channel._query_schedule)
    start = _game_request_method(Channel._start)
    pause = _game_request_method(Channel._pause)
    resume = _game_request_method(Channel._resume)
    cancel = _game_request_method(Channel._cancel)
    draw = _game_request_method(Channel._draw)

    # ===============================
    # Notification callback settings.
    # ===============================

    add_on_cleared_centers = _callback_setting_method(notifications.ClearedCenters)
    add_on_cleared_orders = _callback_setting_method(notifications.ClearedOrders)
    add_on_cleared_units = _callback_setting_method(notifications.ClearedUnits)
    add_on_game_deleted = _callback_setting_method(notifications.GameDeleted)
    add_on_game_message_received = _callback_setting_method(notifications.GameMessageReceived)
    add_on_game_processed = _callback_setting_method(notifications.GameProcessed)
    add_on_game_phase_update = _callback_setting_method(notifications.GamePhaseUpdate)
    add_on_game_status_update = _callback_setting_method(notifications.GameStatusUpdate)
    add_on_omniscient_updated = _callback_setting_method(notifications.OmniscientUpdated)
    add_on_power_orders_flag = _callback_setting_method(notifications.PowerOrdersFlag)
    add_on_power_orders_update = _callback_setting_method(notifications.PowerOrdersUpdate)
    add_on_power_vote_updated = _callback_setting_method(notifications.PowerVoteUpdated)
    add_on_power_wait_flag = _callback_setting_method(notifications.PowerWaitFlag)
    add_on_powers_controllers = _callback_setting_method(notifications.PowersControllers)
    add_on_vote_count_updated = _callback_setting_method(notifications.VoteCountUpdated)
    add_on_vote_updated = _callback_setting_method(notifications.VoteUpdated)

    clear_on_cleared_centers = _callback_clearing_method(notifications.ClearedCenters)
    clear_on_cleared_orders = _callback_clearing_method(notifications.ClearedOrders)
    clear_on_cleared_units = _callback_clearing_method(notifications.ClearedUnits)
    clear_on_game_deleted = _callback_clearing_method(notifications.GameDeleted)
    clear_on_game_message_received = _callback_clearing_method(notifications.GameMessageReceived)
    clear_on_game_processed = _callback_clearing_method(notifications.GameProcessed)
    clear_on_game_phase_update = _callback_clearing_method(notifications.GamePhaseUpdate)
    clear_on_game_status_update = _callback_clearing_method(notifications.GameStatusUpdate)
    clear_on_omniscient_updated = _callback_clearing_method(notifications.OmniscientUpdated)
    clear_on_power_orders_flag = _callback_clearing_method(notifications.PowerOrdersFlag)
    clear_on_power_orders_update = _callback_clearing_method(notifications.PowerOrdersUpdate)
    clear_on_power_vote_updated = _callback_clearing_method(notifications.PowerVoteUpdated)
    clear_on_power_wait_flag = _callback_clearing_method(notifications.PowerWaitFlag)
    clear_on_powers_controllers = _callback_clearing_method(notifications.PowersControllers)
    clear_on_vote_count_updated = _callback_clearing_method(notifications.VoteCountUpdated)
    clear_on_vote_updated = _callback_clearing_method(notifications.VoteUpdated)

    def add_notification_callback(self, notification_class, notification_callback):
        """ Add a callback for a notification.

            :param notification_class: a notification class.
                See :mod:`diplomacy.communication.notifications` about available notifications.
            :param notification_callback: callback to add:
                ``callback(network_game, notification) -> None``.
        """
        assert callable(notification_callback)
        if notification_class not in self.notification_callbacks:
            self.notification_callbacks[notification_class] = [notification_callback]
        else:
            self.notification_callbacks[notification_class].append(notification_callback)

    def clear_notification_callbacks(self, notification_class):
        """ Remove all user callbacks for a notification.

            :param notification_class: a notification class
        """
        self.notification_callbacks.pop(notification_class, None)

    def notify(self, notification):
        """ Notify game with given notification (call associated callbacks if defined). """
        for callback in self.notification_callbacks.get(type(notification), ()):
            callback(self, notification)
