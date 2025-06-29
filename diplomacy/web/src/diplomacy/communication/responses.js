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

/** Responses. **/
export const RESPONSES = {
    names: new Set([
        'error', 'ok', 'data_game_phase', 'data_token', 'data_maps', 'data_power_names', 'data_games',
        'data_possible_orders', 'data_game_info', 'data_time_stamp', 'data_game_phases', 'data_game',
        'data_game_schedule', 'data_saved_game'
    ]),
    parse: function (jsonObject) {
        if (!jsonObject.hasOwnProperty('name'))
            throw new Error('No name field in expected response object');
        if (!RESPONSES.names.has(jsonObject.name))
            throw new Error('Invalid response name ' + jsonObject.name);
        if (jsonObject.name === STRINGS.ERROR)
            throw new Error(jsonObject.name + ': ' + jsonObject.message);
        return jsonObject;
    },
    isOk: function (response) {
        return response.name === STRINGS.OK;
    },
    isUniqueData: function (response) {
        // Expected only 3 fields: name, request_id, data.
        return (response.hasOwnProperty('data') && Object.keys(response).length === 3);
    }
};
