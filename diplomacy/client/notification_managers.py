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
""" Notification managers (client side). """
# pylint: disable=unused-argument
import logging

from diplomacy.client.network_game import NetworkGame
from diplomacy.communication import notifications
from diplomacy.engine.game import Game
from diplomacy.utils import exceptions, strings

LOGGER = logging.getLogger(__name__)

def _get_game_to_notify(connection, notification):
    """ Get notified game from connection using notification parameters.

        :param connection: connection that receives the notification.
        :param notification: notification received.
        :return: a NetworkGame instance, or None if no game found.
        :type connection: diplomacy.Connection
        :type notification: diplomacy.communication.notifications._GameNotification
    """
    channel = connection.channels.get(notification.token, None)
    if channel and notification.game_id in channel.game_id_to_instances:
        return channel.game_id_to_instances[notification.game_id].get(notification.game_role)
    return None

def on_account_deleted(channel, notification):
    """ Manage notification AccountDeleted.

        :param channel: channel associated to received notification.
        :param notification: received notification.
        :type channel: diplomacy.client.channel.Channel
    """
    # We remove channel from related connection.
    channel.connection.channels.pop(channel.token)

def on_cleared_centers(game, notification):
    """ Manage notification ClearedCenters.

        :param game: a Network game
        :param notification: notification received
        :type game: diplomacy.client.network_game.NetworkGame
        :type notification: diplomacy.communication.notifications.ClearedCenters
    """
    Game.clear_centers(game, notification.power_name)

def on_cleared_orders(game, notification):
    """ Manage notification ClearedOrders.

        :param game: a Network game
        :param notification: notification received
        :type game: diplomacy.client.network_game.NetworkGame
        :type notification: diplomacy.communication.notifications.ClearedOrders
    """
    Game.clear_orders(game, notification.power_name)

def on_cleared_units(game, notification):
    """ Manage notification ClearedUnits.

        :param game: a Network game
        :param notification: notification received
        :type game: diplomacy.client.network_game.NetworkGame
        :type notification: diplomacy.communication.notifications.ClearedUnits
    """
    Game.clear_units(game, notification.power_name)

def on_powers_controllers(game, notification):
    """ Manage notification PowersControllers.

        :param game: a Network game
        :param notification: notification received
        :type game: diplomacy.client.network_game.NetworkGame
        :type notification: diplomacy.communication.notifications.PowersControllers
    """
    if Game.is_player_game(game) and notification.powers[game.power.name] != game.power.get_controller():
        # Player is now invalid. We just remove game from related channel.
        game.channel.game_id_to_instances[game.game_id].remove(game.power.name)
    else:
        # In any other case, update powers controllers.
        Game.update_powers_controllers(game, notification.powers, notification.timestamps)

def on_game_deleted(game, notification):
    """ Manage notification GameDeleted.

        :param game: a Network game
        :param notification: notification received
        :type game: diplomacy.client.network_game.NetworkGame
    """
    # We remove game from related channel.
    if Game.is_player_game(game):
        game.channel.game_id_to_instances[game.game_id].remove(game.power.name)
    else:
        game.channel.game_id_to_instances[game.game_id].remove_special()

def on_game_message_received(game, notification):
    """ Manage notification GameMessageReceived.

        :param game: a Network game
        :param notification: notification received
        :type game: diplomacy.client.network_game.NetworkGame
        :type notification: diplomacy.communication.notifications.GameMessageReceived
    """
    Game.add_message(game, notification.message)

def on_game_processed(game, notification):
    """ Manage notification GamePhaseUpdate (for omniscient and observer games).

        :param game: a Network game
        :param notification: notification received
        :type game: diplomacy.client.network_game.NetworkGame
        :type notification: diplomacy.communication.notifications.GameProcessed
    """
    game.set_phase_data([notification.previous_phase_data, notification.current_phase_data], clear_history=False)

def on_game_phase_update(game, notification):
    """ Manage notification GamePhaseUpdate.

        :param game: a Network game
        :param notification: notification received
        :type game: diplomacy.client.network_game.NetworkGame
        :type notification: diplomacy.communication.notifications.GamePhaseUpdate
    """
    if notification.phase_data_type == strings.STATE_HISTORY:
        Game.extend_phase_history(game, notification.phase_data)
    else:
        game.set_phase_data(notification.phase_data)

def on_game_status_update(game, notification):
    """ Manage notification GameStatusUpdate.

        :param game: a Network game
        :param notification: notification received
        :type game: diplomacy.client.network_game.NetworkGame
        :type notification: diplomacy.communication.notifications.GameStatusUpdate
    """
    Game.set_status(game, notification.status)

def on_omniscient_updated(game, notification):
    """ Manage notification OmniscientUpdated.

        :param game: game associated to received notification.
        :param notification: received notification.
        :type game: diplomacy.client.network_game.NetworkGame
        :type notification: notifications.OmniscientUpdated
    """
    assert not Game.is_player_game(game)
    if Game.is_observer_game(game):
        assert notification.grade_update == strings.PROMOTE
        assert notification.game.is_omniscient_game()
    else:
        assert notification.grade_update == strings.DEMOTE
        assert notification.game.is_observer_game()

    # Save client game channel and invalidate client game.
    channel = game.channel
    game.channel = None
    channel.game_id_to_instances[notification.game_id].remove(game.role)

    # Create a new client game with previous client game channel game sent by server.
    new_game = NetworkGame(channel, notification.game)
    new_game.notification_callbacks.update({key: value.copy() for key, value in game.notification_callbacks.items()})
    new_game.data = game.data
    channel.game_id_to_instances[notification.game_id].add(new_game)

def on_power_orders_update(game, notification):
    """ Manage notification PowerOrdersUpdate.

        :param game: a Network game
        :param notification: notification received
        :type game: diplomacy.client.network_game.NetworkGame
        :type notification: diplomacy.communication.notifications.PowerOrdersUpdate
    """
    Game.set_orders(game, notification.power_name, notification.orders)

def on_power_orders_flag(game, notification):
    """ Manage notification PowerOrdersFlag.

        :param game: a Network game
        :param notification: notification received
        :type game: diplomacy.client.network_game.NetworkGame
        :type notification: diplomacy.communication.notifications.PowerOrdersFlag
    """
    # A power should not receive an order flag notification for itself.
    assert game.is_player_game() and game.power.name != notification.power_name
    game.get_power(notification.power_name).order_is_set = notification.order_is_set

def on_power_vote_updated(game, notification):
    """ Manage notification PowerVoteUpdated (for power game).

        :param game: a Network game
        :param notification: notification received
        :type game: diplomacy.client.network_game.NetworkGame
        :type notification: diplomacy.communication.notifications.PowerVoteUpdated
    """
    assert Game.is_player_game(game)
    game.power.vote = notification.vote

def on_power_wait_flag(game, notification):
    """ Manage notification PowerWaitFlag.

        :param game: a Network game
        :param notification: notification received
        :type game: diplomacy.client.network_game.NetworkGame
        :type notification: diplomacy.communication.notifications.PowerWaitFlag
    """
    Game.set_wait(game, notification.power_name, notification.wait)

def on_vote_count_updated(game, notification):
    """ Manage notification VoteCountUpdated (for observer game).

        :param game: game associated to received notification.
        :param notification: received notification.
        :type game: diplomacy.client.network_game.NetworkGame
    """
    assert Game.is_observer_game(game)

def on_vote_updated(game, notification):
    """ Manage notification VoteUpdated (for omniscient game).

        :param game: a Network game
        :param notification: notification received
        :type game: diplomacy.client.network_game.NetworkGame
        :type notification: diplomacy.communication.notifications.VoteUpdated
    """
    assert Game.is_omniscient_game(game)
    for power_name, vote in notification.vote.items():
        Game.get_power(game, power_name).vote = vote

# Mapping dictionary from notification class to notification handler function.
MAPPING = {
    notifications.AccountDeleted: on_account_deleted,
    notifications.ClearedCenters: on_cleared_centers,
    notifications.ClearedOrders: on_cleared_orders,
    notifications.ClearedUnits: on_cleared_units,
    notifications.GameDeleted: on_game_deleted,
    notifications.GameMessageReceived: on_game_message_received,
    notifications.GameProcessed: on_game_processed,
    notifications.GamePhaseUpdate: on_game_phase_update,
    notifications.GameStatusUpdate: on_game_status_update,
    notifications.OmniscientUpdated: on_omniscient_updated,
    notifications.PowerOrdersFlag: on_power_orders_flag,
    notifications.PowerOrdersUpdate: on_power_orders_update,
    notifications.PowersControllers: on_powers_controllers,
    notifications.PowerVoteUpdated: on_power_vote_updated,
    notifications.PowerWaitFlag: on_power_wait_flag,
    notifications.VoteCountUpdated: on_vote_count_updated,
    notifications.VoteUpdated: on_vote_updated,
}

def handle_notification(connection, notification):
    """ Call appropriate handler for given notification received by given connection.

        :param connection: recipient connection.
        :param notification: received notification.
        :type connection: diplomacy.Connection
        :type notification: notifications._AbstractNotification | notifications._GameNotification
    """
    if notification.level == strings.CHANNEL:
        object_to_notify = connection.channels.get(notification.token, None)
    else:
        object_to_notify = _get_game_to_notify(connection, notification)
    if object_to_notify is None:
        LOGGER.error('Unknown notification: %s', notification.name)
    else:
        handler = MAPPING.get(type(notification), None)
        if not handler:
            raise exceptions.DiplomacyException(
                'No handler available for notification class %s' % type(notification).__name__)
        handler(object_to_notify, notification)
        if notification.level == strings.GAME:
            object_to_notify.notify(notification)
