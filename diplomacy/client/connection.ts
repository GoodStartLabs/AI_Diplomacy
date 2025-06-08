// diplomacy/client/connection.ts

import WebSocket from 'ws';
import { EventEmitter } from 'events';
import { setTimeout } from 'timers/promises'; // For async delay

// Logger setup
const logger = {
  debug: (message: string) => console.debug(message),
  info: (message: string) => console.info(message),
  warn: (message: string) => console.warn(message),
  error: (message: string, error?: any) => console.error(message, error),
};

// --- Placeholder for diplomacy.communication.* ---
// (requests, responses, notifications)
// These would be more detailed interfaces or classes in a full conversion.
interface BaseDiplomacyRequest {
  name: string; // For logging
  request_id: string;
  level: string; // e.g., 'GAME', 'CHANNEL'
  phase_dependent?: boolean;
  phase?: string;
  game_id?: string;
  re_sent?: boolean;
  json(): string; // Method to serialize to JSON string
  to_dict(): Record<string, any>; // Method to get as object
}

interface BaseDiplomacyResponse {
  request_id: string;
  // other common response fields
}

interface BaseDiplomacyNotification {
  name: string; // For logging
  notification_id: string;
  token: string; // Channel token this notification is for
  // other common notification fields
}

// Placeholder for response/notification parsing and handling logic
const responses = {
  parse_dict: (json_message: any): BaseDiplomacyResponse => json_message as BaseDiplomacyResponse,
};
const notifications = {
  parse_dict: (json_message: any): BaseDiplomacyNotification => json_message as BaseDiplomacyNotification,
};
const notification_managers = {
  handle_notification: (connection: Connection, notification: BaseDiplomacyNotification) => {
    logger.debug(`Placeholder: Handling notification ${notification.name} for token ${notification.token}`);
  },
};
const handle_response = (request_context: RequestFutureContext, response: BaseDiplomacyResponse): any => {
  logger.debug(`Placeholder: Handling response for request ID ${response.request_id}`);
  return response; // Return raw response for now
};

// Placeholder for requests.SignIn, requests.GetDaidePort, requests.UnknownToken
class SignInRequest implements BaseDiplomacyRequest {
  name = "SignIn";
  level = "CONNECTION";
  request_id: string = String(Math.random()); // Example ID generation
  constructor(public args: { username: string, password: string }) {}
  json = () => JSON.stringify({ ...this.args, request_id: this.request_id, __type__: this.name });
  to_dict = () => ({ ...this.args, request_id: this.request_id, __type__: this.name });
}
class GetDaidePortRequest implements BaseDiplomacyRequest {
  name = "GetDaidePort";
  level = "CONNECTION";
  request_id: string = String(Math.random());
  constructor(public args: { game_id: string }) {}
  json = () => JSON.stringify({ ...this.args, request_id: this.request_id, __type__: this.name });
  to_dict = () => ({ ...this.args, request_id: this.request_id, __type__: this.name });
}
class UnknownTokenRequest implements BaseDiplomacyRequest {
  name = "UnknownToken";
  level = "CONNECTION"; // Or appropriate level
  request_id: string = String(Math.random());
  constructor(public args: { token: string }) {}
  json = () => JSON.stringify({ ...this.args, request_id: this.request_id, __type__: this.name });
  to_dict = () => ({ ...this.args, request_id: this.request_id, __type__: this.name });
}
const diplomacyRequests = { SignInRequest, GetDaidePortRequest, UnknownTokenRequest };


// --- Placeholders for diplomacy.utils.* ---
const diploStrings = { // From channel.ts, assuming shared
  REQUEST_ID: 'request_id',
  NOTIFICATION_ID: 'notification_id',
  TOKEN: 'token',
  GAME: 'GAME', // Added for _Reconnection logic
  // ... other strings used by Connection/Reconnection
};
const diploConstants = {
  NB_CONNECTION_ATTEMPTS: 5,
  ATTEMPT_DELAY_SECONDS: 5,
  REQUEST_TIMEOUT_SECONDS: 30,
};
class DiplomacyException extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DiplomacyException";
  }
}
const diplomacyExceptions = { DiplomacyException };


// --- Placeholder for Channel ---
// Simplified, actual Channel would be imported from channel.ts
interface Channel {
  token: string;
  game_id_to_instances: Record<string, GameInstancesSet>;
  // other Channel properties/methods
}

// --- Placeholder for NetworkGame ---
interface NetworkGame {
  game_id: string;
  role: string;
  current_short_phase: string;
  synchronize(): Promise<any>; // Returns a promise that resolves with server game info
  // other NetworkGame properties/methods
}
// --- Placeholder for GameInstancesSet ---
interface GameInstancesSet {
    get_games(): NetworkGame[];
    // other methods
}


// Represents the context of a request being managed
export interface RequestFutureContext {
  request: BaseDiplomacyRequest;
  future: {
    resolve: (value: any) => void;
    reject: (reason?: any) => void;
    promise: Promise<any>;
  };
  connection: Connection;
  game?: NetworkGame; // Optional game context
  request_id: string; // Added for easier access
}

function createRequestPromise<T>(): { resolve: (value: T | PromiseLike<T>) => void; reject: (reason?: any) => void; promise: Promise<T> } {
    let resolveFunc!: (value: T | PromiseLike<T>) => void;
    let rejectFunc!: (reason?: any) => void;
    const promise = new Promise<T>((res, rej) => {
        resolveFunc = res;
        rejectFunc = rej;
    });
    return { resolve: resolveFunc, reject: rejectFunc, promise };
}


export class Connection extends EventEmitter {
  hostname: string;
  port: number;
  use_ssl: boolean;
  ws_connection: WebSocket | null = null;
  connection_count: number = 0;

  // Events for connection status, similar to Tornado's Event
  private _is_connecting_event = new EventEmitter();
  private _is_reconnecting_event = new EventEmitter();
  private _connecting_in_progress = false; // True while _connect is actively trying
  private _reconnecting_in_progress = false; // True while _reconnect_after_unexpected_close (and its _connect call) is active
  private _connected = false; // True if ws_connection is open and ready


  channels: Map<string, WeakRef<Channel>> = new Map(); // Using Map and WeakRef
  requests_to_send: Map<string, RequestFutureContext> = new Map();
  requests_waiting_responses: Map<string, RequestFutureContext> = new Map();
  unknown_tokens: Set<string> = new Set();

  private _connect_resolve?: () => void;
  private _connect_reject?: (err: Error) => void;
  private _current_connection_attempt_promise: Promise<void> | null = null;


  constructor(hostname: string, port: number, use_ssl: boolean = false) {
    super();
    this.hostname = hostname;
    this.port = port;
    this.use_ssl = use_ssl;

    // Initially, we are not connected, but reconnection is considered "done"
    this._reconnecting_in_progress = false;
    this._is_reconnecting_event.emit('set'); // Event listeners can now resolve their waits if any
  }

  private async _wait_for_event_set(eventEmitter: EventEmitter, isInProgressFlag: () => boolean): Promise<void> {
    if (!isInProgressFlag()) {
      return Promise.resolve();
    }
    return new Promise((resolve) => {
      eventEmitter.once('set', resolve);
    });
  }

  public wait_for_connection(): Promise<void> {
    return this._wait_for_event_set(this._is_connecting_event, () => this._connecting_in_progress || !this._connected);
  }

  public wait_for_reconnection(): Promise<void> {
    return this._wait_for_event_set(this._is_reconnecting_event, () => this._reconnecting_in_progress);
  }


  get url(): string {
    return `${this.use_ssl ? 'wss' : 'ws'}://${this.hostname}:${this.port}`;
  }

  public async _connect(message?: string): Promise<void> {
    if (this._current_connection_attempt_promise) {
        logger.info("Connection attempt already in progress. Returning existing promise.");
        return this._current_connection_attempt_promise;
    }

    if (message) {
      logger.info(message);
    }

    this._connecting_in_progress = true;
    this._connected = false;
    this._is_connecting_event.emit('clear');

    this._current_connection_attempt_promise = new Promise<void>(async (resolve, reject) => {
        // this._connect_resolve = resolve; // Assigning here might be problematic if multiple calls happen
        // this._connect_reject = reject;   // Let each call manage its own resolve/reject for the promise it returns

        for (let attempt_index = 0; attempt_index < diploConstants.NB_CONNECTION_ATTEMPTS; attempt_index++) {
            try {
                logger.info(`Attempting to connect (attempt ${attempt_index + 1}/${diploConstants.NB_CONNECTION_ATTEMPTS})... URL: ${this.url}`);
                this.ws_connection = new WebSocket(this.url);

                // Attach event listeners
                this.ws_connection.on('open', () => {
                    logger.info('WebSocket connection established.');
                    this.connection_count++;
                    this._connected = true; // Set connected status
                    this._connecting_in_progress = false;
                    this._is_connecting_event.emit('set');

                    if (this.connection_count === 1) {
                        // _handle_socket_messages is implicitly handled by 'message' listener setup
                        logger.info("Initial connection successful, message listener active.");
                    }
                    resolve(); // Resolve the promise for _connect
                    return; // Exit loop and function successfully
                });

                this.ws_connection.on('message', (data: WebSocket.Data) => {
                    this._on_socket_message(data.toString());
                });

                this.ws_connection.on('error', (err: Error) => {
                    // This listener handles errors for the *current* attempt's WebSocket object.
                    // It's crucial for the retry logic within the loop.
                    logger.error(`WebSocket error during attempt ${attempt_index + 1}: ${err.message}`);
                    // If this is the last attempt, the outer catch will handle rejection of _current_connection_attempt_promise
                    // No need to reject here, let the loop continue or finish.
                });

                this.ws_connection.on('close', (code: number, reason: Buffer) => {
                    logger.info(`WebSocket closed. Code: ${code}, Reason: ${reason.toString()}`);
                    this._connected = false;
                    if (this.ws_connection === e.target) { // Ensure it's the current WebSocket closing
                        this.ws_connection = null;
                    }
                    // If this close happens during an active connection (not during initial connect attempts)
                    // then _reconnect_after_unexpected_close should be called.
                    // The _connect method itself should not trigger global reconnection for failed initial attempts.
                    if (code !== 1000 && this.connection_count > 0 && !this._connecting_in_progress && !this._reconnecting_in_progress) {
                         this._reconnect_after_unexpected_close();
                    }
                });

                // Wait for 'open' or 'error' for this specific attempt
                const attemptPromise = new Promise<void>((attemptResolve, attemptReject) => {
                    const onOpen = () => {
                        this.ws_connection?.removeListener('error', onError);
                        attemptResolve();
                    };
                    const onError = (err: Error) => {
                        this.ws_connection?.removeListener('open', onOpen);
                        attemptReject(err);
                    };
                    this.ws_connection?.once('open', onOpen);
                    this.ws_connection?.once('error', onError);

                    // Timeout for this specific connection attempt
                    const attemptTimeout = setTimeout(diploConstants.ATTEMPT_DELAY_SECONDS * 1000).then(() => {
                        if (this.ws_connection?.readyState !== WebSocket.OPEN) {
                            this.ws_connection?.removeListener('open', onOpen);
                            this.ws_connection?.removeListener('error', onError);
                            attemptReject(new Error(`Connection attempt timed out after ${diploConstants.ATTEMPT_DELAY_SECONDS} seconds.`));
                        }
                    });
                });

                await attemptPromise; // Wait for this attempt to open or error out
                // If attemptPromise resolved, 'open' was emitted, and the outer 'open' handler has run.
                // The outer 'open' handler calls resolve() for the main _connect promise.
                return; // Successfully connected and resolved.

            } catch (ex: any) { // Catch errors from new WebSocket() or attemptPromise rejection
                logger.warn(`Connection attempt ${attempt_index + 1} failed: ${ex.message}`);
                if (this.ws_connection && this.ws_connection.readyState !== WebSocket.CLOSED && this.ws_connection.readyState !== WebSocket.CLOSING) {
                    this.ws_connection.terminate();
                }
                this.ws_connection = null;
                if (attempt_index + 1 >= diploConstants.NB_CONNECTION_ATTEMPTS) {
                    this._connecting_in_progress = false;
                    this._is_connecting_event.emit('set'); // Allow subsequent calls to _connect
                    reject(ex); // Reject the promise for _connect
                    this._current_connection_attempt_promise = null;
                    return;
                }
                await setTimeout(diploConstants.ATTEMPT_DELAY_SECONDS * 1000);
            }
        }
    }).finally(() => {
        this._current_connection_attempt_promise = null; // Clear the promise once settled
        if (!this._connected) { // If loop finished without connecting
            this._connecting_in_progress = false;
            this._is_connecting_event.emit('set');
        }
    });
    return this._current_connection_attempt_promise;
  }

  private async _reconnect_after_unexpected_close(): Promise<void> {
    if (this._reconnecting_in_progress) {
        logger.info("Reconnection attempt already in progress.");
        return; // Avoid multiple concurrent reconnection attempts
    }
    this._reconnecting_in_progress = true;
    this._is_reconnecting_event.emit('clear'); // Signal that reconnection is in progress

    logger.info("Attempting to reconnect due to unexpected close...");
    try {
        await this._connect('Re-establishing connection.'); // _connect handles its own _connecting_in_progress

        // If _connect was successful, this._connected should be true
        if (this._connected) {
            logger.info("Connection re-established. Starting _Reconnection logic.");
            const reconnectionHandler = new _Reconnection(this);
            await reconnectionHandler.reconnect();
        } else {
            logger.error("Failed to re-establish connection during _reconnect_after_unexpected_close.");
        }
    } catch (error: any) {
        logger.error(`Failed to reconnect: ${error.message}`, error);
        // Potentially schedule another reconnect attempt or emit a fatal error event
    } finally {
        this._reconnecting_in_progress = false;
        this._is_reconnecting_event.emit('set'); // Signal reconnection attempt is complete
        logger.info('Reconnection attempt finished.');
    }
  }

  private async _on_socket_message(socket_message: string): Promise<void> {
    try {
        const json_message = JSON.parse(socket_message);
        if (typeof json_message !== 'object' || json_message === null) {
            logger.error("Unable to convert a JSON string to a dictionary or it's null.");
            return;
        }

        const request_id = json_message[diploStrings.REQUEST_ID] as string | undefined;
        const notification_id = json_message[diploStrings.NOTIFICATION_ID] as string | undefined;

        if (request_id) {
            let request_context = this.requests_waiting_responses.get(request_id);
            if (!request_context) {
                // Wait briefly for potential race condition
                for (let i = 0; i < 10; i++) {
                    await setTimeout(500);
                    request_context = this.requests_waiting_responses.get(request_id);
                    if (request_context) break;
                }
                if (!request_context) {
                    logger.error(`Unknown request_id received: ${request_id}. Message: ${socket_message.substring(0, 200)}`);
                    return;
                }
            }

            this.requests_waiting_responses.delete(request_id);
            try {
                const response = responses.parse_dict(json_message); // Placeholder
                const managed_data = handle_response(request_context, response); // Placeholder
                request_context.future.resolve(managed_data);
            } catch (ex: any) {
                if (ex instanceof diplomacyExceptions.DiplomacyException) {
                    logger.error(`Error received for request ${request_context.request.name} (ID: ${request_id}): ${ex.message}`);
                    logger.debug(`Full request was: ${JSON.stringify(request_context.request.to_dict())}`);
                    request_context.future.reject(ex);
                } else {
                     logger.error(`Unexpected error handling response for ${request_context.request.name} (ID: ${request_id}): ${ex.message}`, ex);
                    request_context.future.reject(new diplomacyExceptions.DiplomacyException(`Unexpected error handling response: ${ex.message}`));
                }
            }

        } else if (notification_id) {
            const notification = notifications.parse_dict(json_message); // Placeholder
            if (!this.channels.has(notification.token) && !this.unknown_tokens.has(notification.token)) {
                 logger.error(`Unknown notification token: ${notification.token} for notification ${notification.name}`);
                this._handle_unknown_token(notification.token);
                return;
            }
            if (this.channels.has(notification.token)) { // Only handle if channel is known and not marked as unknown
                notification_managers.handle_notification(this, notification); // Placeholder
            }
        } else {
            logger.error(`Unknown socket message (not a response or notification): ${socket_message.substring(0,200)}`);
        }

    } catch (e: any) {
        logger.error(`Unable to parse JSON from a socket message or other error: ${e.message}. Message: ${socket_message.substring(0,200)}`, e);
    }
  }

  private _handle_socket_messages(): void {
    // This method is essentially replaced by the 'message' event handler on the WebSocket instance.
    // The Python version had a loop here, but in Node.js, the event emitter handles incoming messages.
    logger.info("WebSocket message processing is handled by the 'message' event listener.");
  }

  private _handle_unknown_token(token: string): void {
    this.unknown_tokens.add(token);
    const request = new diplomacyRequests.UnknownTokenRequest({ token });
    try {
        if (this.ws_connection && this.ws_connection.readyState === WebSocket.OPEN) {
            this.ws_connection.send(request.json());
        } else {
            logger.warn(`Cannot send UnknownTokenRequest for ${token}, WebSocket is not open.`);
            // Optionally, queue this if essential, or just log.
        }
    } catch (e: any) {
        logger.error(`Error sending UnknownTokenRequest for ${token}: ${e.message}`, e);
    }
  }

  private _register_to_send(request_context: RequestFutureContext): void {
    this.requests_to_send.set(request_context.request_id, request_context);
    logger.debug(`Request ${request_context.request_id} (${request_context.request.name}) registered to be sent later.`);
  }

  public async send(request: BaseDiplomacyRequest, for_game?: NetworkGame): Promise<any> {
    const {promise, resolve, reject} = createRequestPromise<any>();
    const request_context: RequestFutureContext = {
        request,
        future: { resolve, reject, promise },
        connection: this,
        game: for_game,
        request_id: request.request_id
    };

    // The timeout for the entire operation
    let timeoutId: NodeJS.Timeout | null = null;
    const timeoutPromise = new Promise<never>((_, rej) => {
        timeoutId = global.setTimeout(() => {
            const err = new Error(`Request timed out after ${diploConstants.REQUEST_TIMEOUT_SECONDS} seconds for request ID ${request.request_id}`);
            this.requests_waiting_responses.delete(request.request_id); // Clean up if it was moved there
            this.requests_to_send.delete(request.request_id); // Clean up if it was re-queued
            rej(err);
        }, diploConstants.REQUEST_TIMEOUT_SECONDS * 1000);
    });

    const executionPromise = this.write_request(request_context)
        .then(() => {
            // If write_request resolves, the request is now waiting for a response.
            // The actual resolution of request_context.future.promise happens in _on_socket_message.
            // We just need to make sure the timeout is cleared if the request_context.future resolves or rejects.
            request_context.future.promise.finally(() => {
                if (timeoutId) clearTimeout(timeoutId);
            });
        })
        .catch(error => {
            // If write_request itself fails (e.g. connection error before writing), reject the main promise.
            if (timeoutId) clearTimeout(timeoutId);
            request_context.future.reject(error);
        });

    return Promise.race([request_context.future.promise, timeoutPromise]);
  }

  public async write_request(request_context: RequestFutureContext): Promise<void> {
    const request = request_context.request;

    try {
        // Determine which readiness event to wait for
        // Synchronize requests only wait for initial connection, others wait for full reconnection
        if (request.name === 'Synchronize') { // Assuming 'Synchronize' is the name of Synchronize request class/type
            await this.wait_for_connection();
        } else {
            await this.wait_for_reconnection(); // This also implies initial connection is done
            await this.wait_for_connection(); // Ensure connected even after reconnection event is set
        }

        if (!this.ws_connection || this.ws_connection.readyState !== WebSocket.OPEN) {
            logger.warn(`WebSocket not open while trying to send ${request.name}. Re-queueing.`);
            this._register_to_send(request_context); // Re-queue
            // Potentially trigger a reconnection if not already in progress
            if (!this._connecting_in_progress && !this._reconnecting_in_progress) {
                this._reconnect_after_unexpected_close();
            }
            throw new diplomacyExceptions.DiplomacyException("Connection not open. Request re-queued.");
        }

        // Attempt to send the message
        this.ws_connection.send(request.json(), (err) => {
            if (err) {
                logger.error(`Failed to send WebSocket message for ${request.name} (ID: ${request.request_id}): ${err.message}`);
                // If send fails, it's likely a connection issue. Re-queue and attempt reconnect.
                this._register_to_send(request_context);
                if (!this._connecting_in_progress && !this._reconnecting_in_progress) {
                    this._reconnect_after_unexpected_close();
                }
                // Reject the promise associated with this specific write attempt.
                // The main request promise in `send()` will be rejected by its timeout or this error if not caught by `send`.
                // For now, let `send` handle the overall request failure.
                // This specific write_request promise can be considered failed.
                // However, the Python code's _MessageWrittenCallback sets the main future's exception.
                // Let's follow that by rejecting the request_context's future.
                request_context.future.reject(new diplomacyExceptions.DiplomacyException(`WebSocket send error: ${err.message}`));
            } else {
                logger.debug(`Request ${request.name} (ID: ${request.request_id}) sent successfully.`);
                // Move from requests_to_send (if it was there) to requests_waiting_responses
                this.requests_to_send.delete(request.request_id);
                this.requests_waiting_responses.set(request.request_id, request_context);
                // The promise for this specific write_request resolves successfully.
                // The overall request_context.future will be resolved when a response is received.
            }
        });
        // Note: ws_connection.send() callback is for the completion of the send operation,
        // not for the server's response. The promise from write_request should resolve
        // when the send operation itself is confirmed (or fails).
        // For simplicity here, we'll assume send callback handles the immediate success/failure of *sending*.
        // The actual resolution of the request_context.future is handled by _on_socket_message.
        // This means write_request itself doesn't need to return a complex promise if send callback handles errors.
        // However, to make write_request awaitable for the send operation itself:
        return new Promise<void>((resolve, reject) => {
             if (!this.ws_connection || this.ws_connection.readyState !== WebSocket.OPEN) {
                // This case should have been caught above, but as a safeguard:
                return reject(new diplomacyExceptions.DiplomacyException("Connection not open at point of send."));
            }
            this.ws_connection.send(request.json(), (err) => {
                if (err) {
                    logger.error(`Failed to send WebSocket message for ${request.name} (ID: ${request.request_id}): ${err.message}`);
                    this._register_to_send(request_context);
                     if (!this._connecting_in_progress && !this._reconnecting_in_progress) {
                        this._reconnect_after_unexpected_close();
                    }
                    reject(new diplomacyExceptions.DiplomacyException(`WebSocket send error: ${err.message}`));
                } else {
                    logger.debug(`Request ${request.name} (ID: ${request.request_id}) sent successfully.`);
                    this.requests_to_send.delete(request.request_id);
                    this.requests_waiting_responses.set(request.request_id, request_context);
                    resolve();
                }
            });
        });

    } catch (error: any) {
        logger.error(`Error in write_request for ${request.name} (ID: ${request.request_id}): ${error.message}`, error);
        // If waiting for connection/reconnection fails, or other unexpected error.
        this._register_to_send(request_context); // Ensure it's re-queued
        if (error instanceof diplomacyExceptions.DiplomacyException) throw error;
        throw new diplomacyExceptions.DiplomacyException(`Failed to write request: ${error.message}`);
    }
  }

  // Public API methods
  public async authenticate(username: string, password: string): Promise<Channel> {
    logger.warn("authenticate not fully implemented.");
    const request = new diplomacyRequests.SignInRequest({ username, password });
    return this.send(request) as Promise<Channel>; // Cast, assuming response handler creates Channel
  }

  public async get_daide_port(game_id: string): Promise<number> {
    logger.warn("get_daide_port not fully implemented.");
    const request = new diplomacyRequests.GetDaidePortRequest({ game_id });
    return this.send(request) as Promise<number>;
  }
}


// --- _Reconnection Class ---
class _Reconnection {
  connection: Connection;
  games_phases: Record<string, Record<string, { phase: string } | null>>; // game_id -> role -> { phase: server_phase_string }
  n_expected_games: number;
  n_synchronized_games: number;

  constructor(connection: Connection) {
    this.connection = connection;
    this.games_phases = {};
    this.n_expected_games = 0;
    this.n_synchronized_games = 0;
  }

  async reconnect(): Promise<void> {
    logger.info("Starting reconnection procedure...");

    // Mark all waiting responses as `re-sent` and move them back to requests_to_send.
    this.connection.requests_waiting_responses.forEach((waiting_context) => {
        waiting_context.request.re_sent = true;
        this.connection.requests_to_send.set(waiting_context.request_id, waiting_context);
    });
    this.connection.requests_waiting_responses.clear();

    // Remove all previous synchronization requests.
    const requests_to_send_updated: Map<string, RequestFutureContext> = new Map();
    this.connection.requests_to_send.forEach((context, request_id) => {
        if (context.request.name === 'Synchronize') { // Assuming 'Synchronize' is the type/name
            context.future.reject(new diplomacyExceptions.DiplomacyException(
                `Sync request invalidated for game ID ${context.request.game_id}.`
            ));
        } else {
            requests_to_send_updated.set(request_id, context);
        }
    });
    this.connection.requests_to_send = requests_to_send_updated;

    // Count games to synchronize and prepare for sync calls.
    this.connection.channels.forEach(channel_ref => {
        const channel = channel_ref.deref();
        if (channel) {
            Object.values(channel.game_id_to_instances).forEach(game_instance_set => {
                game_instance_set.get_games().forEach(game => {
                    if (!this.games_phases[game.game_id]) {
                        this.games_phases[game.game_id] = {};
                    }
                    this.games_phases[game.game_id][game.role] = null; // Mark as needing sync
                    this.n_expected_games++;
                });
            });
        }
    });

    if (this.n_expected_games > 0) {
        logger.info(`Need to synchronize ${this.n_expected_games} game instances.`);
        const sync_promises: Promise<void>[] = [];
        this.connection.channels.forEach(channel_ref => {
            const channel = channel_ref.deref();
            if (channel) {
                Object.values(channel.game_id_to_instances).forEach(game_instance_set => {
                    game_instance_set.get_games().forEach(game => {
                        // Create a promise for each game's synchronization
                        const sync_promise = game.synchronize() // synchronize() should be an async method on NetworkGame
                            .then(server_game_info => { // server_game_info should be { phase: string }
                                this.games_phases[game.game_id][game.role] = server_game_info;
                                this.n_synchronized_games++;
                                logger.debug(`Synchronized ${game.game_id} (${game.role}). ${this.n_synchronized_games}/${this.n_expected_games}`);
                            })
                            .catch(error => {
                                logger.error(`Error synchronizing game ${game.game_id} (${game.role}): ${error.message}`, error);
                                // Still count it as "processed" to avoid deadlock, but log error
                                this.n_synchronized_games++;
                            })
                            .finally(() => {
                                if (this.n_synchronized_games === this.n_expected_games) {
                                    this.sync_done();
                                }
                            });
                        sync_promises.push(sync_promise);
                    });
                });
            }
        });
        // Wait for all sync operations to complete or fail.
        // The actual call to sync_done is now inside the .finally() of each promise.
        // This ensures sync_done is called exactly once when all are processed.
    } else {
        logger.info("No active games to synchronize.");
        this.sync_done(); // No games, so sync is immediately done.
    }
  }

  private sync_done(): void {
    logger.info("All game synchronization attempts finished. Finalizing reconnection.");

    const final_requests_to_send: Map<string, RequestFutureContext> = new Map();
    this.connection.requests_to_send.forEach((context, request_id) => {
        let keep = true;
        if (context.request.level === diploStrings.GAME && context.request.phase_dependent) {
            const request_phase = context.request.phase;
            const server_game_info = context.request.game_id && context.game?.role ? this.games_phases[context.request.game_id]?.[context.game.role] : null;

            if (server_game_info && request_phase !== server_game_info.phase) {
                logger.warn(`Request ${context.request.name} (ID: ${request_id}) for game ${context.request.game_id} is obsolete. Request phase: ${request_phase}, Server phase: ${server_game_info.phase}.`);
                context.future.reject(new diplomacyExceptions.DiplomacyException(
                    `Game ${context.request.game_id}: request ${context.request.name}: request phase ${request_phase} does not match current server game phase ${server_game_info.phase}.`
                ));
                keep = false;
            } else if (!server_game_info) {
                 logger.warn(`Could not determine server phase for request ${context.request.name} (ID: ${request_id}) for game ${context.request.game_id}. Keeping request.`);
            }
        }
        if (keep) {
            final_requests_to_send.set(request_id, context);
        }
    });

    logger.debug(`After phase validation, keeping ${final_requests_to_send.size}/${this.connection.requests_to_send.size} old requests to send.`);
    this.connection.requests_to_send.clear(); // Clear original, will re-populate with validated ones or new ones

    // Re-send validated pending requests
    final_requests_to_send.forEach(async (context_to_resend) => {
        try {
            // Re-trigger the send process for this request.
            // The `send` method itself handles placing it in requests_to_send or requests_waiting_responses.
            // We don't call write_request directly here to ensure all `send` logic (like timeout) is reapplied.
            logger.info(`Re-sending request ${context_to_resend.request.name} (ID: ${context_to_resend.request_id}) after reconnection.`);
            await this.connection.send(context_to_resend.request, context_to_resend.game);
        } catch (error: any) {
            logger.error(`Failed to re-send request ${context_to_resend.request.name} (ID: ${context_to_resend.request_id}) after reconnection: ${error.message}`, error);
            // The request's original future should have been rejected by the send call.
        }
    });

    // Mark reconnection as complete
    this.connection['_reconnecting_in_progress'] = false; // Access private member for state update
    this.connection['_is_reconnecting_event'].emit('set'); // Signal that reconnection attempts are done
    logger.info('Reconnection work complete. Connection is now fully operational.');
  }
}

// Factory function
export async function connect(hostname: string, port: number, use_ssl: boolean = false): Promise<Connection> {
  const connection = new Connection(hostname, port, use_ssl);
  await connection._connect('Trying to connect.');
  return connection;
}

// _MessageWrittenCallback is not directly translated as a class,
// its logic will be part_of write_request's promise handling.
