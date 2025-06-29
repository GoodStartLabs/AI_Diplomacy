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

export class GameInstanceSet {
    constructor(gameID) {
        this.__game_id = gameID;
        this.__games = {};
    }

    getGames() {
        return Object.values(this.__games);
    }

    has(role) {
        return this.__games.hasOwnProperty(role);
    }

    get(role) {
        return this.__games[role] || null;
    }

    getSpecial() {
        if (this.__games.hasOwnProperty(STRINGS.OBSERVER_TYPE))
            return this.__games[STRINGS.OBSERVER_TYPE];
        if (this.__games.hasOwnProperty(STRINGS.OMNISCIENT_TYPE))
            return this.__games[STRINGS.OMNISCIENT_TYPE];
        return null;
    }

    remove(role) {
        let old = null;
        if (this.__games[role]) {
            old = this.__games[role];
            delete this.__games[role];
        }
        return old;
    }

    removeSpecial() {
        if (this.__games.hasOwnProperty(STRINGS.OBSERVER_TYPE))
            delete this.__games[STRINGS.OBSERVER_TYPE];
        if (this.__games.hasOwnProperty(STRINGS.OMNISCIENT_TYPE))
            delete this.__games[STRINGS.OMNISCIENT_TYPE];
    }

    add(game) {
        if (game.local.game_id !== this.__game_id)
            throw new Error('game ID to add does not match game instance set ID.');
        if (this.__games.hasOwnProperty(game.local.role))
            throw new Error('Role already in game instance set.');
        if (!game.local.isPlayerGame() && (
            this.__games.hasOwnProperty(STRINGS.OBSERVER_TYPE) || this.__games.hasOwnProperty(STRINGS.OMNISCIENT_TYPE)))
            throw new Error('Previous special game must be removed before adding new one.');
        this.__games[game.local.role] = game;
    }

    size() {
        return UTILS.javascript.count(this.__games);
    }
}
