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
""" Tornado connection handler class, used internally to manage data received by server application. """
import logging

from urllib.parse import urlparse
from tornado import gen
from tornado.websocket import WebSocketHandler, WebSocketClosedError

import ujson as json

from diplomacy.communication import responses, requests
from diplomacy.server import request_managers
from diplomacy.utils import exceptions, strings
from diplomacy.utils.network_data import NetworkData


LOGGER = logging.getLogger(__name__)

class ConnectionHandler(WebSocketHandler):
    """ ConnectionHandler class. Properties:

        - server: server object representing running server.
    """
    # pylint: disable=abstract-method

    def __init__(self, *args, **kwargs):
        self.server = None
        super(ConnectionHandler, self).__init__(*args, **kwargs)

    def initialize(self, server=None):
        """ Initialize the connection handler.

            :param server: a Server object.
            :type server: diplomacy.Server
        """
        # pylint: disable=arguments-differ
        if self.server is None:
            self.server = server

    def get_compression_options(self):
        """ Return compression options for the connection (see parent method).
            Non-None enables compression with default options.
        """
        return {}

    def check_origin(self, origin):
        """ Return True if we should accept connexion from given origin (str). """

        # It seems origin may be 'null', e.g. if client is a web page loaded from disk (`file:///my_test_file.html`).
        # Accept it.
        if origin == 'null':
            return True

        # Try to check if origin matches host (without regarding port).
        # Adapted from parent method code (tornado 4.5.3).
        parsed_origin = urlparse(origin)
        origin = parsed_origin.netloc.split(':')[0]
        origin = origin.lower()

        # Split host with ':' and keep only first piece to ignore eventual port.
        host = self.request.headers.get("Host").split(':')[0]
        return origin == host

    def on_close(self):
        """ Invoked when the socket is closed (see parent method).
            Detach this connection handler from server users.
        """
        self.server.users.remove_connection(self, remove_tokens=False)
        LOGGER.info("Removed connection. Remaining %d connection(s).", self.server.users.count_connections())

    def write_message(self, message, binary=False):
        """ Sends the given message to the client of this Web Socket. """
        if isinstance(message, NetworkData):
            message = message.json()
        return super(ConnectionHandler, self).write_message(message, binary)

    @staticmethod
    def translate_notification(notification):
        """ Translate a notification to an array of notifications.

            :param notification: a notification object to pass to handler function.
                See diplomacy.communication.notifications for possible notifications.
            :return: An array of notifications containing a single notification.
        """
        return [notification]

    @gen.coroutine
    def on_message(self, message):
        """ Parse given message and manage parsed data (expected a string representation of a request). """
        try:
            json_request = json.loads(message)
            if not isinstance(json_request, dict):
                raise ValueError("Unable to convert a JSON string to a dictionary.")
        except ValueError as exc:
            # Error occurred because either message is not a JSON string
            # or parsed JSON object is not a dict.
            response = responses.Error(error_type=exceptions.ResponseException.__name__,
                                       message=str(exc))
        else:
            try:
                request = requests.parse_dict(json_request)

                if request.level is not None:
                    # Link request token to this connection handler.
                    self.server.users.attach_connection_handler(request.token, self)

                response = yield request_managers.handle_request(self.server, request, self)
                if response is None:
                    response = responses.Ok(request_id=request.request_id)

            except exceptions.ResponseException as exc:
                response = responses.Error(error_type=type(exc).__name__,
                                           message=exc.message,
                                           request_id=json_request.get(strings.REQUEST_ID, None))

        if response:
            try:
                yield self.write_message(response.json())
            except WebSocketClosedError:
                LOGGER.error('Websocket is closed.')
