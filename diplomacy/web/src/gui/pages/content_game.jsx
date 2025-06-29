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
import React from "react";
import Scrollchor from 'react-scrollchor';
import {SelectLocationForm} from "../forms/select_location_form";
import {SelectViaForm} from "../forms/select_via_form";
import {Order} from "../utils/order";
import {Row} from "../components/layouts";
import {Tabs} from "../components/tabs";
import {extendOrderBuilding, ORDER_BUILDER, POSSIBLE_ORDERS} from "../utils/order_building";
import {PowerOrderCreationForm} from "../forms/power_order_creation_form";
import {MessageForm} from "../forms/message_form";
import {UTILS} from "../../diplomacy/utils/utils";
import {Message} from "../../diplomacy/engine/message";
import {PowerOrders} from "../components/power_orders";
import {MessageView} from "../components/message_view";
import {STRINGS} from "../../diplomacy/utils/strings";
import {Diplog} from "../../diplomacy/utils/diplog";
import {Table} from "../components/table";
import {PowerView} from "../utils/power_view";
import {DipStorage} from "../utils/dipStorage";
import Helmet from 'react-helmet';
import {Navigation} from "../components/navigation";
import {PageContext} from "../components/page_context";
import PropTypes from 'prop-types';
import {Help} from "../components/help";
import {Tab} from "../components/tab";
import {Button} from "../components/button";
import {saveGameToDisk} from "../utils/saveGameToDisk";
import {Game} from '../../diplomacy/engine/game';
import {PowerOrdersActionBar} from "../components/power_orders_actions_bar";
import {SvgStandard} from "../maps/standard/SvgStandard";
import {SvgAncMed} from "../maps/ancmed/SvgAncMed";
import {SvgModern} from "../maps/modern/SvgModern";
import {SvgPure} from "../maps/pure/SvgPure";
import {MapData} from "../utils/map_data";
import {Queue} from "../../diplomacy/utils/queue";
import {PhaseSummaryBottomSheet} from "../components/PhaseSummaryBottomSheet";

const HotKey = require('react-shortcut');

/* Order management in game page.
 * When editing orders locally, we have to compare it to server orders
 * to determine when we need to update orders on server side. There are
 * 9 comparison cases, depending on orders:
 * SERVER    LOCAL      DECISION
 * null      null       0 (same)
 * null      {}         1 (different, user wants to send "no orders" on server)
 * null      {orders}   1 (different, user defines new orders locally)
 * {}        null       0 (assumed same: user is not allowed to "delete" a "no orders": he can only add new orders)
 * {}        {}         0 (same)
 * {}        {orders}   1 (different, user defines new orders locally and wants to overwrite the "no-orders" on server)
 * {orders}  null       1 (different, user wants to delete all server orders, will result to "no-orders")
 * {orders}  {}         1 (different, user wants to delete all server orders, will result to "no-orders")
 * {orders}  {orders}   same if we have exactly same orders on both server and local
  * */

const TABLE_POWER_VIEW = {
    name: ['Power', 0],
    controller: ['Controller', 1],
    order_is_set: ['With orders', 2],
    wait: ['Waiting', 3]
};

const PRETTY_ROLES = {
    [STRINGS.OMNISCIENT_TYPE]: 'Omnicient',
    [STRINGS.OBSERVER_TYPE]: 'Observer'
};

const MAP_COMPONENTS = {
    ancmed: SvgAncMed,
    standard: SvgStandard,
    modern: SvgModern,
    pure: SvgPure
};

function getMapComponent(mapName) {
    for (let rootMap of Object.keys(MAP_COMPONENTS)) {
        if (mapName.indexOf(rootMap) === 0)
            return MAP_COMPONENTS[rootMap];
    }
    throw new Error(`Un-implemented map: ${mapName}`);
}

function noPromise() {
    return new Promise(resolve => resolve());
}

export class ContentGame extends React.Component {

    constructor(props) {
        super(props);
        // Load local orders from local storage (if available).
        const savedOrders = this.props.data.client ? DipStorage.getUserGameOrders(
            this.props.data.client.channel.username,
            this.props.data.game_id,
            this.props.data.phase
        ) : null;
        let orders = null;
        if (savedOrders) {
            orders = {};
            for (let entry of Object.entries(savedOrders)) {
                let powerOrders = null;
                const powerName = entry[0];
                if (entry[1]) {
                    powerOrders = {};
                    for (let orderString of entry[1]) {
                        const order = new Order(orderString, true);
                        powerOrders[order.loc] = order;
                    }
                }
                orders[powerName] = powerOrders;
            }
        }
        this.schedule_timeout_id = null;
        this.state = {
            tabMain: null,
            tabPastMessages: null,
            tabCurrentMessages: null,
            messageHighlights: {},
            historyPhaseIndex: null,
            historyShowOrders: true,
            historyCurrentLoc: null,
            historyCurrentOrders: null,
            orders: orders, // {power name => {loc => {local: bool, order: str}}}
            power: null,
            orderBuildingType: null,
            orderBuildingPath: [],
            showAbbreviations: true,
            showPhaseSummarySheet: false,
            bottomSheetVisible: true,
            summaryVisible: true
        };

        // Bind some class methods to this instance.
        this.clearOrderBuildingPath = this.clearOrderBuildingPath.bind(this);
        this.displayFirstPastPhase = this.displayFirstPastPhase.bind(this);
        this.displayLastPastPhase = this.displayLastPastPhase.bind(this);
        this.displayLocationOrders = this.displayLocationOrders.bind(this);
        this.getMapInfo = this.getMapInfo.bind(this);
        this.notifiedGamePhaseUpdated = this.notifiedGamePhaseUpdated.bind(this);
        this.notifiedLocalStateChange = this.notifiedLocalStateChange.bind(this);
        this.notifiedNetworkGame = this.notifiedNetworkGame.bind(this);
        this.notifiedNewGameMessage = this.notifiedNewGameMessage.bind(this);
        this.notifiedPowersControllers = this.notifiedPowersControllers.bind(this);
        this.onChangeCurrentPower = this.onChangeCurrentPower.bind(this);
        this.onChangeMainTab = this.onChangeMainTab.bind(this);
        this.onChangeOrderType = this.onChangeOrderType.bind(this);
        this.onChangePastPhase = this.onChangePastPhase.bind(this);
        this.onChangePastPhaseIndex = this.onChangePastPhaseIndex.bind(this);
        this.onChangeShowPastOrders = this.onChangeShowPastOrders.bind(this);
        this.onChangeShowAbbreviations = this.onChangeShowAbbreviations.bind(this);
        this.onChangeTabCurrentMessages = this.onChangeTabCurrentMessages.bind(this);
        this.onChangeTabPastMessages = this.onChangeTabPastMessages.bind(this);
        this.onClickMessage = this.onClickMessage.bind(this);
        this.onDecrementPastPhase = this.onDecrementPastPhase.bind(this);
        this.onIncrementPastPhase = this.onIncrementPastPhase.bind(this);
        this.onOrderBuilding = this.onOrderBuilding.bind(this);
        this.onOrderBuilt = this.onOrderBuilt.bind(this);
        this.onProcessGame = this.onProcessGame.bind(this);
        this.onRemoveAllCurrentPowerOrders = this.onRemoveAllCurrentPowerOrders.bind(this);
        this.onRemoveOrder = this.onRemoveOrder.bind(this);
        this.onSelectLocation = this.onSelectLocation.bind(this);
        this.onSelectVia = this.onSelectVia.bind(this);
        this.onSetEmptyOrdersSet = this.onSetEmptyOrdersSet.bind(this);
        this.reloadServerOrders = this.reloadServerOrders.bind(this);
        this.renderOrders = this.renderOrders.bind(this);
        this.sendMessage = this.sendMessage.bind(this);
        this.setOrders = this.setOrders.bind(this);
        this.setSelectedLocation = this.setSelectedLocation.bind(this);
        this.setSelectedVia = this.setSelectedVia.bind(this);
        this.setWaitFlag = this.setWaitFlag.bind(this);
        this.vote = this.vote.bind(this);
        this.updateDeadlineTimer = this.updateDeadlineTimer.bind(this);
    }

    static prettyRole(role) {
        if (PRETTY_ROLES.hasOwnProperty(role))
            return PRETTY_ROLES[role];
        return role;
    }

    static gameTitle(game) {
        let title = `${game.game_id} | ${game.phase} | ${game.status} | ${ContentGame.prettyRole(game.role)} | ${game.map_name}`;
        if (game.daide_port)
            title += ` | DAIDE ${game.daide_port}`;
        const remainingTime = game.deadline_timer;
        if (remainingTime === undefined)
            title += ` (deadline: ${game.deadline} sec)`;
        else if (remainingTime)
            title += ` (remaining ${remainingTime} sec)`;
        return title;
    }

    static getServerWaitFlags(engine) {
        const wait = {};
        const controllablePowers = engine.getControllablePowers();
        for (let powerName of controllablePowers) {
            wait[powerName] = engine.powers[powerName].wait;
        }
        return wait;
    }

    static getOrderBuilding(powerName, orderType, orderPath) {
        return {
            type: orderType,
            path: orderPath,
            power: powerName,
            builder: orderType && ORDER_BUILDER[orderType]
        };
    }

    setState(state) {
        return new Promise(resolve => super.setState(state, resolve));
    }

    forceUpdate() {
        return new Promise(resolve => super.forceUpdate(resolve));
    }

    /**
     * Return current page object displaying this content.
     * @returns {Page}
     */
    getPage() {
        return this.context;
    }

    clearOrderBuildingPath() {
        return this.setState({
            orderBuildingPath: []
        });
    }

    // [ Methods used to handle current map.

    setSelectedLocation(location, powerName, orderType, orderPath) {
        if (!location)
            return;
        extendOrderBuilding(
            powerName, orderType, orderPath, location,
            this.onOrderBuilding, this.onOrderBuilt, this.getPage().error
        );
    }

    setSelectedVia(moveType, powerName, orderPath, location) {
        if (!moveType || !['M', 'V'].includes(moveType))
            return;
        extendOrderBuilding(
            powerName, moveType, orderPath, location,
            this.onOrderBuilding, this.onOrderBuilt, this.getPage().error
        );
    }

    onSelectLocation(possibleLocations, powerName, orderType, orderPath) {
        this.getPage().dialog(onClose => (
            <SelectLocationForm path={orderPath}
                                locations={possibleLocations}
                                onSelect={(location) => {
                                    this.setSelectedLocation(location, powerName, orderType, orderPath);
                                    onClose();
                                }}
                                onClose={() => {
                                    this.clearOrderBuildingPath();
                                    onClose();
                                }}/>
        ));
    }

    onSelectVia(location, powerName, orderPath) {
        this.getPage().dialog(onClose => (
            <SelectViaForm path={orderPath}
                           onSelect={(moveType) => {
                               setTimeout(() => {
                                   this.setSelectedVia(moveType, powerName, orderPath, location);
                                   onClose();
                               }, 0);
                           }}
                           onClose={() => {
                               this.clearOrderBuildingPath();
                               onClose();
                           }}/>
        ));
    }

    // ]

    getMapInfo() {
        return this.getPage().availableMaps[this.props.data.map_name];
    }

    clearScheduleTimeout() {
        if (this.schedule_timeout_id) {
            clearInterval(this.schedule_timeout_id);
            this.schedule_timeout_id = null;
        }
    }

    updateDeadlineTimer() {
        const engine = this.props.data;
        --engine.deadline_timer;
        if (engine.deadline_timer <= 0) {
            engine.deadline_timer = 0;
            this.clearScheduleTimeout();
        }
        if (this.networkGameIsDisplayed(engine.client))
            this.forceUpdate();
    }

    reloadDeadlineTimer(networkGame) {
        networkGame.querySchedule()
            .then(dataSchedule => {
                const schedule = dataSchedule.schedule;
                const server_current = schedule.current_time;
                const server_end = schedule.time_added + schedule.delay;
                const server_remaining = server_end - server_current;
                this.props.data.deadline_timer = server_remaining * schedule.time_unit;
                if (!this.schedule_timeout_id)
                    this.schedule_timeout_id = setInterval(this.updateDeadlineTimer, schedule.time_unit * 1000);
            })
            .catch(() => {
                if (this.props.data.hasOwnProperty('deadline_timer'))
                    delete this.props.data.deadline_timer;
                this.clearScheduleTimeout();
            });
    }

    // [ Network game notifications.

    /**
     * Return True if given network game is the game currently displayed on the interface.
     * @param {NetworkGame} networkGame - network game to check
     * @returns {boolean}
     */
    networkGameIsDisplayed(networkGame) {
        return this.getPage().getName() === `game: ${networkGame.local.game_id}`;
    }

    notifiedNetworkGame(networkGame, notification) {
        if (this.networkGameIsDisplayed(networkGame)) {
            const msg = `Game (${networkGame.local.game_id}) received notification ${notification.name}.`;
            this.reloadDeadlineTimer(networkGame);
            return this.forceUpdate().then(() => this.getPage().info(msg));
        }
        return noPromise();
    }

    notifiedPowersControllers(networkGame, notification) {
        if (networkGame.local.isPlayerGame() && (
            !networkGame.channel.game_id_to_instances.hasOwnProperty(networkGame.local.game_id)
            || !networkGame.channel.game_id_to_instances[networkGame.local.game_id].has(networkGame.local.role)
        )) {
            // This power game is now invalid.
            return this.getPage().disconnectGame(networkGame.local.game_id)
                .then(() => {
                    if (this.networkGameIsDisplayed(networkGame)) {
                        return this.getPage().loadGames(
                            {error: `${networkGame.local.game_id}/${networkGame.local.role} was kicked. Deadline over?`});
                    }
                });
        } else {
            return this.notifiedNetworkGame(networkGame, notification);
        }
    }

    notifiedGamePhaseUpdated(networkGame, notification) {
        return networkGame.getAllPossibleOrders()
            .then(allPossibleOrders => {
                networkGame.local.setPossibleOrders(allPossibleOrders);
                if (this.networkGameIsDisplayed(networkGame)) {
                    this.__store_orders(null);
                    this.reloadDeadlineTimer(networkGame);
                    return this.setState({orders: null, messageHighlights: {}, orderBuildingPath: []})
                        .then(() => this.getPage().info(
                            `Game update (${notification.name}) to ${networkGame.local.phase}.`));
                }
            })
            .catch(error => this.getPage().error('Error when updating possible orders: ' + error.toString()));
    }

    notifiedLocalStateChange(networkGame, notification) {
        return networkGame.getAllPossibleOrders()
            .then(allPossibleOrders => {
                networkGame.local.setPossibleOrders(allPossibleOrders);
                if (this.networkGameIsDisplayed(networkGame)) {
                    this.reloadDeadlineTimer(networkGame);
                    let result = null;
                    if (notification.power_name) {
                        result = this.reloadPowerServerOrders(notification.power_name);
                    } else {
                        result = this.forceUpdate();
                    }
                    return result.then(() => this.getPage().info(`Possible orders re-loaded.`));
                }
            })
            .catch(error => this.getPage().error('Error when updating possible orders: ' + error.toString()));
    }

    notifiedNewGameMessage(networkGame, notification) {
        let protagonist = notification.message.sender;
        if (notification.message.recipient === 'GLOBAL')
            protagonist = notification.message.recipient;
        const messageHighlights = Object.assign({}, this.state.messageHighlights);
        if (!messageHighlights.hasOwnProperty(protagonist))
            messageHighlights[protagonist] = 1;
        else
            ++messageHighlights[protagonist];
        return this.setState({messageHighlights: messageHighlights})
            .then(() => this.notifiedNetworkGame(networkGame, notification));
    }

    bindCallbacks(networkGame) {
        const collector = (game, notification) => {
            game.queue.append(notification);
        };
        const consumer = (notification) => {
            switch (notification.name) {
                case 'powers_controllers':
                    return this.notifiedPowersControllers(networkGame, notification);
                case 'game_message_received':
                    return this.notifiedNewGameMessage(networkGame, notification);
                case 'game_processed':
                case 'game_phase_update':
                    return this.notifiedGamePhaseUpdated(networkGame, notification);
                case 'cleared_centers':
                case 'cleared_orders':
                case 'cleared_units':
                case 'power_orders_update':
                case 'power_orders_flag':
                case 'game_status_update':
                case 'omniscient_updated':
                case 'power_vote_updated':
                case 'power_wait_flag':
                case 'vote_count_updated':
                case 'vote_updated':
                    return this.notifiedNetworkGame(networkGame, notification);
                default:
                    throw new Error(`Unhandled notification: ${notification.name}`);
            }
        };
        if (!networkGame.callbacksBound) {
            networkGame.queue = new Queue();
            networkGame.addOnClearedCenters(collector);
            networkGame.addOnClearedOrders(collector);
            networkGame.addOnClearedUnits(collector);
            networkGame.addOnPowerOrdersUpdate(collector);
            networkGame.addOnPowerOrdersFlag(collector);
            networkGame.addOnPowersControllers(collector);
            networkGame.addOnGameMessageReceived(collector);
            networkGame.addOnGameProcessed(collector);
            networkGame.addOnGamePhaseUpdate(collector);
            networkGame.addOnGameStatusUpdate(collector);
            networkGame.addOnOmniscientUpdated(collector);
            networkGame.addOnPowerVoteUpdated(collector);
            networkGame.addOnPowerWaitFlag(collector);
            networkGame.addOnVoteCountUpdated(collector);
            networkGame.addOnVoteUpdated(collector);
            networkGame.callbacksBound = true;
            networkGame.local.markAllMessagesRead();
            networkGame.queue.consumeAsync(consumer);
        }
    }

    // ]

    onChangeCurrentPower(event) {
        return this.setState({power: event.target.value, tabPastMessages: null, tabCurrentMessages: null});
    }

    onChangeMainTab(tab) {
        return this.setState({tabMain: tab});
    }

    onChangeTabCurrentMessages(tab) {
        return this.setState({tabCurrentMessages: tab});
    }

    onChangeTabPastMessages(tab) {
        return this.setState({tabPastMessages: tab});
    }

    sendMessage(networkGame, recipient, body) {
        const engine = networkGame.local;
        const message = new Message({
            phase: engine.phase,
            sender: engine.role,
            recipient: recipient,
            message: body
        });
        const page = this.getPage();
        networkGame.sendGameMessage({message: message})
            .then(() => {
                page.load(
                    `game: ${engine.game_id}`,
                    <ContentGame data={engine}/>,
                    {success: `Message sent: ${JSON.stringify(message)}`}
                );
            })
            .catch(error => page.error(error.toString()));
    }

    onProcessGame() {
        const page = this.getPage();
        this.props.data.client.process()
            .then(() => page.success('Game processed.'))
            .catch(err => {
                page.error(err.toString());
            });
    }

    /**
     * Get name of current power selected on the game page.
     * @returns {null|string}
     */
    getCurrentPowerName() {
        const engine = this.props.data;
        const controllablePowers = engine.getControllablePowers();
        return this.state.power || (controllablePowers.length && controllablePowers[0]);
    }

    // [ Methods involved in orders management.

    /**
     * Return a dictionary of local orders for given game engine.
     * Returned dictionary maps each power name to either:
     * - a dictionary of orders, mapping a location to an Order object with boolean flag `local` correctly set
     *   to determine if that order is a new local order or is a copy of an existing server order for this power.
     * - null or empty dictionary, if there are no local orders defined for this power.
     * @param {Game} engine - game engine from which we must get local orders
     * @returns {{}}
     * @private
     */
    __get_orders(engine) {
        const orders = engine.getServerOrders();
        if (this.state.orders) {
            for (let powerName of Object.keys(orders)) {
                const serverPowerOrders = orders[powerName];
                const localPowerOrders = this.state.orders[powerName];
                if (localPowerOrders) {
                    for (let localOrder of Object.values(localPowerOrders)) {
                        localOrder.local = (
                            !serverPowerOrders
                            || !serverPowerOrders.hasOwnProperty(localOrder.loc)
                            || serverPowerOrders[localOrder.loc].order !== localOrder.order
                        );
                    }
                }
                orders[powerName] = localPowerOrders;
            }
        }
        return orders;
    }

    /**
     * Save given orders into local storage.
     * @param orders - orders to save
     * @private
     */
    __store_orders(orders) {
        const username = this.props.data.client.channel.username;
        const gameID = this.props.data.game_id;
        const gamePhase = this.props.data.phase;
        if (!orders)
            return DipStorage.clearUserGameOrders(username, gameID);
        for (let entry of Object.entries(orders)) {
            const powerName = entry[0];
            let powerOrdersList = null;
            if (entry[1])
                powerOrdersList = Object.values(entry[1]).map(order => order.order);
            DipStorage.clearUserGameOrders(username, gameID, powerName);
            DipStorage.addUserGameOrders(username, gameID, gamePhase, powerName, powerOrdersList);
        }
    }

    /**
     * Reset local orders and replace them with current server orders for given power.
     * @param {string} powerName - name of power to update
     */
    reloadPowerServerOrders(powerName) {
        const serverOrders = this.props.data.getServerOrders();
        const engine = this.props.data;
        const allOrders = this.__get_orders(engine);
        if (!allOrders.hasOwnProperty(powerName)) {
            return this.getPage().error(`Unknown power ${powerName}.`);
        }
        allOrders[powerName] = serverOrders[powerName];
        this.__store_orders(allOrders);
        return this.setState({orders: allOrders});
    }

    /**
     * Reset local orders and replace them with current server orders for current selected power.
     */
    reloadServerOrders() {
        this.setState({orderBuildingPath: []}).then(() => {
            const currentPowerName = this.getCurrentPowerName();
            if (currentPowerName) {
                this.reloadPowerServerOrders(currentPowerName);
            }
        });
    }

    /**
     * Remove given order from local orders of given power name.
     * @param {string} powerName - power name
     * @param {Order} order - order to remove
     */
    onRemoveOrder(powerName, order) {
        const orders = this.__get_orders(this.props.data);
        if (orders.hasOwnProperty(powerName)
            && orders[powerName].hasOwnProperty(order.loc)
            && orders[powerName][order.loc].order === order.order) {
            delete orders[powerName][order.loc];
            if (!UTILS.javascript.count(orders[powerName]))
                orders[powerName] = null;
            this.__store_orders(orders);
            this.setState({orders: orders});
        }
    }

    /**
     * Remove all local orders for current selected power, including empty orders set.
     * Equivalent request is clearOrders().
     */
    onRemoveAllCurrentPowerOrders() {
        const currentPowerName = this.getCurrentPowerName();
        if (currentPowerName) {
            const engine = this.props.data;
            const allOrders = this.__get_orders(engine);
            if (!allOrders.hasOwnProperty(currentPowerName)) {
                this.getPage().error(`Unknown power ${currentPowerName}.`);
                return;
            }
            allOrders[currentPowerName] = null;
            this.__store_orders(allOrders);
            this.setState({orders: allOrders});
        }
    }

    /**
     * Set an empty local orders set for given power name.
     * @param {string} powerName - power name
     */
    onSetEmptyOrdersSet(powerName) {
        const orders = this.__get_orders(this.props.data);
        orders[powerName] = {};
        this.__store_orders(orders);
        return this.setState({orders: orders});
    }

    /**
     * Send local orders to server.
     */
    setOrders() {
        const serverOrders = this.props.data.getServerOrders();
        const orders = this.__get_orders(this.props.data);

        for (let entry of Object.entries(orders)) {
            const powerName = entry[0];
            const localPowerOrders = entry[1] ? Object.values(entry[1]).map(orderEntry => orderEntry.order) : null;
            const serverPowerOrders = serverOrders[powerName] ? Object.values(serverOrders[powerName]).map(orderEntry => orderEntry.order) : null;
            let same = false;

            if (serverPowerOrders === null) {
                // No orders set on server.
                same = localPowerOrders === null;
                // Otherwise, we have local orders set (even empty local orders).
            } else if (serverPowerOrders.length === 0) {
                // Empty orders set on server.
                // If we have empty orders set locally, then it's same thing.
                same = localPowerOrders && localPowerOrders.length === 0;
                // Otherwise, we have either local non-empty orders set or local null order.
            } else {
                // Orders set on server. Identical to local orders only if we have exactly same orders on server and locally.
                if (localPowerOrders && localPowerOrders.length === serverPowerOrders.length) {
                    localPowerOrders.sort();
                    serverPowerOrders.sort();
                    same = true;
                    for (let i = 0; i < localPowerOrders.length; ++i) {
                        if (localPowerOrders[i] !== serverPowerOrders[i]) {
                            same = false;
                            break;
                        }
                    }
                }
            }

            if (same) {
                Diplog.warn(`Orders not changed for ${powerName}.`);
                continue;
            }

            Diplog.info(`Sending orders for ${powerName}: ${localPowerOrders ? JSON.stringify(localPowerOrders) : null}`);
            let requestCall = null;
            if (localPowerOrders) {
                requestCall = this.props.data.client.setOrders({power_name: powerName, orders: localPowerOrders});
            } else {
                requestCall = this.props.data.client.clearOrders({power_name: powerName});
            }
            requestCall
                .then(() => {
                    this.getPage().success('Orders sent.');
                })
                .catch(err => {
                    this.getPage().error(err.toString());
                })
                .then(() => {
                    this.reloadServerOrders();
                });
        }
    }

    // ]

    onOrderBuilding(powerName, path) {
        const pathToSave = path.slice(1);
        return this.setState({orderBuildingPath: pathToSave})
            .then(() => this.getPage().success(`Building order ${pathToSave.join(' ')} ...`));
    }

    onOrderBuilt(powerName, orderString) {
        const state = Object.assign({}, this.state);
        state.orderBuildingPath = [];
        if (!orderString) {
            Diplog.warn('No order built.');
            return this.setState(state);
        }
        const engine = this.props.data;
        const localOrder = new Order(orderString, true);
        const allOrders = this.__get_orders(engine);
        if (!allOrders.hasOwnProperty(powerName)) {
            Diplog.warn(`Unknown power ${powerName}.`);
            return this.setState(state);
        }

        if (!allOrders[powerName])
            allOrders[powerName] = {};
        allOrders[powerName][localOrder.loc] = localOrder;
        state.orders = allOrders;
        this.getPage().success(`Built order: ${orderString}`);
        this.__store_orders(allOrders);
        return this.setState(state);
    }

    onChangeOrderType(form) {
        return this.setState({
            orderBuildingType: form.order_type,
            orderBuildingPath: [],
        });
    }

    vote(decision) {
        const engine = this.props.data;
        const networkGame = engine.client;
        const controllablePowers = engine.getControllablePowers();
        const currentPowerName = this.state.power || (controllablePowers.length ? controllablePowers[0] : null);
        if (!currentPowerName)
            throw new Error(`Internal error: unable to detect current selected power name.`);
        networkGame.vote({power_name: currentPowerName, vote: decision})
            .then(() => this.getPage().success(`Vote set to ${decision} for ${currentPowerName}`))
            .catch(error => {
                Diplog.error(error.stack);
                this.getPage().error(`Error while setting vote for ${currentPowerName}: ${error.toString()}`);
            });
    }

    setWaitFlag(waitFlag) {
        const engine = this.props.data;
        const networkGame = engine.client;
        const controllablePowers = engine.getControllablePowers();
        const currentPowerName = this.state.power || (controllablePowers.length ? controllablePowers[0] : null);
        if (!currentPowerName)
            throw new Error(`Internal error: unable to detect current selected power name.`);
        networkGame.setWait(waitFlag, {power_name: currentPowerName})
            .then(() => {
                this.forceUpdate(() => this.getPage().success(`Wait flag set to ${waitFlag} for ${currentPowerName}`));
            })
            .catch(error => {
                Diplog.error(error.stack);
                this.getPage().error(`Error while setting wait flag for ${currentPowerName}: ${error.toString()}`);
            });
    }

    __change_past_phase(newPhaseIndex) {
        return this.setState({
            historyPhaseIndex: newPhaseIndex,
            historyCurrentLoc: null,
            historyCurrentOrders: null
        });
    }

    onChangePastPhase(event) {
        this.__change_past_phase(event.target.value);
    }

    onChangePastPhaseIndex(increment) {
        const selectObject = document.getElementById('select-past-phase');
        if (selectObject) {
          const index = selectObject.selectedIndex;
          const newIndex = index + (increment ? 1 : -1);
          if (newIndex >= 0 && newIndex < selectObject.length) {
            selectObject.selectedIndex = newIndex;
            // Ensure we do parseInt with a base of 10
            this.__change_past_phase(parseInt(selectObject.options[newIndex].value, 10));
          }
        }
      }

    onIncrementPastPhase(event) {
        this.onChangePastPhaseIndex(true);
        if (event && event.preventDefault)
            event.preventDefault();
    }

    onDecrementPastPhase(event) {
        this.onChangePastPhaseIndex(false);
        if (event && event.preventDefault)
            event.preventDefault();
    }

    displayFirstPastPhase() {
        this.__change_past_phase(0, 0);
    }

    displayLastPastPhase() {
        this.__change_past_phase(-1, 1);
    }

    onChangeShowPastOrders(event) {
        return this.setState({historyShowOrders: event.target.checked});
    }

    onChangeShowAbbreviations(event) {
        return this.setState({showAbbreviations: event.target.checked});
    }

    onClickMessage(message) {
        if (!message.read) {
            message.read = true;
            let protagonist = message.sender;
            if (message.recipient === 'GLOBAL')
                protagonist = message.recipient;
            this.getPage().load(`game: ${this.props.data.game_id}`, <ContentGame data={this.props.data}/>);
            if (this.state.messageHighlights.hasOwnProperty(protagonist) && this.state.messageHighlights[protagonist] > 0) {
                const messageHighlights = Object.assign({}, this.state.messageHighlights);
                --messageHighlights[protagonist];
                this.setState({messageHighlights: messageHighlights});
            }
        }
    }

    displayLocationOrders(loc, orders) {
        return this.setState({
            historyCurrentLoc: loc || null,
            historyCurrentOrders: orders && orders.length ? orders : null
        });
    }

    // [ Rendering methods.

    renderOrders(engine, currentPowerName) {
        const serverOrders = this.props.data.getServerOrders();
        const orders = this.__get_orders(engine);
        const wait = ContentGame.getServerWaitFlags(engine);

        const render = [];
        render.push(<PowerOrders key={currentPowerName} name={currentPowerName} wait={wait[currentPowerName]}
                                 orders={orders[currentPowerName]}
                                 serverCount={serverOrders[currentPowerName] ? UTILS.javascript.count(serverOrders[currentPowerName]) : -1}
                                 onRemove={this.onRemoveOrder}/>);
        return render;
    }

    renderPastMessages(engine, role) {
        const messageChannels = engine.getMessageChannels(role, true);
        const tabNames = [];
        for (let powerName of Object.keys(engine.powers)) {
          if (powerName !== role) tabNames.push(powerName);
        }
        tabNames.sort();
        tabNames.push('GLOBAL');
        const titles = tabNames.map(tabName => (tabName === 'GLOBAL' ? tabName : tabName.substr(0, 3)));
        const currentTabId = this.state.tabPastMessages || tabNames[0];
            
       
      
        return (
          <div className={'panel-messages'} key={'panel-messages'}>
                {/* Messages. */}
                <Tabs menu={tabNames} titles={titles} onChange={this.onChangeTabPastMessages} active={currentTabId}>
                    {tabNames.map(protagonist => (
                        <Tab key={protagonist} className={'game-messages'} display={currentTabId === protagonist}>
                            {(!messageChannels.hasOwnProperty(protagonist) || !messageChannels[protagonist].length ?
                                    (<div className={'no-game-message'}>No
                                        messages{engine.isPlayerGame() ? ` with ${protagonist}` : ''}.</div>) :
                                    messageChannels[protagonist].map((message, index) => (
                                        <MessageView key={index} phase={engine.phase} owner={role} message={message}
                                                     read={true}/>
                                    ))
                            )}
                        </Tab>
                    ))}
                </Tabs>
            </div>
        );
    }

    renderCurrentMessages(engine, role) {
        const messageChannels = engine.getMessageChannels(role, true);
        console.log('messageChannels =>', messageChannels);
        const tabNames = [];
        for (let powerName of Object.keys(engine.powers)) if (powerName !== role)
            tabNames.push(powerName);
        tabNames.sort();
        tabNames.push('GLOBAL');
        const titles = tabNames.map(tabName => (tabName === 'GLOBAL' ? tabName : tabName.substr(0, 3)));
        const currentTabId = this.state.tabCurrentMessages || tabNames[0];
        const highlights = this.state.messageHighlights;
        const unreadMarked = new Set();

        return (
            <div className={'panel-messages'} key={'panel-messages'}>
                {/* Messages. */}
                <Tabs menu={tabNames} titles={titles} onChange={this.onChangeTabCurrentMessages} active={currentTabId}
                      highlights={highlights}>
                    {tabNames.map(protagonist => (
                        <Tab key={protagonist} className={'game-messages'} display={currentTabId === protagonist}
                             id={`panel-current-messages-${protagonist}`}>
                            {(!messageChannels.hasOwnProperty(protagonist) || !messageChannels[protagonist].length ?
                                    (<div className={'no-game-message'}>No
                                        messages{engine.isPlayerGame() ? ` with ${protagonist}` : ''}.</div>) :
                                    (messageChannels[protagonist].map((message, index) => {
                                        let id = null;
                                        if (!message.read && !unreadMarked.has(protagonist)) {
                                            if (engine.isOmniscientGame() || message.sender !== role) {
                                                unreadMarked.add(protagonist);
                                                id = `${protagonist}-unread`;
                                            }
                                        }
                                        return <MessageView key={index} phase={engine.phase} owner={role}
                                                            message={message}
                                                            read={message.phase !== engine.phase}
                                                            id={id} onClick={this.onClickMessage}/>;
                                    }))
                            )}
                        </Tab>
                    ))}
                </Tabs>
                {/* Link to go to first unread received message. */}
                {unreadMarked.has(currentTabId) && (
                    <Scrollchor className={'link-unread-message'}
                                to={`${currentTabId}-unread`}
                                target={`panel-current-messages-${currentTabId}`}>
                        Go to 1st unread message
                    </Scrollchor>
                )}
                {/* Send form. */}
                {engine.isPlayerGame() && (
                    <MessageForm sender={role} recipient={currentTabId} onSubmit={form =>
                        this.sendMessage(engine.client, currentTabId, form.message)}/>)}
            </div>
        );
    }

    renderMapForResults(gameEngine, showOrders) {
        const Map = getMapComponent(gameEngine.map_name);
        return (
            <div id="past-map" key="past-map">
                <Map game={gameEngine}
                     showAbbreviations={this.state.showAbbreviations}
                     mapData={new MapData(this.getMapInfo(gameEngine.map_name), gameEngine)}
                     onError={this.getPage().error}
                     orders={(showOrders && gameEngine.order_history.contains(gameEngine.phase) && gameEngine.order_history.get(gameEngine.phase)) || null}
                     onHover={showOrders ? this.displayLocationOrders : null}
                     onSelectVia={this.onSelectVia}/>
            </div>
        );
    }

    renderMapForMessages(gameEngine, showOrders) {
        const Map = getMapComponent(gameEngine.map_name);
        return (
            <div id="messages-map" key="messages-map">
                <Map game={gameEngine}
                     showAbbreviations={this.state.showAbbreviations}
                     mapData={new MapData(this.getMapInfo(gameEngine.map_name), gameEngine)}
                     onError={this.getPage().error}
                     orders={(showOrders && gameEngine.order_history.contains(gameEngine.phase) && gameEngine.order_history.get(gameEngine.phase)) || null}
                     onHover={showOrders ? this.displayLocationOrders : null}
                     onSelectVia={this.onSelectVia}/>
            </div>
        );
    }

    renderMapForCurrent(gameEngine, powerName, orderType, orderPath) {
        const Map = getMapComponent(gameEngine.map_name);
        const rawOrders = this.__get_orders(gameEngine);
        const orders = {};
        for (let entry of Object.entries(rawOrders)) {
            orders[entry[0]] = [];
            if (entry[1]) {
                for (let orderObject of Object.values(entry[1]))
                    orders[entry[0]].push(orderObject.order);
            }
        }
        return (
            <div id="current-map" key="current-map">
                <Map game={gameEngine}
                     showAbbreviations={this.state.showAbbreviations}
                     mapData={new MapData(this.getMapInfo(gameEngine.map_name), gameEngine)}
                     onError={this.getPage().error}
                     orderBuilding={ContentGame.getOrderBuilding(powerName, orderType, orderPath)}
                     onOrderBuilding={this.onOrderBuilding}
                     onOrderBuilt={this.onOrderBuilt}
                     orders={orders}
                     onSelectLocation={this.onSelectLocation}
                     onSelectVia={this.onSelectVia}/>
            </div>
        );
    }

    __get_engine_to_display(initialEngine) {
        const pastPhases = initialEngine.state_history.values().map(state => state.name);
        pastPhases.push(initialEngine.phase);
        let phaseIndex = 0;
        if (initialEngine.displayed) {
            if (this.state.historyPhaseIndex === null || this.state.historyPhaseIndex >= pastPhases.length) {
                phaseIndex = pastPhases.length - 1;
            } else if (this.state.historyPhaseIndex < 0) {
                phaseIndex = pastPhases.length + this.state.historyPhaseIndex;
            } else {
                phaseIndex = this.state.historyPhaseIndex;
            }
        }
        const engine = (
            pastPhases[phaseIndex] === initialEngine.phase ?
                initialEngine : initialEngine.cloneAt(pastPhases[phaseIndex])
        );
        return {engine, pastPhases, phaseIndex};
    }

    __form_phases(pastPhases, phaseIndex) {
        return (
            <form key={1} className="form-inline mb-4">
                <div className="custom-control-inline">
                    <Button title={UTILS.html.UNICODE_LEFT_ARROW} onClick={this.onDecrementPastPhase} pickEvent={true}
                            disabled={phaseIndex === 0}/>
                </div>
                <div className="custom-control-inline">
                    <select className="custom-select"
                            id="select-past-phase"
                            value={phaseIndex}
                            onChange={this.onChangePastPhase}>
                        {pastPhases.map((phaseName, index) => <option key={index} value={index}>{phaseName}</option>)}
                    </select>
                </div>
                <div className="custom-control-inline">
                    <Button title={UTILS.html.UNICODE_RIGHT_ARROW} onClick={this.onIncrementPastPhase} pickEvent={true}
                            disabled={phaseIndex === pastPhases.length - 1}/>
                </div>
                <div className="custom-control custom-control-inline custom-checkbox">
                    <input className="custom-control-input" id="show-orders" type="checkbox"
                           checked={this.state.historyShowOrders} onChange={this.onChangeShowPastOrders}/>
                    <label className="custom-control-label" htmlFor="show-orders">Show orders</label>
                </div>
            </form>
        );
    }

    renderTabResults(toDisplay, initialEngine) {
        const {
            engine: displayedEngine,
            pastPhases,
            phaseIndex
        } = this.__get_engine_to_display(initialEngine);
        let orders = {};
        let orderResult = null;
        if (displayedEngine.order_history.contains(displayedEngine.phase))
            orders = displayedEngine.order_history.get(displayedEngine.phase);
        if (displayedEngine.result_history.contains(displayedEngine.phase))
            orderResult = displayedEngine.result_history.get(displayedEngine.phase);
        let countOrders = 0;
        for (let powerOrders of Object.values(orders)) {
            if (powerOrders)
                countOrders += powerOrders.length;
        }
        const powerNames = Object.keys(orders);
        powerNames.sort();

        const getOrderResult = (order) => {
            if (orderResult) {
                const pieces = order.split(/ +/);
                const unit = `${pieces[0]} ${pieces[1]}`;
                if (orderResult.hasOwnProperty(unit)) {
                    const resultsToParse = orderResult[unit];
                    if (!resultsToParse.length)
                        resultsToParse.push('');
                    const results = [];
                    for (let r of resultsToParse) {
                        if (results.length)
                            results.push(', ');
                        results.push(<span key={results.length} className={r || 'success'}>{r || 'OK'}</span>);
                    }
                    return <span className={'order-result'}> ({results})</span>;
                }
            }
            return '';
        };

        const orderView = [
            this.__form_phases(pastPhases, phaseIndex),
            (((countOrders && (
                    <div key={2} className={'past-orders container'}>
                        {powerNames.map(powerName => !orders[powerName] || !orders[powerName].length ? '' : (
                            <div key={powerName} className={'row'}>
                                <div className={'past-power-name col-sm-2'}>{powerName}</div>
                                <div className={'past-power-orders col-sm-10'}>
                                    {orders[powerName].map((order, index) => (
                                        <div key={index}>{order}{getOrderResult(order)}</div>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                )) || <div key={2} className={'no-orders'}>No orders for this phase!</div>
            ))
        ];

        return (
            <Tab id={'tab-phase-history'} display={toDisplay}>
                <Row>
                    <div className={'col-xl'}>
                        {this.state.historyCurrentOrders && (
                            <div className={'history-current-orders'}>{this.state.historyCurrentOrders.join(', ')}</div>
                        )}
                        {this.renderMapForResults(displayedEngine, this.state.historyShowOrders)}
                    </div>
                    <div className={'col-xl'}>{orderView}</div>
                </Row>
                {toDisplay && <HotKey keys={['arrowleft']} onKeysCoincide={this.onDecrementPastPhase}/>}
                {toDisplay && <HotKey keys={['arrowright']} onKeysCoincide={this.onIncrementPastPhase}/>}
                {toDisplay && <HotKey keys={['home']} onKeysCoincide={this.displayFirstPastPhase}/>}
                {toDisplay && <HotKey keys={['end']} onKeysCoincide={this.displayLastPastPhase}/>}
            </Tab>
        );
    }

    renderTabMessages(toDisplay, initialEngine, currentPowerName) {
        const {
            engine: displayedEngine,
            pastPhases,
            phaseIndex
        } = this.__get_engine_to_display(initialEngine);
        const messageChannels = displayedEngine.getMessageChannels(currentPowerName, true);
        const tabNames = [];
        for (let powerName of Object.keys(displayedEngine.powers)) {
            if (powerName !== currentPowerName) tabNames.push(powerName);
        }
        tabNames.sort();
        tabNames.push('GLOBAL');
        const titles = tabNames.map(tabName => (tabName === 'GLOBAL' ? tabName : tabName.substr(0, 3)));
        const currentTabId = this.state.tabPastMessages || tabNames[0];
            
        return (
            <Tab id={'tab-phase-history'} display={toDisplay}>
                <Row>
                    <div className={'col-xl'}>
                        {this.state.historyCurrentOrders && (
                            <div className={'history-current-orders'}>{this.state.historyCurrentOrders.join(', ')}</div>
                        )}
                        {this.renderMapForMessages(displayedEngine, this.state.historyShowOrders)}
                    </div>
                    <div className={'col-xl'}>
                        {this.__form_phases(pastPhases, phaseIndex)}
                        {pastPhases[phaseIndex] === initialEngine.phase ? (
                            this.renderCurrentMessages(displayedEngine, currentPowerName)
                        ) : (
                            this.renderPastMessages(displayedEngine, currentPowerName)
                        )}
                    </div>
                </Row>
                {toDisplay && <HotKey keys={['arrowleft']} onKeysCoincide={this.onDecrementPastPhase}/>}
                {toDisplay && <HotKey keys={['arrowright']} onKeysCoincide={this.onIncrementPastPhase}/>}
                {toDisplay && <HotKey keys={['home']} onKeysCoincide={this.displayFirstPastPhase}/>}
                {toDisplay && <HotKey keys={['end']} onKeysCoincide={this.displayLastPastPhase}/>}
            </Tab>
        );
    }

    renderTabCurrentPhase(toDisplay, engine, powerName, orderType, orderPath, currentPowerName, currentTabOrderCreation) {
        const powerNames = Object.keys(engine.powers);
        powerNames.sort();
        const orderedPowers = powerNames.map(pn => engine.powers[pn]);
        return (
            <Tab id={'tab-current-phase'} display={toDisplay}>
                <Row>
                    <div className={'col-xl'}>
                        {this.renderMapForCurrent(engine, powerName, orderType, orderPath)}
                    </div>
                    <div className={'col-xl'}>
                        {/* Orders. */}
                        <div className={'panel-orders mb-4'}>
                            {currentTabOrderCreation ? <div className="mb-4">{currentTabOrderCreation}</div> : ''}
                            <PowerOrdersActionBar
                                onReset={this.reloadServerOrders}
                                onDeleteAll={this.onRemoveAllCurrentPowerOrders}
                                onUpdate={this.setOrders}
                                onProcess={(!this.props.data.isPlayerGame()
                                    && this.props.data.observer_level === STRINGS.MASTER_TYPE) ?
                                    this.onProcessGame : null}/>
                            <div className={'orders'}>{this.renderOrders(this.props.data, powerName)}</div>
                            <div className={'table-responsive'}>
                                <Table className={'table table-striped table-sm'}
                                       caption={'Powers info'}
                                       columns={TABLE_POWER_VIEW}
                                       data={orderedPowers}
                                       wrapper={PowerView.wrap}/>
                            </div>
                        </div>
                    </div>
                </Row>
            </Tab>
        );
    }

    // ]

    // [ React.Component overridden methods.

    render() {
        const page = this.context;
        const engine = this.props.data;

        // 1) Quick log to confirm engine is not null/undefined
        console.log("Render content_game with engine:", engine);

        if (!engine) {
            console.warn("Engine is null or undefined. Rendering fallback or forcing a logout?");
            return <main><div>Error: No engine found.</div></main>;
        }

        this.props.data.displayed = true;
        const title = ContentGame.gameTitle(engine);
        const navigation = [
            ['Help', () => page.dialog(onClose => <Help onClose={onClose}/>)],
            ['Load a game from disk', page.loadGameFromDisk],
            ['Save game to disk', () => saveGameToDisk(engine, page.error)],
            [`${UTILS.html.UNICODE_SMALL_LEFT_ARROW} Games`, () => page.loadGames()],
            [`${UTILS.html.UNICODE_SMALL_LEFT_ARROW} Leave game`, () => page.leaveGame(engine.game_id)],
            [`${UTILS.html.UNICODE_SMALL_LEFT_ARROW} Logout`, page.logout]
        ];
        const phaseType = engine.getPhaseType();
        const controllablePowers = engine.getControllablePowers();
        if (this.props.data.client)
            this.bindCallbacks(this.props.data.client);

        if (engine.phase === 'FORMING')
            return <main>
                <div className={'forming'}>Game not yet started!</div>
            </main>;

        const tabNames = [];
        const tabTitles = [];
        let hasTabPhaseHistory = false;
        let hasTabCurrentPhase = false;
        if (engine.state_history.size()) {
            hasTabPhaseHistory = true;
            tabNames.push('phase_history');
            tabTitles.push('Results');
        }
        tabNames.push('messages');
        tabTitles.push('Messages');
        if (controllablePowers.length && phaseType && !engine.isObserverGame()) {
            hasTabCurrentPhase = true;
            tabNames.push('current_phase');
            tabTitles.push('Current');
        }
        if (!tabNames.length) {
            // This should never happen, but let's display this message.
            return <main>
                <div className={'no-data'}>No data in this game!</div>
            </main>;
        }
        const mainTab = this.state.tabMain && tabNames.includes(this.state.tabMain) ? this.state.tabMain : tabNames[tabNames.length - 1];

        const currentPowerName = this.state.power || (controllablePowers.length && controllablePowers[0]);
        let currentPower = null;
        let orderTypeToLocs = null;
        let allowedPowerOrderTypes = null;
        let orderBuildingType = null;
        let buildCount = null;
        if (hasTabCurrentPhase) {
            currentPower = engine.getPower(currentPowerName);
            orderTypeToLocs = engine.getOrderTypeToLocs(currentPowerName);
            allowedPowerOrderTypes = Object.keys(orderTypeToLocs);
            // canOrder = allowedPowerOrderTypes.length
            if (allowedPowerOrderTypes.length) {
                POSSIBLE_ORDERS.sortOrderTypes(allowedPowerOrderTypes, phaseType);
                if (this.state.orderBuildingType && allowedPowerOrderTypes.includes(this.state.orderBuildingType))
                    orderBuildingType = this.state.orderBuildingType;
                else
                    orderBuildingType = allowedPowerOrderTypes[0];
            }
            buildCount = engine.getBuildsCount(currentPowerName);
        }

        const navAfterTitle = (
            <form className="form-inline form-current-power">
                {(controllablePowers.length === 1 &&
                    <span className="power-name">{controllablePowers[0]}</span>) || (
                    <div className="custom-control custom-control-inline">
                        <label className="sr-only" htmlFor="current-power">power</label>
                        <select className="form-control custom-select custom-control-inline" id="current-power"
                                value={currentPowerName} onChange={this.onChangeCurrentPower}>
                            {controllablePowers.map(
                                powerName => <option key={powerName} value={powerName}>{powerName}</option>)}
                        </select>
                    </div>
                )}
                <div className="custom-control custom-control-inline custom-checkbox">
                    <input className="custom-control-input" id="show-abbreviations" type="checkbox"
                           checked={this.state.showAbbreviations} onChange={this.onChangeShowAbbreviations}/>
                    <label className="custom-control-label" htmlFor="show-abbreviations">Show abbreviations</label>
                </div>
            </form>
        );

        const currentTabOrderCreation = hasTabCurrentPhase && (
            <div>
                <PowerOrderCreationForm orderType={orderBuildingType}
                                        orderTypes={allowedPowerOrderTypes}
                                        onChange={this.onChangeOrderType}
                                        onPass={() => this.onSetEmptyOrdersSet(currentPowerName)}
                                        onSetWaitFlag={() => this.setWaitFlag(!currentPower.wait)}
                                        onVote={this.vote}
                                        role={engine.role}
                                        power={currentPower}/>
                {(allowedPowerOrderTypes.length && (
                    <span>
                                <strong>Orderable locations</strong>: {orderTypeToLocs[orderBuildingType].join(', ')}
                            </span>
                ))
                || (<strong>&nbsp;No orderable location.</strong>)}
                {phaseType === 'A' && (
                    (buildCount === null && (
                        <strong>&nbsp;(unknown build count)</strong>
                    ))
                    || (buildCount === 0 ? (
                        <strong>&nbsp;(nothing to build or disband)</strong>
                    ) : (buildCount > 0 ? (
                        <strong>&nbsp;({buildCount} unit{buildCount > 1 && 's'} may be built)</strong>
                    ) : (
                        <strong>&nbsp;({-buildCount} unit{buildCount < -1 && 's'} to disband)</strong>
                    )))
                )}
            </div>
        );

        // 1) Compute which engine & phase to display
        const {
            engine: displayedEngine,
            pastPhases,
            phaseIndex
        } = this.__get_engine_to_display(engine);

        // 2) Identify the actual current phase in the user's selection
        const currentPhase = pastPhases[phaseIndex];
        const summaryText =
            (engine.phase_summaries && engine.phase_summaries[currentPhase])
            ? engine.phase_summaries[currentPhase]
            : "";  // fallback if no summary

        console.log("[DEBUG content_game] Chosen phase:", currentPhase, 
                    "Summary length:", summaryText.length);

        // Example: Flatten messages from all known phases
        let allMessages = [];
        if (engine.message_history) {
            for (const phaseName of Object.keys(engine.message_history)) {
                const phaseMsgsDict = engine.message_history[phaseName];
                // Convert { time_sent: messageObj, ... } to an array
                const phaseMsgsArray = Object.values(phaseMsgsDict);
                allMessages = allMessages.concat(phaseMsgsArray);
            }
            console.log('engine.message_history =>', engine.message_history);
            for (const [key, value] of Object.entries(engine.message_history)) {
                console.log('key =>', key, 'value =>', value);
            }
        }

        console.log("DEBUG: content_game messages =>", allMessages, "length:", allMessages.length);

        return (
            <main>
                <Helmet>
                    <title>{title} | Diplomacy</title>
                </Helmet>
                <Navigation title={title}
                            afterTitle={navAfterTitle}
                            username={page.channel.username}
                            navigation={navigation}/>
                <Tabs menu={tabNames} titles={tabTitles} onChange={this.onChangeMainTab} active={mainTab}>
                    {/* Tab Phase history. */}
                    {(hasTabPhaseHistory && mainTab === 'phase_history' && this.renderTabResults(mainTab === 'phase_history', engine)) || ''}
                    {mainTab === 'messages' && this.renderTabMessages(mainTab === 'messages', engine, currentPowerName)}
                    {/* Tab Current phase. */}
                    {(mainTab === 'current_phase' && hasTabCurrentPhase && this.renderTabCurrentPhase(
                        mainTab === 'current_phase',
                        engine,
                        currentPowerName,
                        orderBuildingType,
                        this.state.orderBuildingPath,
                        currentPowerName,
                        currentTabOrderCreation
                    )) || ''}
                </Tabs>
                {/* Debug log before rendering the bottom sheet */}
                {console.log("Rendering PhaseSummaryBottomSheet with phase:", currentPhase, "summary length:", summaryText.length)}

                <PhaseSummaryBottomSheet
                    visible={this.state.summaryVisible}
                    phase={currentPhase}
                    summaryText={summaryText}
                    onClose={() => this.setState({ summaryVisible: false })}
                />
            </main>
        );
    }

    componentDidMount() {
        this._isMounted = true;
        window.scrollTo(0, 0);
        if (this.props.data.client) {
            this.reloadDeadlineTimer(this.props.data.client).then(() => {
                if (this._isMounted) {
                    this.setState({ doneLoading: true });
                }
            });
        }
        this.props.data.displayed = true;
        // Try to prevent scrolling when pressing keys Home and End.
        document.onkeydown = (event) => {
            if (['home', 'end'].includes(event.key.toLowerCase())) {
                // Try to prevent scrolling.
                if (event.hasOwnProperty('cancelBubble'))
                    event.cancelBubble = true;
                if (event.stopPropagation)
                    event.stopPropagation();
                if (event.preventDefault)
                    event.preventDefault();
            }
        };
    }

    componentDidUpdate() {
        this.props.data.displayed = true;
    }

    componentWillUnmount() {
        this._isMounted = false;
        this.clearScheduleTimeout();
        this.props.data.displayed = false;
        document.onkeydown = null;
    }

    // ]

}

ContentGame.contextType = PageContext;
ContentGame.propTypes = {
    data: PropTypes.instanceOf(Game).isRequired
};
