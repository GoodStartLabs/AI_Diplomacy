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
""" Contains the base API class """
from abc import ABCMeta, abstractmethod
import logging
from tornado import gen
from tornado.httpclient import AsyncHTTPClient

# Constants
LOGGER = logging.getLogger(__name__)

class BaseAPI(metaclass=ABCMeta):
    """ Base API class """

    def __init__(self, api_key, connect_timeout=30, request_timeout=60):
        """ Constructor

            :param api_key: The API key to use for sending API requests
            :param connect_timeout: The maximum amount of time to wait for the connection to be established
            :param request_timeout: The maximum amount of time to wait for the request to be processed
            :type api_key: str
            :type connect_timeout: int, optional
            :type request_timeout: int, optional
        """
        self.api_key = api_key
        self.http_client = AsyncHTTPClient()
        self.connect_timeout = connect_timeout
        self.request_timeout = request_timeout

    @gen.coroutine
    @abstractmethod
    def get_game_and_power(self, *args, **kwargs):
        """ Returns the game and the power we are playing
            *Arguments are specific to each implementation.*

            :return: A tuple consisting of

                #. The diplomacy.Game object or None if an error occurred
                #. The power name (e.g. 'FRANCE')
        """
        raise NotImplementedError()

    @gen.coroutine
    @abstractmethod
    def set_orders(self, game, power_name, orders, wait=None):
        """ Submits orders back to the server

            :param game: A diplomacy.Game object representing the current state of the game
            :param power_name: The name of the power submitting the orders (e.g. 'FRANCE')
            :param orders: A list of strings representing the orders (e.g. ['A PAR H', 'F BRE - MAO'])
            :param wait: Optional. If True, sets ready=False, if False sets ready=True.
            :return: True for success, False for failure
            :type game: diplomacy.Game
        """
        raise NotImplementedError()
