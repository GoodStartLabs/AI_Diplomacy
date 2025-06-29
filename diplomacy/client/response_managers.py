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
""" Response managers (client side). One manager corresponds to one request, except for requests that don't need
    specific manager (in such case, method default_manager() is used).
    Each manager is a function with name format "on_<request name in snake case>", expecting a request context
    and a response as parameters.
"""
# pylint: disable=unused-argument
from diplomacy.client.game_instances_set import GameInstancesSet
from diplomacy.client.network_game import NetworkGame
from diplomacy.client.channel import Channel
from diplomacy.communication import requests, responses
from diplomacy.engine.game import Game
from diplomacy.utils import exceptions
from diplomacy.utils.game_phase_data import GamePhaseData

class RequestFutureContext:
    """ Helper class to store a context around a request
        (with future for response management, related connection and optional related game).
    """
    __slots__ = ['request', 'future', 'connection', 'game']

    def __init__(self, request, future, connection, game=None):
        """ Initialize a request future context.

            :param request: a request object (see diplomacy.communication.requests about possible classes).
            :param future: a tornado Future object.
            :param connection: a diplomacy.Connection object.
            :param game: (optional) a NetworkGame object (from module diplomacy.client.network_game).
            :type request: requests._AbstractRequest | requests._AbstractGameRequest
            :type future: tornado.concurrent.Future
            :type connection: diplomacy.Connection
            :type game: diplomacy.client.network_game.NetworkGame
        """
        self.request = request
        self.future = future
        self.connection = connection
        self.game = game

    request_id = property(lambda self: self.request.request_id)
    token = property(lambda self: self.request.token)
    channel = property(lambda self: self.connection.channels[self.request.token])

    def new_channel(self, token):
        """ Create, store (in associated connection), and return a new channel with given token. """
        channel = Channel(self.connection, token)
        self.connection.channels[token] = channel
        return channel

    def new_game(self, received_game):
        """ Create, store (in associated connection) and return a new network game wrapping given game data.
            Returned game is already in appropriate type (observer game, omniscient game or power game).

            :param received_game: game sent by server (Game object)
            :type received_game: Game
        """
        game = NetworkGame(self.channel, received_game)
        if game.game_id not in self.channel.game_id_to_instances:
            self.channel.game_id_to_instances[game.game_id] = GameInstancesSet(game.game_id)
        self.channel.game_id_to_instances[game.game_id].add(game)
        return game

    def remove_channel(self):
        """ Remove associated channel (inferred from request token) from associated connection. """
        del self.connection.channels[self.channel.token]

    def delete_game(self):
        """ Delete local game instances corresponding to game ID in associated request. """
        assert hasattr(self.request, 'game_id')
        assert self.game is not None and self.game.game_id == self.request.game_id
        if self.request.game_id in self.channel.game_id_to_instances:
            del self.channel.game_id_to_instances[self.request.game_id]

def default_manager(context, response):
    """ Default manager called for requests that don't have specific management.
        If response is OK, return None.
        If response is a UniqueData, return response data field.
        Else, return response.
        Expect response to be either OK or a UniqueData
        (containing only 1 field intended to be returned by server for associated request).

        :param context: request context
        :param response: response received
        :return: None, or data if response is a UniqueData.
    """
    if isinstance(response, responses.UniqueData):
        return response.data
    if isinstance(response, responses.Ok):
        return None
    return response

def on_clear_centers(context, response):
    """ Manage response for request ClearCenters.

        :param context: request context
        :param response: response received
        :return: None
        :type context: RequestFutureContext
    """
    request = context.request  # type: requests.ClearCenters
    Game.clear_centers(context.game, request.power_name)

def on_clear_orders(context, response):
    """ Manage response for request ClearOrders.

        :param context: request context
        :param response: response received
        :return: None
        :type context: RequestFutureContext
    """
    request = context.request  # type: requests.ClearOrders
    Game.clear_orders(context.game, request.power_name)

def on_clear_units(context, response):
    """ Manage response for request ClearUnits.

        :param context: request context
        :param response: response received
        :return: None
        :type context: RequestFutureContext
    """
    request = context.request  # type: requests.ClearUnits
    Game.clear_units(context.game, request.power_name)

def on_create_game(context, response):
    """ Manage response for request CreateGame.

        :param context: request context
        :param response: response received
        :return: a new network game
        :type context: RequestFutureContext
        :type response: responses.DataGame
    """
    return context.new_game(response.data)

def on_delete_account(context, response):
    """ Manage response for request DeleteAccount.

        :param context: request context
        :param response: response received
        :return: None
        :type context: RequestFutureContext
    """
    context.remove_channel()

def on_delete_game(context, response):
    """ Manage response for request DeleteGame.

        :param context: request context
        :param response: response received
        :return: None
        :type context: RequestFutureContext
    """
    context.delete_game()

def on_get_phase_history(context, response):
    """ Manage response for request GetPhaseHistory.

        :param context: request context
        :param response: response received
        :return: a list of game states
        :type context: RequestFutureContext
        :type response: responses.DataGamePhases
    """
    phase_history = response.data
    for game_phase in phase_history:  # type: diplomacy.utils.game_phase_data.GamePhaseData
        Game.extend_phase_history(context.game, game_phase)
    return phase_history

def on_join_game(context, response):
    """ Manage response for request JoinGame.

        :param context: request context
        :param response: response received
        :return: a new network game
        :type response: responses.DataGame
    """
    return context.new_game(response.data)

def on_leave_game(context, response):
    """ Manage response for request LeaveGame.

        :param context: request context
        :param response: response received
        :return: None
        :type context: RequestFutureContext
    """
    context.delete_game()

def on_logout(context, response):
    """ Manage response for request Logout.

        :param context: request context
        :param response: response received
        :return: None
        :type context: RequestFutureContext
    """
    context.remove_channel()

def on_send_game_message(context, response):
    """ Manage response for request SendGameMessage.

        :param context: request context
        :param response: response received
        :return: None
        :type context: RequestFutureContext
        :type response: responses.DataTimeStamp
    """
    request = context.request  # type: requests.SendGameMessage
    message = request.message
    message.time_sent = response.data
    Game.add_message(context.game, message)

def on_set_game_state(context, response):
    """ Manage response for request SetGameState.

        :param context: request context
        :param response: response received
        :return: None
        :type context: RequestFutureContext
    """
    request = context.request  # type: requests.SetGameState
    context.game.set_phase_data(GamePhaseData(name=request.state['name'],
                                              state=request.state,
                                              orders=request.orders,
                                              messages=request.messages,
                                              results=request.results))

def on_set_game_status(context, response):
    """ Manage response for request SetGameStatus.

        :param context: request context
        :param response: response received
        :return: None
        :type context: RequestFutureContext
    """
    request = context.request  # type: requests.SetGameStatus
    Game.set_status(context.game, request.status)

def on_set_orders(context, response):
    """ Manage response for request SetOrders.

        :param context: request context
        :param response: response received
        :return: None
        :type context: RequestFutureContext
    """
    request = context.request  # type: requests.SetOrders
    orders = request.orders
    if Game.is_player_game(context.game):
        assert context.game.power.name == context.request.game_role
        Game.set_orders(context.game, request.game_role, orders)
    else:
        Game.set_orders(context.game, request.power_name, orders)

def on_set_wait_flag(context, response):
    """ Manage response for request SetWaitFlag.

        :param context: request context
        :param response: response received
        :return: None
        :type context: RequestFutureContext
    """
    request = context.request  # type: requests.SetWaitFlag
    wait = request.wait
    if Game.is_player_game(context.game):
        assert context.game.power.name == context.request.game_role
        Game.set_wait(context.game, request.game_role, wait)
    else:
        Game.set_wait(context.game, request.power_name, wait)

def on_sign_in(context, response):
    """ Manage response for request SignIn.

        :param context: request context
        :param response: response received
        :return: a new channel
        :type context: RequestFutureContext
        :type response: responses.DataToken
    """
    return context.new_channel(response.data)

def on_vote(context, response):
    """ Manage response for request VoteAboutDraw.

        :param context: request context
        :param response: response received
        :return: None
        :type context: RequestFutureContext
    """
    request = context.request  # type: requests.Vote
    vote = request.vote
    assert Game.is_player_game(context.game)
    assert context.game.power.name == context.request.game_role
    context.game.power.vote = vote

# Mapping dictionary from request class to response handler function.
MAPPING = {
    requests.ClearCenters: on_clear_centers,
    requests.ClearOrders: on_clear_orders,
    requests.ClearUnits: on_clear_units,
    requests.CreateGame: on_create_game,
    requests.DeleteAccount: on_delete_account,
    requests.DeleteGame: on_delete_game,
    requests.GetAllPossibleOrders: default_manager,
    requests.GetAvailableMaps: default_manager,
    requests.GetDaidePort: default_manager,
    requests.GetDummyWaitingPowers: default_manager,
    requests.GetGamesInfo: default_manager,
    requests.GetPhaseHistory: on_get_phase_history,
    requests.GetPlayablePowers: default_manager,
    requests.JoinGame: on_join_game,
    requests.JoinPowers: default_manager,
    requests.LeaveGame: on_leave_game,
    requests.ListGames: default_manager,
    requests.Logout: on_logout,
    requests.ProcessGame: default_manager,
    requests.QuerySchedule: default_manager,
    requests.SaveGame: default_manager,
    requests.SendGameMessage: on_send_game_message,
    requests.SetDummyPowers: default_manager,
    requests.SetGameState: on_set_game_state,
    requests.SetGameStatus: on_set_game_status,
    requests.SetGrade: default_manager,
    requests.SetOrders: on_set_orders,
    requests.SetWaitFlag: on_set_wait_flag,
    requests.SignIn: on_sign_in,
    requests.Synchronize: default_manager,
    requests.Vote: on_vote,
}

def handle_response(context, response):
    """ Call appropriate handler for given response with given request context.

        :param context: request context.
        :param response: response received.
        :return: value returned by handler.
    """
    handler = MAPPING.get(type(context.request), None)
    if not handler:
        raise exceptions.DiplomacyException(
            'No response handler available for request class %s' % type(context.request).__name__)
    return handler(context, response)
