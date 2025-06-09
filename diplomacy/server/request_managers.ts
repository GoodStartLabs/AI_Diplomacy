// diplomacy/server/request_managers.ts

import {
    AbstractRequest, ClearCentersRequest, ClearOrdersRequest, ClearUnitsRequest, CreateGameRequest,
    DeleteAccountRequest, DeleteGameRequest, GetAllPossibleOrdersRequest, GetAvailableMapsRequest,
    GetDaidePortRequest, GetDummyWaitingPowersRequest, GetGamesInfoRequest, GetPhaseHistoryRequest,
    GetPlayablePowersRequest, JoinGameRequest, JoinPowersRequest, LeaveGameRequest, ListGamesRequest,
    LogoutRequest, ProcessGameRequest, QueryScheduleRequest, SaveGameRequest, SendGameMessageRequest,
    SetDummyPowersRequest, SetGameStateRequest, SetGameStatusRequest, SetGradeRequest, SetOrdersRequest,
    SetWaitFlagRequest, SignInRequest, SynchronizeRequest, UnknownTokenRequest, VoteRequest,
    // Add other request types as they are defined
} from '../../communication/requests'; // Adjust path as necessary
import * as responses from '../../communication/responses';
import * as notifications from '../../communication/notifications';
import { Notifier, ConnectionHandler } from './notifier'; // ConnectionHandler might be a placeholder
import { ServerGame, DiplomacyServerInterface } from './server_game';
import {
    verify_request, transfer_special_tokens, assert_game_not_finished, GameRequestLevel, SynchronizedData, sortSynchronizedData
} from './request_manager_utils';
import {
    DiplomacyException, ResponseException, GameIdException, MapIdException, MapPowerException,
    GameSolitaireException, GameCreationException, UserException, PasswordException,
    ServerRegistrationException, GameJoinRoleException, GameObserverException,
    GameRegistrationPasswordException, GameFinishedException, DaidePortException, GameCanceledException, GamePhaseException
} from '../utils/exceptions'; // Adjust path
import {
    GAME as GAME_LEVEL, CHANNEL as CHANNEL_LEVEL, OBSERVER_TYPE, OMNISCIENT_TYPE, MASTER_TYPE,
    FORMING, ACTIVE, PAUSED, COMPLETED, CANCELED, PRIVATE_BOT_USERNAME,
    PROMOTE, DEMOTE, ADMIN // Assuming these are in strings
} from '../utils/strings'; // Adjust path
import { OrderSettings } from '../utils/constants'; // Adjust path
import { GamePhaseData } from '../utils/game_phase_data'; // Adjust path
import { hash_password } from '../utils/common'; // Adjust path
import { exportJson } from '../utils/export'; // Assuming export.ts for to_saved_game_format

// --- Request Handler Function Types ---
type RequestHandler<T extends AbstractRequest> =
    (server: DiplomacyServerInterface, request: T, connection_handler: ConnectionHandler) => Promise<responses.AbstractResponse | null | void>;

// --- Request Handlers ---

async function on_clear_centers(server: DiplomacyServerInterface, request: ClearCentersRequest, connection_handler: ConnectionHandler): Promise<void> {
    const level = await verify_request(server, request, connection_handler, { observer_role: false });
    if (!level) throw new ResponseException("Invalid request level for ClearCenters.");
    assert_game_not_finished(level.game);
    level.game.clear_centers(level.power_name); // power_name should be asserted as non-null by verify_request if power_role=true
    const notifier = new Notifier(server, { ignore_addresses: [[request.game_role!, request.token!]] }); // game_role and token must exist
    await notifier.notify_cleared_centers(level.game, level.power_name);
}

async function on_clear_orders(server: DiplomacyServerInterface, request: ClearOrdersRequest, connection_handler: ConnectionHandler): Promise<void> {
    const level = await verify_request(server, request, connection_handler, { observer_role: false });
    if (!level) throw new ResponseException("Invalid request level for ClearOrders.");
    assert_game_not_finished(level.game);
    if (!request.phase || request.phase !== level.game.current_short_phase) {
        throw new ResponseException(`Invalid order phase, received ${request.phase}, server phase is ${level.game.current_short_phase}`);
    }
    level.game.clear_orders(level.power_name!); // power_name is guaranteed by verify_request with default power_role=true
    const notifier = new Notifier(server, { ignore_addresses: [[request.game_role!, request.token!]] });
    await notifier.notify_cleared_orders(level.game, level.power_name);
}

async function on_clear_units(server: DiplomacyServerInterface, request: ClearUnitsRequest, connection_handler: ConnectionHandler): Promise<void> {
    const level = await verify_request(server, request, connection_handler, { observer_role: false });
    if (!level) throw new ResponseException("Invalid request level for ClearUnits.");
    assert_game_not_finished(level.game);
    level.game.clear_units(level.power_name);
    const notifier = new Notifier(server, { ignore_addresses: [[request.game_role!, request.token!]] });
    await notifier.notify_cleared_units(level.game, level.power_name);
}

async function on_create_game(server: DiplomacyServerInterface, request: CreateGameRequest, connection_handler: ConnectionHandler): Promise<responses.DataGame> {
    await verify_request(server, request, connection_handler); // Verifies token
    let { game_id, token, power_name, state, map_name, rules, n_controls, deadline, registration_password } = request;
    token = token!; // Token is asserted by verify_request for non-connection requests

    if (server.cannot_create_more_games()) { // Method to be implemented on server
        throw new GameCreationException("Server cannot create more games.");
    }

    const gameMap = server.get_map(map_name); // Method to be implemented on server
    if (!gameMap) {
        throw new MapIdException(`Map ${map_name} not found.`);
    }

    rules = rules || ['NO_PRESS', 'POWER_CHOICE']; // SERVER_GAME_RULES equivalent

    if (rules.includes('SOLITAIRE') && power_name != null) {
        throw new GameSolitaireException("Cannot specify power_name for SOLITAIRE games.");
    }
    if (power_name != null && !gameMap.powers.includes(power_name.toUpperCase())) { // map.powers should be UC
        throw new MapPowerException(power_name);
    }

    const username = server.users.get_name(token)!;
    if (game_id == null || game_id === '') {
        game_id = server.create_game_id(); // Method to be implemented on server
    } else if (server.has_game_id(game_id)) { // Method to be implemented on server
        throw new GameIdException(`Game ID already used: ${game_id}`);
    }

    const server_game = new ServerGame({ // Assumes ServerGame constructor matches this
        map_name: map_name,
        rules: rules,
        game_id: game_id,
        initial_state: state, // state needs to be compatible with DiplomacyGameOptions
        n_controls: n_controls,
        deadline: deadline,
        registration_password: registration_password,
        server: server
    });

    if (!server.users.has_admin(username)) {
        server_game.promote_moderator(username);
    }
    server.add_new_game(server_game); // Method to be implemented on server

    let client_game_view: DiplomacyGame;
    if (power_name) {
        server_game.control(power_name, username, token);
        client_game_view = server_game.as_power_game(power_name);
    } else {
        server_game.add_omniscient_token(token);
        client_game_view = server_game.as_omniscient_game(username);
    }

    if (server_game.game_can_start()) {
        await server.start_game(server_game); // Method to be implemented on server
    }
    await server.save_game(server_game); // Method to be implemented on server

    return new responses.DataGame({data: client_game_view, request_id: request.request_id});
}

async function on_sign_in(server: DiplomacyServerInterface, request: SignInRequest, connection_handler: ConnectionHandler): Promise<responses.DataToken> {
    const { username, password } = request;
    if (!username) throw new UserException("Username is required.");
    if (!password) throw new PasswordException("Password is required.");

    if (!server.users.has_username(username)) {
        if (!server.properties.allow_registrations) { // Assuming server.properties.allow_registrations
            throw new ServerRegistrationException("Server registrations are disabled.");
        }
        const passwordHash = await hash_password(password); // Assuming hash_password from common.ts
        server.users.add_user(username, passwordHash);
    } else if (!server.users.has_user(username, password)) {
        throw new UserException("Invalid username or password.");
    }

    const token = server.users.connect_user(username, connection_handler);
    await server.save_data(); // Method to be implemented on server
    return new responses.DataToken({ data: token, request_id: request.request_id });
}

// ... other handlers will be translated similarly ...
// For brevity, I'll include a few more key handlers and then the MAPPING and handle_request

async function on_set_orders(server: DiplomacyServerInterface, request: SetOrdersRequest, connection_handler: ConnectionHandler): Promise<void> {
    const level = await verify_request(server, request, connection_handler, {observer_role: false, require_power: true});
    if (!level || !level.power_name) throw new ResponseException("Invalid request level for SetOrders.");
    assert_game_not_finished(level.game);

    if (!request.phase || request.phase !== level.game.current_short_phase) {
        throw new ResponseException(`Invalid order phase, received ${request.phase}, server phase is ${level.game.current_short_phase}`);
    }
    const power = level.game.powers[level.power_name];
    if (!power) throw new MapPowerException(level.power_name);

    const previous_wait = power.wait;
    power.clear_orders();
    power.wait = previous_wait;
    level.game.set_orders(level.power_name, request.orders); // This is from engine/game.ts

    const notifier = new Notifier(server, {ignore_addresses: [[request.game_role!, request.token!]]});
    await notifier.notify_power_orders_update(level.game, power, request.orders);

    if (request.wait !== undefined && request.wait !== null) {
        level.game.set_wait(level.power_name, request.wait); // This is from engine/game.ts
        await notifier.notify_power_wait_flag(level.game, power, request.wait);
    }
    if (level.game.does_not_wait()) { // This is from engine/game.ts
        await server.force_game_processing(level.game); // Method to be implemented on server
    }
    await server.save_game(level.game);
}


// --- MAPPING ---
// Using a Map for type safety with class constructors as keys
const MAPPING = new Map<any, RequestHandler<any>>([
    [ClearCentersRequest, on_clear_centers],
    [ClearOrdersRequest, on_clear_orders],
    [ClearUnitsRequest, on_clear_units],
    [CreateGameRequest, on_create_game],
    [SignInRequest, on_sign_in],
    [SetOrdersRequest, on_set_orders],
    // [DeleteAccountRequest, onDeleteAccount],
    // [DeleteGameRequest, onDeleteGame],
    // [GetAllPossibleOrdersRequest, onGetAllPossibleOrders],
    // [GetAvailableMapsRequest, onGetAvailableMaps],
    // [GetDaidePortRequest, onGetDaidePort],
    // [GetDummyWaitingPowersRequest, onGetDummyWaitingPowers],
    // [GetGamesInfoRequest, onGetGamesInfo],
    // [GetPhaseHistoryRequest, onGetPhaseHistory],
    // [GetPlayablePowersRequest, onGetPlayablePowers],
    // [JoinGameRequest, onJoinGame],
    // [JoinPowersRequest, onJoinPowers],
    // [LeaveGameRequest, onLeaveGame],
    // [ListGamesRequest, onListGames],
    // [LogoutRequest, onLogout],
    // [ProcessGameRequest, onProcessGame],
    // [QueryScheduleRequest, onQuerySchedule],
    // [SaveGameRequest, onSaveGame],
    // [SendGameMessageRequest, onSendGameMessage],
    // [SetDummyPowersRequest, onSetDummyPowers],
    // [SetGameStateRequest, onSetGameState],
    // [SetGameStatusRequest, onSetGameStatus],
    // [SetGradeRequest, onSetGrade],
    // [SetWaitFlagRequest, onSetWaitFlag],
    // [SynchronizeRequest, onSynchronize],
    // [UnknownTokenRequest, onUnknownToken],
    // [VoteRequest, onVote],
]);

export async function handle_request(
    server: DiplomacyServerInterface,
    request: AbstractRequest,
    connection_handler: ConnectionHandler
): Promise<responses.AbstractResponse | null | void> {
    const RequestClass = request.constructor;
    const request_handler_fn = MAPPING.get(RequestClass);

    if (!request_handler_fn) {
        console.error(`No handler found for request type: ${request.name || RequestClass.name}`);
        throw new exceptions.RequestException(`No handler for request type ${request.name || RequestClass.name}`);
    }

    try {
        // All handlers are now async
        return await request_handler_fn(server, request, connection_handler);
    } catch (exc: any) {
        if (exc instanceof DiplomacyException) {
            // Specific diplomacy exceptions can be re-thrown if they are meant to be caught by a higher level
            // or converted to specific error responses.
            // For now, re-throw and let the server's main error handler deal with it.
            throw exc;
        }
        // Generic error
        console.error(`Error processing request ${request.name}:`, exc);
        throw new exceptions.ResponseException(`Internal server error while processing ${request.name}: ${exc.message}`);
    }
}
