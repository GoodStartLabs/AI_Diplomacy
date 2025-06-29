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

/** Requests. **/
export const REQUESTS = {
    /** Abstract request models, mapping base request field names with default values.
     * Every request has at least basic fields.
     * Every channel request has at least basic and channel fields.
     * Every game request has at least basic, channel and game fields. **/
    abstract: {
        basic: {request_id: null, name: null, re_sent: false},
        channel: {token: null},
        game: {game_id: null, game_role: null, phase: null},
    },

    /** Request models. A request model is defined with:
     * - request level: either null, 'channel' or 'game'
     * - request model itself: a dictionary mapping each request field name with a default value.
     * - request phase dependent (optional, for game requests): boolean (default, true)
     * **/
    models: {
        sign_in: {level: null, model: {username: null, password: null}},
        create_game: {
            level: STRINGS.CHANNEL,
            model: {
                game_id: null, n_controls: null, deadline: 300, registration_password: null,
                power_name: null, state: null, map_name: 'standard', rules: null
            }
        },
        delete_account: {level: STRINGS.CHANNEL, model: {username: null}},
        get_all_possible_orders: {level: STRINGS.GAME, model: {}},
        get_available_maps: {level: STRINGS.CHANNEL, model: {}},
        get_playable_powers: {level: STRINGS.CHANNEL, model: {game_id: null}},
        join_game: {level: STRINGS.CHANNEL, model: {game_id: null, power_name: null, registration_password: null}},
        list_games: {
            level: STRINGS.CHANNEL,
            model: {game_id: null, status: null, map_name: null, include_protected: true, for_omniscience: false}
        },
        get_games_info: {level: STRINGS.CHANNEL, model: {games: null}},
        logout: {level: STRINGS.CHANNEL, model: {}},
        set_grade: {level: STRINGS.CHANNEL, model: {grade: null, grade_update: null, username: null, game_id: null}},
        clear_centers: {level: STRINGS.GAME, model: {power_name: null}},
        clear_orders: {level: STRINGS.GAME, model: {power_name: null}},
        clear_units: {level: STRINGS.GAME, model: {power_name: null}},
        delete_game: {level: STRINGS.GAME, phase_dependent: false, model: {}},
        get_phase_history: {
            level: STRINGS.GAME,
            phase_dependent: false,
            model: {from_phase: null, to_phase: null}
        },
        leave_game: {level: STRINGS.GAME, model: {}},
        process_game: {level: STRINGS.GAME, model: {}},
        query_schedule: {level: STRINGS.GAME, model: {}},
        send_game_message: {level: STRINGS.GAME, model: {message: null}},
        set_dummy_powers: {level: STRINGS.GAME, model: {username: null, power_names: null}},
        set_game_state: {level: STRINGS.GAME, model: {state: null, orders: null, results: null, messages: null}},
        set_game_status: {level: STRINGS.GAME, model: {status: null}},
        set_orders: {level: STRINGS.GAME, model: {power_name: null, orders: null}},
        set_wait_flag: {level: STRINGS.GAME, model: {power_name: null, wait: null}},
        synchronize: {level: STRINGS.GAME, phase_dependent: false, model: {timestamp: null}},
        vote: {level: STRINGS.GAME, model: {vote: null}},
        save_game: {level: STRINGS.GAME, model: {}},
    },

    isPhaseDependent: function (name) {
        if (!REQUESTS.models.hasOwnProperty(name))
            throw new Error('Unknown request name ' + name);
        const model = REQUESTS.models[name];
        return (model.level === STRINGS.GAME && (!model.hasOwnProperty('phase_dependent') || model.phase_dependent));
    },

    /** Return request level for given request name. Either null, 'channel' or 'game'. **/
    getLevel: function (name) {
        if (!REQUESTS.models.hasOwnProperty(name))
            throw new Error('Unknown request name ' + name);
        return REQUESTS.models[name].level;
    },

    /** Create a request object for given request name with given request field values.
     * `parameters` is a dictionary mapping some request fields with values.
     * Parameters may not contain values for optional request fields. See Python module
     * diplomacy.communication.requests about requests definitions, required and optional fields.
     * **/
    create: function (name, parameters) {
        if (!REQUESTS.models.hasOwnProperty(name))
            throw new Error('Unknown request name ' + name);
        let models = null;
        const definition = REQUESTS.models[name];
        if (definition.level === STRINGS.GAME)
            models = [{}, definition.model, REQUESTS.abstract.game, REQUESTS.abstract.channel];
        else if (definition.level === STRINGS.CHANNEL)
            models = [{}, definition.model, REQUESTS.abstract.channel];
        else
            models = [{}, definition.model];
        models.push(REQUESTS.abstract.basic);
        models.push({name: name});
        const request = Object.assign.apply(null, models);
        if (parameters) for (let parameter of Object.keys(parameters)) if (request.hasOwnProperty(parameter))
            request[parameter] = parameters[parameter];
        if (!request.request_id)
            request.request_id = UTILS.createID();
        return request;
    },
};
