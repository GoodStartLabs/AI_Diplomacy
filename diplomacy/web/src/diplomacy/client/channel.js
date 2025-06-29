// ==============================================================================
// Copyright (C) 2019 - Philip Paquette, Steven Bocco
//
//  This program is free software: you can redistribute it and/or modify it under
//  the terms of the GNU Affero General Public License as published by the Free
//  Software Foundation, either version 3 of the License, or (at your option) any
//  later version.
//
//  This program is distributed in the hope that it will be useful, but WITHOUT
//  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
//  FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
//  details.
//
//  You should have received a copy of the GNU Affero General Public License along
//  with this program.  If not, see <https://www.gnu.org/licenses/>.
// ==============================================================================
import {STRINGS} from "../utils/strings";
import {UTILS} from "../utils/utils";
import {REQUESTS} from "../communication/requests";

/** Class Channel. **/
export class Channel {
    constructor(connection, username, token) {
        this.connection = connection;
        this.token = token;
        this.username = username;
        this.game_id_to_instances = {};
    }

    localJoinGame(joinParameters) {
        // Game ID must be known.
        if (this.game_id_to_instances.hasOwnProperty(joinParameters.game_id)) {
            // If there is a power name, we return associated power game.
            if (joinParameters.power_name)
                return this.game_id_to_instances[joinParameters.game_id].get(joinParameters.power_name);
            // Otherwise, we return current special game (if exists).
            return this.game_id_to_instances[joinParameters.game_id].getSpecial();
        }
        return null;
    }

    _req(name, forcedParameters, localChannelFunction, parameters, game) {
        /** Send a request object for given request name with (optional) given forced parameters..
         * If a local channel function is given, it will be used to try retrieving a data
         * locally instead of sending a request. If local channel function returns something, this value is returned.
         * Otherwise, normal procedure (request sending) is used. Local channel function would be called with
         * request parameters passed to channel request method.
         * **/
        parameters = Object.assign(parameters || {}, forcedParameters || {});
        const level = REQUESTS.getLevel(name);
        if (level === STRINGS.GAME) {
            if (!game)
                throw new Error('A game object is required to send a game request.');
            parameters.token = this.token;
            parameters.game_id = game.local.game_id;
            parameters.game_role = game.local.role;
            parameters.phase = game.local.phase;
        } else {
            if (game)
                throw new Error('A game object should not be provided for a non-game request.');
            if (level === STRINGS.CHANNEL)
                parameters.token = this.token;
        }
        if (localChannelFunction) {
            const localResult = localChannelFunction.apply(this, [parameters]);
            if (localResult)
                return localResult;
        }
        const request = REQUESTS.create(name, parameters);
        const future = this.connection.send(request, game);
        const timeoutID = setTimeout(function () {
            if (!future.done())
                future.setException('Timeout reached when trying to send a request ' + name + '/' + request.request_id + '.');
        }, UTILS.REQUEST_TIMEOUT_SECONDS * 1000);
        return future.promise().then((result) => {
            clearTimeout(timeoutID);
            return result;
        });
    }

    //// Public channel API.

    createGame(parameters) {
        return this._req('create_game', undefined, undefined, parameters, undefined);
    }

    getAvailableMaps(parameters) {
        return this._req('get_available_maps', undefined, undefined, parameters, undefined);
    }

    getPlayablePowers(parameters) {
        return this._req('get_playable_powers', undefined, undefined, parameters, undefined);
    }

    joinGame(parameters) {
        return this._req('join_game', null, this.localJoinGame, parameters, undefined);
    }

    listGames(parameters) {
        return this._req('list_games', undefined, undefined, parameters, undefined);
    }

    getGamesInfo(parameters) {
        return this._req('get_games_info', undefined, undefined, parameters, undefined);
    }

    // User account API.

    deleteAccount(parameters) {
        return this._req('delete_account', undefined, undefined, parameters, undefined);
    }

    logout(parameters) {
        return this._req('logout', undefined, undefined, parameters, undefined);
    }

    // Admin/moderator API.

    makeOmniscient(parameters) {
        return this._req('set_grade', {
            grade: STRINGS.OMNISCIENT,
            grade_update: STRINGS.PROMOTE
        }, undefined, parameters, undefined);
    }

    removeOmniscient(parameters) {
        return this._req('set_grade', {
            grade: STRINGS.OMNISCIENT,
            grade_update: STRINGS.DEMOTE
        }, undefined, parameters, undefined);
    }

    promoteAdministrator(parameters) {
        return this._req('set_grade', {
            grade: STRINGS.ADMIN,
            grade_update: STRINGS.PROMOTE
        }, undefined, parameters, undefined);
    }

    demoteAdministrator(parameters) {
        return this._req('set_grade', {
            grade: STRINGS.ADMIN,
            grade_update: STRINGS.DEMOTE
        }, undefined, parameters, undefined);
    }

    promoteModerator(parameters) {
        return this._req('set_grade', {
            grade: STRINGS.MODERATOR,
            grade_update: STRINGS.PROMOTE
        }, undefined, parameters, undefined);
    }

    demoteModerator(parameters) {
        return this._req('set_grade', {
            grade: STRINGS.MODERATOR,
            grade_update: STRINGS.DEMOTE
        }, undefined, parameters, undefined);
    }

    //// Public game API.

    getAllPossibleOrders(parameters, game) {
        return this._req('get_all_possible_orders', undefined, undefined, parameters, game);
    }

    getPhaseHistory(parameters, game) {
        return this._req('get_phase_history', undefined, undefined, parameters, game);
    }

    leaveGame(parameters, game) {
        return this._req('leave_game', undefined, undefined, parameters, game);
    }

    sendGameMessage(parameters, game) {
        return this._req('send_game_message', undefined, undefined, parameters, game);
    }

    setOrders(parameters, game) {
        return this._req('set_orders', undefined, undefined, parameters, game);
    }

    clearCenters(parameters, game) {
        return this._req('clear_centers', undefined, undefined, parameters, game);
    }

    clearOrders(parameters, game) {
        return this._req('clear_orders', undefined, undefined, parameters, game);
    }

    clearUnits(parameters, game) {
        return this._req('clear_units', undefined, undefined, parameters, game);
    }

    wait(parameters, game) {
        return this._req('set_wait_flag', {wait: true}, undefined, parameters, game);
    }

    noWait(parameters, game) {
        return this._req('set_wait_flag', {wait: false}, undefined, parameters, game);
    }

    vote(parameters, game) {
        return this._req('vote', undefined, undefined, parameters, game);
    }

    save(parameters, game) {
        return this._req('save_game', undefined, undefined, parameters, game);
    }

    synchronize(parameters, game) {
        return this._req('synchronize', undefined, undefined, parameters, game);
    }

    // Admin/moderator game API.

    deleteGame(parameters, game) {
        return this._req('delete_game', undefined, undefined, parameters, game);
    }

    kickPowers(parameters, game) {
        return this._req('set_dummy_powers', undefined, undefined, parameters, game);
    }

    setState(parameters, game) {
        return this._req('set_game_state', undefined, undefined, parameters, game);
    }

    process(parameters, game) {
        return this._req('process_game', undefined, undefined, parameters, game);
    }

    querySchedule(parameters, game) {
        return this._req('query_schedule', undefined, undefined, parameters, game);
    }

    start(parameters, game) {
        return this._req('set_game_status', {status: STRINGS.ACTIVE}, undefined, parameters, game);
    }

    pause(parameters, game) {
        return this._req('set_game_status', {status: STRINGS.PAUSED}, undefined, parameters, game);
    }

    resume(parameters, game) {
        return this._req('set_game_status', {status: STRINGS.ACTIVE}, undefined, parameters, game);
    }

    cancel(parameters, game) {
        return this._req('set_game_status', {status: STRINGS.CANCELED}, undefined, parameters, game);
    }

    draw(parameters, game) {
        return this._req('set_game_status', {status: STRINGS.COMPLETED}, undefined, parameters, game);
    }
}
