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
/*eslint no-unused-vars: ["error", { "args": "none" }]*/
import {RESPONSES} from "../communication/responses";

/** Default response manager. **/
function defaultResponseManager(context, response) {
    if (RESPONSES.isOk(response))
        return null;
    if (RESPONSES.isUniqueData(response))
        return response.data;
    return response;
}

/** Response managers. **/
export const RESPONSE_MANAGERS = {
    get_all_possible_orders: defaultResponseManager,
    get_available_maps: defaultResponseManager,
    get_playable_powers: defaultResponseManager,
    list_games: defaultResponseManager,
    get_games_info: defaultResponseManager,
    process_game: defaultResponseManager,
    query_schedule: defaultResponseManager,
    save_game: defaultResponseManager,
    set_dummy_powers: defaultResponseManager,
    set_grade: defaultResponseManager,
    synchronize: defaultResponseManager,
    create_game: function (context, response) {
        return context.newGame(response.data);
    },
    delete_account: function (context, response) {
        context.removeChannel();
    },
    delete_game: function (context, response) {
        context.deleteGame();
    },
    get_phase_history: function (context, response) {
        for (let phaseData of response.data) {
            context.game.local.extendPhaseHistory(phaseData);
        }
        return response.data;
    },
    join_game: function (context, response) {
        return context.newGame(response.data);
    },
    leave_game: function (context, response) {
        context.deleteGame();
    },
    logout: function (context, response) {
        context.removeChannel();
    },
    send_game_message: function (context, response) {
        const message = context.request.message;
        message.time_sent = response.data;
        context.game.local.addMessage(message);
    },
    set_game_state: function (context, response) {
        context.game.local.setPhaseData({
            name: context.request.state.name,
            state: context.request.state,
            orders: context.request.orders,
            messages: context.request.messages,
            results: context.request.results
        });
    },
    set_game_status: function (context, response) {
        context.game.local.setStatus(context.request.status);
    },
    set_orders: function (context, response) {
        const orders = context.request.orders;
        if (context.game.local.isPlayerGame(context.request.game_role))
            context.game.local.setOrders(context.request.game_role, orders);
        else
            context.game.local.setOrders(context.request.power_name, orders);
    },
    clear_orders: function (context, response) {
        context.game.local.clearOrders(context.request.power_name);
    },
    clear_units: function (context, response) {
        context.game.local.clearUnits(context.request.power_name);
    },
    clear_centers: function (context, response) {
        context.game.local.clearCenters(context.request.power_name);
    },
    set_wait_flag: function (context, response) {
        const wait = context.request.wait;
        if (context.game.local.isPlayerGame(context.request.game_role))
            context.game.local.setWait(context.request.game_role, wait);
        else
            context.game.local.setWait(context.request.power_name, wait);
    },
    vote: function (context, response) {
        context.game.local.getRelatedPower().vote = context.request.vote;
    },
    sign_in: function (context, response) {
        return context.newChannel(context.request.username, response.data);
    },
    handleResponse: function (context, response) {
        if (!RESPONSE_MANAGERS.hasOwnProperty(context.request.name))
            throw new Error('No response handler available for request ' + context.request.name);
        const handler = RESPONSE_MANAGERS[context.request.name];
        return handler(context, response);
    }
};
