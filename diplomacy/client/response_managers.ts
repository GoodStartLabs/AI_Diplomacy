// diplomacy/client/response_managers.ts

import { Connection } from './connection';
import { Channel } from './channel';
import { NetworkGame } from './network_game';
import { GameInstancesSet } from './game_instances_set';

// Logger setup
const logger = {
  debug: (message: string) => console.debug(message),
  info: (message: string) => console.info(message),
  warn: (message: string) => console.warn(message),
  error: (message: string, error?: any) => console.error(message, error),
};

// --- Placeholders for diplomacy.communication.* ---
// (requests, responses) - These would be more detailed and imported.

// Requests (assuming a __type__ property for identification)
interface BaseRequest { __type__: string; request_id: string; token?: string; game_id?: string; game_role?: string; [key: string]: any; }
interface ClearCentersRequest extends BaseRequest { __type__: "ClearCenters"; power_name: string; }
interface ClearOrdersRequest extends BaseRequest { __type__: "ClearOrders"; power_name: string; }
interface ClearUnitsRequest extends BaseRequest { __type__: "ClearUnits"; power_name: string; }
interface CreateGameRequest extends BaseRequest { __type__: "CreateGame"; /* ... */ }
interface DeleteAccountRequest extends BaseRequest { __type__: "DeleteAccount"; /* ... */ }
interface DeleteGameRequest extends BaseRequest { __type__: "DeleteGame"; game_id: string; /* ... */ }
interface GetAllPossibleOrdersRequest extends BaseRequest { __type__: "GetAllPossibleOrders"; /* ... */ }
interface GetAvailableMapsRequest extends BaseRequest { __type__: "GetAvailableMaps"; /* ... */ }
interface GetDaidePortRequest extends BaseRequest { __type__: "GetDaidePort"; /* ... */ }
interface GetDummyWaitingPowersRequest extends BaseRequest { __type__: "GetDummyWaitingPowers"; /* ... */ }
interface GetGamesInfoRequest extends BaseRequest { __type__: "GetGamesInfo"; /* ... */ }
interface GetPhaseHistoryRequest extends BaseRequest { __type__: "GetPhaseHistory"; /* ... */ }
interface GetPlayablePowersRequest extends BaseRequest { __type__: "GetPlayablePowers"; /* ... */ }
interface JoinGameRequest extends BaseRequest { __type__: "JoinGame"; /* ... */ }
interface JoinPowersRequest extends BaseRequest { __type__: "JoinPowers"; /* ... */ }
interface LeaveGameRequest extends BaseRequest { __type__: "LeaveGame"; game_id: string; /* ... */ }
interface ListGamesRequest extends BaseRequest { __type__: "ListGames"; /* ... */ }
interface LogoutRequest extends BaseRequest { __type__: "Logout"; /* ... */ }
interface ProcessGameRequest extends BaseRequest { __type__: "ProcessGame"; /* ... */ }
interface QueryScheduleRequest extends BaseRequest { __type__: "QuerySchedule"; /* ... */ }
interface SaveGameRequest extends BaseRequest { __type__: "SaveGame"; /* ... */ }
interface SendGameMessageRequest extends BaseRequest { __type__: "SendGameMessage"; message: any; /* Message type needed */ }
interface SetDummyPowersRequest extends BaseRequest { __type__: "SetDummyPowers"; /* ... */ }
interface SetGameStateRequest extends BaseRequest { __type__: "SetGameState"; state: any; orders: any; messages: any; results: any; }
interface SetGameStatusRequest extends BaseRequest { __type__: "SetGameStatus"; status: string; }
interface SetGradeRequest extends BaseRequest { __type__: "SetGrade"; /* ... */ }
interface SetOrdersRequest extends BaseRequest { __type__: "SetOrders"; orders: string[]; power_name?: string; game_role: string; }
interface SetWaitFlagRequest extends BaseRequest { __type__: "SetWaitFlag"; wait: boolean; power_name?: string; game_role: string; }
interface SignInRequest extends BaseRequest { __type__: "SignIn"; /* ... */ }
interface SynchronizeRequest extends BaseRequest { __type__: "Synchronize"; /* ... */ }
interface VoteRequest extends BaseRequest { __type__: "Vote"; vote: string; game_role: string; }


// Responses
interface BaseResponse { __type__: string; }
interface OkResponse extends BaseResponse { __type__: "Ok"; }
interface UniqueDataResponse<T = any> extends BaseResponse { __type__: "UniqueData"; data: T; }
interface DataGameResponse extends BaseResponse { __type__: "DataGame"; data: any; /* Placeholder for Game object from server */ }
interface DataGamePhasesResponse extends BaseResponse { __type__: "DataGamePhases"; data: any[]; /* Array of GamePhaseData */ }
interface DataTimeStampResponse extends BaseResponse { __type__: "DataTimeStamp"; data: any; /* Timestamp data */ }
interface DataTokenResponse extends BaseResponse { __type__: "DataToken"; data: string; /* Token string */ }


// --- Placeholder for diplomacy.engine.game.Game and GamePhaseData ---
// Using GameEngine facade similar to notification_managers.ts
const GameEngine = {
  clear_centers: (game: NetworkGame, power_name: string) => { game.clear_centers(power_name); },
  clear_orders: (game: NetworkGame, power_name: string) => { game.clear_orders(power_name); },
  clear_units: (game: NetworkGame, power_name: string) => { game.clear_units(power_name); },
  extend_phase_history: (game: NetworkGame, phase_data: any) => { game.extend_phase_history(phase_data); },
  add_message: (game: NetworkGame, message: any) => { game.add_message(message); },
  set_phase_data: (game: NetworkGame, phase_data: any) => { game.set_phase_data([phase_data]); }, // Assuming single phase data for set
  set_status: (game: NetworkGame, status: string) => { game.set_status(status); },
  set_orders: (game: NetworkGame, power_name: string, orders: string[]) => { game.set_orders(power_name, orders); },
  set_wait: (game: NetworkGame, power_name: string, wait: boolean) => { game.set_wait(power_name, wait); },
  is_player_game: (game: NetworkGame): boolean => NetworkGame.is_player_game(game),
  // get_power is assumed to be on NetworkGame instance
};
// Placeholder for GamePhaseData constructor/type
class GamePhaseData {
    constructor(params: { name: string; state: any; orders: any; messages: any; results: any; }) {
        Object.assign(this, params);
    }
}

// --- Placeholder for diplomacy.utils.exceptions ---
class DiplomacyException extends Error { constructor(message: string) { super(message); this.name = "DiplomacyException"; } }


export class RequestFutureContext {
  request: BaseRequest;
  future: { // Mimicking Tornado Future for response management
    resolve: (value: any) => void;
    reject: (reason?: any) => void;
    // promise: Promise<any>; // The actual promise is stored by the Connection class
  };
  connection: Connection;
  game?: NetworkGame;

  constructor(
    request: BaseRequest,
    future_resolve: (value: any) => void,
    future_reject: (reason?: any) => void,
    connection: Connection,
    game?: NetworkGame
  ) {
    this.request = request;
    this.future = { resolve: future_resolve, reject: future_reject };
    this.connection = connection;
    this.game = game;
  }

  get request_id(): string { return this.request.request_id; }
  get token(): string | undefined { return this.request.token; }

  get channel(): Channel | undefined {
    if (!this.request.token) return undefined;
    const channel_ref = this.connection.channels.get(this.request.token);
    return channel_ref?.deref();
  }

  new_channel(token: string): Channel {
    const channel = new Channel(this.connection, token);
    this.connection.channels.set(token, new WeakRef(channel));
    return channel;
  }

  new_game(received_game_data: any): NetworkGame {
    const current_channel = this.channel;
    if (!current_channel) {
        throw new DiplomacyException("Cannot create new game without a valid channel in context.");
    }
    // Assuming received_game_data is the raw game object structure from server
    const game = new NetworkGame(current_channel, received_game_data);

    if (!current_channel.game_id_to_instances[game.game_id]) {
      current_channel.game_id_to_instances[game.game_id] = new GameInstancesSet(game.game_id);
    }
    current_channel.game_id_to_instances[game.game_id].add(game);
    return game;
  }

  remove_channel(): void {
    if (this.channel) { // Check if channel exists
      this.connection.channels.delete(this.channel.token);
    }
  }

  delete_game(): void {
    if (!this.request.game_id) {
        logger.error("Request has no game_id to delete.");
        return;
    }
    if (!this.channel) {
        logger.error("No channel context to delete game from.");
        return;
    }
    if (this.channel.game_id_to_instances[this.request.game_id]) {
      delete this.channel.game_id_to_instances[this.request.game_id];
      logger.debug(`Deleted all instances for game ID ${this.request.game_id} from channel ${this.channel.token}`);
    }
  }
}

// Response Handler Functions
function default_manager(context: RequestFutureContext, response: BaseResponse): any {
  if (response.__type__ === "UniqueData") {
    return (response as UniqueDataResponse).data;
  }
  if (response.__type__ === "Ok") {
    return null;
  }
  return response;
}

function on_clear_centers(context: RequestFutureContext, response: OkResponse): void {
  if (!context.game) return;
  GameEngine.clear_centers(context.game, (context.request as ClearCentersRequest).power_name);
}
function on_clear_orders(context: RequestFutureContext, response: OkResponse): void {
  if (!context.game) return;
  GameEngine.clear_orders(context.game, (context.request as ClearOrdersRequest).power_name);
}
function on_clear_units(context: RequestFutureContext, response: OkResponse): void {
  if (!context.game) return;
  GameEngine.clear_units(context.game, (context.request as ClearUnitsRequest).power_name);
}
function on_create_game(context: RequestFutureContext, response: DataGameResponse): NetworkGame {
  return context.new_game(response.data);
}
function on_delete_account(context: RequestFutureContext, response: OkResponse): void {
  context.remove_channel();
}
function on_delete_game(context: RequestFutureContext, response: OkResponse): void {
  context.delete_game();
}
function on_get_phase_history(context: RequestFutureContext, response: DataGamePhasesResponse): any[] {
  if (!context.game) return response.data; // Or throw error
  for (const game_phase of response.data) {
    GameEngine.extend_phase_history(context.game, game_phase);
  }
  return response.data;
}
function on_join_game(context: RequestFutureContext, response: DataGameResponse): NetworkGame {
  return context.new_game(response.data);
}
function on_leave_game(context: RequestFutureContext, response: OkResponse): void {
  context.delete_game();
}
function on_logout(context: RequestFutureContext, response: OkResponse): void {
  context.remove_channel();
}
function on_send_game_message(context: RequestFutureContext, response: DataTimeStampResponse): void {
  if (!context.game) return;
  const request = context.request as SendGameMessageRequest;
  const message_obj = { ...request.message, time_sent: response.data }; // Assume request.message is the message payload
  GameEngine.add_message(context.game, message_obj);
}
function on_set_game_state(context: RequestFutureContext, response: OkResponse): void {
  if (!context.game) return;
  const request = context.request as SetGameStateRequest;
  // Assuming GamePhaseData can be constructed or is a simple object
  const gamePhaseDataInstance = new GamePhaseData({
      name: request.state['name'], // Python dict access
      state: request.state,
      orders: request.orders,
      messages: request.messages,
      results: request.results
  });
  GameEngine.set_phase_data(context.game, gamePhaseDataInstance);
}
function on_set_game_status(context: RequestFutureContext, response: OkResponse): void {
  if (!context.game) return;
  GameEngine.set_status(context.game, (context.request as SetGameStatusRequest).status);
}
function on_set_orders(context: RequestFutureContext, response: OkResponse): void {
  if (!context.game) return;
  const request = context.request as SetOrdersRequest;
  const power_name_to_set = GameEngine.is_player_game(context.game) ? request.game_role : request.power_name;
  if (power_name_to_set) {
    GameEngine.set_orders(context.game, power_name_to_set, request.orders);
  } else {
    logger.error("Could not determine power name for SetOrders");
  }
}
function on_set_wait_flag(context: RequestFutureContext, response: OkResponse): void {
  if (!context.game) return;
  const request = context.request as SetWaitFlagRequest;
  const power_name_to_set = GameEngine.is_player_game(context.game) ? request.game_role : request.power_name;
   if (power_name_to_set) {
    GameEngine.set_wait(context.game, power_name_to_set, request.wait);
  } else {
    logger.error("Could not determine power name for SetWaitFlag");
  }
}
function on_sign_in(context: RequestFutureContext, response: DataTokenResponse): Channel {
  return context.new_channel(response.data);
}
function on_vote(context: RequestFutureContext, response: OkResponse): void {
  if (!context.game || !GameEngine.is_player_game(context.game)) return;
  const request = context.request as VoteRequest;
  const power = context.game.get_power(request.game_role); // Assumes NetworkGame has get_power
  if (power) {
    power.vote = request.vote;
  }
}

// Mapping from request __type__ string to handler function
const RESPONSE_HANDLER_MAP: Record<string, (context: RequestFutureContext, response: any) => any> = {
  "ClearCenters": on_clear_centers,
  "ClearOrders": on_clear_orders,
  "ClearUnits": on_clear_units,
  "CreateGame": on_create_game,
  "DeleteAccount": on_delete_account,
  "DeleteGame": on_delete_game,
  "GetAllPossibleOrders": default_manager,
  "GetAvailableMaps": default_manager,
  "GetDaidePort": default_manager,
  "GetDummyWaitingPowers": default_manager,
  "GetGamesInfo": default_manager,
  "GetPhaseHistory": on_get_phase_history,
  "GetPlayablePowers": default_manager,
  "JoinGame": on_join_game,
  "JoinPowers": default_manager,
  "LeaveGame": on_leave_game,
  "ListGames": default_manager,
  "Logout": on_logout,
  "ProcessGame": default_manager,
  "QuerySchedule": default_manager,
  "SaveGame": default_manager,
  "SendGameMessage": on_send_game_message,
  "SetDummyPowers": default_manager,
  "SetGameState": on_set_game_state,
  "SetGameStatus": on_set_game_status,
  "SetGrade": default_manager,
  "SetOrders": on_set_orders,
  "SetWaitFlag": on_set_wait_flag,
  "SignIn": on_sign_in,
  "Synchronize": default_manager,
  "Vote": on_vote,
};

export function handle_response(context: RequestFutureContext, response: BaseResponse): any {
  const handler = RESPONSE_HANDLER_MAP[context.request.__type__];
  if (!handler) {
    throw new DiplomacyException(`No response handler available for request class ${context.request.__type__}`);
  }
  return handler(context, response);
}
