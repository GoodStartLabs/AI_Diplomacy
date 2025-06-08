// diplomacy/daide/request_managers.ts

import { Buffer } from 'buffer';
import {
    DaideRequest, NameRequestTs, ObserverRequestTs, IAmRequestTs, HelloRequestTs, MapRequestTs,
    MapDefinitionRequestTs, SupplyCentreOwnershipRequestTs, CurrentPositionRequestTs, HistoryRequestTs,
    SubmitOrdersRequestTs, MissingOrdersRequestTs, GoFlagRequestTs, TimeToDeadlineRequestTs, DrawRequestTs,
    SendMessageRequestTs, NotRequestTs, AcceptRequestTs, RejectRequestTs, ParenthesisErrorRequestTs,
    SyntaxErrorRequestTs, AdminMessageRequestTs
} from './requests';
import {
    DaideResponse, MapNameResponseTs, HelloResponseTs, SupplyCenterResponseTs, CurrentPositionResponseTs,
    ThanksResponseTs, MissingOrdersResponseTs as DaideMissingOrdersResponse, // Alias to avoid name clash
    OrderResultNotificationTs as DaideOrderResultNotification, // This was ORD response, now a notification in DAIDE context
    TimeToDeadlineResponseTs, AcceptResponseTs as DaideAcceptResponse, RejectResponseTs as DaideRejectResponse,
    NotResponseTs as DaideNotResponse, PowerInCivilDisorderResponseTs, PowerIsEliminatedResponseTs,
    TurnOffResponseTs, ParenthesisErrorResponseTs, SyntaxErrorResponseTs
} from './responses';
import * as daideTokens from './tokens';
import { Token } from './tokens';
import * as daideClauses from './clauses';
import * as daideUtils from './utils';
import { ConnectionHandlerTs } from './connection_handler';

// Placeholders for server-internal types and modules
interface MasterServer {
    users: any; // Placeholder for server.users (e.g., UserManagementClass)
    get_game(gameId: string): DiplomacyGame | null; // Gets the main game engine instance
    assert_token(token: string | null | undefined, connection_handler: ConnectionHandlerTs): void; // Throws TokenException
    save_data(): void; // Example
    // Placeholder for internal_request_managers.handle_request
    handleInternalRequest(request: any, connection_handler?: ConnectionHandlerTs): Promise<any>;
}
interface DiplomacyGame { // Placeholder for diplomacy.engine.game.Game
    game_id: string;
    map: any; // Placeholder for map object with name property
    map_name: string;
    powers: Record<string, any>; // Placeholder for power objects
    get_current_phase(): string;
    is_controlled_by(powerName: string, username: string | null): boolean;
    get_power(powerName: string): any; // Placeholder for Power object
    order_history: Record<string, Record<string, string[]>>; // phase -> power -> orders
    result_history: Record<string, Record<string, any[]>>; // phase -> unit -> results
    state_history: Record<string, any>; // phase -> state
    get_state(): any;
    error: any[]; // Game errors
    deadline: number;
    rules: string[];
    is_game_completed: boolean;
    is_game_canceled: boolean;
}
interface InternalRequest { /* ... */ } // Base for internal server requests
interface InternalSignInRequest extends InternalRequest { username: string; password?: string; }
interface InternalJoinGameRequest extends InternalRequest { game_id: string; power_name: string; registration_password?: string | null; token: string; }
interface InternalSetOrdersRequest extends InternalRequest { /* ... */ }
interface InternalClearOrdersRequest extends InternalRequest { /* ... */ }
interface InternalSetWaitFlagRequest extends InternalRequest { /* ... */ }
interface InternalVoteRequest extends InternalRequest { /* ... */ }
interface InternalSendGameMessageRequest extends InternalRequest { /* ... */ }

// Exceptions
class DiplomacyException extends Error { constructor(message: string) { super(message); this.name = "DiplomacyException"; } }
class TokenException extends DiplomacyException { constructor(message: string) { super(message); this.name = "TokenException"; } }
class UserException extends DiplomacyException { constructor(message: string) { super(message); this.name = "UserException"; } }
class ResponseException extends DiplomacyException { constructor(message: string) { super(message); this.name = "ResponseException"; } }

// DaideUser (simplified from server.user)
interface DaideUser {
    username: string;
    passcode: number;
    client_name: string;
    client_version: string;
    to_dict(): any; // To get properties for creating new DaideUser
}

// OrderSplitter placeholder
interface OrderSplit { /* ... */ }


// Logger
const logger = {
  debug: (message: string) => console.debug(message),
  info: (message: string) => console.info(message),
  warn: (message: string) => console.warn(message),
  error: (message: string, error?: any) => console.error(message, error),
};


// Request Handlers
async function onNameRequest(
    server: MasterServer,
    request: NameRequestTs,
    connection_handler: ConnectionHandlerTs,
    game: DiplomacyGame
): Promise<DaideResponse[] | null> {
    const username = connection_handler.getNameVariant() + request.client_name;
    try {
        server.assert_token(connection_handler.token, connection_handler);
    } catch (e) {
        if (e instanceof TokenException) {
            connection_handler.token = null;
        } else { throw e; }
    }

    if (!connection_handler.token) {
        const signInRequest = { __type__: "InternalSignIn", username: username, password: '1234' } as InternalSignInRequest;
        try {
            const token_response = await server.handleInternalRequest(signInRequest, connection_handler);
            connection_handler.token = token_response.data; // Assuming response has { data: token_string }

            const userFromServer = server.users.get_user(username); // Assuming server.users.get_user
            if (userFromServer && !(userFromServer instanceof Object && 'passcode' in userFromServer) ) { // A bit of a hacky check for DaideUser
                const daideUserProps = {
                    ...userFromServer.to_dict(), // Assuming to_dict exists
                    passcode: Math.floor(Math.random() * 8190) + 1, // 1 to 8191
                    client_name: request.client_name,
                    client_version: request.client_version,
                };
                server.users.replace_user(username, daideUserProps); // Assuming server.users.replace_user
                server.save_data();
            }
        } catch (e) {
            if (e instanceof UserException) { return [new DaideRejectResponse(request.toBytes())]; }
            throw e;
        }
    }

    const power_name = Object.keys(game.powers).find(pn => !game.powers[pn].is_controlled());
    if (!power_name) {
        return [new DaideRejectResponse(request.toBytes())];
    }

    return [new DaideAcceptResponse(request.toBytes()), new MapNameResponseTs(game.map.name)];
}

function onObserverRequest(
    server: MasterServer, request: ObserverRequestTs, connection_handler: ConnectionHandlerTs, game: DiplomacyGame
): DaideResponse[] | null {
    return [new DaideRejectResponse(request.toBytes())]; // No DAIDE observers allowed per Python
}

async function onIAmRequest(
    server: MasterServer, request: IAmRequestTs, connection_handler: ConnectionHandlerTs, game: DiplomacyGame
): Promise<DaideResponse[] | null> {
    const { power_name, passcode } = request;
    let username: string | null = null;

    for (const user of Object.values(server.users.users as Record<string, DaideUser>)) { // Iterate server.users.users
        if (user.passcode && user.passcode === parseInt(passcode, 10) && game.is_controlled_by(power_name, user.username)) {
            username = user.username;
            break;
        }
    }

    if (username === null) return [new DaideRejectResponse(request.toBytes())];

    try { server.assert_token(connection_handler.token, connection_handler); }
    catch (e) { if (e instanceof TokenException) connection_handler.token = null; else throw e; }

    if (!connection_handler.token) {
        const signInRequest = { __type__: "InternalSignIn", username, password: '1234' } as InternalSignInRequest;
        try {
            const token_response = await server.handleInternalRequest(signInRequest, connection_handler);
            connection_handler.token = token_response.data;
        } catch (e) { if (e instanceof UserException) return [new DaideRejectResponse(request.toBytes())]; throw e;}
    }

    const joinGameRequest = {
        __type__: "InternalJoinGame", game_id: game.game_id, power_name,
        registration_password: null, token: connection_handler.token
    } as InternalJoinGameRequest;
    await server.handleInternalRequest(joinGameRequest, connection_handler);

    return [new DaideAcceptResponse(request.toBytes())];
}

// ... Other handlers will be more complex and depend on internal server logic & game engine placeholders ...
// For brevity, stubs for the rest:
function onHelloRequest(s: MasterServer, r: HelloRequestTs, ch: ConnectionHandlerTs, g: DiplomacyGame): DaideResponse[] | null {
    const uinfo = daideUtils.get_user_connection(s.users, g, ch);
    if (!uinfo.daide_user || !uinfo.power_name) return [new DaideRejectResponse(r.toBytes())];
    return [new HelloResponseTs(uinfo.power_name, uinfo.daide_user.passcode, DEFAULT_LEVEL, g.deadline, g.rules)];
}
function onMapRequest(s: MasterServer, r: MapRequestTs, ch: ConnectionHandlerTs, g: DiplomacyGame): DaideResponse[] | null { return [new MapNameResponseTs(g.map.name)]; }
function onMapDefinitionRequest(s: MasterServer, r: MapDefinitionRequestTs, ch: ConnectionHandlerTs, g: DiplomacyGame): DaideResponse[] | null { return [new responses.MDF(g.map_name)]; } // Assuming responses.MDF is DaideMapDefinitionResponse
function onSupplyCentreOwnershipRequest(s: MasterServer, r: SupplyCentreOwnershipRequestTs, ch: ConnectionHandlerTs, g: DiplomacyGame): DaideResponse[] | null {
    const pc = {} as Record<string,string[]>;
    Object.values(g.powers).forEach(p => pc[p.name] = p.centers);
    return [new SupplyCenterResponseTs(pc, g.map_name)];
}
function onCurrentPositionRequest(s: MasterServer, r: CurrentPositionRequestTs, ch: ConnectionHandlerTs, g: DiplomacyGame): DaideResponse[] | null {
    const units = {} as Record<string,string[]>; Object.values(g.powers).forEach(p => units[p.name] = p.units);
    const retreats = {} as Record<string,Record<string,string[]>>; Object.values(g.powers).forEach(p => retreats[p.name] = p.retreats);
    return [new CurrentPositionResponseTs(g.get_current_phase(), units, retreats)];
}
async function onSubmitOrdersRequest(s: MasterServer, r: SubmitOrdersRequestTs, ch: ConnectionHandlerTs, g: DiplomacyGame): Promise<DaideResponse[] | null> {
    logger.warn("onSubmitOrdersRequest is a complex stub and needs full internal logic ported.");
    // This involves validating each order with game engine, which is complex.
    // Simplified: acknowledge receipt and send current MIS.
    const uinfo = daideUtils.get_user_connection(s.users, g, ch);
    if (!uinfo.power_name) return [new DaideRejectResponse(r.toBytes())];

    // Simulate setting orders via internal request for each order string
    // for (const orderStr of r.orders) {
    //    const setOrderReq = { ..., orders: [orderStr], ... }
    //    await s.handleInternalRequest(setOrderReq, ch);
    // }
    // Then create THX for each, and one MIS. This is highly simplified.
    const orderResponses: DaideResponse[] = r.orders.map(orderStr => {
        // This is not correct, THX needs original order bytes.
        // The python code re-parses the original daide_bytes for each order.
        const orderClause = daideClauses.parse_string_ts(daideClauses.OrderTs, orderStr);
        return new ThanksResponseTs(orderClause ? orderClause.toBytes() : new Uint8Array(0), [0]); // Assume success
    });
    orderResponses.push(new DaideMissingOrdersResponse(g.get_current_phase(), g.get_power(uinfo.power_name)));
    return orderResponses;
}

// ... Stubs for History, MissingOrders, GoFlag, TimeToDeadline, Draw, SendMessage, Not, Accept, Reject, Errors, Admin ...
// These would follow similar patterns, calling internal server logic and constructing DAIDE responses.

const DAIDE_REQUEST_HANDLER_MAP: Record<string, (server: MasterServer, request: DaideRequest, ch: ConnectionHandlerTs, game: DiplomacyGame) => Promise<DaideResponse[] | null> | DaideResponse[] | null> = {
  "NameRequest": onNameRequest,
  "ObserverRequest": onObserverRequest,
  "IAmRequest": onIAmRequest,
  "HelloRequest": onHelloRequest,
  "MapRequest": onMapRequest,
  "MapDefinitionRequest": onMapDefinitionRequest,
  "SupplyCentreOwnershipRequest": onSupplyCentreOwnershipRequest,
  "CurrentPositionRequest": onCurrentPositionRequest,
  "HistoryRequest": async (s,r,ch,g) => {logger.warn("HST handler stub"); return [new DaideRejectResponse(r.toBytes())];},
  "SubmitOrdersRequest": onSubmitOrdersRequest,
  "MissingOrdersRequest": (s,r,ch,g) => {
      const uinfo = daideUtils.get_user_connection(s.users, g, ch);
      if (!uinfo.power_name) return [new DaideRejectResponse(r.toBytes())];
      return [new DaideMissingOrdersResponse(g.get_current_phase(), g.get_power(uinfo.power_name))];
  },
  "GoFlagRequest": async (s,r,ch,g) => {logger.warn("GOF handler stub"); return [new DaideAcceptResponse(r.toBytes())];},
  "TimeToDeadlineRequest": (s,r,ch,g) => [new DaideRejectResponse(r.toBytes())], // Rejected in python
  "DrawRequest": async (s,r,ch,g) => {logger.warn("DRW handler stub"); return [new DaideAcceptResponse(r.toBytes())];},
  "SendMessageRequest": async (s,r,ch,g) => {logger.warn("SND handler stub"); return [new DaideAcceptResponse(r.toBytes())];},
  "NotRequest": async (s,r,ch,g) => {logger.warn("NOT handler stub"); return [new DaideRejectResponse(r.toBytes())];},
  "AcceptRequest": async (s,r,ch,g) => {logger.warn("YES handler stub"); return null;},
  "RejectRequest": (s,r,ch,g) => {logger.warn("REJ handler stub"); return null;},
  "ParenthesisErrorRequest": (s,r,ch,g) => null, // No response in python
  "SyntaxErrorRequest": (s,r,ch,g) => null,      // No response in python
  "AdminMessageRequest": (s,r,ch,g) => {
      // ADM_MESSAGE_ENABLED is from daide/index.ts (needs import if used)
      // import { ADM_MESSAGE_ENABLED } from '../index';
      // if (!ADM_MESSAGE_ENABLED) return [new DaideRejectResponse(r.toBytes())];
      logger.warn("ADM handler stub, assuming disabled"); return [new DaideRejectResponse(r.toBytes())];
    },
};

export async function handle_daide_request(
    server: MasterServer,
    request: DaideRequest, // This is the parsed DAIDE request object (e.g., NameRequestTs)
    connection_handler: ConnectionHandlerTs
): Promise<DaideResponse[] | null> {
    const handler = DAIDE_REQUEST_HANDLER_MAP[request.__type__]; // Use __type__ added during parsing
    if (!handler) {
        throw new DiplomacyException(`No DAIDE request handler for type ${request.__type__}`);
    }

    const game = server.get_game(request.game_id || connection_handler.gameId); // game_id might be on request or handler
    if (!game || game.is_game_completed || game.is_game_canceled) {
        return [new DaideRejectResponse(request.toBytes())];
    }

    // Call the handler. It might be async or sync.
    const result = handler(server, request, connection_handler, game);
    if (result instanceof Promise) {
        return await result;
    }
    return result;
}
