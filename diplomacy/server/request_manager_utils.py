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
""" Utility classes and functions used for request management.
    Put here to avoid having file request_managers.py with too many lines.
"""
from collections.__init__ import namedtuple

from diplomacy.communication import notifications
from diplomacy.server.notifier import Notifier

from diplomacy.utils import strings, exceptions

class SynchronizedData(namedtuple('SynchronizedData', ('timestamp', 'order', 'type', 'data'))):
    """ Small class used to store and sort data to synchronize for a game.

        Properties:

        - **timestamp** (int): timestamp of related data to synchronize.
        - **order** (int): rank of data to synchronize.
        - **type** (str): type name of data to synchronize. Possible values:

            - 'message': data is a game message. Order is 0.
            - 'state_history': data is a game state for history. Order is 1.
            - 'state': data is current game state. Order is 2.

        - **data**: proper data to synchronize.

        Synchronized data are sorted using timestamp then order, meaning that:

            - data are synchronized from former to later timestamps
            - for a same timestamp, messages are synchronized first,
              then states for history, then current state.
    """

class GameRequestLevel:
    """ Describe a game level retrieved from a game request. Used by some game requests managers
        to determine user rights in a game. Possible game levels:
        power, observer, omniscient and master.
    """
    __slots__ = ['game', 'power_name', '__action_level']

    def __init__(self, game, action_level, power_name):
        """ Initialize a game request level.

            :param game: related game data
            :param action_level: action level, either:

                - 'power'
                - 'observer'
                - 'omniscient'
                - 'master'

            :param power_name: (optional) power name specified in game request. Required if level is 'power'.
            :type game: diplomacy.server.server_game.ServerGame
            :type action_level: str
            :type power_name: str
        """
        assert action_level in {'power', 'observer', 'omniscient', 'master'}
        self.game = game
        self.power_name = power_name  # type: str
        self.__action_level = action_level  # type: str

    def is_power(self):
        """ Return True if game level is power. """
        return self.__action_level == 'power'

    def is_observer(self):
        """ Return True if game level is observer. """
        return self.__action_level == 'observer'

    def is_omniscient(self):
        """ Return True if game level is omniscient. """
        return self.__action_level == 'omniscient'

    def is_master(self):
        """ Return True if game level is master. """
        return self.__action_level == 'master'

    @classmethod
    def power_level(cls, game, power_name):
        """ Create and return a game power level with given game data and power name. """
        return cls(game, 'power', power_name)

    @classmethod
    def observer_level(cls, game, power_name):
        """ Create and return a game observer level with given game data and power name. """
        return cls(game, 'observer', power_name)

    @classmethod
    def omniscient_level(cls, game, power_name):
        """ Create and return a game omniscient level with given game data and power name. """
        return cls(game, 'omniscient', power_name)

    @classmethod
    def master_level(cls, game, power_name):
        """ Create and return a game master level with given game data and power name. """
        return cls(game, 'master', power_name)

def verify_request(server, request, connection_handler,
                   omniscient_role=True, observer_role=True, power_role=True,
                   require_power=False, require_master=True):
    """ Verify request token, and game role and rights if request is a game request.
        Ignore connection requests (e.g. SignIn), as such requests don't have any token.
        Verifying token:

        - check if server knows request token
        - check if request token is still valid.
        - Update token lifetime. See method Server.assert_token() for more details.

        Verifying game role and rights:

        - check if server knows request game ID.
        - check if request token is allowed to have request game role in associated game ID.

        If request is a game request, return a GameRequestLevel containing:

        - the server game object
        - the level of rights (power, observer or master) allowed for request sender.
        - the power name associated to request (if present), representing which power is queried by given request.

        See class GameRequestLevel for more details.

        :param server: server which receives the request
        :param request: request received by server
        :param connection_handler: connection handler which receives the request
        :param omniscient_role: (for game requests) Indicate if omniscient role is accepted for this request.
        :param observer_role: (for game requests) Indicate if observer role is accepted for this request.
        :param power_role: (for game requests) Indicate if power role is accepted for this request.
        :param require_power: (for game requests) Indicate if a power name is required for this request.
            If true, either game role must be power role, or request must have a non-null `power_name` role.
        :param require_master: (for game requests) Indicate if an omniscient must be a master.
            If true and if request role is omniscient, then request token must be a master token for related game.
        :return: a GameRequestLevel object for game requests, else None.
        :rtype: diplomacy.server.request_manager_utils.GameRequestLevel
        :type server: diplomacy.Server
        :type request: requests._AbstractRequest | requests._AbstractGameRequest
        :type connection_handler: diplomacy.server.connection_handler.ConnectionHandler
    """

    # A request may be a connection request, a channel request or a game request.
    # For connection request, field level is None.
    # For channel request, field level is CHANNEL. Channel request has a `token` field.
    # For game request, field level is GAME.
    # Game request is a channel request with supplementary fields `game_role` and `game_id`.

    # No permissions to check for connection requests (e.g. SignIn).
    if not request.level:
        return None

    # Check token for channel and game requests.
    server.assert_token(request.token, connection_handler)

    # No more permissions to check for non-game requests.
    if request.level != strings.GAME:
        return None

    # Check and get game.
    server_game = server.get_game(request.game_id)

    power_name = getattr(request, 'power_name', None)

    if strings.role_is_special(request.game_role):

        if request.game_role == strings.OMNISCIENT_TYPE:

            # Check if omniscient role is accepted (for this call).
            if not omniscient_role:
                raise exceptions.ResponseException(
                    'Omniscient role disallowed for request %s' % request.name)

            # Check if request token is known as omniscient token by related game.
            if not server_game.has_omniscient_token(request.token):
                raise exceptions.GameTokenException()

            # Check if request token is a master token (if required for this call)
            # and create game request level.
            token_is_master = server.token_is_master(request.token, server_game)
            if require_master and not token_is_master:
                raise exceptions.GameMasterTokenException()
            if token_is_master:
                level = GameRequestLevel.master_level(server_game, power_name)
            else:
                level = GameRequestLevel.omniscient_level(server_game, power_name)

        else:
            # Check if observer role is accepted (for this call).
            if not observer_role:
                raise exceptions.ResponseException(
                    'Observer role disallowed for request %s' % request.game_role)

            # Check if request token is known as observer token by related game.
            if not server_game.has_observer_token(request.token):
                raise exceptions.GameTokenException()

            # Create game request level object.
            level = GameRequestLevel.observer_level(server_game, power_name)

        # Check if we have a valid power name if power name is required (for this call) or given.
        if power_name is None:
            if require_power:
                raise exceptions.MapPowerException(None)
        elif not server_game.has_power(power_name):
            raise exceptions.MapPowerException(power_name)

    else:
        # Check if power role is accepted (for this call).
        if not power_role:
            raise exceptions.ResponseException('Power role disallowed for request %s' % request.name)

        # Get power name to check: either given power name if defined, else game role.
        if power_name is None:
            power_name = request.game_role

        # Check if given power name is valid.
        if not server_game.has_power(power_name):
            raise exceptions.MapPowerException(power_name)

        # Check if request sender is allowed to query given power name.
        # We don't care anymore if sender token is currently associated to this power,
        # as long as sender is registered as the controller of this power.
        if not server_game.is_controlled_by(power_name, server.users.get_name(request.token)):
            raise exceptions.ResponseException('User %s does not currently control power %s'
                                               % (server.users.get_name(request.token), power_name))

        # Create game request level.
        level = GameRequestLevel.power_level(server_game, power_name)

    return level

def transfer_special_tokens(server_game, server, username, grade_update, from_observation=True):
    """ Transfer tokens of given username from an observation role to the opposite in given
        server game, and notify all user tokens about observation role update with given grade update.
        This method is used in request manager on_set_grade().

        :param server_game: server game in which tokens roles must be changed.
        :param server: server from which notifications will be sent.
        :param username: name of user whom tokens will be transferred. Only user tokens registered in
            server games as observer tokens or omniscient tokens will be updated.
        :param grade_update: type of upgrading.
            Possibles values in strings.ALL_GRADE_UPDATES (PROMOTE or DEMOTE).
        :param from_observation: indicate transfer direction.
            If True, we expect to transfer role from observer to omniscient.
            If False, we expect to transfer role from omniscient to observer.
        :type server_game: diplomacy.server.server_game.ServerGame
        :type server: diplomacy.Server
    """
    if from_observation:
        old_role = strings.OBSERVER_TYPE
        new_role = strings.OMNISCIENT_TYPE
        token_filter = server_game.has_observer_token
    else:
        old_role = strings.OMNISCIENT_TYPE
        new_role = strings.OBSERVER_TYPE
        token_filter = server_game.has_omniscient_token

    connected_user_tokens = [user_token for user_token in server.users.get_tokens(username)
                             if token_filter(user_token)]

    if connected_user_tokens:

        # Update observer level for each connected user token.
        for user_token in connected_user_tokens:
            server_game.transfer_special_token(user_token)

        addresses = [(old_role, user_token) for user_token in connected_user_tokens]
        Notifier(server).notify_game_addresses(
            server_game.game_id, addresses, notifications.OmniscientUpdated,
            grade_update=grade_update, game=server_game.cast(new_role, username))

def assert_game_not_finished(server_game):
    """ Check if given game is not yet completed or canceled, otherwise raise a GameFinishedException.

        :param server_game: server game to check
        :type server_game: diplomacy.server.server_game.ServerGame
    """
    if server_game.is_game_completed or server_game.is_game_canceled:
        raise exceptions.GameFinishedException()
