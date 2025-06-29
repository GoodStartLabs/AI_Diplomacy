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
""" Channel

    - The channel object represents an authenticated connection over a socket.
    - It has a token that it sends with every request to authenticate itself.
"""
import logging

from tornado import gen

from diplomacy.communication import requests
from diplomacy.utils import strings, common

LOGGER = logging.getLogger(__name__)

def _req_fn(request_class, local_req_fn=None, **request_args):
    """ Create channel request method that sends request with channel token.

        :param request_class: class of request to send with channel request method.
        :param local_req_fn: (optional) Channel method to use locally to try retrieving a data
            instead of sending a request. If provided, local_req_fn is called with request args:

            - if it returns anything else than None, then returned data is returned by channel request method.
            - else, request class is still sent and channel request method follows standard path
              (request sent, response received, response handler called and final handler result returned).

        :param request_args: arguments to pass to request class to create the request object.
        :return: a Channel method.
    """
    str_params = (', '.join('%s=%s' % (key, common.to_string(value))
                            for (key, value) in sorted(request_args.items()))) if request_args else ''

    @gen.coroutine
    def func(self, game=None, **kwargs):
        """ Send an instance of request_class with given kwargs and game object.
            :param self: Channel object who sends the request.
            :param game: (optional) a NetworkGame object (required for game requests).
            :param kwargs: request arguments.
            :return: Data returned after response is received and handled by associated response manager.
                See module diplomacy.client.response_managers about responses management.
            :type game: diplomacy.client.network_game.NetworkGame
        """
        kwargs.update(request_args)
        if request_class.level == strings.GAME:
            assert game is not None
            kwargs[strings.TOKEN] = self.token
            kwargs[strings.GAME_ID] = game.game_id
            kwargs[strings.GAME_ROLE] = game.role
            kwargs[strings.PHASE] = game.current_short_phase
        else:
            assert game is None
            if request_class.level == strings.CHANNEL:
                kwargs[strings.TOKEN] = self.token
        if local_req_fn is not None:
            local_ret = local_req_fn(self, **kwargs)
            if local_ret is not None:
                return local_ret
        request = request_class(**kwargs)
        return (yield self.connection.send(request, game))

    func.__request_name__ = request_class.__name__
    func.__request_params__ = str_params
    func.__doc__ = """
            Send request :class:`.%(request_name)s`%(with_params)s``kwargs``.
            Return response data returned by server for this request.
            See :class:`.%(request_name)s` about request parameters and response.
                """ % {'request_name': request_class.__name__,
                       'with_params': ' with forced parameters ``(%s)`` and additional request parameters '
                                      % str_params if request_args else ' with request parameters '}
    return func

class Channel:
    """ Channel - Represents an authenticated connection over a physical socket """
    # pylint: disable=too-few-public-methods
    __slots__ = ['connection', 'token', 'game_id_to_instances', '__weakref__']

    def __init__(self, connection, token):
        """ Initialize a channel.

            Properties:

            - **connection**: :class:`.Connection` object from which this channel originated.
            - **token**: Channel token, used to identify channel on server.
            - **game_id_to_instances**: Dictionary mapping a game ID to :class:`.NetworkGame` objects loaded for this
              game. Each :class:`.NetworkGame` has a specific role, which is either an observer role, an omniscient
              role, or a power (player) role. Network games for a specific game ID are managed within a
              :class:`.GameInstancesSet`, which makes sure that there will be at most 1 :class:`.NetworkGame` instance
              per possible role.

            :param connection: a Connection object.
            :param token: Channel token.
            :type connection: diplomacy.client.connection.Connection
            :type token: str
        """
        self.connection = connection
        self.token = token
        self.game_id_to_instances = {}  # {game id => GameInstances}

    def _local_join_game(self, **kwargs):
        """ Look for a local game with given kwargs intended to be used to build a JoinGame request.
            Return None if no local game found, else local game found.
            Game is identified with game ID **(required)** and power name *(optional)*.
            If power name is None, we look for a "special" game (observer or omniscient game)
            loaded locally. Note that there is at most 1 special game per (channel + game ID)
            couple: either observer or omniscient, not both.
        """
        game_id = kwargs[strings.GAME_ID]
        power_name = kwargs.get(strings.POWER_NAME, None)
        if game_id in self.game_id_to_instances:
            if power_name is not None:
                return self.game_id_to_instances[game_id].get(power_name)
            return self.game_id_to_instances[game_id].get_special()
        return None

    # ===================
    # Public channel API.
    # ===================

    create_game = _req_fn(requests.CreateGame)
    get_available_maps = _req_fn(requests.GetAvailableMaps)
    get_playable_powers = _req_fn(requests.GetPlayablePowers)
    join_game = _req_fn(requests.JoinGame, local_req_fn=_local_join_game)
    join_powers = _req_fn(requests.JoinPowers)
    list_games = _req_fn(requests.ListGames)
    get_games_info = _req_fn(requests.GetGamesInfo)
    get_dummy_waiting_powers = _req_fn(requests.GetDummyWaitingPowers)

    # User Account API.
    delete_account = _req_fn(requests.DeleteAccount)
    logout = _req_fn(requests.Logout)

    # Admin / Moderator API.
    make_omniscient = _req_fn(requests.SetGrade, grade=strings.OMNISCIENT, grade_update=strings.PROMOTE)
    remove_omniscient = _req_fn(requests.SetGrade, grade=strings.OMNISCIENT, grade_update=strings.DEMOTE)
    promote_administrator = _req_fn(requests.SetGrade, grade=strings.ADMIN, grade_update=strings.PROMOTE)
    demote_administrator = _req_fn(requests.SetGrade, grade=strings.ADMIN, grade_update=strings.DEMOTE)
    promote_moderator = _req_fn(requests.SetGrade, grade=strings.MODERATOR, grade_update=strings.PROMOTE)
    demote_moderator = _req_fn(requests.SetGrade, grade=strings.MODERATOR, grade_update=strings.DEMOTE)

    # ====================================================================
    # Game API. Intended to be called by NetworkGame object, not directly.
    # ====================================================================

    _get_phase_history = _req_fn(requests.GetPhaseHistory)
    _leave_game = _req_fn(requests.LeaveGame)
    _send_game_message = _req_fn(requests.SendGameMessage)
    _set_orders = _req_fn(requests.SetOrders)

    _clear_centers = _req_fn(requests.ClearCenters)
    _clear_orders = _req_fn(requests.ClearOrders)
    _clear_units = _req_fn(requests.ClearUnits)

    _wait = _req_fn(requests.SetWaitFlag, wait=True)
    _no_wait = _req_fn(requests.SetWaitFlag, wait=False)
    _vote = _req_fn(requests.Vote)
    _save = _req_fn(requests.SaveGame)
    _synchronize = _req_fn(requests.Synchronize)

    # Admin / Moderator API.
    _delete_game = _req_fn(requests.DeleteGame)
    _kick_powers = _req_fn(requests.SetDummyPowers)
    _set_state = _req_fn(requests.SetGameState)
    _process = _req_fn(requests.ProcessGame)
    _query_schedule = _req_fn(requests.QuerySchedule)
    _start = _req_fn(requests.SetGameStatus, status=strings.ACTIVE)
    _pause = _req_fn(requests.SetGameStatus, status=strings.PAUSED)
    _resume = _req_fn(requests.SetGameStatus, status=strings.ACTIVE)
    _cancel = _req_fn(requests.SetGameStatus, status=strings.CANCELED)
    _draw = _req_fn(requests.SetGameStatus, status=strings.COMPLETED)
