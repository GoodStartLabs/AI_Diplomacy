// diplomacy/server/request_manager_utils.ts

import * as notifications from '../../communication/notifications';
import { Notifier } from './notifier';
import { ServerGame, DiplomacyServerInterface } from './server_game'; // Assuming DiplomacyServerInterface is defined here or centrally
import { User } from './user'; // May not be directly needed, but server.users will be of Users type
import { Users } from './users'; // For server.users type
import { ConnectionHandler } from './notifier'; // Using placeholder from notifier for now

import { GAME as GAME_LEVEL, CHANNEL as CHANNEL_LEVEL, OBSERVER_TYPE, OMNISCIENT_TYPE, MASTER_TYPE } from '../utils/strings';
import {
    DiplomacyException, ResponseException, GameTokenException, MapPowerException,
    GameMasterTokenException, GameFinishedException
} from '../utils/exceptions';
import { AbstractRequest, AbstractGameRequest } from '../../communication/requests'; // Assuming base request types

export interface SynchronizedData {
    timestamp: number;
    order: number; // 0 for message, 1 for state_history, 2 for current state
    type: 'message' | 'state_history' | 'state';
    data: any; // Message, GameState, etc.
}

// Static sort function for SynchronizedData if needed elsewhere
export function sortSynchronizedData(a: SynchronizedData, b: SynchronizedData): number {
    if (a.timestamp !== b.timestamp) {
        return a.timestamp - b.timestamp;
    }
    return a.order - b.order;
}

export type ActionLevel = 'power' | 'observer' | 'omniscient' | 'master';

export class GameRequestLevel {
    public game: ServerGame;
    public power_name: string | null; // Name of the power the request pertains to, if any
    private __action_level: ActionLevel;

    constructor(game: ServerGame, action_level: ActionLevel, power_name: string | null = null) {
        this.game = game;
        this.__action_level = action_level;
        this.power_name = power_name;
    }

    public is_power(): boolean { return this.__action_level === 'power'; }
    public is_observer(): boolean { return this.__action_level === 'observer'; }
    public is_omniscient(): boolean { return this.__action_level === 'omniscient'; }
    public is_master(): boolean { return this.__action_level === 'master'; }
    public get action_level(): ActionLevel { return this.__action_level; }


    public static power_level(game: ServerGame, power_name: string): GameRequestLevel {
        return new GameRequestLevel(game, 'power', power_name);
    }
    public static observer_level(game: ServerGame, power_name: string | null = null): GameRequestLevel {
        return new GameRequestLevel(game, 'observer', power_name);
    }
    public static omniscient_level(game: ServerGame, power_name: string | null = null): GameRequestLevel {
        return new GameRequestLevel(game, 'omniscient', power_name);
    }
    public static master_level(game: ServerGame, power_name: string | null = null): GameRequestLevel {
        return new GameRequestLevel(game, 'master', power_name);
    }
}

/**
 * Verifies request token, game role, and rights.
 * Returns a GameRequestLevel for game requests, else null.
 */
export async function verify_request(
    server: DiplomacyServerInterface, // Server object should have users, get_game, assert_token methods
    request: AbstractRequest,       // Base request type
    connection_handler: ConnectionHandler, // Placeholder
    omniscient_role: boolean = true,
    observer_role: boolean = true,
    power_role: boolean = true,
    require_power: boolean = false,
    require_master: boolean = true
): Promise<GameRequestLevel | null> {

    if (!request.level) { // Connection requests like SignIn
        return null;
    }

    // Check token for channel and game requests.
    // server.assert_token would throw if invalid.
    // Assuming assert_token is part of the DiplomacyServerInterface or its Users object
    (server.users as Users).relaunch_token(request.token!); // Relaunch before check (Python version does this in assert_token)
    if (!(server.users as Users).token_is_alive(request.token!)) {
        (server.users as Users).disconnect_token(request.token!); // Disconnect if expired
        throw new GameTokenException('Token has expired or is invalid.');
    }
    // Associate connection handler if not already (Python's assert_token might do this)
    (server.users as Users).attach_connection_handler(request.token!, connection_handler);


    if (request.level !== GAME_LEVEL) { // Not a game-specific request (e.g. CHANNEL_LEVEL)
        return null;
    }

    // It's a game request, so it should conform to AbstractGameRequest
    const gameRequest = request as AbstractGameRequest;
    if (gameRequest.game_id === undefined || gameRequest.game_role === undefined) {
        throw new ResponseException("Game request missing game_id or game_role.");
    }

    const server_game = server.get_game(String(gameRequest.game_id)); // get_game should handle string ID
    if (!server_game) {
        throw new ResponseException(`Game ${gameRequest.game_id} not found.`);
    }

    const power_name_from_request = gameRequest.power_name || null; // Optional in request

    if (gameRequest.game_role === OMNISCIENT_TYPE || gameRequest.game_role === OBSERVER_TYPE) {
        if (gameRequest.game_role === OMNISCIENT_TYPE) {
            if (!omniscient_role) throw new ResponseException(`Omniscient role disallowed for request ${request.name}`);
            if (!server_game.has_omniscient_token(request.token!)) throw new GameTokenException('Token is not an omniscient token for this game.');

            const token_is_master = (server.users as Users).token_is_admin(request.token!) || server_game.is_moderator((server.users as Users).get_name(request.token!)!);
            if (require_master && !token_is_master) throw new GameMasterTokenException();
            return token_is_master ?
                GameRequestLevel.master_level(server_game, power_name_from_request) :
                GameRequestLevel.omniscient_level(server_game, power_name_from_request);
        } else { // OBSERVER_TYPE
            if (!observer_role) throw new ResponseException(`Observer role disallowed for request ${request.name}`);
            if (!server_game.has_observer_token(request.token!)) throw new GameTokenException('Token is not an observer token for this game.');
            return GameRequestLevel.observer_level(server_game, power_name_from_request);
        }

        // Check power_name validity if provided for observer/omniscient roles
        if (power_name_from_request && !server_game.powers[power_name_from_request]) {
            throw new MapPowerException(power_name_from_request);
        }
        if (require_power && !power_name_from_request){
             throw new MapPowerException(null); // Power name required but not given
        }

    } else { // Power role
        if (!power_role) throw new ResponseException(`Power role disallowed for request ${request.name}`);

        const target_power_name = power_name_from_request || gameRequest.game_role;
        if (!server_game.powers[target_power_name]) throw new MapPowerException(target_power_name);

        const username = (server.users as Users).get_name(request.token!);
        if (!username || !server_game.is_controlled_by(target_power_name, username)) {
            throw new ResponseException(`User ${username} does not control power ${target_power_name}.`);
        }
        return GameRequestLevel.power_level(server_game, target_power_name);
    }
    return null; // Should not be reached if logic is correct
}

export async function transfer_special_tokens(
    server_game: ServerGame,
    server: DiplomacyServerInterface, // Server object
    username: string,
    grade_update: string, // e.g. 'PROMOTE' or 'DEMOTE' from strings
    from_observation: boolean = true
): Promise<void> {
    const old_role = from_observation ? OBSERVER_TYPE : OMNISCIENT_TYPE;
    const new_role = from_observation ? OMNISCIENT_TYPE : OBSERVER_TYPE;
    const token_filter = from_observation ?
        (token: string) => server_game.has_observer_token(token) :
        (token: string) => server_game.has_omniscient_token(token);

    const userTokens = (server.users as Users).get_tokens(username);
    const connected_user_tokens: string[] = [];
    userTokens.forEach(user_token => {
        if (token_filter(user_token)) {
            connected_user_tokens.push(user_token);
        }
    });

    if (connected_user_tokens.length > 0) {
        for (const user_token of connected_user_tokens) {
            server_game.transfer_special_token(user_token); // Assuming this method exists on ServerGame
        }

        const addresses: Array<[string, string]> = connected_user_tokens.map(token => [old_role, token]);
        // Notifier needs to be instantiated or accessed via server
        // Assuming server has a notifier instance or Notifier can be newed up with server
        const notifier = new Notifier(server);
        await notifier.notify_game_addresses(
            server_game.game_id,
            addresses,
            notifications.OmniscientUpdated, // Ensure this notification type is defined
            {
                grade_update,
                game: server_game.cast(new_role, username) // cast returns a game view for the new role
            }
        );
    }
}

export function assert_game_not_finished(server_game: ServerGame): void {
    if (server_game.is_game_completed || server_game.is_game_canceled) { // is_game_canceled might need to be added to ServerGame
        throw new GameFinishedException("Game is finished or canceled.");
    }
}
