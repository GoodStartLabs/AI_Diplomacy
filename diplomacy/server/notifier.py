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
""" Server notifier class. Used to send server notifications, allowing to ignore some addresses. """
from tornado import gen

from diplomacy.communication import notifications
from diplomacy.utils import strings

class Notifier:
    """ Server notifier class. """
    __slots__ = ['server', 'ignore_tokens', 'ignore_addresses']

    def __init__(self, server, ignore_tokens=None, ignore_addresses=None):
        """ Initialize a server notifier. You can specify some tokens or addresses to ignore using
            ignore_tokens or ignore_addresses. Note that these parameters are mutually exclusive
            (you can use either none of them or only one of them).

            :param server: a server object.
            :param ignore_tokens: (optional) sequence of tokens to ignore.
            :param ignore_addresses: (optional) sequence of couples (power name, token) to ignore.
            :type server: diplomacy.Server
        """
        self.server = server
        self.ignore_tokens = None
        self.ignore_addresses = None
        if ignore_tokens and ignore_addresses:
            raise AssertionError('Notifier cannot ignore both tokens and addresses.')

        # Expect a sequence of tokens to ignore.
        # Convert it to a set.
        if ignore_tokens:
            self.ignore_tokens = set(ignore_tokens)

        # Expect a sequence of tuples (power name, token) to ignore.
        # Convert it to a dict {power name => {token}}
        # (each power name with all associated ignored tokens).
        elif ignore_addresses:
            self.ignore_addresses = {}
            for power_name, token in ignore_addresses:
                if power_name not in self.ignore_addresses:
                    self.ignore_addresses[power_name] = set()
                self.ignore_addresses[power_name].add(token)

    def ignores(self, notification):
        """ Return True if given notification must be ignored.

            :param notification:
            :return: a boolean
            :type notification: notifications._AbstractNotification | notifications._GameNotification
        """
        if self.ignore_tokens:
            return notification.token in self.ignore_tokens
        if self.ignore_addresses and notification.level == strings.GAME:
            # We can ignore addresses only for game requests
            # (as other requests only have a token, not a full address).
            return (notification.game_role in self.ignore_addresses
                    and notification.token in self.ignore_addresses[notification.game_role])
        return False

    @gen.coroutine
    def _notify(self, notification):
        """ Register a notification to send.

            :param notification: a notification instance.
            :type notification: notifications._AbstractNotification | notifications._GameNotification
        """
        connection_handler = self.server.users.get_connection_handler(notification.token)
        if not self.ignores(notification) and connection_handler:
            translated_notifications = connection_handler.translate_notification(notification)
            if translated_notifications:
                for translated_notification in translated_notifications:
                    yield self.server.notifications.put((connection_handler, translated_notification))

    @gen.coroutine
    def _notify_game(self, server_game, notification_class, **kwargs):
        """ Send a game notification.
            Game token, game ID and game role will be automatically provided to notification object.

            :param server_game: game to notify
            :param notification_class: class of notification to send
            :param kwargs: (optional) other notification parameters
            :type server_game: diplomacy.server.server_game.ServerGame
        """
        for game_role, token in server_game.get_reception_addresses():
            yield self._notify(notification_class(token=token,
                                                  game_id=server_game.game_id,
                                                  game_role=game_role,
                                                  **kwargs))

    @gen.coroutine
    def _notify_power(self, game_id, power, notification_class, **kwargs):
        """ Send a notification to all tokens of a power.
            Automatically add token, game ID and game role to notification parameters.

            :param game_id: power game ID.
            :param power: power to send notification.
            :param notification_class: class of notification to send.
            :param kwargs: (optional) other notification parameters.
            :type power: diplomacy.Power
        """
        for token in power.tokens:
            yield self._notify(notification_class(token=token,
                                                  game_id=game_id,
                                                  game_role=power.name,
                                                  **kwargs))

    @gen.coroutine
    def notify_game_processed(self, server_game, previous_phase_data, current_phase_data):
        """ Notify all game tokens about a game phase update (game processing).

            :param server_game: game to notify
            :param previous_phase_data: game phase data before phase update
            :param current_phase_data: game phase data after phase update
            :type server_game: diplomacy.server.server_game.ServerGame
            :type previous_phase_data: diplomacy.utils.game_phase_data.GamePhaseData
            :type current_phase_data: diplomacy.utils.game_phase_data.GamePhaseData
        """
        # Send game updates to observers ans omniscient observers..
        for game_role, token in server_game.get_observer_addresses():
            yield self._notify(notifications.GameProcessed(
                token=token,
                game_id=server_game.game_id,
                game_role=game_role,
                previous_phase_data=server_game.filter_phase_data(previous_phase_data, strings.OBSERVER_TYPE, False),
                current_phase_data=server_game.filter_phase_data(current_phase_data, strings.OBSERVER_TYPE, True)
            ))
        for game_role, token in server_game.get_omniscient_addresses():
            yield self._notify(notifications.GameProcessed(
                token=token,
                game_id=server_game.game_id,
                game_role=game_role,
                previous_phase_data=server_game.filter_phase_data(previous_phase_data, strings.OMNISCIENT_TYPE, False),
                current_phase_data=server_game.filter_phase_data(current_phase_data, strings.OMNISCIENT_TYPE, True)))
        # Send game updates to powers.
        for power in server_game.powers.values():
            yield self._notify_power(server_game.game_id, power, notifications.GameProcessed,
                                     previous_phase_data=server_game.filter_phase_data(
                                         previous_phase_data, power.name, False),
                                     current_phase_data=server_game.filter_phase_data(
                                         current_phase_data, power.name, True))
        # Also send wait flag for each power.
        for power in server_game.powers.values():
            yield self.notify_power_wait_flag(server_game, power, power.wait)

    @gen.coroutine
    def notify_account_deleted(self, username):
        """ Notify all tokens of given username about account deleted. """
        for token_to_notify in self.server.users.get_tokens(username):
            yield self._notify(notifications.AccountDeleted(token=token_to_notify))

    @gen.coroutine
    def notify_game_deleted(self, server_game):
        """ Notify all game tokens about game deleted.

            :param server_game: game to notify
            :type server_game: diplomacy.server.server_game.ServerGame
        """
        yield self._notify_game(server_game, notifications.GameDeleted)

    @gen.coroutine
    def notify_game_powers_controllers(self, server_game):
        """ Notify all game tokens about current game powers controllers.

            :param server_game: game to notify
            :type server_game: diplomacy.server.server_game.ServerGame
        """
        yield self._notify_game(server_game, notifications.PowersControllers,
                                powers=server_game.get_controllers(),
                                timestamps=server_game.get_controllers_timestamps())

    @gen.coroutine
    def notify_game_status(self, server_game):
        """ Notify all game tokens about current game status.

            :param server_game: game to notify
            :type server_game: diplomacy.server.server_game.ServerGame
        """
        yield self._notify_game(server_game, notifications.GameStatusUpdate, status=server_game.status)

    @gen.coroutine
    def notify_game_phase_data(self, server_game):
        """ Notify all game tokens about current game state.

            :param server_game: game to notify
            :type server_game: diplomacy.server.server_game.ServerGame
        """
        phase_data = server_game.get_phase_data()
        state_type = strings.STATE
        # Notify omniscient tokens.
        yield self.notify_game_addresses(server_game.game_id,
                                         server_game.get_omniscient_addresses(),
                                         notifications.GamePhaseUpdate,
                                         phase_data=server_game.filter_phase_data(
                                             phase_data, strings.OMNISCIENT_TYPE, is_current=True),
                                         phase_data_type=state_type)
        # Notify observer tokens.
        yield self.notify_game_addresses(server_game.game_id,
                                         server_game.get_observer_addresses(),
                                         notifications.GamePhaseUpdate,
                                         phase_data=server_game.filter_phase_data(
                                             phase_data, strings.OBSERVER_TYPE, is_current=True),
                                         phase_data_type=state_type)
        # Notify power addresses.
        for power_name in server_game.get_map_power_names():
            yield self.notify_game_addresses(server_game.game_id,
                                             server_game.get_power_addresses(power_name),
                                             notifications.GamePhaseUpdate,
                                             phase_data=server_game.filter_phase_data(
                                                 phase_data, power_name, is_current=True),
                                             phase_data_type=state_type)

    @gen.coroutine
    def notify_game_vote_updated(self, server_game):
        """ Notify all game tokens about current game vote.
            Send relevant notifications to each type of tokens.

            :param server_game: game to notify
            :type server_game: diplomacy.server.server_game.ServerGame
        """
        # Notify observers about vote count changed.
        for game_role, token in server_game.get_observer_addresses():
            yield self._notify(notifications.VoteCountUpdated(token=token,
                                                              game_id=server_game.game_id,
                                                              game_role=game_role,
                                                              count_voted=server_game.count_voted(),
                                                              count_expected=server_game.count_controlled_powers()))
        # Notify omniscient observers about power vote changed.
        for game_role, token in server_game.get_omniscient_addresses():
            yield self._notify(notifications.VoteUpdated(token=token,
                                                         game_id=server_game.game_id,
                                                         game_role=game_role,
                                                         vote={power.name: power.vote
                                                               for power in server_game.powers.values()}))
        # Notify each power about its own changes.
        for power in server_game.powers.values():
            yield self._notify_power(server_game.game_id, power, notifications.PowerVoteUpdated,
                                     count_voted=server_game.count_voted(),
                                     count_expected=server_game.count_controlled_powers(),
                                     vote=power.vote)

    @gen.coroutine
    def notify_power_orders_update(self, server_game, power, orders):
        """ Notify all power tokens and all observers about new orders for given power.

            :param server_game: game to notify
            :param power: power to notify
            :param orders: new power orders
            :type server_game: diplomacy.server.server_game.ServerGame
            :type power: diplomacy.Power
        """
        yield self._notify_power(server_game.game_id, power, notifications.PowerOrdersUpdate,
                                 power_name=power.name, orders=orders)
        addresses = list(server_game.get_omniscient_addresses()) + list(server_game.get_observer_addresses())
        yield self.notify_game_addresses(server_game.game_id, addresses,
                                         notifications.PowerOrdersUpdate,
                                         power_name=power.name, orders=orders)
        other_powers_addresses = []
        for other_power_name in server_game.powers:
            if other_power_name != power.name:
                other_powers_addresses.extend(server_game.get_power_addresses(other_power_name))
        yield self.notify_game_addresses(server_game.game_id, other_powers_addresses,
                                         notifications.PowerOrdersFlag,
                                         power_name=power.name, order_is_set=power.order_is_set)

    @gen.coroutine
    def notify_power_wait_flag(self, server_game, power, wait_flag):
        """ Notify all power tokens about new wait flag for given power.

            :param server_game: game to notify
            :param power: power to notify
            :param wait_flag: new wait flag
            :type power: diplomacy.Power
        """
        yield self._notify_game(server_game, notifications.PowerWaitFlag, power_name=power.name, wait=wait_flag)

    @gen.coroutine
    def notify_cleared_orders(self, server_game, power_name):
        """ Notify all game tokens about game orders cleared for a given power name.

            :param server_game: game to notify
            :param power_name: name of power for which orders were cleared.
                None means all power orders were cleared.
            :type server_game: diplomacy.server.server_game.ServerGame
        """
        yield self._notify_game(server_game, notifications.ClearedOrders, power_name=power_name)

    @gen.coroutine
    def notify_cleared_units(self, server_game, power_name):
        """ Notify all game tokens about game units cleared for a given power name.

            :param server_game: game to notify
            :param power_name: name of power for which units were cleared.
                None means all power units were cleared.
            :type server_game: diplomacy.server.server_game.ServerGame
        """
        yield self._notify_game(server_game, notifications.ClearedUnits, power_name=power_name)

    @gen.coroutine
    def notify_cleared_centers(self, server_game, power_name):
        """ Notify all game tokens about game centers cleared for a given power name.

            :param server_game: game to notify
            :param power_name: name of power for which centers were cleared.
                None means all power centers were cleared.
            :type server_game: diplomacy.server.server_game.ServerGame
        """
        yield self._notify_game(server_game, notifications.ClearedCenters, power_name=power_name)

    @gen.coroutine
    def notify_game_message(self, server_game, game_message):
        """ Notify relevant users about a game message received.

            :param server_game: Game data who handles this game message.
            :param game_message: the game message received.
            :return: None
            :type server_game: diplomacy.server.server_game.ServerGame
        """
        if game_message.is_global():
            yield self._notify_game(server_game, notifications.GameMessageReceived, message=game_message)
        else:
            power_from = server_game.get_power(game_message.sender)
            power_to = server_game.get_power(game_message.recipient)
            yield self._notify_power(
                server_game.game_id, power_from, notifications.GameMessageReceived, message=game_message)
            yield self._notify_power(
                server_game.game_id, power_to, notifications.GameMessageReceived, message=game_message)
            for game_role, token in server_game.get_omniscient_addresses():
                yield self._notify(notifications.GameMessageReceived(token=token,
                                                                     game_id=server_game.game_id,
                                                                     game_role=game_role,
                                                                     message=game_message))

    @gen.coroutine
    def notify_game_addresses(self, game_id, addresses, notification_class, **kwargs):
        """ Notify addresses of a game with a notification.
            Game ID is automatically provided to notification.
            Token and game role are automatically provided to notifications from given addresses.

            :param game_id: related game ID
            :param addresses: addresses to notify. Sequence of couples (game role, token).
            :param notification_class: class of notification to send
            :param kwargs: (optional) other parameters for notification
        """
        for game_role, token in addresses:
            yield self._notify(notification_class(token=token, game_id=game_id, game_role=game_role, **kwargs))
