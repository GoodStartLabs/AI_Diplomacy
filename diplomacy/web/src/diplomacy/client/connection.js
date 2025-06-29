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
import {UTILS} from "../utils/utils";
import {REQUESTS} from "../communication/requests";
import {RESPONSES} from "../communication/responses";
import {NOTIFICATIONS} from "../communication/notifications";
import {RESPONSE_MANAGERS} from "./response_managers";
import {NOTIFICATION_MANAGERS} from "./notification_managers";
import {Future} from "../utils/future";
import {FutureEvent} from "../utils/future_event";
import {RequestFutureContext} from "./request_future_context";
import {Diplog} from "../utils/diplog";

class Reconnection {
    constructor(connection) {
        this.connection = connection;
        this.games_phases = {};
        this.n_expected_games = 0;
        this.n_synchronized_games = 0;
    }

    genSyncCallback(game) {
        const reconnection = this;
        return ((serverSyncResponse) => {
            reconnection.games_phases[game.local.game_id][game.local.game_role] = serverSyncResponse;
            ++reconnection.n_synchronized_games;
            if (reconnection.n_synchronized_games === reconnection.n_expected_games)
                reconnection.syncDone();
        });
    }

    reconnect() {
        for (let waitingContext of Object.values(this.connection.requestsWaitingResponses))
            waitingContext.request.re_sent = true;
        const lenWaiting = Object.keys(this.connection.requestsWaitingResponses).length;
        const lenBefore = Object.keys(this.connection.requestsToSend).length;
        Object.assign(this.connection.requestsToSend, this.connection.requestsWaitingResponses);
        const lenAfter = Object.keys(this.connection.requestsToSend).length;
        if (lenAfter !== lenWaiting + lenBefore)
            throw new Error('Programming error.');
        this.connection.requestsWaitingResponses = {};

        const requestsToSendUpdated = {};
        for (let context of Object.values(this.connection.requestsToSend)) {
            if (context.request.name === STRINGS.SYNCHRONIZE)
                context.future.setException(new Error('Sync request invalidated for game ID ' + context.request.game_id));
            else
                requestsToSendUpdated[context.request.request_id] = context;
        }
        this.connection.requestsToSend = requestsToSendUpdated;

        for (let channel of Object.values(this.connection.channels)) {
            for (let gis of Object.values(channel.game_id_to_instances)) {
                for (let game of gis.getGames()) {
                    const game_id = game.local.game_id;
                    const game_role = game.local.role;
                    if (!this.games_phases.hasOwnProperty(game_id))
                        this.games_phases[game_id] = {};
                    this.games_phases[game_id][game_role] = null;
                    ++this.n_expected_games;
                }
            }
        }

        if (this.n_expected_games) {
            for (let channel of Object.values(this.connection.channels))
                for (let gis of Object.values(channel.game_id_to_instances))
                    for (let game of gis.getGames())
                        game.synchronize().then(this.genSyncCallback(game));
        } else {
            this.syncDone();
        }
    }

    syncDone() {
        const requestsToSendUpdated = {};
        for (let context of Object.values(this.connection.requestsToSend)) {
            let keep = true;
            if (REQUESTS.isPhaseDependent(context.request.name)) {
                const request_phase = context.request.phase;
                const server_phase = this.games_phases[context.request.game_id][context.request.game_role].phase;
                if (request_phase !== server_phase) {
                    context.future.setException(new Error(
                        'Game ' + context.request.game_id + ': request ' + context.request.name +
                        ': request phase ' + request_phase + ' does not match current server game phase '
                        + server_phase + '.'));
                    keep = false;
                }
            }
            if (keep)
                requestsToSendUpdated[context.request.request_id] = context;
        }
        Diplog.info('Keep ' + Object.keys(requestsToSendUpdated).length + '/' +
            Object.keys(this.connection.requestsToSend).length + ' old request(s) to send.');
        this.connection.requestsToSend = requestsToSendUpdated;

        for (let context of Object.values(requestsToSendUpdated)) {
            this.connection.__write_request(context);
        }

        this.connection.isReconnecting.set();

        Diplog.info('Done reconnection work.');
    }
}

class ConnectionProcessing {
    constructor(connection, logger) {
        this.connection = connection;
        this.logger = logger || Diplog;
        this.isConnected = false;
        this.attemptIndex = 1;
        this.timeoutID = null;

        this.onSocketOpen = this.onSocketOpen.bind(this);
        this.onSocketTimeout = this.onSocketTimeout.bind(this);
        this.tryConnect = this.tryConnect.bind(this);
    }

    __on_error(error) {
        this.connection.isConnecting.set(error);
    }

    onSocketOpen(event) {
        this.isConnected = true;
        if (this.timeoutID) {
            clearTimeout(this.timeoutID);
            this.timeoutID = null;
        }
        // Socket open: set onMessage and onClose callbacks.
        this.connection.socket.onmessage = this.connection.onSocketMessage;
        this.connection.socket.onclose = this.connection.onSocketClose;
        this.connection.currentConnectionProcessing = null;
        this.connection.isConnecting.set();
        this.logger.info('Connection succeeds.');
    }

    onSocketTimeout() {
        if (!this.isConnected) {
            this.connection.socket.close();
            if (this.attemptIndex === UTILS.NB_CONNECTION_ATTEMPTS) {
                this.connection.isConnecting.set(
                    new Error(`${this.connection.isReconnecting.isWaiting() ? 'Reconnection' : 'Connection'} failed after ${UTILS.NB_CONNECTION_ATTEMPTS} attempts.`));
                return;
            }
            this.logger.warn('Connection failing (attempt ' + this.attemptIndex + '/' +
                UTILS.NB_CONNECTION_ATTEMPTS + '), retrying ...');
            ++this.attemptIndex;
            setTimeout(this.tryConnect, 0);
        }
    }

    tryConnect() {
        // When opening a socket, we configure only onOpen callback.
        // We will configure onMessage and onClose callbacks only when the socket will be effectively open.
        try {
            this.connection.socket = new WebSocket(this.connection.getUrl());
            this.connection.socket.onopen = this.onSocketOpen;
            this.timeoutID = setTimeout(this.onSocketTimeout, UTILS.ATTEMPT_DELAY_SECONDS * 1000);
        } catch (error) {
            this.__on_error(error);
        }
    }

    process() {
        this.connection.isConnecting.clear();
        if (this.connection.socket)
            this.connection.socket.close();
        this.tryConnect();
        return this.connection.isConnecting.wait();
    }

    stop() {
        if (!this.isConnected) {
            if (this.connection.socket)
                this.connection.socket.onopen = null;
            if (this.timeoutID) {
                clearTimeout(this.timeoutID);
                this.timeoutID = null;
            }
        }
    }
}

/** Class Connection (like Python class diplomacy.client.connection.Connection). **/
export class Connection {
    constructor(hostname, port, useSSL) {
        if (useSSL)
            Diplog.info(`Using SSL.`);
        this.protocol = useSSL ? 'wss' : 'ws';
        this.hostname = hostname;
        this.port = port;
        this.socket = null;
        this.isConnecting = new FutureEvent();
        this.isReconnecting = new FutureEvent();
        this.channels = {};
        this.requestsToSend = {};
        this.requestsWaitingResponses = {};
        this.currentConnectionProcessing = null;

        // Attribute used to make distinction between a connection
        // explicitly closed by client and a connection closed for
        // other unexpected reasons (e.g. by server).
        this.closed = false;

        this.onSocketMessage = this.onSocketMessage.bind(this);
        this.onSocketClose = this.onSocketClose.bind(this);

        this.isReconnecting.set();

        /** Public events. **/
        this.onReconnection = null;  // onReconnection()
        this.onReconnectionError = null; // onReconnectionError(error)
    }

    getUrl() {
        return this.protocol + '://' + this.hostname + ':' + this.port;
    }

    onSocketMessage(messageEvent) {
        /** Callback used to manage a socket message string.
         * Try-catch block will capture eventual:
         * - JSON parsing errors
         * - response parsing errors
         * - response handling errors
         * - notification parsing errors
         * - notification handling errors
         * **/
        try {
            const message = messageEvent.data;
            const jsonMessage = JSON.parse(message);
            if (!(jsonMessage instanceof Object)) {
                Diplog.error('Unable to convert a message to a JSON object.');
                return;
            }
            if (jsonMessage.request_id) {
                const requestID = jsonMessage.request_id;
                if (!this.requestsWaitingResponses.hasOwnProperty(requestID)) {
                    Diplog.error('Unknown request ' + requestID + '.');
                    return;
                }
                const context = this.requestsWaitingResponses[requestID];
                delete this.requestsWaitingResponses[requestID];
                try {
                    context.future.setResult(RESPONSE_MANAGERS.handleResponse(context, RESPONSES.parse(jsonMessage)));
                } catch (error) {
                    context.future.setException(error);
                }
            } else if (jsonMessage.hasOwnProperty('notification_id') && jsonMessage.notification_id)
                NOTIFICATION_MANAGERS.handleNotification(this, NOTIFICATIONS.parse(jsonMessage));
            else
                Diplog.error('Unknown socket message received.');
        } catch (error) {
            Diplog.error(error);
        }
    }

    onSocketClose(closeEvent) {
        if (this.closed)
            Diplog.info('Disconnected.');
        else {
            Diplog.error('Disconnected, trying to reconnect.');
            this.isReconnecting.clear();
            this.__connect()
                .then(() => {
                    new Reconnection(this).reconnect();
                    if (this.onReconnection)
                        this.onReconnection();
                })
                .catch(error => {
                    if (this.onReconnectionError)
                        this.onReconnectionError(error);
                    else
                        throw error;
                });
        }
    }

    __connect(logger) {
        if (this.currentConnectionProcessing) {
            this.currentConnectionProcessing.stop();
            this.currentConnectionProcessing = null;
        }
        this.currentConnectionProcessing = new ConnectionProcessing(this, logger);
        return this.currentConnectionProcessing.process();
    }

    __write_request(requestContext) {
        const writeFuture = new Future();
        const request = requestContext.request;
        const requestID = request.request_id;
        const connection = this;

        const onConnected = () => {
            connection.socket.send(JSON.stringify(request));
            connection.requestsWaitingResponses[requestID] = requestContext;
            if (connection.requestsToSend.hasOwnProperty(requestID)) {
                delete connection.requestsToSend[requestID];
            }
            writeFuture.setResult(null);
        };
        const onAnyError = (error) => {
            if (!connection.requestsToSend.hasOwnProperty(requestID)) {
                connection.requestsToSend[requestID] = requestContext;
            }
            Diplog.info('Error occurred while sending a request ' + requestID);
            writeFuture.setException(error);
        };
        if (request.name === STRINGS.SYNCHRONIZE)
            this.isConnecting.wait().then(onConnected, onAnyError);
        else
            this.isReconnecting.wait().then(onConnected, onAnyError);
        return writeFuture.promise();
    }

    connect(logger) {
        Diplog.info('Trying to connect.');
        return this.__connect(logger);
    }

    send(request, game = null) {
        const requestContext = new RequestFutureContext(request, this, game);
        this.__write_request(requestContext);
        return requestContext.future;
    }

    authenticate(username, password) {
        return this.send(REQUESTS.create('sign_in', {
            username: username,
            password: password
        })).promise();
    }

    close() {
        this.closed = true;
        this.socket.close();
    }
}
