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
import {UTILS} from "../utils/utils";
import {STRINGS} from "../utils/strings";
import {SortedDict} from "../utils/sorted_dict";
import {Power} from "./power";
import {Message} from "./message";
import {Order} from "../../gui/utils/order";

export function comparablePhase(shortPhaseName) {
    /** Return a unique integer corresponding to given short phase name, so that
     * phases can be compared using such integers.
     * **/
    // Phase 'FORMING' is assumed to be the smallest phase.
    if (shortPhaseName === 'FORMING')
        return 0;
    // Phase 'COMPLETED' is assumed to be the greatest phase.
    if (shortPhaseName === 'COMPLETED')
        return Number.MAX_SAFE_INTEGER;
    if (shortPhaseName.length !== 6)
        throw new Error(`Invalid short phase name: ${shortPhaseName}`);
    const seasonOrder = {S: 0, F: 1, W: 2};
    const stepOrder = {M: 0, R: 1, A: 2};
    const phaseSeason = shortPhaseName[0];
    const phaseYear = parseInt(shortPhaseName.substring(1, 5), 10);
    const phaseStep = shortPhaseName[5];
    if (isNaN(phaseYear))
        throw new Error(`Unable to parse phase year from ${shortPhaseName}`);
    if (!seasonOrder.hasOwnProperty(phaseSeason))
        throw new Error(`Unable to parse phase season from ${shortPhaseName}`);
    if (!stepOrder.hasOwnProperty(phaseStep))
        throw new Error(`Unable to parse phase step from ${shortPhaseName}`);
    return (phaseYear * 100) + (seasonOrder[phaseSeason] * 10) + stepOrder[phaseStep];
}

export class Game {
    constructor(gameData) {
        ////// Instead of using: `Object.assign(this, gameState)`,
        ////// we set each field separately to let IDE know all attributes expected for Game class.
        //// We first check gameState.
        // These fields must not be null.

        const nonNullFields = [
            'game_id', 'map_name', 'messages', 'role', 'rules', 'status', 'timestamp_created', 'deadline',
            'message_history', 'order_history', 'state_history'
        ];
        // These fields may be null.
        const nullFields = ['n_controls', 'registration_password'];
        // All fields are required.
        for (let field of nonNullFields)
            if (!gameData.hasOwnProperty(field) || gameData[field] == null)
                throw new Error('Game: given state must have field `' + field + '` with non-null value.');
        for (let field of nullFields)
            if (!gameData.hasOwnProperty(field))
                throw new Error('Game: given state must have field `' + field + '`.');

        this.game_id = gameData.game_id;
        this.map_name = gameData.map_name;
        this.messages = new SortedDict(gameData instanceof Game ? null : gameData.messages, parseInt);

        // {short phase name => state}
        this.state_history = new SortedDict(gameData instanceof Game ? gameData.state_history.toDict() : gameData.state_history, comparablePhase);
        // {short phase name => {power name => [orders]}}
        this.order_history = new SortedDict(gameData instanceof Game ? gameData.order_history.toDict() : gameData.order_history, comparablePhase);
        // {short phase name => {unit => [results]}}
        this.result_history = new SortedDict(gameData instanceof Game ? gameData.result_history.toDict() : gameData.result_history, comparablePhase);
        // {short phase name => {message.time_sent => message}}
        if (gameData instanceof Game) {
            this.message_history = new SortedDict(gameData.message_history.toDict(), comparablePhase);
        } else {
            this.message_history = new SortedDict(null, comparablePhase);
            for (let entry of Object.entries(gameData.message_history)) {
                const shortPhaseName = entry[0];
                const phaseMessages = entry[1];
                const sortedPhaseMessages = new SortedDict(phaseMessages, parseInt);
                this.message_history.put(shortPhaseName, sortedPhaseMessages);
            }
        }

        this.role = gameData.role;
        this.rules = gameData.rules;
        this.status = gameData.status;
        this.timestamp_created = gameData.timestamp_created;
        this.deadline = gameData.deadline;
        this.n_controls = gameData.n_controls;
        this.registration_password = gameData.registration_password;
        this.observer_level = gameData.observer_level;
        this.controlled_powers = gameData.controlled_powers;
        this.daide_port = gameData.daide_port;
        this.result = gameData.result || null;

        this.phase = gameData.phase_abbr || null; // phase abbreviation

        this.powers = {};
        if (gameData.powers) {
            for (let entry of Object.entries(gameData.powers)) {
                const power_name = entry[0];
                const powerState = entry[1];
                if (powerState instanceof Power) {
                    this.powers[power_name] = powerState.copy();
                } else {
                    this.powers[power_name] = new Power(power_name, (this.isPlayerGame() ? power_name : this.role), this);
                    this.powers[power_name].setState(powerState);
                }
            }
        } else if (this.state_history.size()) {
            const lastState = this.state_history.lastValue();
            if (lastState.units) {
                for (let powerName of Object.keys(lastState.units)) {
                    this.powers[powerName] = new Power(powerName, (this.isPlayerGame() ? powerName : this.role), this);
                }
            }
        }

        this.note = gameData.note;
        this.builds = null;

        // {location => [possible orders]}
        this.possibleOrders = null;
        // {power name => [orderable locations]}
        this.orderableLocations = null;
        this.ordersTree = null;
        // {loc => order type}
        this.orderableLocToTypes = null;
        this.client = null; // Used as pointer to a NetworkGame.

        this.phase_summaries = gameData.phase_summaries || {};
    }

    get n_players() {
        return this.countControlledPowers();
    }

    static createOrdersTree(possibleOrders, tree, locToTypes) {
        for (let orders of Object.values(possibleOrders)) {
            for (let order of orders) {
                // We ignore WAIVE order.
                if (order === 'WAIVE')
                    continue;
                const pieces = order.split(/ +/);
                const thirdPiece = pieces[2];
                const lastPiece = pieces[pieces.length - 1];
                switch (thirdPiece) {
                    case 'H':
                        // 'H', unit
                        UTILS.javascript.extendTreeValue(tree, ['H'], `${pieces[0]} ${pieces[1]}`);
                        UTILS.javascript.extendArrayWithUniqueValues(locToTypes, pieces[1], 'H');
                        break;
                    case '-':
                        // 'M', unit, province
                        // 'V', unit, province
                        UTILS.javascript.extendTreeValue(tree, ['M', `${pieces[0]} ${pieces[1]}`, pieces[3]], (lastPiece === 'VIA' ? 'V' : 'M'));
                        UTILS.javascript.extendArrayWithUniqueValues(locToTypes, pieces[1], 'M');
                        break;
                    case 'S':
                        // 'S', supporter unit, supported unit, province
                        UTILS.javascript.extendTreeValue(tree, ['S', `${pieces[0]} ${pieces[1]}`, `${pieces[3]} ${pieces[4]}`], lastPiece);
                        UTILS.javascript.extendArrayWithUniqueValues(locToTypes, pieces[1], 'S');
                        break;
                    case 'C':
                        // 'C', convoyer unit, convoyed unit, province
                        UTILS.javascript.extendTreeValue(tree, ['C', `${pieces[0]} ${pieces[1]}`, `${pieces[3]} ${pieces[4]}`], pieces[6]);
                        UTILS.javascript.extendArrayWithUniqueValues(locToTypes, pieces[1], 'C');
                        break;
                    case 'R':
                        // 'R', unit, province
                        UTILS.javascript.extendTreeValue(tree, ['R', `${pieces[0]} ${pieces[1]}`], pieces[3]);
                        UTILS.javascript.extendArrayWithUniqueValues(locToTypes, pieces[1], 'R');
                        break;
                    case 'D':
                        // D, unit
                        UTILS.javascript.extendTreeValue(tree, ['D'], `${pieces[0]} ${pieces[1]}`);
                        UTILS.javascript.extendArrayWithUniqueValues(locToTypes, pieces[1], 'D');
                        break;
                    case 'B':
                        // B, unit
                        UTILS.javascript.extendTreeValue(tree, [pieces[0]], pieces[1]);
                        UTILS.javascript.extendArrayWithUniqueValues(locToTypes, pieces[1], pieces[0]);
                        break;
                    default:
                        throw new Error(`Unable to parse order: ${order}`);
                }
            }
        }
    }

    extendPhaseHistory(phaseData) {
        if (this.state_history.contains(phaseData.name)) throw new Error(`Phase ${phaseData.phase} already in state history.`);
        if (this.message_history.contains(phaseData.name)) throw new Error(`Phase ${phaseData.phase} already in message history.`);
        if (this.order_history.contains(phaseData.name)) throw new Error(`Phase ${phaseData.phase} already in order history.`);
        if (this.result_history.contains(phaseData.name)) throw new Error(`Phase ${phaseData.phase} already in result history.`);
        this.state_history.put(phaseData.name, phaseData.state);
        this.order_history.put(phaseData.name, phaseData.orders);
        this.result_history.put(phaseData.name, phaseData.results);
        this.message_history.put(phaseData.name, new SortedDict(phaseData.messages, parseInt));
    }

    addMessage(message) {
        message = new Message(message);
        if (!message.time_sent)
            throw new Error('No time sent for given message.');
        if (this.messages.hasOwnProperty(message.time_sent))
            throw new Error('There is already a message with time sent ' + message.time_sent + ' in message history.');
        if (this.isPlayerGame() && !message.isGlobal() && this.role !== message.sender && this.role !== message.recipient)
            throw new Error('Given message is not related to current player ' + this.role);
        this.messages.put(message.time_sent, message);
    }

    assertPlayerGame(powerName) {
        if (!this.isPlayerGame(powerName))
            throw new Error('Expected a player game' + (powerName ? (' ' + powerName) : '') + ', got role ' + this.role + '.');
    }

    assertObserverGame() {
        if (!this.isObserverGame())
            throw new Error('Expected an observer game, got role ' + this.role + '.');
    }

    assertOmniscientGame() {
        if (!this.isOmniscientGame())
            throw new Error('Expected an omniscient game, got role ' + this.role + '.');
    }

    clearCenters(powerName) {
        for (let power_name of Object.keys(this.powers)) {
            if (!powerName || power_name === powerName)
                this.powers[power_name].clearCenters();
        }
    }

    clearOrders(powerName) {
        for (let power_name of Object.keys(this.powers))
            if (!powerName || power_name === powerName)
                this.powers[power_name].clearOrders();
    }

    clearUnits(powerName) {
        for (let power_name of Object.keys(this.powers)) {
            if (!powerName || power_name === powerName)
                this.powers[power_name].clearUnits();
        }
    }

    clearVote() {
        for (let power_name of Object.keys(this.powers))
            this.powers[power_name].vote = 'neutral';
    }

    countControlledPowers() {
        let count = 0;
        for (let power of Object.values(this.powers))
            count += power.isControlled() ? 1 : 0;
        return count;
    }

    extendStateHistory(state) {
        if (this.state_history.contains(state.name))
            throw new Error('There is already a state with phase ' + state.name + ' in state history.');
        this.state_history.put(state.name, state);
    }

    getLatestTimestamp() {
        return Math.max(
            this.timestamp_created,
            (this.state_history.size() ? this.state_history.lastValue().timestamp : 0),
            (this.messages.size() ? this.messages.lastKey() : 0)
        );
    }

    getPower(name) {
        return this.powers.hasOwnProperty(name) ? this.powers[name] : null;
    }

    getRelatedPower() {
        return this.getPower(this.role);
    }

    hasPower(powerName) {
        return this.powers.hasOwnProperty(powerName);
    }

    isPlayerGame(powerName) {
        return (this.hasPower(this.role) && (!powerName || this.role === powerName));
    }

    isObserverGame() {
        return this.role === STRINGS.OBSERVER_TYPE;
    }

    isOmniscientGame() {
        return this.role === STRINGS.OMNISCIENT_TYPE;
    }

    isRealTime() {
        return this.rules.includes('REAL_TIME');
    }

    isNoCheck() {
        return this.rules.includes('NO_CHECK');
    }

    setPhaseData(phaseData) {
        this.setState(phaseData.state);
        this.clearOrders();
        for (let entry of Object.entries(phaseData.orders)) {
            if (entry[1])
                this.setOrders(entry[0], entry[1]);
        }
        this.messages = phaseData.messages instanceof SortedDict ? phaseData.messages : new SortedDict(phaseData.messages, parseInt);
    }

    setState(state) {
        this.result = state.result || null;
        this.note = state.note || null;
        this.phase = state.name;
        if (state.units) {
            for (let power_name of Object.keys(state.units)) {
                if (this.powers.hasOwnProperty(power_name)) {
                    const units = state.units[power_name];
                    const power = this.powers[power_name];
                    power.retreats = {};
                    power.units = [];
                    for (let unit of units) {
                        if (unit.charAt(0) === '*')
                            power.retreats[unit.substr(1)] = {};
                        else
                            power.units.push(unit);
                    }
                }
            }
        }
        if (state.centers)
            for (let power_name of Object.keys(state.centers))
                if (this.powers.hasOwnProperty(power_name))
                    this.powers[power_name].centers = state.centers[power_name];
        if (state.homes)
            for (let power_name of Object.keys(state.homes))
                if (this.powers.hasOwnProperty(power_name))
                    this.powers[power_name].homes = state.homes[power_name];
        if (state.influence)
            for (let power_name of Object.keys(state.influence))
                if (this.powers.hasOwnProperty(power_name))
                    this.powers[power_name].influence = state.influence[power_name];
        if (state.civil_disorder)
            for (let power_name of Object.keys(state.civil_disorder))
                if (this.powers.hasOwnProperty(power_name))
                    this.powers[power_name].civil_disorder = state.civil_disorder[power_name];
        if (state.builds)
            this.builds = state.builds;
    }

    setStatus(status) {
        this.status = status;
    }

    setOrders(powerName, orders) {
        if (this.powers.hasOwnProperty(powerName) && (!this.isPlayerGame() || this.isPlayerGame(powerName)))
            this.powers[powerName].setOrders(orders);
    }

    setWait(powerName, wait) {
        if (this.powers.hasOwnProperty(powerName)) {
            this.powers[powerName].wait = wait;
        }
    }

    updateDummyPowers(dummyPowers) {
        for (let dummyPowerName of dummyPowers) if (this.powers.hasOwnProperty(dummyPowerName))
            this.powers[dummyPowerName].setDummy();
    }

    updatePowersControllers(controllers, timestamps) {
        for (let entry of Object.entries(controllers)) {
            this.getPower(entry[0]).updateController(entry[1], timestamps[entry[0]]);
        }
    }

    cloneAt(pastPhase) {
        if (pastPhase !== null && this.state_history.contains(pastPhase)) {
            const game = new Game(this);
            const pastPhaseIndex = this.state_history.indexOf(pastPhase);
            const nbPastPhases = this.state_history.size();
            for (let i = nbPastPhases - 1; i > pastPhaseIndex; --i) {
                const keyToRemove = this.state_history.keyFromIndex(i);
                game.message_history.remove(keyToRemove);
                game.state_history.remove(keyToRemove);
                game.order_history.remove(keyToRemove);
                game.result_history.remove(keyToRemove);
            }
            game.setPhaseData({
                name: pastPhase,
                state: this.state_history.get(pastPhase),
                orders: this.order_history.get(pastPhase),
                messages: this.message_history.get(pastPhase)
            });
            return game;
        }
        return null;
    }

    getPhaseType() {
        if (this.phase === null || this.phase === 'FORMING' || this.phase === 'COMPLETED')
            return null;
        return this.phase[this.phase.length - 1];
    }

    getControllablePowers() {
        if (this.isObserverGame() || this.isOmniscientGame())
            return Object.keys(this.powers);
        return [this.role];
    }

    getServerOrders() {
        /** Return a dictionary of server orders.
         * Returned dictionary maps each power name to either:
         * - a dictionary of orders, mapping a loc to an Order object with boolean flag `local` set to false.
         * - an empty dictionary, to represent an empty orders set.
         * - null value, if power.order_is_set is false.
         * **/
        const orders = {};
        const controllablePowers = this.getControllablePowers();
        for (let powerName of controllablePowers) {
            const powerOrders = {};
            let countOrders = 0;
            const power = this.powers[powerName];
            for (let orderString of power.orders) {
                const serverOrder = new Order(orderString, false);
                powerOrders[serverOrder.loc] = serverOrder;
                ++countOrders;
            }
            orders[powerName] = (countOrders || power.order_is_set) ? powerOrders : null;
        }
        return orders;
    }

    getMessageChannels(role, all) {
        const messageChannels = {};
        role = role || this.role;
        let messagesToShow = null;
        if (all) {
            messagesToShow = this.message_history.values();
            if (this.messages.size() && !this.message_history.contains(this.phase))
                messagesToShow.push(this.messages);
        } else {
            if (this.messages.size())
                messagesToShow = [this.messages];
            else if (this.message_history.contains(this.phase))
                messagesToShow = this.message_history.get(this.phase);
        }
        for (let messages of messagesToShow) {
            for (let message of messages.values()) {
                let protagonist = null;
                if (message.sender === role || message.recipient === 'GLOBAL')
                    protagonist = message.recipient;
                else if (message.recipient === role)
                    protagonist = message.sender;
                if (!messageChannels.hasOwnProperty(protagonist))
                    messageChannels[protagonist] = [];
                messageChannels[protagonist].push(message);
            }
        }
        return messageChannels;
    }

    markAllMessagesRead() {
        for (let message of this.messages.values()) {
            if (message.sender !== this.role)
                message.read = true;
        }
    }

    setPossibleOrders(possibleOrders) {
        this.possibleOrders = possibleOrders.possible_orders;
        this.orderableLocations = possibleOrders.orderable_locations;
        this.ordersTree = {};
        this.orderableLocToTypes = {};
        Game.createOrdersTree(this.possibleOrders, this.ordersTree, this.orderableLocToTypes);
    }

    getOrderTypeToLocs(powerName) {
        const typeToLocs = {};
        for (let loc of this.orderableLocations[powerName]) {
            // loc may be a coastal province. In such case, we must check province coasts too.
            const associatedLocs = [];
            for (let possibleLoc of Object.keys(this.orderableLocToTypes)) {
                if (possibleLoc.substring(0, 3).toUpperCase() === loc.toUpperCase()) {
                    associatedLocs.push(possibleLoc);
                }
            }
            for (let associatedLoc of associatedLocs) {
                const orderTypes = this.orderableLocToTypes[associatedLoc];
                for (let orderType of orderTypes) {
                    if (!typeToLocs.hasOwnProperty(orderType))
                        typeToLocs[orderType] = [associatedLoc];
                    else
                        typeToLocs[orderType].push(associatedLoc);
                }
            }
        }
        return typeToLocs;
    }

    _build_sites(power) {
        const homes = this.rules.includes('BUILD_ANY') ? power.centers : power.homes;
        const occupiedLocations = [];
        for (let p of Object.values(this.powers)) {
            for (let unit of p.units) {
                occupiedLocations.push(unit.substring(2, 5));
            }
        }
        const buildSites = [];
        for (let h of homes) {
            if (power.centers.includes(h) && !occupiedLocations.includes(h))
                buildSites.push(h);
        }
        return buildSites;
    }

    getBuildsCount(powerName) {
        if (this.getPhaseType() !== 'A')
            return 0;
        const power = this.powers[powerName];
        let buildCount = power.centers.length - power.units.length;
        if (buildCount > 0) {
            const buildSites = this._build_sites(power);
            buildCount = Math.min(buildSites.length, buildCount);
        }
        return buildCount;
    }

    get phasePrior() {
        // If state_history has fewer than 2 entries, no prior phase is available.
        if (this.state_history.size() < 2) return null;
        return this.state_history.keyFromIndex(this.state_history.size() - 2);
    }
}
