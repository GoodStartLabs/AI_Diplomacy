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
""" Request managers (server side). Remarks:
    Even if request managers use many server methods which are coroutines, we currently never yield
    on any of this method because we don't need to wait for them to finish before continuing request
    management. Thus, current request managers are all normal functions.
    Server coroutines used here are usually:
    - game scheduling/unscheduling
    - game saving
    - server saving
    - notifications sending
"""
#pylint:disable=too-many-lines
import logging

from tornado import gen
from tornado.concurrent import Future

from diplomacy.communication import notifications, requests, responses
from diplomacy.server.notifier import Notifier
from diplomacy.server.server_game import ServerGame
from diplomacy.server.request_manager_utils import (SynchronizedData, verify_request, transfer_special_tokens,
                                                    assert_game_not_finished)
from diplomacy.utils import exceptions, strings, constants, export
from diplomacy.utils.common import hash_password
from diplomacy.utils.constants import OrderSettings
from diplomacy.utils.game_phase_data import GamePhaseData

LOGGER = logging.getLogger(__name__)

# =================
# Request managers.
# =================

SERVER_GAME_RULES = ['NO_PRESS', 'IGNORE_ERRORS', 'POWER_CHOICE']

def on_clear_centers(server, request, connection_handler):
    """ Manage request ClearCenters.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: None
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.ClearCenters
    """
    level = verify_request(server, request, connection_handler, observer_role=False)
    assert_game_not_finished(level.game)
    level.game.clear_centers(level.power_name)
    Notifier(server, ignore_addresses=[request.address_in_game]).notify_cleared_centers(level.game, level.power_name)

def on_clear_orders(server, request, connection_handler):
    """ Manage request ClearOrders.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: None
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.ClearOrders
    """
    level = verify_request(server, request, connection_handler, observer_role=False)
    assert_game_not_finished(level.game)
    if not request.phase or request.phase != level.game.current_short_phase:
        raise exceptions.ResponseException(
            'Invalid order phase, received %s, server phase is %s' % (request.phase, level.game.current_short_phase))
    level.game.clear_orders(level.power_name)
    Notifier(server, ignore_addresses=[request.address_in_game]).notify_cleared_orders(level.game, level.power_name)

def on_clear_units(server, request, connection_handler):
    """ Manage request ClearUnits.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: None
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.ClearUnits
    """
    level = verify_request(server, request, connection_handler, observer_role=False)
    assert_game_not_finished(level.game)
    level.game.clear_units(level.power_name)
    Notifier(server, ignore_addresses=[request.address_in_game]).notify_cleared_units(level.game, level.power_name)

def on_create_game(server, request, connection_handler):
    """ Manage request CreateGame.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: None
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.CreateGame
    """

    # Check request token.
    verify_request(server, request, connection_handler)
    game_id, token, power_name, state = request.game_id, request.token, request.power_name, request.state

    # Check if server still accepts to create new games.
    if server.cannot_create_more_games():
        raise exceptions.GameCreationException()

    # Check if given map name is valid and if there is such map.
    game_map = server.get_map(request.map_name)
    if not game_map:
        raise exceptions.MapIdException()

    # If rule SOLITAIRE is required, a power name cannot be queried (as all powers should be dummy).
    # In such case, game creator can only be omniscient.
    if request.rules and 'SOLITAIRE' in request.rules and power_name is not None:
        raise exceptions.GameSolitaireException()

    # If a power name is given, check if it's a valid power name for related map.
    if power_name is not None and power_name not in game_map['powers']:
        raise exceptions.MapPowerException(power_name)

    # Create server game.
    username = server.users.get_name(token)
    if game_id is None or game_id == '':
        game_id = server.create_game_id()
    elif server.has_game_id(game_id):
        raise exceptions.GameIdException('Game ID already used (%s).' % game_id)
    server_game = ServerGame(map_name=request.map_name,
                             rules=request.rules or SERVER_GAME_RULES,
                             game_id=game_id,
                             initial_state=state,
                             n_controls=request.n_controls,
                             deadline=request.deadline,
                             registration_password=request.registration_password,
                             server=server)

    # Make sure game creator will be a game master (set him as moderator if he's not an admin).
    if not server.users.has_admin(username):
        server_game.promote_moderator(username)

    # Register game on server.
    server.add_new_game(server_game)

    # Register game creator, as either power player or omniscient observer.
    if power_name:
        server_game.control(power_name, username, token)
        client_game = server_game.as_power_game(power_name)
    else:
        server_game.add_omniscient_token(token)
        client_game = server_game.as_omniscient_game(username)

    # Start game immediately if possible (e.g. if it's a solitaire game).
    if server_game.game_can_start():
        server.start_game(server_game)

    server.save_game(server_game)

    return responses.DataGame(data=client_game, request_id=request.request_id)

def on_delete_account(server, request, connection_handler):
    """ Manage request DeleteAccount.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: None
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.DeleteAccount
    """

    # Check request token.
    verify_request(server, request, connection_handler)
    token, username = request.token, request.username

    # Get username of account to delete, either from given username or from request token.
    # If given username is not token username, admin privileges are required to delete account of given username.
    if not username:
        username = server.users.get_name(token)
    elif username != server.users.get_name(token):
        server.assert_admin_token(token)

    # Delete account.
    if server.users.has_username(username):

        # Send notification about account deleted to all account tokens.
        Notifier(server, ignore_tokens=[token]).notify_account_deleted(username)

        # Delete user from server.
        server.users.remove_user(username)

        # Remove tokens related to this account from loaded server games.
        # Unregister this account from moderators, omniscient observers and players of loaded games.
        for server_game in server.games.values():  # type: ServerGame
            server_game.filter_tokens(server.users.has_token)
            filter_status = server_game.filter_usernames(server.users.has_username)

            # If this account was a player for this game, notify game about new dummy powers.
            if filter_status > 0:
                server.stop_game_if_needed(server_game)
                Notifier(server, ignore_tokens=[token]).notify_game_powers_controllers(server_game)

            # Require game disk backup.
            server.save_game(server_game)

        # Require server data disk backup.
        server.save_data()

def on_delete_game(server, request, connection_handler):
    """ Manage request DeleteGame.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.DeleteGame
    """
    level = verify_request(server, request, connection_handler, observer_role=False, power_role=False)
    server.delete_game(level.game)
    server.unschedule_game(level.game)
    Notifier(server, ignore_tokens=[request.token]).notify_game_deleted(level.game)

def on_get_all_possible_orders(server, request, connection_handler):
    """ Manage request GetAllPossibleOrders

        :param server: server which receives the request
        :param request: request to manage
        :param connection_handler: connection handler from which the request was sent
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.GetAllPossibleOrders
    """
    level = verify_request(server, request, connection_handler, require_master=False)
    return responses.DataPossibleOrders(possible_orders=level.game.get_all_possible_orders(),
                                        orderable_locations=level.game.get_orderable_locations(),
                                        request_id=request.request_id)

def on_get_available_maps(server, request, connection_handler):
    """ Manage request GetAvailableMaps.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: None
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.GetAvailableMaps
    """
    verify_request(server, request, connection_handler)
    return responses.DataMaps(data=server.available_maps, request_id=request.request_id)

def on_get_daide_port(server, request, connection_handler):
    """ Manage request GetDaidePort.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: None
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.GetDaidePort
    """
    del connection_handler
    daide_port = server.get_daide_port(request.game_id)
    if daide_port is None:
        raise exceptions.DaidePortException(
            "Invalid game id %s or game's DAIDE server is not started for that game" % request.game_id)
    return responses.DataPort(data=daide_port, request_id=request.request_id)

def on_get_dummy_waiting_powers(server, request, connection_handler):
    """ Manage request GetAllDummyPowerNames.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: an instance of responses.DataGamesToPowerNames
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.GetDummyWaitingPowers
    """
    verify_request(server, request, connection_handler)
    return responses.DataGamesToPowerNames(
        data=server.get_dummy_waiting_power_names(request.buffer_size, request.token), request_id=request.request_id)

def on_get_games_info(server, request, connection_handler):
    """ Manage request GetGamesInfo.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: an instance of responses.DataGames
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.GetGamesInfo
    """
    verify_request(server, request, connection_handler)
    username = server.users.get_name(request.token)
    games = []
    for game_id in request.games:
        try:
            server_game = server.load_game(game_id)
            games.append(responses.DataGameInfo(
                game_id=server_game.game_id,
                phase=server_game.current_short_phase,
                timestamp=server_game.get_latest_timestamp(),
                timestamp_created=server_game.timestamp_created,
                map_name=server_game.map_name,
                observer_level=server_game.get_observer_level(username),
                controlled_powers=server_game.get_controlled_power_names(username),
                rules=server_game.rules,
                status=server_game.status,
                n_players=server_game.count_controlled_powers(),
                n_controls=server_game.get_expected_controls_count(),
                deadline=server_game.deadline,
                registration_password=bool(server_game.registration_password)
            ))
        except exceptions.GameIdException:
            # Invalid game ID, just pass.
            pass
    return responses.DataGames(data=games, request_id=request.request_id)

def on_get_phase_history(server, request, connection_handler):
    """ Manage request GetPhaseHistory.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: a DataGamePhases object.
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.GetPhaseHistory
        :rtype: diplomacy.communication.responses.DataGamePhases
    """
    level = verify_request(server, request, connection_handler, require_master=False)
    game_phases = level.game.get_phase_history(request.from_phase, request.to_phase, request.game_role)
    return responses.DataGamePhases(data=game_phases, request_id=request.request_id)

def on_get_playable_powers(server, request, connection_handler):
    """ Manage request GetPlayablePowers.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: None
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.GetPlayablePowers
    """
    verify_request(server, request, connection_handler)
    return responses.DataPowerNames(
        data=server.get_game(request.game_id).get_dummy_power_names(), request_id=request.request_id)

def on_join_game(server, request, connection_handler):
    """ Manage request JoinGame.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: a Data response with client game data.
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.JoinGame
    """

    # Check request token.
    verify_request(server, request, connection_handler)
    token, power_name, registration_password = request.token, request.power_name, request.registration_password

    # Get related game.
    server_game = server.get_game(request.game_id)  # type: ServerGame

    username = server.users.get_name(token)

    # No power name given, request sender wants to be an observer.
    if power_name is None:

        # Check given registration password for related game.
        if not server_game.is_valid_password(registration_password) and not server.token_is_master(token, server_game):
            raise exceptions.GameRegistrationPasswordException()

        # Request token must not already be a player token.
        if server_game.has_player_token(token):
            raise exceptions.GameJoinRoleException()

        # Observations must be allowed for this game, or request sender must be a game master.
        if server_game.no_observations and not server.token_is_master(token, server_game):
            raise exceptions.GameObserverException('Disallowed observation for non-master users.')

        # Flag used to check if token was already registered with expected game role
        # (possibly because of a re-sent request). If True, we can send response
        # immediately without saving anything.
        token_already_registered = True

        if server.user_is_omniscient(username, server_game):

            # Request sender is allowed to be omniscient for this game.
            # Let's set him as an omniscient observer.

            if not server_game.has_omniscient_token(token):
                # Register request token as omniscient token.
                server_game.add_omniscient_token(token)
                token_already_registered = False
            elif not request.re_sent:
                # Token already registered but request is a new one.
                # This should not happen (programming error?).
                raise exceptions.ResponseException('Token already omniscient from a new request.')

            # Create client game.
            client_game = server_game.as_omniscient_game(username)

        else:

            # Request sender is not allowed to be omniscient for this game.
            # Let's set him as an observer.

            # A token should not be registered twice as observer token.
            if not server_game.has_observer_token(token):
                # Register request token as observer token.
                server_game.add_observer_token(token)
                token_already_registered = False
            elif not request.re_sent:
                # Token already registered but request is a new one.
                # This should not happen (programming error?).
                raise exceptions.ResponseException('Token already observer.')

            # Create client game.
            client_game = server_game.as_observer_game(username)

        # If token was already registered, return immediately (no need to save anything).
        if token_already_registered:
            return responses.DataGame(data=client_game, request_id=request.request_id)

    # Power name given, request sender wants to be a player.
    else:

        # Check given registration password for related game.
        if not (server_game.is_valid_password(registration_password)
                or server.token_is_master(token, server_game)
                or username == constants.PRIVATE_BOT_USERNAME):
            raise exceptions.GameRegistrationPasswordException()

        # No new player allowed if game is ended.
        if server_game.is_game_completed or server_game.is_game_canceled:
            raise exceptions.GameFinishedException()

        if not server_game.has_power(power_name):
            raise exceptions.MapPowerException(power_name)

        # Forbid to play a power that is already eliminated.
        if server_game.get_power(power_name).is_eliminated():
            raise exceptions.ResponseException('%s is eliminated.' % power_name)

        if username == constants.PRIVATE_BOT_USERNAME:
            # Private bot is allowed to control any dummy power after game started
            # (ie. after reached expected number of real players).
            # A dummy power controlled by bot is still marked as "dummy", but
            # has tokens associated.
            if not server_game.is_game_active and not server_game.is_game_paused:
                raise exceptions.ResponseException('Game is not active.')
            if power_name not in server_game.get_dummy_power_names():
                raise exceptions.ResponseException('Invalid dummy power name %s' % power_name)
            server_game.get_power(power_name).add_token(token)
            client_game = server_game.as_power_game(power_name)
            return responses.DataGame(data=client_game, request_id=request.request_id)

        # Power already controlled by request sender.
        if server_game.is_controlled_by(power_name, username):

            # Create client game.
            client_game = server_game.as_power_game(power_name)

            # If token is already registered (probably because of a re-sent request),
            # then we can send response immediately without saving anything.
            if server_game.power_has_token(power_name, token):
                return responses.DataGame(data=client_game, request_id=request.request_id)

            # Otherwise, register token.
            server_game.get_power(power_name).add_token(token)

        # Power not already controlled by request sender.
        else:

            # Request token must not be already an observer token or an omniscient token.
            if server_game.has_observer_token(token) or server_game.has_omniscient_token(token):
                raise exceptions.GameJoinRoleException()

            # If allowed number of players is already reached, only game masters are allowed to control dummy powers.
            if server_game.has_expected_controls_count() and not server.token_is_master(token, server_game):
                raise exceptions.ResponseException(
                    'Reached maximum number of allowed controlled powers for this game (%d).'
                    % server_game.get_expected_controls_count())

            # If power is already controlled (by someone else), game must allow to select a power randomly.
            if server_game.is_controlled(power_name) and server_game.power_choice:
                raise exceptions.ResponseException('You want to control a power that is already controlled,'
                                                   'and this game does not allocate powers randomly.')

            # If request sender is already a game player and game does not allow multiple powers per player,
            # then it cannot register.
            if server_game.has_player(username) and not server_game.multiple_powers_per_player:
                raise exceptions.ResponseException('Disallowed multiple powers per player.')

            # If game has no rule POWER_CHOICE, a randomly selected power is assigned to request sender,
            # whatever be the power he queried.
            if not server_game.power_choice:
                power_name = server_game.get_random_power_name()

            # Register sender token as power token.
            server_game.control(power_name, username, token)

            # Notify other game tokens about new powers controllers.
            Notifier(server, ignore_addresses=[(power_name, token)]).notify_game_powers_controllers(server_game)

            # Create client game.
            client_game = server_game.as_power_game(power_name)

            # Start game if it can start.
            if server_game.game_can_start():
                server.start_game(server_game)

    # Require game disk backup.
    server.save_game(server_game)

    return responses.DataGame(data=client_game, request_id=request.request_id)

def on_join_powers(server, request, connection_handler):
    """ Manage request JoinPowers.
        Current code does not care about rule POWER_CHOICE. It only
        checks if queried powers can be joined by request sender.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: None.
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.JoinPowers
    """

    # Check request token.
    verify_request(server, request, connection_handler)
    token, power_names = request.token, request.power_names
    username = server.users.get_name(token)

    if not power_names:
        raise exceptions.ResponseException('Required at least 1 power name to join powers.')

    # Get related game.
    server_game = server.get_game(request.game_id)  # type: ServerGame

    # No new player allowed if game is ended.
    if server_game.is_game_completed or server_game.is_game_canceled:
        raise exceptions.GameFinishedException()

    # Check given registration password for related game.
    if not (server_game.is_valid_password(request.registration_password)
            or server.token_is_master(token, server_game)
            or username == constants.PRIVATE_BOT_USERNAME):
        raise exceptions.GameRegistrationPasswordException()

    # Check if given power names are valid.
    for power_name in power_names:
        if not server_game.has_power(power_name):
            raise exceptions.MapPowerException(power_name)

    dummy_power_names = server_game.get_dummy_power_names()

    if username == constants.PRIVATE_BOT_USERNAME:
        # Private bot is allowed to control any dummy power after game started
        # (ie. after reached expected number of real players).
        # A dummy power controlled by bot is still marked as "dummy", but
        # has tokens associated.

        # Check if game is started.
        if server_game.is_game_forming:
            raise exceptions.ResponseException('Game is not active.')

        # Check if all given power names are dummy.
        for power_name in power_names:
            if power_name not in dummy_power_names:
                raise exceptions.ResponseException('Invalid dummy power name %s' % power_name)

        # Join bot to each given power name.
        for power_name in power_names:
            server_game.get_power(power_name).add_token(token)

        # Done with bot.
        server.save_game(server_game)
        return

    # Request token must not be already an observer token or an omniscient token.
    if server_game.has_observer_token(token) or server_game.has_omniscient_token(token):
        raise exceptions.GameJoinRoleException()

    # All given powers must be dummy or already controlled by request sender.
    required_dummy_powers = set()
    for power_name in power_names:
        power = server_game.get_power(power_name)
        if power.is_dummy():
            required_dummy_powers.add(power_name)
        elif not power.is_controlled_by(username):
            raise exceptions.ResponseException('Power %s is controlled by someone else.' % power_name)

    # Nothing to do if all queried powers are already controlled by request sender.
    if not required_dummy_powers:
        server.save_game(server_game)
        return

    # Do additional checks for non-game masters.
    if not server.token_is_master(token, server_game):

        if len(required_dummy_powers) < len(power_names) and not server_game.multiple_powers_per_player:
            # Request sender already controls some powers but game does not allow multiple powers per player.
            raise exceptions.ResponseException('Disallowed multiple powers per player.')

        if server_game.has_expected_controls_count():
            # Allowed number of players is already reached for this game.
            raise exceptions.ResponseException(
                'Reached maximum number of allowed controlled powers for this game (%d).'
                % server_game.get_expected_controls_count())

    # Join user to each queried dummy power.
    for power_name in required_dummy_powers:
        server_game.control(power_name, username, token)

    # Notify game about new powers controllers.

    Notifier(server).notify_game_powers_controllers(server_game)

    # Start game if it can start.
    if server_game.game_can_start():
        server.start_game(server_game)

    # Require game disk backup.
    server.save_game(server_game)

def on_leave_game(server, request, connection_handler):
    """ Manage request LeaveGame.
        If user is an (omniscient) observer, stop observation.
        Else, stop to control given power name.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: None
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.LeaveGame
    """
    level = verify_request(server, request, connection_handler, require_master=False)
    if level.is_power():
        level.game.set_controlled(level.power_name, None)
        Notifier(server, ignore_addresses=[request.address_in_game]).notify_game_powers_controllers(level.game)
        server.stop_game_if_needed(level.game)
    else:
        level.game.remove_special_token(request.game_role, request.token)
    server.save_game(level.game)

def on_list_games(server, request, connection_handler):
    """ Manage request ListGames.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: an instance of responses.DataGames
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.ListGames
    """
    verify_request(server, request, connection_handler)
    if request.map_name is not None and server.get_map(request.map_name) is None:
        raise exceptions.MapIdException()
    selected_game_indices = []
    for game_id in server.get_game_indices():
        if request.game_id and not (game_id.lower() in request.game_id.lower()
                                    or request.game_id.lower() in game_id.lower()):
            continue
        server_game = server.load_game(game_id)
        if request.for_omniscience and not server.token_is_omniscient(request.token, server_game):
            continue
        if not request.include_protected and server_game.registration_password is not None:
            continue
        if request.status and server_game.status != request.status:
            continue
        if request.map_name and server_game.map_name != request.map_name:
            continue
        username = server.users.get_name(request.token)
        selected_game_indices.append(responses.DataGameInfo(
            game_id=server_game.game_id,
            phase=server_game.current_short_phase,
            timestamp=server_game.get_latest_timestamp(),
            timestamp_created=server_game.timestamp_created,
            map_name=server_game.map_name,
            observer_level=server_game.get_observer_level(username),
            controlled_powers=server_game.get_controlled_power_names(username),
            rules=server_game.rules,
            status=server_game.status,
            n_players=server_game.count_controlled_powers(),
            n_controls=server_game.get_expected_controls_count(),
            deadline=server_game.deadline,
            registration_password=bool(server_game.registration_password)
        ))
    return responses.DataGames(data=selected_game_indices, request_id=request.request_id)

def on_logout(server, request, connection_handler):
    """ Manage request Logout.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: None
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.Logout
    """
    verify_request(server, request, connection_handler)
    server.remove_token(request.token)

def on_process_game(server, request, connection_handler):
    """ Manage request ProcessGame. Force a game to be processed the sooner.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: None
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.ProcessGame
    """
    level = verify_request(server, request, connection_handler, observer_role=False, power_role=False)
    assert_game_not_finished(level.game)
    for power_name in level.game.get_map_power_names():
        # Force power to not wait and tag it as if it has orders.
        # (this is valid only for this processing and will be reset for next phase).
        power = level.game.get_power(power_name)
        power.order_is_set = OrderSettings.ORDER_SET
        power.wait = False
    if level.game.status == strings.FORMING:
        level.game.set_status(strings.ACTIVE)
    server.force_game_processing(level.game)

@gen.coroutine
def on_query_schedule(server, request, connection_handler):
    """ Manage request QuerySchedule.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: None
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.QuerySchedule
    """
    level = verify_request(server, request, connection_handler, require_master=False)
    schedule_event = yield server.games_scheduler.get_info(level.game)
    if not schedule_event:
        raise exceptions.ResponseException('Game not scheduled.')
    return responses.DataGameSchedule(
        game_id=level.game.game_id,
        phase=level.game.current_short_phase,
        schedule=schedule_event,
        request_id=request.request_id
    )

def on_save_game(server, request, connection_handler):
    """ Manage request SaveGame

        :param server: server which receives the request
        :param request: request to manage
        :param connection_handler: connection handler from which the request was sent
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.SaveGame
    """
    level = verify_request(server, request, connection_handler, require_master=False)
    game_json = export.to_saved_game_format(level.game)
    return responses.DataSavedGame(data=game_json, request_id=request.request_id)

def on_send_game_message(server, request, connection_handler):
    """ Manage request SendGameMessage.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: None
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.SendGameMessage
    """
    level = verify_request(server, request, connection_handler, omniscient_role=False, observer_role=False)
    token, message = request.token, request.message
    assert_game_not_finished(level.game)
    if level.game.no_press:
        raise exceptions.ResponseException('Messages not allowed for this game.')
    if request.game_role != message.sender:
        raise exceptions.ResponseException('A power can only send its own messages.')

    if not level.game.has_power(message.sender):
        raise exceptions.MapPowerException(message.sender)
    if not request.message.is_global():
        if level.game.public_press:
            raise exceptions.ResponseException('Only public messages allowed for this game.')
        if not level.game.is_game_active:
            raise exceptions.GameNotPlayingException()
        if level.game.current_short_phase != message.phase:
            raise exceptions.GamePhaseException(level.game.current_short_phase, message.phase)
        if not level.game.has_power(message.recipient):
            raise exceptions.MapPowerException(message.recipient)
        username = server.users.get_name(token)
        power_name = message.sender
        if not level.game.is_controlled_by(power_name, username):
            raise exceptions.ResponseException('Power name %s is not controlled by given username.' % power_name)
        if message.sender == message.recipient:
            raise exceptions.ResponseException('A power cannot send message to itself.')

    if request.re_sent:
        # Request is re-sent (e.g. after a synchronization). We may have already received this message.
        # lookup message. WARNING: This may take time if there are many messages. How to improve that ?
        for archived_message in level.game.messages.reversed_values():
            if (archived_message.sender == message.sender
                    and archived_message.recipient == message.recipient
                    and archived_message.phase == message.phase
                    and archived_message.message == message.message):
                # Message found. Send archived time_sent, don't notify anyone.
                LOGGER.warning('Game message re-sent.')
                return responses.DataTimeStamp(data=archived_message.time_sent, request_id=request.request_id)
        # If message not found, consider it as a new message.
    if message.time_sent is not None:
        raise exceptions.ResponseException('Server cannot receive a message with a time sent already set.')
    message.time_sent = level.game.add_message(message)
    Notifier(server, ignore_addresses=[(request.game_role, token)]).notify_game_message(level.game, message)
    server.save_game(level.game)
    return responses.DataTimeStamp(data=message.time_sent, request_id=request.request_id)

def on_set_dummy_powers(server, request, connection_handler):
    """ Manage request SetDummyPowers.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: None
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.SetDummyPowers
    """
    level = verify_request(server, request, connection_handler, observer_role=False, power_role=False)
    assert_game_not_finished(level.game)
    username, power_names = request.username, request.power_names
    if username is not None and not server.users.has_username(username):
        raise exceptions.UserException()
    if power_names:
        power_names = [power_name for power_name in power_names if level.game.has_power(power_name)]
    else:
        power_names = list(level.game.get_map_power_names())
    if username is not None:
        power_names = [power_name for power_name in power_names
                       if level.game.is_controlled_by(power_name, username)]
    count_before = level.game.count_controlled_powers()
    level.game.update_dummy_powers(power_names)
    if count_before != level.game.count_controlled_powers():
        server.stop_game_if_needed(level.game)
        Notifier(server).notify_game_powers_controllers(level.game)
        server.save_game(level.game)

def on_set_game_state(server, request, connection_handler):
    """ Manage request SetGameState.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: None
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.SetGameState
    """
    level = verify_request(server, request, connection_handler, observer_role=False, power_role=False)
    level.game.set_phase_data(GamePhaseData(
        request.phase, request.state, request.orders, request.results, request.messages))
    server.stop_game_if_needed(level.game)
    Notifier(server, ignore_addresses=[request.address_in_game]).notify_game_phase_data(level.game)
    server.save_game(level.game)

def on_set_game_status(server, request, connection_handler):
    """ Manage request SetGameStatus.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: None
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.SetGameStatus
    """
    level = verify_request(server, request, connection_handler, observer_role=False, power_role=False)
    status = request.status
    previous_status = level.game.status
    if previous_status != status:
        if previous_status == strings.CANCELED:
            raise exceptions.GameCanceledException()
        if previous_status == strings.COMPLETED:
            raise exceptions.GameFinishedException()
        level.game.set_status(status)
        if status == strings.COMPLETED:
            phase_data_before_draw, phase_data_after_draw = level.game.draw()
            server.unschedule_game(level.game)
            Notifier(server).notify_game_processed(level.game, phase_data_before_draw, phase_data_after_draw)
        else:
            if status == strings.ACTIVE:
                server.schedule_game(level.game)
            elif status == strings.PAUSED:
                server.unschedule_game(level.game)
            elif status == strings.CANCELED:
                server.unschedule_game(level.game)
                if server.remove_canceled_games:
                    server.delete_game(level.game)
            Notifier(server, ignore_addresses=[request.address_in_game]).notify_game_status(level.game)
        server.save_game(level.game)

def on_set_grade(server, request, connection_handler):
    """ Manage request SetGrade.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: None
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.SetGrade
    """

    # Check request token.
    verify_request(server, request, connection_handler)
    token, grade, grade_update, username, game_id = (
        request.token, request.grade, request.grade_update, request.username, request.game_id)

    to_save = False

    if grade == strings.ADMIN:

        # Requested admin grade update.

        # Check if request token is admin.
        server.assert_admin_token(token)

        # Promote username to administrator only if not already admin.
        # Demote username from administration only if already admin.
        if grade_update == strings.PROMOTE:
            if not server.users.has_admin(username):
                server.users.add_admin(username)
                to_save = True
        elif server.users.has_admin(username):
            server.users.remove_admin(username)
            to_save = True

        if to_save:

            # Require server data disk backup.
            server.save_data()

            # Update each loaded games where user was connected as observer or omniscient
            # without explicitly allowed to be moderator or omniscient. This means its
            # observer role has changed (observer -> omniscient or vice versa) in related games.
            for server_game in server.games.values():  # type: ServerGame

                # We check games where user is not explicitly allowed to be moderator or omniscient.
                if not server_game.is_moderator(username) and not server_game.is_omniscient(username):
                    transfer_special_tokens(server_game, server, username, grade_update,
                                            grade_update == strings.PROMOTE)

    else:
        # Requested omniscient or moderator grade update for a specific game.

        # Get related game.
        server_game = server.get_game(game_id)

        # Check if request sender is a game master.
        server.assert_master_token(token, server_game)

        # We must check if grade update changes omniscient rights for user.
        # Reminder: a user is omniscient if either server admin, game moderator or game explicit omniscient.
        # So, even if moderator or explicit omniscient grade is updated for user, his omniscient rights
        # may not change.
        user_is_omniscient_before = server.user_is_omniscient(username, server_game)

        if grade == strings.OMNISCIENT:

            # Promote explicitly user to omniscient only if not already explicit omniscient.
            # Demote explicitly user from omniscience only if already explicit omniscient.

            if grade_update == strings.PROMOTE:
                if not server_game.is_omniscient(username):
                    server_game.promote_omniscient(username)
                    to_save = True
            elif server_game.is_omniscient(username):
                server_game.demote_omniscient(username)
                to_save = True
        else:

            # Promote user to moderator if not already moderator.
            # Demote user from moderation if already moderator.

            if grade_update == strings.PROMOTE:
                if not server_game.is_moderator(username):
                    server_game.promote_moderator(username)
                    to_save = True
            elif server_game.is_moderator(username):
                server_game.demote_moderator(username)
                to_save = True

        if to_save:

            # Require game disk backup.
            server.save_game(server_game)

            # Check if user omniscient rights was changed.
            user_is_omniscient_after = server.user_is_omniscient(username, server_game)
            if user_is_omniscient_before != user_is_omniscient_after:
                transfer_special_tokens(server_game, server, username, grade_update, user_is_omniscient_after)

def on_set_orders(server, request, connection_handler):
    """ Manage request SetOrders.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: None
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.SetOrders
    """
    level = verify_request(server, request, connection_handler, observer_role=False, require_power=True)
    assert_game_not_finished(level.game)
    if not request.phase or request.phase != level.game.current_short_phase:
        raise exceptions.ResponseException(
            'Invalid order phase, received %s, server phase is %s' % (request.phase, level.game.current_short_phase))
    power = level.game.get_power(level.power_name)
    previous_wait = power.wait
    power.clear_orders()
    power.wait = previous_wait
    level.game.set_orders(level.power_name, request.orders)
    # Notify other power tokens.
    Notifier(server, ignore_addresses=[request.address_in_game]).notify_power_orders_update(
        level.game, level.game.get_power(level.power_name), request.orders)
    if request.wait is not None:
        level.game.set_wait(level.power_name, request.wait)
        Notifier(server, ignore_addresses=[request.address_in_game]).notify_power_wait_flag(
            level.game, level.game.get_power(level.power_name), request.wait)
    if level.game.does_not_wait():
        server.force_game_processing(level.game)
    server.save_game(level.game)

def on_set_wait_flag(server, request, connection_handler):
    """ Manage request SetWaitFlag.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: None
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.SetWaitFlag
    """
    level = verify_request(server, request, connection_handler, observer_role=False, require_power=True)
    assert_game_not_finished(level.game)
    level.game.set_wait(level.power_name, request.wait)
    # Notify other power tokens.
    Notifier(server, ignore_addresses=[request.address_in_game]).notify_power_wait_flag(
        level.game, level.game.get_power(level.power_name), request.wait)
    if level.game.does_not_wait():
        server.force_game_processing(level.game)
    server.save_game(level.game)

def on_sign_in(server, request, connection_handler):
    """ Manage request SignIn.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: None
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.SignIn
    """
    # No channel/game request verification to do.
    username, password = request.username, request.password

    if not username:
        raise exceptions.UserException()
    if not password:
        raise exceptions.PasswordException()

    # New user
    if not server.users.has_username(username):
        if not server.allow_registrations:
            raise exceptions.ServerRegistrationException()
        server.users.add_user(username, hash_password(password))

    # Existing user
    elif not server.users.has_user(username, password):
        raise exceptions.UserException()

    token = server.users.connect_user(username, connection_handler)
    server.save_data()
    return responses.DataToken(data=token, request_id=request.request_id)

def on_synchronize(server, request, connection_handler):
    """ Manage request Synchronize.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: None
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.Synchronize
    """

    level = verify_request(server, request, connection_handler, require_master=False)

    # Get sync data.

    timestamp = request.timestamp
    if request.game_role == strings.OBSERVER_TYPE:
        assert level.game.has_observer_token(request.token)
    elif request.game_role == strings.OMNISCIENT_TYPE:
        assert level.game.has_omniscient_token(request.token)
    elif not level.game.power_has_token(request.game_role, request.token):
        raise exceptions.GamePlayerException()
    messages = level.game.get_messages(request.game_role, timestamp + 1)
    if level.is_power():
        # Don't notify a power about messages she sent herself.
        messages = {message.time_sent: message for message in messages.values()
                    if message.sender != level.power_name}
    phase_data_list = level.game.phase_history_from_timestamp(timestamp + 1)
    current_phase_data = None
    if phase_data_list:
        # If there is no new state history, then current state should have not changed
        # and does not need to be sent. Otherwise current state is a new state
        # got after a processing, and must be sent.
        current_phase_data = level.game.get_phase_data()
    data_to_send = [SynchronizedData(message.time_sent, 0, 'message', message) for message in messages.values()]
    data_to_send += [SynchronizedData(phase_data.state['timestamp'], 1, 'state_history', phase_data)
                     for phase_data in phase_data_list]
    if current_phase_data:
        data_to_send.append(SynchronizedData(current_phase_data.state['timestamp'], 2, 'phase', current_phase_data))
    data_to_send.sort(key=lambda x: (x.timestamp, x.order))

    # Send sync data.

    notifier = Notifier(server)
    if strings.role_is_special(request.game_role):
        addresses = [request.address_in_game]
    else:
        addresses = list(level.game.get_power_addresses(request.game_role))

    for data in data_to_send:
        if data.type == 'message':
            notifier.notify_game_addresses(
                level.game.game_id, addresses, notifications.GameMessageReceived, message=data.data)
        else:
            if data.type not in ('state_history', 'phase'):
                raise AssertionError('Unknown synchronized data.')
            phase_data = level.game.filter_phase_data(data.data, request.game_role, is_current=(data.type == 'phase'))
            notifier.notify_game_addresses(level.game.game_id, addresses, notifications.GamePhaseUpdate,
                                           phase_data=phase_data, phase_data_type=data.type)
    # Send game status.
    notifier.notify_game_addresses(level.game.game_id, addresses, notifications.GameStatusUpdate,
                                   status=level.game.status)
    return responses.DataGameInfo(game_id=level.game.game_id,
                                  phase=level.game.current_short_phase,
                                  timestamp=level.game.get_latest_timestamp(),
                                  timestamp_created=level.game.timestamp_created,
                                  request_id=request.request_id)

def on_unknown_token(server, request, connection_handler):
    """ Manage notification request UnknownToken.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: NoResponse. No responses are sent back to the server
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.UnknownToken
    """
    del connection_handler                  # Unused - Not sending any responses back
    LOGGER.debug('Removing token %s', request.token)
    if server.users.has_token(request.token):
        server.remove_token(request.token)
    return responses.NoResponse()

def on_vote(server, request, connection_handler):
    """ Manage request Vote.

        :param server: server which receives the request.
        :param request: request to manage.
        :param connection_handler: connection handler from which the request was sent.
        :return: None
        :type server: diplomacy.Server
        :type request: diplomacy.communication.requests.Vote
    """
    level = verify_request(server, request, connection_handler,
                           omniscient_role=False, observer_role=False, require_power=True)
    assert_game_not_finished(level.game)
    power = level.game.get_power(level.power_name)
    if power.is_eliminated():
        raise exceptions.ResponseException('Power %s is eliminated.' % power.name)
    if not power.is_controlled_by(server.users.get_name(request.token)):
        raise exceptions.GamePlayerException()
    power.vote = request.vote
    Notifier(server).notify_game_vote_updated(level.game)
    if level.game.has_draw_vote():
        # Votes allows to draw the game.
        phase_data_before_draw, phase_data_after_draw = level.game.draw()
        server.unschedule_game(level.game)
        Notifier(server).notify_game_processed(level.game, phase_data_before_draw, phase_data_after_draw)
    server.save_game(level.game)


# Mapping dictionary from request class to request handler function.
MAPPING = {
    requests.ClearCenters: on_clear_centers,
    requests.ClearOrders: on_clear_orders,
    requests.ClearUnits: on_clear_units,
    requests.CreateGame: on_create_game,
    requests.DeleteAccount: on_delete_account,
    requests.DeleteGame: on_delete_game,
    requests.GetAllPossibleOrders: on_get_all_possible_orders,
    requests.GetAvailableMaps: on_get_available_maps,
    requests.GetDaidePort: on_get_daide_port,
    requests.GetDummyWaitingPowers: on_get_dummy_waiting_powers,
    requests.GetGamesInfo: on_get_games_info,
    requests.GetPhaseHistory: on_get_phase_history,
    requests.GetPlayablePowers: on_get_playable_powers,
    requests.JoinGame: on_join_game,
    requests.JoinPowers: on_join_powers,
    requests.LeaveGame: on_leave_game,
    requests.ListGames: on_list_games,
    requests.Logout: on_logout,
    requests.ProcessGame: on_process_game,
    requests.QuerySchedule: on_query_schedule,
    requests.SaveGame: on_save_game,
    requests.SendGameMessage: on_send_game_message,
    requests.SetDummyPowers: on_set_dummy_powers,
    requests.SetGameState: on_set_game_state,
    requests.SetGameStatus: on_set_game_status,
    requests.SetGrade: on_set_grade,
    requests.SetOrders: on_set_orders,
    requests.SetWaitFlag: on_set_wait_flag,
    requests.SignIn: on_sign_in,
    requests.Synchronize: on_synchronize,
    requests.UnknownToken: on_unknown_token,
    requests.Vote: on_vote,
}

def handle_request(server, request, connection_handler):
    """ (coroutine) Find request handler function for associated request, run it and return its result.

        :param server: a Server object to pass to handler function.
        :param request: a request object to pass to handler function.
            See diplomacy.communication.requests for possible requests.
        :param connection_handler: a ConnectionHandler object to pass to handler function.
        :return: (future) either None or a response object.
            See module diplomacy.communication.responses for possible responses.
    """
    request_handler_fn = MAPPING.get(type(request), None)
    if not request_handler_fn:
        raise exceptions.RequestException()
    if gen.is_coroutine_function(request_handler_fn):
        # Throw the future returned by this coroutine.
        return request_handler_fn(server, request, connection_handler)
    # Create and return a future.
    future = Future()
    try:
        result = request_handler_fn(server, request, connection_handler)
        future.set_result(result)
    except exceptions.DiplomacyException as exc:
        future.set_exception(exc)
    return future
