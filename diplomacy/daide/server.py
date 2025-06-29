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
""" Parallel server to receive DAIDE communications """
import logging
from tornado import gen
from tornado.iostream import StreamClosedError
from tornado.tcpserver import TCPServer
from diplomacy.daide.connection_handler import ConnectionHandler

# Constants
LOGGER = logging.getLogger(__name__)

class Server(TCPServer):
    """ Represents a server to receive DAIDE communications """
    def __init__(self, master_server, game_id):
        """ Constructor

            :param master_server: the internal server
            :param game_id: the game id for which this server will receive communications
        """
        super(Server, self).__init__()
        self._master_server = master_server
        self._game_id = game_id
        self._registered_connections = {}

    @property
    def master_server(self):
        """ Return the master server """
        return self._master_server

    @property
    def game_id(self):
        """ Return the game id associated with the server """
        return self._game_id

    def stop(self):
        """ Stop the server and close all connections """
        for connection_handler in self._registered_connections.values():
            connection_handler.close_connection()
        super(Server, self).stop()

    @gen.coroutine
    def handle_stream(self, stream, address):
        """ Handle an open stream

            :param stream: the stream to handle
            :param address: the address of the client
        """
        LOGGER.info('Connection from client [%s]', str(address))

        handler = ConnectionHandler()
        handler.initialize(stream, self._master_server, self._game_id)
        self._registered_connections[stream] = handler

        try:
            while not handler.stream.closed():
                yield handler.read_stream()
        except StreamClosedError:
            LOGGER.error('[%s] disconnected', str(address))

        del self._registered_connections[stream]
