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
""" Connection object, handling an internal websocket tornado connection. """
import logging
import weakref
from datetime import timedelta
from typing import Dict
from tornado import gen, ioloop
from tornado.concurrent import Future
from tornado.iostream import StreamClosedError
from tornado.locks import Event
from tornado.websocket import websocket_connect, WebSocketClosedError

import ujson as json

from diplomacy.client import notification_managers
from diplomacy.client.response_managers import RequestFutureContext, handle_response
from diplomacy.communication import notifications, requests, responses
from diplomacy.utils import exceptions, strings, constants

LOGGER = logging.getLogger(__name__)

@gen.coroutine
def connect(hostname, port):
    """ Connect to given hostname and port.

        :param hostname: a hostname
        :param port: a port
        :return: a Connection object connected.
        :type hostname: str
        :type port: int
        :rtype: Connection
    """
    connection = Connection(hostname, port)
    yield connection._connect('Trying to connect.')                 # pylint: disable=protected-access
    return connection

class Connection:
    """ Connection class.

        The connection class should not be initiated directly, but through the connect method

        .. code-block:: python

            >>> from diplomacy.client.connection import connect
            >>> connection = await connect(hostname, port)

        Properties:

        - **hostname**: :class:`str` hostname to connect (e.g. 'localhost')
        - **port**: :class:`int` port to connect (e.g. 8888)
        - **use_ssl**: :class:`bool` telling if connection should be securized (True) or not (False).
        - **url**: (property) :class:`str` websocket url to connect (generated with hostname and port)
        - **connection**: :class:`tornado.websocket.WebSocketClientConnection` a tornado websocket connection object
        - **connection_count**: :class:`int` number of successful connections from this Connection object.
          Used to check if message callbacks is already launched (if count > 0).
        - **is_connecting**: :class:`tornado.locks.Event` a tornado Event used to keep connection status.
          No request can be sent while is_connecting.
          If connected, Synchronize requests can be sent immediately even if is_reconnecting.
          Other requests must wait full reconnection.
        - **is_reconnecting**: :class:`tornado.locks.Event` a tornado Event used to keep re-connection status.
          Non-synchronize request cannot be sent while is_reconnecting.
          If reconnected, all requests can be sent.
        - **channels**: a :class:`weakref.WeakValueDictionary` mapping channel token to :class:`.Channel` object.
        - **requests_to_send**: a :class:`Dict` mapping a request ID to the context of a request
          **not sent**. If we are disconnected when trying to send a request, then request
          context is added to this dictionary to be send later once reconnected.
        - **requests_waiting_responses**: a :class:`Dict` mapping a request ID to the context of a
          request **sent**. Contains requests that are waiting for a server response.
        - **unknown_tokens**: :class:`set` a set of unknown tokens. We can safely ignore them, as the server has been
          notified.
    """
    __slots__ = ['hostname', 'port', 'use_ssl', 'connection', 'is_connecting', 'is_reconnecting', 'connection_count',
                 'channels', 'requests_to_send', 'requests_waiting_responses', 'unknown_tokens']

    def __init__(self, hostname, port, use_ssl=False):
        """ Constructor

            The connection class should not be initiated directly, but through the connect method

            .. code-block:: python

                >>> from diplomacy.client.connection import connect
                >>> connection = await connect(hostname, port)

            :param hostname: hostname to connect (e.g. 'localhost')
            :param port: port to connect (e.g. 8888)
            :param use_ssl: telling if connection should be securized (True) or not (False).
            :type hostname: str
            :type port: int
            :type use_ssl: bool
        """
        self.hostname = hostname
        self.port = port
        self.use_ssl = bool(use_ssl)

        self.connection = None
        self.connection_count = 0
        self.is_connecting = Event()
        self.is_reconnecting = Event()

        self.channels = weakref.WeakValueDictionary()  # {token => Channel}

        self.requests_to_send = {}                      # type: Dict[str, RequestFutureContext]
        self.requests_waiting_responses = {}            # type: Dict[str, RequestFutureContext]
        self.unknown_tokens = set()

        # When connection is created, we are not yet connected, but reconnection does not matter
        # (we consider we are reconnected).
        self.is_reconnecting.set()

    url = property(lambda self: '%s://%s:%d' % ('wss' if self.use_ssl else 'ws', self.hostname, self.port))

    # ===================
    # Public Methods.
    # ===================

    @gen.coroutine
    def authenticate(self, username, password):
        """ Send a :class:`.SignIn` request.
            User will be created on the server automatically if it doesn't exist.

            :param username: username
            :param password: password
            :return: a :class:`.Channel` object representing the authentication.
            :type username: str
            :type password: str
            :rtype: diplomacy.client.channel.Channel
        """
        request = requests.SignIn(username=username, password=password)
        return (yield self.send(request))

    @gen.coroutine
    def get_daide_port(self, game_id):
        """ Send a :class:`.GetDaidePort` request.

            :param game_id: game id for which to retrieve the DAIDE port.
            :return: the game DAIDE port
            :type game_id: str
            :rtype: int
        """
        request = requests.GetDaidePort(game_id=game_id)
        return (yield self.send(request))

    # ===================
    # Private Methods
    # ===================

    @gen.coroutine
    def _connect(self, message=None):
        """ Create (force) a tornado websocket connection. Try NB_CONNECTION_ATTEMPTS attempts,
            waiting for ATTEMPT_DELAY_SECONDS seconds between 2 attempts.
            Raise an exception if it cannot connect.

            :param message: if provided, print this message as a logger info before starting to connect.
            :type message: str, optional
        """
        if message:
            LOGGER.info(message)

        # We are connecting.
        self.is_connecting.clear()

        # Create a connection (currently using websockets).
        self.connection = None
        for attempt_index in range(constants.NB_CONNECTION_ATTEMPTS):
            try:
                future_connection = websocket_connect(self.url)
                self.connection = yield gen.with_timeout(
                    timedelta(seconds=constants.ATTEMPT_DELAY_SECONDS), future_connection)
                break
            except (gen.TimeoutError, ConnectionAbortedError, ConnectionError,
                    ConnectionRefusedError, ConnectionResetError) as ex:
                if attempt_index + 1 == constants.NB_CONNECTION_ATTEMPTS:
                    raise ex
                LOGGER.warning('Connection failing (attempt %d), retrying.', attempt_index + 1)
                yield gen.sleep(constants.ATTEMPT_DELAY_SECONDS)

        if not self.connection_count:
            # Start receiving messages as soon as we are connected.
            ioloop.IOLoop.current().add_callback(self._handle_socket_messages)

        # We are connected.
        self.connection_count += 1
        self.is_connecting.set()

        LOGGER.info('Connection succeeds.')

    @gen.coroutine
    def _reconnect(self):
        """ Reconnect. """
        # We are reconnecting.
        self.is_reconnecting.clear()
        yield self._connect('Trying to reconnect.')
        # We will be reconnected when method Reconnection.sync_done() will finish.
        _Reconnection(self).reconnect()

    @gen.coroutine
    def _on_socket_message(self, socket_message):
        """ Manage given socket_message (string),
            that may be a string representation of either a request or a notification.
        """

        # Check response format and run callback (if defined).
        try:
            json_message = json.loads(socket_message)
        except ValueError:
            LOGGER.exception('Unable to parse JSON from a socket message.')
            return

        if not isinstance(json_message, dict):
            LOGGER.error("Unable to convert a JSON string to a dictionary.")
            return
        request_id = json_message.get(strings.REQUEST_ID, None)
        notification_id = json_message.get(strings.NOTIFICATION_ID, None)

        if request_id:
            if request_id not in self.requests_waiting_responses:
                # Response received before the request was marked as 'waiting responses'
                # Waiting 5 secs to make sure this is not a race condition before aborting
                for _ in range(10):
                    yield gen.sleep(0.5)
                    if request_id in self.requests_waiting_responses:
                        break
                else:
                    LOGGER.error('Unknown request.')
                    return
            request_context = self.requests_waiting_responses.pop(request_id)  # type: RequestFutureContext
            try:
                response = responses.parse_dict(json_message)
                managed_data = handle_response(request_context, response)
                request_context.future.set_result(managed_data)
            except exceptions.ResponseException as ex:
                LOGGER.error('Error received for request %s: %s', request_context.request.name, ex)
                LOGGER.debug('Full request was: %s', request_context.request.to_dict())
                request_context.future.set_exception(ex)

        elif notification_id:
            notification = notifications.parse_dict(json_message)
            if notification.token not in self.channels:
                if notification.token not in self.unknown_tokens:
                    LOGGER.error('Unknown notification: %s', notification.name)
                    self._handle_unknown_token(notification.token)
                return
            notification_managers.handle_notification(self, notification)
        else:
            LOGGER.error('Unknown socket message.')

    @gen.coroutine
    def _handle_socket_messages(self):
        """ Main looping method used to received connection messages. """
        while True:
            msg = yield self.connection.read_message()
            if msg is None:
                # Reconnect.
                LOGGER.error('Disconnected.')
                yield self._reconnect()
            else:
                # Check response format and run callback (if defined).
                yield self._on_socket_message(msg)

    def _handle_unknown_token(self, token):
        """ Notify server about an unknown channel token.
            This is likely because the channel has gone out of scope.
            :param token: token to notify server with.
        """
        # Send notification request without waiting any server response. Ignore errors if any.
        try:
            self.unknown_tokens.add(token)
            self.connection.write_message(requests.UnknownToken(token=token).json())
        except (WebSocketClosedError, StreamClosedError):
            pass

    def _register_to_send(self, request_context):
        """ Register given request context as a request to send as soon as possible.

            :param request_context: context of request to send.
            :type request_context: RequestFutureContext
        """
        self.requests_to_send[request_context.request_id] = request_context

    def send(self, request, for_game=None):
        """ Send a request.

            :param request: request object.
            :param for_game: (optional) NetworkGame object (required for game requests).
            :return: a Future that returns the response handler result of this request.
            :type request: diplomacy.communication.requests._AbstractRequest
            :type for_game: diplomacy.client.network_game.NetworkGame, optional
            :rtype: Future
        """
        request_future = Future()
        request_context = RequestFutureContext(request=request, future=request_future, connection=self, game=for_game)

        self.write_request(request_context).add_done_callback(_MessageWrittenCallback(request_context).callback)
        return gen.with_timeout(timedelta(seconds=constants.REQUEST_TIMEOUT_SECONDS), request_future)

    def write_request(self, request_context):
        """ Write a request into internal connection object.

            :param request_context: context of request to send.
            :type request_context: RequestFutureContext
        """
        future = Future()
        request = request_context.request

        def on_message_written(write_future):
            """ 3) Writing returned, set future as done (with writing result)
                or with writing exception.
            """
            exception = write_future.exception()
            if exception is not None:
                future.set_exception(exception)
            else:
                future.set_result(write_future.result())

        def on_connected(reconnected_future):
            """ 2) Send request. """
            exception = reconnected_future.exception()
            if exception is not None:
                LOGGER.error('Fatal (re)connection error occurred while sending a request.')
                future.set_exception(exception)
            else:
                try:
                    if self.connection is None:
                        raise WebSocketClosedError()
                    write_future = self.connection.write_message(request.json())
                except (WebSocketClosedError, StreamClosedError) as exc:
                    # We were disconnected.
                    # Save request context as a request to send.
                    # We will re-try to send it later once reconnected.
                    self._register_to_send(request_context)
                    # Transfer exception to returned future.
                    future.set_exception(exc)
                else:
                    write_future.add_done_callback(on_message_written)

        # 1)    Synchronize requests just wait for connection.
        #       Other requests wait for reconnection (which also implies connection).
        if isinstance(request, requests.Synchronize):
            self.is_connecting.wait().add_done_callback(on_connected)
        else:
            self.is_reconnecting.wait().add_done_callback(on_connected)

        return future

class _Reconnection:
    """ Class performing reconnection work for a given connection.

        Class properties:

        - connection: Connection object to reconnect.
        - games_phases: dictionary mapping each game address (game ID + game role) to server game info:
          {game ID => {game role => responses.DataGamePhase}}.
          Server game info is a DataGamePhase response sent by server as response to a Synchronize request.
          It contains 3 fields: game ID, current server game phase and current server game timestamp.
          We currently use only game phase.
        - n_expected_games: number of games registered in games_phases.
        - n_synchronized_games: number of games already synchronized.

        Reconnection procedure:

        - Mark all waiting responses as `re-sent` (may be useful on server-side) and
          move them back to responses_to_send.
        - Remove all previous synchronization requests that are not yet sent. We will send new synchronization
          requests with latest games timestamps. Future associated to removed requests will raise an exception.
        - Initialize games_phases associating None to each game object currently opened in connection.
        - Send synchronization request for each game object currently opened in connection. For each game:

          - server will send a response describing current server game phase (current phase and timestamp). This info
            will be used to check local requests to send. Note that concrete synchronization is done via notifications.
            Thus, when server responses is received, game synchronization may not be yet terminated, but at least
            we will now current server game phase.
          - Server response is saved in games_phases (replacing None associated to game object).
          - n_synchronized_games is incremented.

        - When sync responses are received for all games registered in games_phases
          (n_expected_games == n_synchronized_games), we can finalize reconnection:

          - Remove every phase-dependent game request not yet sent for which phase does not match
            server game phase. Futures associated to removed request will raise an exception.
          - Finally send all remaining requests.

        These requests may be marked as re-sent.
        For these requests, server is (currently) responsible for checking if they don't represent
        a duplicated query.
    """

    __slots__ = ['connection', 'games_phases', 'n_expected_games', 'n_synchronized_games']

    def __init__(self, connection):
        """ Initialize reconnection data/

            :param connection: connection to reconnect.
            :type connection: Connection
        """
        self.connection = connection
        self.games_phases = {}
        self.n_expected_games = 0
        self.n_synchronized_games = 0

    def reconnect(self):
        """ Perform concrete reconnection work. """

        # Mark all waiting responses as `re-sent` and move them back to responses_to_send.
        for waiting_context in self.connection.requests_waiting_responses.values():  # type: RequestFutureContext
            waiting_context.request.re_sent = True
        self.connection.requests_to_send.update(self.connection.requests_waiting_responses)
        self.connection.requests_waiting_responses.clear()

        # Remove all previous synchronization requests.
        requests_to_send_updated = {}
        for context in self.connection.requests_to_send.values():  # type: RequestFutureContext
            if isinstance(context.request, requests.Synchronize):
                context.future.set_exception(exceptions.DiplomacyException(
                    'Sync request invalidated for game ID %s.' % context.request.game_id))
            else:
                requests_to_send_updated[context.request.request_id] = context
        self.connection.requests_to_send = requests_to_send_updated

        # Count games to synchronize.
        for channel in self.connection.channels.values():
            for game_instance_set in channel.game_id_to_instances.values():
                for game in game_instance_set.get_games():
                    self.games_phases.setdefault(game.game_id, {})[game.role] = None
                    self.n_expected_games += 1

        if self.n_expected_games:
            # Synchronize games.
            for channel in self.connection.channels.values():
                for game_instance_set in channel.game_id_to_instances.values():
                    for game in game_instance_set.get_games():
                        game.synchronize().add_done_callback(self.generate_sync_callback(game))
        else:
            # No game to sync, finish sync now.
            self.sync_done()

    def generate_sync_callback(self, game):
        """ Generate callback to call when response to sync request is received for given game.

        :param game: game
        :return: a callback.
        :type game: diplomacy.client.network_game.NetworkGame
        """

        def on_sync(future):
            """ Callback. If exception occurs, print it as logging error. Else, register server response,
                and move forward to final reconnection work if all games received sync responses.
            """
            exception = future.exception()
            if exception is not None:
                LOGGER.error(str(exception))
            else:
                self.games_phases[game.game_id][game.role] = future.result()
                self.n_synchronized_games += 1
                if self.n_synchronized_games == self.n_expected_games:
                    self.sync_done()

        return on_sync

    def sync_done(self):
        """ Final reconnection work. Remove obsolete game requests and send remaining requests. """

        # All sync requests sent have finished.
        # Remove all obsolete game requests from connection.
        # A game request is obsolete if it's phase-dependent and if its phase does not match current game phase.

        request_to_send_updated = {}
        for context in self.connection.requests_to_send.values():  # type: RequestFutureContext
            keep = True
            if context.request.level == strings.GAME and context.request.phase_dependent:
                request_phase = context.request.phase
                server_phase = self.games_phases[context.request.game_id][context.request.game_role].phase
                if request_phase != server_phase:
                    # Request is obsolete.
                    context.future.set_exception(exceptions.DiplomacyException(
                        'Game %s: request %s: request phase %s does not match current server game phase %s.'
                        % (context.request.game_id, context.request.name, request_phase, server_phase)))
                    keep = False
            if keep:
                request_to_send_updated[context.request.request_id] = context

        LOGGER.debug('Keep %d/%d old requests to send.',
                     len(request_to_send_updated), len(self.connection.requests_to_send))

        # All requests to send are stored in request_to_send_updated.
        # Then we can empty connection.requests_to_send.
        # If we fail to send a request, it will be re-added again.
        self.connection.requests_to_send.clear()

        # Send requests.
        for request_to_send in request_to_send_updated.values():  # type: RequestFutureContext
            self.connection.write_request(request_to_send).add_done_callback(
                _MessageWrittenCallback(request_to_send).callback)

        # We are reconnected.
        self.connection.is_reconnecting.set()

        LOGGER.info('Done reconnection work.')

class _MessageWrittenCallback:
    """ Helper class representing callback to call on a connection
        when a request is written in a websocket.
    """
    __slots__ = ['request_context']

    def __init__(self, request_context):
        """ Initialize the callback object.

            :param request_context: a request context
            :type request_context: RequestFutureContext
        """
        self.request_context = request_context

    def callback(self, msg_future):
        """ Called when request is effectively written on socket, and move the request
            from `request to send` to `request assumed sent`.
        """
        # Remove request context from `requests to send` in any case.
        connection = self.request_context.connection  # type: Connection
        request_id = self.request_context.request_id
        exception = msg_future.exception()
        if exception is not None:
            if isinstance(exception, (WebSocketClosedError, StreamClosedError)):
                # Connection suddenly closed.
                # Request context was stored in connection.requests_to_send
                # and will be re-sent when reconnection succeeds.
                # For more details, see method Connection.write_request().
                LOGGER.error('Connection was closed when sending a request. Silently waiting for a reconnection.')
            else:
                LOGGER.error('Fatal error occurred while writing a request.')
                self.request_context.future.set_exception(exception)
        else:
            connection.requests_waiting_responses[request_id] = self.request_context
