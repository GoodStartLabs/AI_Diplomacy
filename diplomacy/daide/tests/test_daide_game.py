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
""" Tests for complete DAIDE games """
from collections import namedtuple
import logging
import os
import random
import signal

from tornado import gen
from tornado.concurrent import chain_future, Future
from tornado.ioloop import IOLoop
from tornado.iostream import StreamClosedError
from tornado.tcpclient import TCPClient

from diplomacy import Server
from diplomacy.daide import messages, tokens
from diplomacy.daide.tokens import Token
from diplomacy.daide.utils import str_to_bytes, bytes_to_str
from diplomacy.server.server import is_port_opened
from diplomacy.server.server_game import ServerGame
from diplomacy.client.connection import connect
from diplomacy.utils import common, constants, strings

# Constants
LOGGER = logging.getLogger('diplomacy.daide.tests.test_daide_game')
HOSTNAME = 'localhost'
FILE_FOLDER_NAME = os.path.abspath(os.path.dirname(__file__))
BOT_KEYWORD = '__bot__'

# Named Tuples
DaideComm = namedtuple('DaideComm', ['client_id', 'request', 'resp_notifs'])
ClientRequest = namedtuple('ClientRequest', ['client', 'request'])

# Adapted from: https://stackoverflow.com/questions/492519/timeout-on-a-function-call
def run_with_timeout(callable_fn, timeout):
    """ Raises an error on timeout """
    def handler(signum, frame):
        """ Raises a timeout """
        raise TimeoutError()

    signal.signal(signal.SIGALRM, handler)
    signal.alarm(timeout)
    try:
        return callable_fn()
    except TimeoutError as exc:
        raise exc
    finally:
        signal.alarm(0)

class ClientCommsSimulator:
    """ Represents a client's comms """
    def __init__(self, client_id):
        """ Constructor

            :param client_id: the id
        """
        self._id = client_id
        self._stream = None
        self._is_game_joined = False
        self._comms = False

    @property
    def stream(self):
        """ Returns the stream """
        return self._stream

    @property
    def comms(self):
        """ Returns the comms """
        return self._comms

    @property
    def is_game_joined(self):
        """ Returns if the client has joinded the game """
        return self._is_game_joined

    def set_comms(self, comms):
        """ Set the client's communications.

            The client's comms will be sorted to have the requests of a phase
            preceding the responses / notifications of the phase

            :param comms: the game's communications
        """
        self._comms = [comm for comm in comms if comm.client_id == self._id]

        comm_idx = 0
        while comm_idx < len(self._comms):
            comm = self._comms[comm_idx]

            # Find the request being right after a synchonization point (TME notification)
            if not comm.request:
                comm_idx += 1
                continue

            # Next communication to sort
            next_comm_idx = comm_idx + 1
            while next_comm_idx < len(self._comms):
                next_comm = self._comms[next_comm_idx]

                # Group the request at the beginning of the communications in the phase
                if next_comm.request:
                    comm_idx += 1
                    self._comms.insert(comm_idx, self._comms.pop(next_comm_idx))

                # Synchonization point is a TME notif as it marks the beginning of a phase
                if any(resp_notif.startswith('TME') for resp_notif in next_comm.resp_notifs):
                    break

                next_comm_idx += 1

            comm_idx += 1

    def pop_next_request(self, comms):
        """ Pop the next request from a DAIDE communications list

            :return: The next request along with the updated list of communications
                 or None and the updated list of communications
        """
        com = next(iter(comms), None)
        request = None

        while com and com.client_id == self._id:
            if com.request:
                request = com.request
                comms[0] = DaideComm(com.client_id, '', com.resp_notifs)
                LOGGER.info('[%d:%d] preparing to send request [%s]', self._id, self.stream.socket.fileno()+1, request)
                break
            elif com.resp_notifs:
                break
            else:
                comms.pop(0)
                com = next(iter(comms), None)

        return request, comms

    def pop_next_resp_notif(self, comms):
        """ Pop the next response or notifcation from a DAIDE communications list

            :return: The next response or notifcation along with the updated list of communications
                 or None and the updated list of communications
        """
        com = next(iter(comms), None)
        resp_notif = None

        while com and com.client_id == self._id:
            if com.request:
                break
            elif com.resp_notifs:
                resp_notif = com.resp_notifs.pop(0)
                LOGGER.info('[%d:%d] waiting for resp_notif [%s]', self._id, self.stream.socket.fileno()+1, resp_notif)
                break
            else:
                comms.pop(0)
                com = next(iter(comms), None)

        return resp_notif, comms

    @gen.coroutine
    def connect(self, game_port):
        """ Connect to the DAIDE server

            :param game_port: the DAIDE game's port
        """
        self._stream = yield TCPClient().connect('localhost', game_port)
        LOGGER.info('Connected to %d', game_port)
        message = messages.InitialMessage()
        yield self._stream.write(bytes(message))
        yield messages.DaideMessage.from_stream(self._stream)

    @gen.coroutine
    def send_request(self, request):
        """ Sends a request

            :param request: the request to send
        """
        message = messages.DiplomacyMessage()
        message.content = str_to_bytes(request)
        yield self._stream.write(bytes(message))

    @gen.coroutine
    def validate_resp_notifs(self, expected_resp_notifs):
        """ Validate that expected response / notifications are received regardless of the order

            :param expected_resp_notifs: the response / notifications to receive
        """
        while expected_resp_notifs:
            resp_notif_message = yield messages.DaideMessage.from_stream(self._stream)

            resp_notif = bytes_to_str(resp_notif_message.content)
            if Token(from_bytes=resp_notif_message.content[:2]) == tokens.HLO:
                resp_notif = resp_notif.split(' ')
                resp_notif[5] = expected_resp_notifs[0].split(' ')[5]
                resp_notif = ' '.join(resp_notif)
                self._is_game_joined = True

            LOGGER.info('[%d:%d] Received reply [%s]', self._id, self.stream.socket.fileno() + 1, str(resp_notif))
            LOGGER.info('[%d:%d] Replies in buffer [%s]', self._id, self.stream.socket.fileno() + 1,
                        ','.join(expected_resp_notifs))
            assert resp_notif in expected_resp_notifs
            expected_resp_notifs.remove(resp_notif)

    @gen.coroutine
    def execute_phase(self, game_id, channels):
        """ Execute a single communications phase

            :param game_id: The game id of the current game
            :param channels: A dictionary of power name to its channel (BOT_KEYWORD for dummies)
            :return: True if there are communications left to execute in the game
        """
        # pylint: disable=too-many-nested-blocks
        try:
            while self._comms:
                request, self._comms = self.pop_next_request(self._comms)

                # If request is GOF - Sending empty orders for all human and dummy powers
                if request and request.split()[0] == 'GOF':

                    # Joining all games first
                    games = {}
                    for power_name, channel in channels.items():
                        if power_name == BOT_KEYWORD:
                            all_dummy_power_names = yield channel.get_dummy_waiting_powers(buffer_size=100)
                            for dummy_name in all_dummy_power_names.get(game_id, []):
                                games[dummy_name] = yield channel.join_game(game_id=game_id, power_name=dummy_name)
                        else:
                            games[power_name] = yield channel.join_game(game_id=game_id, power_name=power_name)

                    # Submitting orders
                    for power_name, game in games.items():
                        yield game.set_orders(power_name=power_name, orders=[], wait=False)

                # Sending request
                if request is not None:
                    yield self.send_request(request)

                expected_resp_notifs = []
                expected_resp_notif, self._comms = self.pop_next_resp_notif(self._comms)

                while expected_resp_notif is not None:
                    expected_resp_notifs.append(expected_resp_notif)
                    # Synchonization point is the request being right after a TME notif or
                    # the next set of responses / notifications
                    if expected_resp_notif.startswith('TME'):
                        break
                    expected_resp_notif, self._comms = self.pop_next_resp_notif(self._comms)

                if expected_resp_notifs:
                    future = self.validate_resp_notifs(expected_resp_notifs)
                    @gen.coroutine
                    def validate_resp_notifs():
                        yield future
                    run_with_timeout(validate_resp_notifs, 1)
                    yield future
                    break

        except StreamClosedError as err:
            LOGGER.error('Stream closed: %s', err)
            return False

        return bool(self._comms)

class ClientsCommsSimulator:
    """ Represents multi clients's communications """
    def __init__(self, nb_clients, csv_file, game_id, channels):
        """ Constructor

            :param nb_clients: the number of clients
            :param csv_file: the csv containing the communications in chronological order
            :param game_id: The game id on the server
            :param channels: A dictionary of power name to its channel (BOT_KEYWORD for dummies)
        """
        with open(csv_file, 'r') as file:
            content = file.read()

        content = [line.split(',') for line in content.split('\n') if not line.startswith('#')]

        self._game_port = None
        self._nb_clients = nb_clients
        self._comms = [DaideComm(int(line[0]), line[1], line[2:]) for line in content if line[0]]
        self._clients = {}
        self._game_id = game_id
        self._channels = channels

    @gen.coroutine
    def retrieve_game_port(self, host, port):
        """ Retreive and store the game's port

            :param host: the host
            :param port: the port
            :param game_id: the game id
        """
        connection = yield connect(host, port)
        self._game_port = yield connection.get_daide_port(self._game_id)
        yield connection.connection.close()

    @gen.coroutine
    def execute(self):
        """ Executes the communications between clients """
        try:
            # Synchronize clients joining the game
            while self._comms and (not self._clients
                                   or not all(client.is_game_joined for client in self._clients.values())):
                try:
                    next_comm = next(iter(self._comms))                 # type: DaideComm
                except StopIteration:
                    break

                if next_comm.client_id not in self._clients and len(self._clients) < self._nb_clients:
                    client = ClientCommsSimulator(next_comm.client_id)
                    yield client.connect(self._game_port)
                    self._clients[next_comm.client_id] = client

                for client in self._clients.values():
                    request, self._comms = client.pop_next_request(self._comms)

                    if request is not None:
                        yield client.send_request(request)

                    expected_resp_notif, self._comms = client.pop_next_resp_notif(self._comms)

                    while expected_resp_notif is not None:
                        yield client.validate_resp_notifs([expected_resp_notif])
                        expected_resp_notif, self._comms = client.pop_next_resp_notif(self._comms)

        except StreamClosedError as err:
            LOGGER.error('Stream closed: %s', err)

        execution_running = []

        for client in self._clients.values():
            client.set_comms(self._comms)
            execution_running.append(client.execute_phase(self._game_id, self._channels))

        execution_running = yield execution_running

        while any(execution_running):
            execution_running = yield [client.execute_phase(self._game_id, self._channels)
                                       for client in self._clients.values()]

        assert all(not client.comms for client in self._clients.values())

def run_game_data(nb_daide_clients, rules, csv_file):
    """ Start a server and a client to test DAIDE communications

        :param port: The port of the DAIDE server
        :param csv_file: the csv file containing the list of DAIDE communications
    """
    server = Server()
    io_loop = IOLoop()
    io_loop.make_current()
    common.Tornado.stop_loop_on_callback_error(io_loop)

    @gen.coroutine
    def coroutine_func():
        """ Concrete call to main function. """
        port = random.randint(9000, 9999)

        while is_port_opened(port, HOSTNAME):
            port = random.randint(9000, 9999)

        nb_human_players = 1 if nb_daide_clients < 7 else 0

        server.start(port=port)
        server_game = ServerGame(map_name='standard',
                                 n_controls=nb_daide_clients + nb_human_players,
                                 rules=rules,
                                 server=server)

        # Register game on server.
        game_id = server_game.game_id
        server.add_new_game(server_game)
        server.start_new_daide_server(game_id)

        # Creating human player
        human_username = 'username'
        human_password = 'password'

        # Creating bot player to play for dummy powers
        bot_username = constants.PRIVATE_BOT_USERNAME
        bot_password = constants.PRIVATE_BOT_PASSWORD

        # Connecting
        connection = yield connect(HOSTNAME, port)
        human_channel = yield connection.authenticate(human_username, human_password)
        bot_channel = yield connection.authenticate(bot_username, bot_password)

        # Joining human to game
        channels = {BOT_KEYWORD: bot_channel}
        if nb_human_players:
            yield human_channel.join_game(game_id=game_id, power_name='AUSTRIA')
            channels['AUSTRIA'] = human_channel

        comms_simulator = ClientsCommsSimulator(nb_daide_clients, csv_file, game_id, channels)
        yield comms_simulator.retrieve_game_port(HOSTNAME, port)

        # done_future is only used to prevent pylint E1101 errors on daide_future
        done_future = Future()
        daide_future = comms_simulator.execute()
        chain_future(daide_future, done_future)

        for _ in range(3 + nb_daide_clients):
            if done_future.done() or server_game.count_controlled_powers() >= (nb_daide_clients + nb_human_players):
                break
            yield gen.sleep(2.5)
        else:
            raise TimeoutError()

        # Waiting for process to finish
        while not done_future.done() and server_game.status == strings.ACTIVE:
            yield gen.sleep(2.5)

        yield daide_future

    try:
        io_loop.run_sync(coroutine_func)

    finally:
        server.stop_daide_server(None)
        if server.backend.http_server:
            server.backend.http_server.stop()

        io_loop.stop()
        io_loop.clear_current()
        io_loop.close()

        server = None
        Server.__cache__.clear()

def test_game_reject_map():
    """ Test a game where the client rejects the map """
    _ = Server()            # Initialize cache to prevent timeouts during tests
    game_path = os.path.join(FILE_FOLDER_NAME, 'game_data_1_reject_map.csv')
    run_with_timeout(lambda: run_game_data(1, ['NO_PRESS', 'IGNORE_ERRORS', 'POWER_CHOICE'], game_path), 60)

def test_game_1():
    """ Test a complete 1 player game """
    _ = Server()            # Initialize cache to prevent timeouts during tests
    game_path = os.path.join(FILE_FOLDER_NAME, 'game_data_1.csv')
    run_with_timeout(lambda: run_game_data(1, ['NO_PRESS', 'IGNORE_ERRORS', 'POWER_CHOICE'], game_path), 60)

def test_game_history():
    """ Test a complete 1 player game and validate the full history (except last phase) """
    _ = Server()            # Initialize cache to prevent timeouts during tests
    game_path = os.path.join(FILE_FOLDER_NAME, 'game_data_1_history.csv')
    run_with_timeout(lambda: run_game_data(1, ['NO_PRESS', 'IGNORE_ERRORS', 'POWER_CHOICE'], game_path), 60)

def test_game_7():
    """ Test a complete 7 players game """
    _ = Server()            # Initialize cache to prevent timeouts during tests
    game_path = os.path.join(FILE_FOLDER_NAME, 'game_data_7.csv')
    run_with_timeout(lambda: run_game_data(7, ['NO_PRESS', 'IGNORE_ERRORS', 'POWER_CHOICE'], game_path), 60)

def test_game_7_draw():
    """ Test a complete 7 players game that ends with a draw """
    _ = Server()            # Initialize cache to prevent timeouts during tests
    game_path = os.path.join(FILE_FOLDER_NAME, 'game_data_7_draw.csv')
    run_with_timeout(lambda: run_game_data(7, ['NO_PRESS', 'IGNORE_ERRORS', 'POWER_CHOICE'], game_path), 60)

def test_game_7_press():
    """ Test a complete 7 players game with press """
    _ = Server()            # Initialize cache to prevent timeouts during tests
    game_path = os.path.join(FILE_FOLDER_NAME, 'game_data_7_press.csv')
    run_with_timeout(lambda: run_game_data(7, ['IGNORE_ERRORS', 'POWER_CHOICE'], game_path), 60)
