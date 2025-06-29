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
import {Future} from "../utils/future";
import {Channel} from "./channel";
import {GameInstanceSet} from "./game_instance_set";
import {NetworkGame} from "./network_game";

/** Class RequestFutureContext. **/
export class RequestFutureContext {
    constructor(request, connection, game = null) {
        this.request = request;
        this.connection = connection;
        this.game = game;
        this.future = new Future();
    }

    getRequestId() {
        return this.request.request_id;
    }

    getChannel() {
        return this.connection.channels[this.request.token];
    }

    newChannel(username, token) {
        const channel = new Channel(this.connection, username, token);
        this.connection.channels[token] = channel;
        return channel;
    }

    newGame(received_game) {
        const channel = this.getChannel();
        const game = new NetworkGame(channel, received_game);
        if (!channel.game_id_to_instances.hasOwnProperty(game.local.game_id))
            channel.game_id_to_instances[game.local.game_id] = new GameInstanceSet(game.local.game_id);
        channel.game_id_to_instances[game.local.game_id].add(game);
        return game;
    }

    removeChannel() {
        delete this.connection.channels[this.request.token];
    }

    deleteGame() {
        const channel = this.getChannel();
        if (channel.game_id_to_instances.hasOwnProperty(this.request.game_id))
            delete channel.game_id_to_instances[this.request.game_id];
    }
}
