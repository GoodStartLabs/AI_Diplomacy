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
""" Test server game in real environment with test data in files `{15, 20, 23}.json`. """
# pylint: disable=unused-argument
import logging
import os
import random
from typing import Dict

from tornado import gen
from tornado.concurrent import Future
from tornado.ioloop import IOLoop

import ujson as json

from diplomacy.client.connection import connect
from diplomacy.server.server import Server
from diplomacy.engine.game import Game
from diplomacy.engine.map import Map
from diplomacy.engine.message import GLOBAL, Message as EngineMessage
from diplomacy.utils import common, constants, strings

LOGGER = logging.getLogger('diplomacy.tests.network.test_real_game')

DEFAULT_HOSTNAME = 'localhost'

DEFAULT_PORT = random.randint(9000, 10000)

class ExpectedPhase:
    """ Helper class to manage data from an expected phase. """
    __slots__ = ['name', 'state', 'orders', 'messages']

    def __init__(self, json_phase):
        """ Initialize expected phase.

            :param json_phase: JSON dict representing a phase. Expected fields: name, state, orders, messages.
        """
        self.name = json_phase['name']
        self.state = json_phase['state']
        self.orders = json_phase['orders']
        self.messages = [EngineMessage(**json_message) for json_message in json_phase['messages']]

        self.messages.sort(key=lambda msg: msg.time_sent)

    def get_power_orders(self, power_name):
        """ Return expected orders for given power name. """
        return self.orders[power_name]

    def get_power_related_messages(self, power_name):
        """ Return expected messages for given power name. """
        return [message for message in self.messages
                if message.sender == power_name or message.recipient in (power_name, GLOBAL)]

class ExpectedMessages:
    """ Expected list of messages sent and received by a power name. """
    __slots__ = ['power_name', 'messages', 'next_messages_to_send']

    def __init__(self, power_name, messages):
        """  Initialize the expected messages.

            :param power_name: power name which exchanges these messages
            :param messages: messages exchanged
        """
        self.power_name = power_name
        self.messages = messages  # type: [EngineMessage]
        self.next_messages_to_send = []

    def has_messages_to_receive(self):
        """ Return True if messages list still contains messages to receive. """
        return any(message.sender != self.power_name for message in self.messages)

    def has_messages_to_send(self):
        """ Return True if messages list still contains messages to send. """
        return any(message.sender == self.power_name for message in self.messages)

    def move_forward(self):
        """ Move next messages to send from messages list to sending queue (self.next_messages_to_send). """
        self.next_messages_to_send.clear()
        if self.messages:
            if self.messages[0].sender != self.power_name:
                # First message in stack is a message to receive. We cannot send any message
                # until all messages to receive at top of stack were indeed received.
                return
            next_message_to_receive = len(self.messages)
            for index, message in enumerate(self.messages):
                if message.sender != self.power_name:
                    next_message_to_receive = index
                    break
            self.next_messages_to_send.extend(self.messages[:next_message_to_receive])
            del self.messages[:next_message_to_receive]

class ExpectedData:
    """ Expected data for a power in a game. """

    __slots__ = ['messages', 'phases', '__phase_index', 'playing']

    def __init__(self, power_name, phases, phase_index):
        """ Initialize expected data for a game power.

            :param power_name: name of power for which those data are expected.
            :param phases: list of expected phases.
            :param phase_index: index of current expected phase in given phases.
            :type power_name: str
            :type phases: list[ExpectedPhase]
            :type phase_index: int
        """
        self.messages = ExpectedMessages(power_name, phases[phase_index].get_power_related_messages(power_name))
        self.phases = phases
        self.__phase_index = phase_index
        self.playing = False

    power_name = property(lambda self: self.messages.power_name)
    phase_index = property(lambda self: self.__phase_index)
    expected_phase = property(lambda self: self.phases[self.__phase_index])

    def move_forward(self):
        """ Move to next expected phase. """
        self.__phase_index += 1
        if self.__phase_index < len(self.phases):
            self.messages = ExpectedMessages(
                self.messages.power_name, self.phases[self.__phase_index].get_power_related_messages(self.power_name))

class CaseData:
    """ Helper class to store test data. """
    FILE_FOLDER_NAME = os.path.abspath(os.path.dirname(__file__))

    def __init__(self, case_file_name, hostname=DEFAULT_HOSTNAME, port=DEFAULT_PORT):
        """ Initialize game test.

            :param case_file_name: File name of JSON file containing expected game data.
                JSON file must be located in folder FILE_FOLDER_NAME.
            :param hostname: hostname to use to load server.
            :param port: port to use to load server.
        """
        full_file_path = os.path.join(self.FILE_FOLDER_NAME, case_file_name)
        with open(full_file_path, 'rb') as file:
            data = json.load(file)
        self.case_name = case_file_name
        self.map_name = data['map']
        self.phases = [ExpectedPhase(json_phase) for json_phase in data['phases']]
        self.rules = set(data['rules'])
        self.rules.add('POWER_CHOICE')
        self.rules.add('REAL_TIME')

        self.test_server = None
        self.io_loop = None  # type: IOLoop
        self.connection = None
        self.admin_channel = None
        self.admin_game = None
        self.user_games = {}
        self.future_games_ended = {}  # type: Dict[str, Future]

        self.hostname = hostname
        self.port = port

    def terminate_game(self, power_name):
        """ Tell Tornado that a power game is finished. """
        self.future_games_ended[power_name].set_result(None)

    @gen.coroutine
    def on_power_phase_update(self, game, notification=None):
        """ User game notification callback for game phase updated.

            :param game: game
            :param notification: notification
            :type game: NetworkGame
            :type notification: diplomacy.communication.notifications.GameProcessed | None
        """
        print('We changed phase for power', game.power.name)
        expected_data = game.data  # type: ExpectedData
        expected_data.move_forward()
        if expected_data.phase_index >= len(expected_data.phases):
            assert expected_data.phase_index == len(expected_data.phases)
            self.terminate_game(game.data.power_name)
            print('Game fully terminated at phase', game.phase)
        else:
            yield verify_current_phase(game)

    @gen.coroutine
    def on_power_state_update(self, game, notification):
        """ User game notification callback for game state update.

            :param game: game
            :param notification: notification
            :type game: NetworkGame
            :type notification: diplomacy.communication.notifications.GamePhaseUpdate
        """
        if notification.phase_data_type == strings.PHASE:
            yield self.on_power_phase_update(game, None)

@gen.coroutine
def send_messages_if_needed(game, expected_messages):
    """ Take messages to send in top of given messages list and send them.

        :param game: a NetworkGame object.
        :param expected_messages: an instance of ExpectedMessages.
        :type game: NetworkGame
        :type expected_messages: ExpectedMessages
    """
    power_name = game.power.name

    if expected_messages.messages:
        expected_messages.move_forward()
        for message in expected_messages.next_messages_to_send:
            if message.recipient == GLOBAL:
                print('%s/sending global message (time %d)' % (power_name, message.time_sent))
                yield game.send_game_message(message=game.new_global_message(message.message))
                print('%s/sent global message (time %d)' % (power_name, message.time_sent))
            else:
                print('%s/sending message to %s (time %d)' % (power_name, message.recipient, message.time_sent))
                yield game.send_game_message(message=game.new_power_message(
                    message.recipient, message.message))
                print('%s/sent message to %s (time %d)' % (power_name, message.recipient, message.time_sent))
        expected_messages.next_messages_to_send.clear()

@gen.coroutine
def send_current_orders(game):
    """ Send expected orders for current phase.

        :param game: a Network game object.
        :type game: NetworkGame
    """
    expected_data = game.data  # type: ExpectedData
    orders_to_send = expected_data.expected_phase.get_power_orders(expected_data.power_name)
    if orders_to_send is None:
        orders_to_send = []

    if not orders_to_send and not game.get_orderable_locations(expected_data.power_name):
        print('%s/no need to send empty orders for unorderable power at phase %s' % (
            expected_data.power_name, expected_data.expected_phase.name))
        return

    print('%s/sending %d orders for phase %s: %s' % (expected_data.power_name, len(orders_to_send),
                                                     expected_data.expected_phase.name, orders_to_send))
    yield game.set_orders(orders=orders_to_send)
    print('%s/sent orders for phase %s' % (expected_data.power_name, expected_data.expected_phase.name))

def on_message_received(game, notification):
    """ User game notification callback for messages received.

        :param game: a NetworkGame object,
        :param notification: a notification received by this game.
        :type game: NetworkGame
        :type notification: diplomacy.communication.notifications.GameMessageReceived
    """
    power_name = game.power.name
    messages = game.data.messages  # type: ExpectedMessages

    if not messages.has_messages_to_receive():
        raise AssertionError('%s/should not receive more messages.' % power_name)

    power_from = notification.message.sender
    index_found = None
    for index, expected_message in enumerate(messages.messages):
        if expected_message.recipient == power_from:
            raise AssertionError(
                '%s/there are still messages to send to %s (%d) before receiving messages from him. Received: %s'
                % (power_name, power_from, expected_message.time_sent, notification.message.message))
        if expected_message.sender == power_from:
            if notification.message.is_global():
                if not (expected_message.recipient == GLOBAL
                        and expected_message.message == notification.message.message):
                    raise AssertionError(
                        '%s/first expected message from %s does not match received global message: %s'
                        % (power_name, power_from, notification.message.message))
            else:
                if not (expected_message.recipient == notification.message.recipient
                        and expected_message.message == notification.message.message):
                    raise AssertionError(
                        '%s/first expected message from %s does not match received power message: to %s: %s'
                        % (power_name, power_from, notification.message.recipient, notification.message.message))
            index_found = index
            break

    if index_found is None:
        raise AssertionError('%s/Received unknown message from %s to %s: %s' % (
            power_name, notification.message.sender, notification.message.recipient, notification.message.message))

    expected_message = messages.messages.pop(index_found)

    print('%s/checked message (time %d)' % (power_name, expected_message.time_sent))

def on_admin_game_phase_update(admin_game, notification=None):
    """ Admin game notification callback for game phase update.

        :param admin_game: admin game
        :param notification: notification
        :type admin_game: NetworkGame
        :type notification: diplomacy.communication.notifications.GameProcessed | None
    """
    assert admin_game.is_omniscient_game()
    expected_data = admin_game.data  # type: ExpectedData
    expected_data.move_forward()
    print('=' * 80)
    print('We changed phase for admin game, moving from phase', expected_data.phase_index,
          'to phase', (expected_data.phase_index + 1), '/', len(expected_data.phases))
    print('=' * 80)

    # state_history must not be empty.
    assert len(admin_game.state_history) == expected_data.phase_index, (
        len(admin_game.state_history), expected_data.phase_index)

    # Verify previous game state.
    if admin_game.state_history:
        expected_state = expected_data.phases[expected_data.phase_index - 1].state
        expected_engine = Game(initial_state=expected_state)
        given_state = admin_game.state_history.last_value()
        given_engine = Game(initial_state=given_state)

        print('Verifying expected previous phase', expected_engine.get_current_phase())
        print('Verifying game processing from previous phase to next phase.')

        other_expected_engine = Game(initial_state=expected_state)
        other_expected_engine.process()
        other_given_engine = Game(initial_state=given_state)
        other_given_engine.rules.append('SOLITAIRE')
        other_given_engine.process()
        assert other_expected_engine.get_current_phase() == other_given_engine.get_current_phase(), (
            'Computed expected next phase %s, got computed given next phase %s'
            % (other_expected_engine.get_current_phase(), other_given_engine.get_current_phase())
        )

        assert expected_engine.map_name == given_engine.map_name
        assert expected_engine.get_current_phase() == given_engine.get_current_phase()

        expected_orders = expected_engine.get_orders()
        given_orders = given_engine.get_orders()
        assert len(expected_orders) == len(given_orders), (expected_orders, given_orders)
        for power_name in given_orders:
            assert power_name in expected_orders, power_name
            given_power_orders = list(sorted(given_orders[power_name]))
            expected_power_orders = list(sorted(expected_orders[power_name]))
            assert expected_power_orders == given_power_orders, (
                'Power orders for %s\nExpected: %s\nGiven: %s\nAll given: %s\n'
                % (power_name, expected_power_orders, given_power_orders, given_orders))

        expected_units = expected_engine.get_units()
        given_units = expected_engine.get_units()
        assert len(expected_units) == len(given_units)
        for power_name in given_units:
            assert power_name in expected_units, (power_name, expected_units, given_units)
            expected_power_units = list(sorted(expected_units[power_name]))
            given_power_units = list(sorted(given_units[power_name]))
            assert expected_power_units == given_power_units, (
                power_name, expected_power_units, given_power_units, given_units)

        expected_centers = expected_engine.get_centers()
        given_centers = given_engine.get_centers()
        assert len(expected_centers) == len(given_centers), (expected_centers, given_centers)
        for power_name in given_centers:
            assert power_name in expected_centers
            expected_power_centers = list(sorted(expected_centers[power_name]))
            given_power_centers = list(sorted(given_centers[power_name]))
            assert expected_power_centers == given_power_centers, (
                power_name, expected_power_centers, given_power_centers)

        assert expected_engine.get_hash() == given_engine.get_hash(), (
            expected_engine.get_hash(), given_engine.get_hash())

    if expected_data.phase_index >= len(expected_data.phases):
        assert expected_data.phase_index == len(expected_data.phases)
        assert admin_game.state_history.last_value()['name'] == expected_data.phases[-1].name, (
            'Wrong last phase, expected %s, got %s'
            % (admin_game.state_history.last_value()['name'], expected_data.phases[-1].name)
        )
        print('Admin game terminated.')

def on_admin_game_state_update(admin_game, notification):
    """ Admin game notification callback for game state update.

        :param admin_game: admin game
        :param notification: notification
        :type admin_game: NetworkGame
        :type notification: diplomacy.communication.notifications.GamePhaseUpdate
    """
    if notification.phase_data_type == strings.PHASE:
        on_admin_game_phase_update(admin_game, None)

def on_admin_powers_controllers(admin_game, notification):
    """  Admin game notification callback for powers controllers received (unexpected).

        :param admin_game: game
        :param notification: notification
        :type admin_game: NetworkGame
        :type notification: diplomacy.communication.notifications.PowersControllers
    """
    LOGGER.warning('%d dummy power(s).',
                   len([controller for controller in notification.powers.values() if controller == strings.DUMMY]))

def on_admin_game_status_update(admin_game, notification):
    """ Admin game notification callback for game status update.

        :param admin_game: admin game
        :param notification: notification
        :type admin_game: NetworkGame
    """
    print('(admin game) game status of %s updated to %s' % (admin_game.role, admin_game.status))

@gen.coroutine
def play_phase(game, expected_messages):
    """ Play a phase for a user game:

        #. Send messages
        #. wait for messages to receive
        #. send current orders.

        :param game: user game
        :param expected_messages: expected messages
        :type game: NetworkGame
        :type expected_messages: ExpectedMessages
    """
    while expected_messages.has_messages_to_send():
        yield gen.sleep(10e-6)
        yield send_messages_if_needed(game, expected_messages)
    while expected_messages.has_messages_to_receive():
        yield gen.sleep(10e-6)
    yield send_current_orders(game)

@gen.coroutine
def on_game_status_update(game, notification):
    """ User game notification callback for game status update.
        Used to start the game locally when game started on server.

        :param game: game
        :param notification: notification
        :type game: NetworkGame
        :type notification: diplomacy.communication.notifications.GameStatusUpdate
    """
    LOGGER.warning('Game status of %s updated to %s', game.role, game.status)
    expected_data = game.data  # type: ExpectedData
    if not expected_data.playing and game.is_game_active:
        # Game started on server.
        expected_data.playing = True
        print('Playing.')
        yield play_phase(game, expected_data.messages)

@gen.coroutine
def verify_current_phase(game):
    """ Check and play current phase.

        :param game: a NetWork game object.
        :type game: NetworkGame
    """
    expected_data = game.data  # type: ExpectedData

    # Verify current phase.
    expected_messages = expected_data.messages
    print('=' * 80)
    print('Checking expected phase', expected_data.expected_phase.name,
          '(%d/%d) for' % (expected_data.phase_index + 1, len(expected_data.phases)), expected_data.power_name,
          'with', len(expected_data.messages.messages), 'messages.')
    print('=' * 80)
    # Verify phase name.
    if game.current_short_phase != str(expected_data.expected_phase.name):
        raise AssertionError(str(expected_data.expected_phase.name), str(game.current_short_phase))

    if game.is_game_active:
        yield play_phase(game, expected_messages)

def get_user_game_fn(case_data, power_name):
    """ Return a coroutine procedure that loads and play a user game for given power name.

        :param case_data: case data
        :param power_name: str
        :return: a procedure.
        :type case_data: CaseData
    """

    @gen.coroutine
    def load_fn():
        """ Coroutine for loading power game for given power name. """
        yield load_power_game(case_data, power_name)

    return load_fn

def get_future_game_done_fn(power_name):
    """ Return a callback to call when a power game is finished.
        Callback currently just prints a message to tell that power game is terminated.

        :param power_name: power name of associated game.
        :return: a callable that receives the future done when game is finished.
    """

    def game_done_fn(future):
        """ Function called when related game is done. """
        print('Game ended (%s).' % power_name)

    return game_done_fn

@gen.coroutine
def load_power_game(case_data, power_name):
    """ Load and play a power game from admin game for given power name.

        :type case_data: CaseData
    """
    print('Loading game for power', power_name)

    username = 'user_%s' % power_name
    password = 'password_%s' % power_name
    user_channel = yield case_data.connection.authenticate(username, password)
    print('User', username, 'connected.')

    user_game = yield user_channel.join_game(game_id=case_data.admin_game.game_id, power_name=power_name)
    assert user_game.is_player_game()
    assert user_game.power.name == power_name

    case_data.user_games[power_name] = user_game
    print('Game created for user %s.' % username, len(user_game.messages), len(user_game.state_history))

    # Set notification callback for user game to manage messages received.
    user_game.add_on_game_status_update(on_game_status_update)
    user_game.add_on_game_message_received(on_message_received)
    user_game.add_on_game_processed(case_data.on_power_phase_update)
    user_game.add_on_game_phase_update(case_data.on_power_state_update)

    # Save expected data into attribute user_game.data.
    user_game.data = ExpectedData(power_name=power_name, phases=case_data.phases, phase_index=0)
    # Start to play and test game.
    yield verify_current_phase(user_game)

@gen.coroutine
def main(case_data):
    """ Test real game environment with one game and all power controlled (no dummy powers).
        This method may be called form a non-test code to run a real game case.

        :param case_data: test data
        :type case_data: CaseData
    """
    # ================
    # Initialize test.
    # ================
    if case_data.admin_channel is None:
        LOGGER.info('Creating connection, admin channel and admin game.')
        case_data.connection = yield connect(case_data.hostname, case_data.port)
        case_data.admin_channel = yield case_data.connection.authenticate('admin', 'password')
        # NB: For all test cases, first game state should be default game engine state when starting.
        # So, we don't need to pass game state of first expected phase when creating a server game.
        case_data.admin_game = yield case_data.admin_channel.create_game(
            map_name=case_data.map_name, rules=case_data.rules, deadline=0)
        assert case_data.admin_game.power_choice
        assert case_data.admin_game.real_time
        case_data.admin_game.data = ExpectedData(power_name='', phases=case_data.phases, phase_index=0)
        case_data.admin_game.add_on_game_status_update(on_admin_game_status_update)
        case_data.admin_game.add_on_game_processed(on_admin_game_phase_update)
        case_data.admin_game.add_on_game_phase_update(on_admin_game_state_update)
        case_data.admin_game.add_on_powers_controllers(on_admin_powers_controllers)

    # ==========
    # Test game.
    # ==========

    # Get available maps to retrieve map power names.
    available_maps = yield case_data.admin_channel.get_available_maps()
    print('Map: %s, powers:' % case_data.map_name,
          ', '.join(power_name for power_name in sorted(available_maps[case_data.map_name])))
    # Load one game per power name.
    for power_name in available_maps[case_data.map_name]['powers']:
        case_data.future_games_ended[power_name] = Future()
        case_data.future_games_ended[power_name].add_done_callback(get_future_game_done_fn(power_name))
        case_data.io_loop.add_callback(get_user_game_fn(case_data, power_name))

    # Wait to let power games play.
    print('Running ...')
    yield case_data.future_games_ended
    print('All game terminated. Just wait a little ...')
    yield gen.sleep(2)
    print('End running.')

def run(case_data, **server_kwargs):
    """ Real test function called for a given case data.
        Load a server (with optional given server kwargs),
        call function main(case_data) as client code
        and wait for main function to terminate.

        :type case_data: CaseData
    """

    print()
    io_loop = IOLoop()
    io_loop.make_current()
    common.Tornado.stop_loop_on_callback_error(io_loop)
    case_data.io_loop = io_loop
    case_data.test_server = Server(**server_kwargs)

    @gen.coroutine
    def coroutine_func():
        """ Concrete call to main function. """
        yield main(case_data)
        case_data.io_loop.stop()
        print('Finished', case_data.case_name, 'at', common.timestamp_microseconds())

    io_loop.add_callback(coroutine_func)
    case_data.test_server.start(case_data.port, io_loop)
    case_data.io_loop.clear_current()
    case_data.io_loop.close()
    case_data.test_server.backend.http_server.stop()

def test_maps():
    """ Building required maps to avoid timeout on the primary test """
    for map_name in ('ancmed', 'colonial', 'empire', 'known_world_901', 'modern', 'standard',
                     'standard_france_austria', 'standard_germany_italy', 'world'):
        Map(map_name)

def test_3():
    """ Test case 3. """
    case_data = CaseData('3.json')
    run(case_data, ping_seconds=constants.DEFAULT_PING_SECONDS)
    # We must clear server caches to allow to re-create a Server with same test case but different server attributes.
    Server.__cache__.clear()

def test_3_ping_1s():
    """ Test case 3 with small ping (1 second). """
    case_data = CaseData('3.json')
    run(case_data, ping_seconds=1)
    # We must clear server caches to allow to re-create a Server with same test case but different server attributes.
    Server.__cache__.clear()
