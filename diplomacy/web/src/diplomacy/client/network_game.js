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
import {Channel} from "./channel";
import {Game} from "../engine/game";

/** Class NetworkGame. **/

export class NetworkGame {
    constructor(channel, serverGameState) {
        // Let's use a "local" instance to manage game.
        // This will help make distinction between network game request methods and local gme methods
        // (e.g. for request set_orders).
        this.local = new Game(serverGameState);
        this.channel = channel;
        this.notificationCallbacks = {};
        this.data = null;
        this.local.client = this;
    }

    addCallback(notificationName, notificationCallback) {
        if (!this.notificationCallbacks.hasOwnProperty(notificationName))
            this.notificationCallbacks[notificationName] = [notificationCallback];
        else if (!this.notificationCallbacks[notificationName].includes(notificationCallback))
            this.notificationCallbacks[notificationName].push(notificationCallback);
    }

    clearCallbacks(notificationName) {
        if (this.notificationCallbacks.hasOwnProperty(notificationName))
            delete this.notificationCallbacks[notificationName];
    }

    clearAllCallbacks() {
        this.notificationCallbacks = {};
    }

    notify(notification) {
        if (this.notificationCallbacks.hasOwnProperty(notification.name)) {
            for (let callback of this.notificationCallbacks[notification.name])
                setTimeout(() => callback(this, notification), 0);
        }
    }

    _req(channelMethod, parameters) {
        /** Send a game request using given channel request method. **/
        if (!this.channel)
            throw new Error('Invalid client game.');
        return channelMethod.apply(this.channel, [parameters, this]);
    }

    //// Game requests API.

    getAllPossibleOrders(parameters) {
        return this._req(Channel.prototype.getAllPossibleOrders, parameters);
    }

    getPhaseHistory(parameters) {
        return this._req(Channel.prototype.getPhaseHistory, parameters);
    }

    leave(parameters) {
        return this._req(Channel.prototype.leaveGame, parameters);
    }

    sendGameMessage(parameters) {
        return this._req(Channel.prototype.sendGameMessage, parameters);
    }

    setOrders(parameters) {
        return this._req(Channel.prototype.setOrders, parameters);
    }

    clearCenters(parameters) {
        return this._req(Channel.prototype.clearCenters, parameters);
    }

    clearOrders(parameters) {
        return this._req(Channel.prototype.clearOrders, parameters);
    }

    clearUnits(parameters) {
        return this._req(Channel.prototype.clearUnits, parameters);
    }

    wait(parameters) {
        return this._req(Channel.prototype.wait, parameters);
    }

    noWait(parameters) {
        return this._req(Channel.prototype.noWait, parameters);
    }

    setWait(wait, parameters) {
        return wait ? this.wait(parameters) : this.noWait(parameters);
    }

    vote(parameters) {
        return this._req(Channel.prototype.vote, parameters);
    }

    save(parameters) {
        return this._req(Channel.prototype.save, parameters);
    }

    synchronize() {
        if (!this.channel)
            throw new Error('Invalid client game.');
        return Channel.prototype.synchronize.apply(this.channel, [{timestamp: this.local.getLatestTimestamp()}, this]);
    }

    // Admin/moderator API.

    remove(parameters) {
        return this._req(Channel.prototype.deleteGame, parameters);
    }

    kickPowers(parameters) {
        return this._req(Channel.prototype.kickPowers, parameters);
    }

    setState(parameters) {
        return this._req(Channel.prototype.setState, parameters);
    }

    process(parameters) {
        return this._req(Channel.prototype.process, parameters);
    }

    querySchedule(parameters) {
        return this._req(Channel.prototype.querySchedule, parameters);
    }

    start(parameters) {
        return this._req(Channel.prototype.start, parameters);
    }

    pause(parameters) {
        return this._req(Channel.prototype.pause, parameters);
    }

    resume(parameters) {
        return this._req(Channel.prototype.resume, parameters);
    }

    cancel(parameters) {
        return this._req(Channel.prototype.cancel, parameters);
    }

    draw(parameters) {
        return this._req(Channel.prototype.draw, parameters);
    }

    //// Game callbacks setting API.

    addOnClearedCenters(callback) {
        this.addCallback('cleared_centers', callback);
    }

    addOnClearedOrders(callback) {
        this.addCallback('cleared_orders', callback);
    }

    addOnClearedUnits(callback) {
        this.addCallback('cleared_units', callback);
    }

    addOnPowersControllers(callback) {
        this.addCallback('powers_controllers', callback);
    }

    addOnGameDeleted(callback) {
        this.addCallback('game_deleted', callback);
    }

    addOnGameMessageReceived(callback) {
        this.addCallback('game_message_received', callback);
    }

    addOnGameProcessed(callback) {
        this.addCallback('game_processed', callback);
    }

    addOnGamePhaseUpdate(callback) {
        this.addCallback('game_phase_update', callback);
    }

    addOnGameStatusUpdate(callback) {
        this.addCallback('game_status_update', callback);
    }

    addOnOmniscientUpdated(callback) {
        this.addCallback('omniscient_updated', callback);
    }

    addOnPowerOrdersUpdate(callback) {
        this.addCallback('power_orders_update', callback);
    }

    addOnPowerOrdersFlag(callback) {
        this.addCallback('power_orders_flag', callback);
    }

    addOnPowerVoteUpdated(callback) {
        this.addCallback('power_vote_updated', callback);
    }

    addOnPowerWaitFlag(callback) {
        this.addCallback('power_wait_flag', callback);
    }

    addOnVoteCountUpdated(callback) {
        this.addCallback('vote_count_updated', callback);
    }

    addOnVoteUpdated(callback) {
        this.addCallback('vote_updated', callback);
    }

    //// Game callbacks clearing API.

    clearOnClearedCenters() {
        this.clearCallbacks('cleared_centers');
    }

    clearOnClearedOrders() {
        this.clearCallbacks('cleared_orders');
    }

    clearOnClearedUnits() {
        this.clearCallbacks('cleared_units');
    }

    clearOnPowersControllers() {
        this.clearCallbacks('powers_controllers');
    }

    clearOnGameDeleted() {
        this.clearCallbacks('game_deleted');
    }

    clearOnGameMessageReceived() {
        this.clearCallbacks('game_message_received');
    }

    clearOnGameProcessed() {
        this.clearCallbacks('game_processed');
    }

    clearOnGamePhaseUpdate() {
        this.clearCallbacks('game_phase_update');
    }

    clearOnGameStatusUpdate() {
        this.clearCallbacks('game_status_update');
    }

    clearOnOmniscientUpdated() {
        this.clearCallbacks('omniscient_updated');
    }

    clearOnPowerOrdersUpdate() {
        this.clearCallbacks('power_orders_update');
    }

    clearOnPowerOrdersFlag() {
        this.clearCallbacks('power_orders_flag');
    }

    clearOnPowerVoteUpdated() {
        this.clearCallbacks('power_vote_updated');
    }

    clearOnPowerWaitFlag() {
        this.clearCallbacks('power_wait_flag');
    }

    clearOnVoteCountUpdated() {
        this.clearCallbacks('vote_count_updated');
    }

    clearOnVoteUpdated() {
        this.clearCallbacks('vote_updated');
    }
}
