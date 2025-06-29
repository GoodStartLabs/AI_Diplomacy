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
import {STRINGS} from "../utils/strings";
import {NOTIFICATIONS} from "../communication/notifications";
import {Game} from "../engine/game";

/** Notification managers. **/
export const NOTIFICATION_MANAGERS = {
    account_deleted: function (channel, notification) {
        const connection = channel.connection;
        if (connection.channels.hasOwnProperty(channel.token))
            delete channel.connection.channels[channel.token];
    },
    cleared_centers: function (game, notification) {
        game.local.clearCenters(notification.power_name);
    },
    cleared_orders: function (game, notification) {
        game.local.clearOrders(notification.power_name);
    },
    cleared_units: function (game, notification) {
        game.local.clearUnits(notification.power_name);
    },
    powers_controllers: function (game, notification) {
        if (game.local.isPlayerGame() && notification.powers[game.local.role] !== game.local.getRelatedPower().getController()) {
            game.channel.game_id_to_instances[game.local.game_id].remove(game.local.role);
            if (!game.channel.game_id_to_instances[game.local.game_id].size())
                delete game.channel.game_id_to_instances[game.local.game_id];
        } else {
            game.local.updatePowersControllers(notification.powers, notification.timestamps);
        }
    },
    game_deleted: function (game, notification) {
        game.channel.game_id_to_instances[game.local.game_id].remove(game.local.role);
    },
    game_message_received: function (game, notification) {
        game.local.addMessage(notification.message);
    },
    game_processed: function (game, notification) {
        game.local.extendPhaseHistory(notification.previous_phase_data);
        game.local.setPhaseData(notification.current_phase_data);

        // If the server attached a summary to previous_phase_data
        if (notification.previous_phase_data && notification.previous_phase_data.summary) {
            const phaseName = notification.previous_phase_data.name;
            const summaryText = notification.previous_phase_data.summary;
            // Store it in game.local so that the React components can render it
            if (!game.local.phase_summaries) {
                game.local.phase_summaries = {};
            }
            game.local.phase_summaries[phaseName] = summaryText;
        }

        game.local.clearVote();
    },
    game_phase_update: function (game, notification) {
        if (notification.phase_data_type === STRINGS.STATE_HISTORY)
            game.local.extendPhaseHistory(notification.phase_data);
        else
            game.local.setPhaseData(notification.phase_data);
    },
    game_status_update: function (game, notification) {
        if (game.local.status !== notification.status) {
            game.local.setStatus(notification.status);
        }
    },
    omniscient_updated: function (game, notification) {
        if (game.local.isPlayerGame()) return;
        if (game.local.isObserverGame()) {
            if (notification.grade_update !== STRINGS.PROMOTE || notification.game.role !== STRINGS.OMNISCIENT_TYPE)
                throw new Error('Omniscient updated: expected promotion from observer to omniscient');
        } else {
            if (notification.grade_update !== STRINGS.DEMOTE || notification.game.role !== STRINGS.OBSERVER_TYPE)
                throw new Error('Omniscient updated: expected demotion from omniscient to observer.');
        }
        const channel = game.channel;
        const oldGame = channel.game_id_to_instances[game.local.game_id].remove(game.local.role);
        oldGame.client = null;
        game.local = new Game(notification.game);
        game.local.client = game;
        channel.game_id_to_instances[game.local.game_id].add(game);
    },
    power_orders_update: function (game, notification) {
        game.local.setOrders(notification.power_name, notification.orders);
    },
    power_orders_flag: function (game, notification) {
        game.local.getPower(notification.power_name).order_is_set = notification.order_is_set;
    },
    power_vote_updated: function (game, notification) {
        game.local.assertPlayerGame();
        game.local.getRelatedPower().vote = notification.vote;
    },
    power_wait_flag: function (game, notification) {
        game.local.setWait(notification.power_name, notification.wait);
    },
    vote_count_updated: function (game, notification) {
        // Nothing currently done.
    },
    vote_updated: function (game, notification) {
        game.assertOmniscientGame();
        for (let power_name of notification.vote) {
            game.local.getPower(power_name).vote = notification.vote[power_name];
        }
    },
    handleNotification: function (connection, notification) {
        if (!NOTIFICATION_MANAGERS.hasOwnProperty(notification.name))
            throw new Error('No notification handler available for notification ' + notification.name);
        const handler = NOTIFICATION_MANAGERS[notification.name];
        const level = NOTIFICATIONS.levels[notification.name];
        if (!connection.channels.hasOwnProperty(notification.token))
            throw new Error('Unable to find channel related to notification ' + notification.name);
        let objectToNotify = connection.channels[notification.token];
        if (level === STRINGS.GAME) {
            if (objectToNotify.game_id_to_instances.hasOwnProperty(notification.game_id)
                && objectToNotify.game_id_to_instances[notification.game_id].has(notification.game_role))
                objectToNotify = objectToNotify.game_id_to_instances[notification.game_id].get(notification.game_role);
            else
                throw new Error('Unable to find game instance related to notification '
                    + notification.name + '/' + notification.game_id + '/' + notification.game_role);
        }
        handler(objectToNotify, notification);
        if (level === STRINGS.GAME)
            objectToNotify.notify(notification);
    }
};
