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

/** Notifications. **/
export const NOTIFICATIONS = {
    levels: {
        // Notification name to notification level ('channel' or 'game').
        account_deleted: STRINGS.CHANNEL,
        cleared_centers: STRINGS.GAME,
        cleared_orders: STRINGS.GAME,
        cleared_units: STRINGS.GAME,
        game_deleted: STRINGS.GAME,
        game_message_received: STRINGS.GAME,
        game_processed: STRINGS.GAME,
        game_phase_update: STRINGS.GAME,
        game_status_update: STRINGS.GAME,
        omniscient_updated: STRINGS.GAME,
        power_orders_flag: STRINGS.GAME,
        power_orders_update: STRINGS.GAME,
        power_vote_updated: STRINGS.GAME,
        power_wait_flag: STRINGS.GAME,
        powers_controllers: STRINGS.GAME,
        vote_count_updated: STRINGS.GAME,
        vote_updated: STRINGS.GAME,
    },
    parse: function (jsonObject) {
        if (!jsonObject.hasOwnProperty('name'))
            throw new Error('No name field in expected notification object.');
        if (!jsonObject.hasOwnProperty('token'))
            throw new Error('No token field in expected notification object.');
        if (!NOTIFICATIONS.levels.hasOwnProperty(jsonObject.name))
            throw new Error('Invalid notification name ' + jsonObject.name);
        if (NOTIFICATIONS.levels[jsonObject.name] === STRINGS.GAME) {
            if (!jsonObject.hasOwnProperty('game_id'))
                throw new Error('No game_id field in expected game notification object.');
            if (!jsonObject.hasOwnProperty('game_role'))
                throw new Error('No game_role field in expected game notification object.');
        }
        return jsonObject;
    }
};
