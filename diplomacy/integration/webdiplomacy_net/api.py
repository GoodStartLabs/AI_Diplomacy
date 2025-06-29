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
""" Contains an API class to send requests to webdiplomacy.net """
import logging
import os
from socket import herror, gaierror, timeout
from urllib.parse import urlencode
from tornado import gen
from tornado.httpclient import HTTPRequest
from tornado.simple_httpclient import HTTPTimeoutError, HTTPStreamClosedError
import ujson as json
from diplomacy.integration.base_api import BaseAPI
from diplomacy.integration.webdiplomacy_net.game import state_dict_to_game_and_power
from diplomacy.integration.webdiplomacy_net.orders import Order
from diplomacy.integration.webdiplomacy_net.utils import CACHE, GameIdCountryId

# Constants
LOGGER = logging.getLogger(__name__)
HTTP_ERRORS = (herror, gaierror, timeout, HTTPTimeoutError, HTTPStreamClosedError,
               ConnectionResetError, ConnectionRefusedError, OSError)
API_USER_AGENT = 'KestasBot / Philip Paquette v1.0'
API_WEBDIPLOMACY_NET = os.environ.get('API_WEBDIPLOMACY', 'https://webdiplomacy.net/api.php')

class API(BaseAPI):
    """ API to interact with webdiplomacy.net """

    @gen.coroutine
    def list_games_with_players_in_cd(self):
        """ Lists the game on the standard map where a player is in CD (civil disorder)
            and the bots needs to submit orders

            :return: List of :class:`.GameIdCountryId` tuples  [(game_id, country_id), (game_id, country_id)]
        """
        route = 'players/cd'
        url = '%s?%s' % (API_WEBDIPLOMACY_NET, urlencode({'route': route}))
        return_val = []

        # Sending request
        try:
            response = yield self._send_get_request(url)
        except HTTP_ERRORS as err:
            LOGGER.error('Unable to connect to server. Error raised is: "%s"', repr(err))
            return return_val

        # 200 - Response OK
        if response.code == 200 and response.body:
            try:
                list_games_players = json.loads(response.body.decode('utf-8'))
            except (TypeError, ValueError):
                LOGGER.warning('ERROR during "%s". Unable to load JSON: %s.', route, response.body.decode('utf-8'))
                return return_val
            for game_player in list_games_players:
                return_val += [GameIdCountryId(game_id=game_player['gameID'], country_id=game_player['countryID'])]

        # Error Occurred
        else:
            LOGGER.warning('ERROR during "%s". Error code: %d. Body: %s.', route, response.code, response.body)

        # Returning
        return return_val

    @gen.coroutine
    def list_games_with_missing_orders(self):
        """ Lists of the game on the standard where the user has not submitted orders yet.

            :return: List of :class:`.GameIdCountryId` tuples  [(game_id, country_id), (game_id, country_id)]
        """
        route = 'players/missing_orders'
        url = '%s?%s' % (API_WEBDIPLOMACY_NET, urlencode({'route': route}))
        return_val = []

        # Sending request
        try:
            response = yield self._send_get_request(url)
        except HTTP_ERRORS as err:
            LOGGER.error('Unable to connect to server. Error raised is: "%s"', repr(err))
            return return_val

        # 200 - Response OK
        if response.code == 200 and response.body:
            try:
                list_games_players = json.loads(response.body.decode('utf-8'))
            except (TypeError, ValueError):
                LOGGER.warning('ERROR during "%s". Unable to load JSON: %s.', route, response.body.decode('utf-8'))
                return return_val
            for game_player in list_games_players:
                return_val += [GameIdCountryId(game_id=game_player['gameID'], country_id=game_player['countryID'])]

        # Error Occurred
        else:
            LOGGER.warning('ERROR during "%s". Error code: %d. Body: %s.', route, response.code, response.body)

        # Returning
        return return_val

    @gen.coroutine
    def get_game_and_power(self, game_id, country_id, max_phases=None):
        """ Returns the game and the power we are playing

            :param game_id: The id of the game object (integer)
            :param country_id: The id of the country for which we want the game state (integer)
            :param max_phases: Optional. If set, improve speed by generating game only using the last 'x' phases.
            :type game_id: int
            :type country_id: int
            :type max_phases: int | None, optional
            :return: A tuple consisting of

                #. The diplomacy.Game object from the game state or None if an error occurred
                #. The power name (e.g. 'FRANCE') referred to by country_id
        """
        # pylint: disable=arguments-differ
        route = 'game/status'
        url = '%s?%s' % (API_WEBDIPLOMACY_NET, urlencode({'route': route, 'gameID': game_id, 'countryID': country_id}))
        return_val = None, None

        # Sending request
        try:
            response = yield self._send_get_request(url)
        except HTTP_ERRORS as err:
            LOGGER.error('Unable to connect to server. Error raised is: "%s"', repr(err))
            return return_val

        # 200 - Response OK
        if response.code == 200 and response.body:
            try:
                state_dict = json.loads(response.body.decode('utf-8'))
            except (TypeError, ValueError):
                LOGGER.warning('ERROR during "%s". Unable to load JSON: %s.', route, response.body.decode('utf-8'))
                return return_val
            game, power_name = state_dict_to_game_and_power(state_dict, country_id, max_phases=max_phases)
            return_val = game, power_name

        # Error Occurred
        else:
            LOGGER.warning('ERROR during "%s". Error code: %d. Body: %s.', route, response.code, response.body)

        # Returning
        return return_val

    @gen.coroutine
    def set_orders(self, game, power_name, orders, wait=None):
        """ Submits orders back to the server

            :param game: A :class:`diplomacy.engine.game.Game` object representing the current state of the game
            :param power_name: The name of the power submitting the orders (e.g. 'FRANCE')
            :param orders: A list of strings representing the orders (e.g. ['A PAR H', 'F BRE - MAO'])
            :param wait: Optional. If True, sets ready=False, if False sets ready=True.
            :return: True for success, False for failure
            :type game: diplomacy.Game
            :type power_name: str
            :type orders: List[str]
            :type wait: bool | None, optional
        """
        # Logging orders
        LOGGER.info('[%s/%s/%s] - Submitting orders: %s', game.game_id, game.get_current_phase(), power_name, orders)

        # Converting orders to dict
        orders_dict = [Order(order, map_name=game.map_name, phase_type=game.phase_type, game=game) for order in orders]

        # Recording submitted orders
        submitted_orders = {}
        for order in orders_dict:
            unit = ' '.join(order.to_string().split()[:2])
            if order.to_string()[-2:] == ' D':
                unit = '? ' + unit[2:]
            submitted_orders[unit] = order.to_norm_string()

        # Getting other info
        game_id = int(game.game_id)
        country_id = CACHE[game.map_name]['power_to_ix'].get(power_name, -1)
        current_phase = game.get_current_phase()

        if current_phase != 'COMPLETED':
            season, current_year, phase_type = current_phase[0], int(current_phase[1:5]), current_phase[5]
            nb_years = current_year - game.map.first_year
            turn = 2 * nb_years + (0 if season == 'S' else 1)
            phase = {'M': 'Diplomacy', 'R': 'Retreats', 'A': 'Builds'}[phase_type]
        else:
            turn = -1
            phase = 'Diplomacy'

        # Sending request
        route = 'game/orders'
        url = '%s?%s' % (API_WEBDIPLOMACY_NET, urlencode({'route': route}))
        body = {'gameID': game_id,
                'turn': turn,
                'phase': phase,
                'countryID': country_id,
                'orders': [order.to_dict() for order in orders_dict if order]}
        if wait is not None:
            body['ready'] = 'Yes' if not wait else 'No'
        body = json.dumps(body).encode('utf-8')

        # Sending request
        try:
            response = yield self._send_post_request(url, body)
        except HTTP_ERRORS as err:
            LOGGER.error('Unable to connect to server. Error raised is: "%s"', repr(err))
            return False

        # Error Occurred
        if response.code != 200:
            LOGGER.warning('ERROR during "%s". Error code: %d. Body: %s.', route, response.code, response.body)
            return False

        # No orders set - Was only setting the ready flag
        if not orders:
            return True

        # No response received from the server - Maybe a connection timeout?
        if not response.body:
            LOGGER.warning('WARNING during "%s". No response body received. Is the server OK?', route)
            return False

        # Otherwise, validating that received orders are the same as submitted orders
        try:
            response_body = json.loads(response.body.decode('utf-8'))
        except (TypeError, ValueError):
            LOGGER.warning('ERROR during "%s". Unable to load JSON: %s.', route, response.body.decode('utf-8'))
            return False
        orders_dict = [Order(order, map_name=game.map_name, phase_type=game.phase_type) for order in response_body]
        all_orders_set = True

        # Recording received orders
        received_orders = {}
        for order in orders_dict:
            unit = ' '.join(order.to_string().split()[:2])
            if order.to_string()[-2:] == ' D':
                unit = '? ' + unit[2:]
            received_orders[unit] = order.to_norm_string()

        # Logging different orders
        for unit in submitted_orders:
            if submitted_orders[unit] != received_orders.get(unit, ''):
                all_orders_set = False
                LOGGER.warning('[%s/%s/%s]. Submitted: "%s" - Server has: "%s".',
                               game.game_id, game.get_current_phase(), power_name,
                               submitted_orders[unit], received_orders.get(unit, ''))

        # Returning status
        return all_orders_set

    # ---- Helper methods ----
    @gen.coroutine
    def _send_get_request(self, url):
        """ Helper method to send a get request to the API endpoint """
        http_request = HTTPRequest(url=url,
                                   method='GET',
                                   headers={'Authorization': 'Bearer %s' % self.api_key},
                                   connect_timeout=self.connect_timeout,
                                   request_timeout=self.request_timeout,
                                   user_agent=API_USER_AGENT)
        http_response = yield self.http_client.fetch(http_request, raise_error=False)
        return http_response

    @gen.coroutine
    def _send_post_request(self, url, body):
        """ Helper method to send a post request to the API endpoint """
        http_request = HTTPRequest(url=url,
                                   method='POST',
                                   body=body,
                                   headers={'Authorization': 'Bearer %s' % self.api_key},
                                   connect_timeout=self.connect_timeout,
                                   request_timeout=self.request_timeout,
                                   user_agent=API_USER_AGENT)
        http_response = yield self.http_client.fetch(http_request, raise_error=False)
        return http_response
