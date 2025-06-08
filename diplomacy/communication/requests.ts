// diplomacy/communication/requests.ts

// --- Logger (Optional) ---
const logger = {
  debug: (message: string) => console.debug(message),
  info: (message: string) => console.info(message),
  warn: (message: string) => console.warn(message),
  error: (message: string, error?: any) => console.error(message, error),
};

// --- Placeholders for diplomacy.utils.* ---
const diploStrings = {
  REQUEST_ID: 'request_id',
  NAME: 'name',
  RE_SENT: 're_sent',
  TOKEN: 'token',
  GAME_ID: 'game_id',
  GAME_ROLE: 'game_role',
  PHASE: 'phase',
  USERNAME: 'username',
  PASSWORD: 'password',
  N_CONTROLS: 'n_controls',
  DEADLINE: 'deadline',
  REGISTRATION_PASSWORD: 'registration_password',
  POWER_NAME: 'power_name',
  STATE: 'state',
  MAP_NAME: 'map_name',
  RULES: 'rules',
  BUFFER_SIZE: 'buffer_size',
  POWER_NAMES: 'power_names',
  STATUS: 'status',
  INCLUDE_PROTECTED: 'include_protected',
  FOR_OMNISCIENCE: 'for_omniscience',
  GAMES: 'games',
  GRADE: 'grade',
  GRADE_UPDATE: 'grade_update',
  FROM_PHASE: 'from_phase',
  TO_PHASE: 'to_phase',
  MESSAGE: 'message',
  ORDERS: 'orders',
  RESULTS: 'results', // Used in SetGameState
  MESSAGES: 'messages', // Used in SetGameState
  WAIT: 'wait',
  TIMESTAMP: 'timestamp',
  VOTE: 'vote',
  CHANNEL: 'CHANNEL',
  GAME: 'GAME',
  CONNECTION: 'CONNECTION', // Assuming this level might exist based on _AbstractRequest
  ALL_COMM_LEVELS: ['CHANNEL', 'GAME', 'CONNECTION'],
  ALL_GAME_STATUSES: ['FORMING', 'ACTIVE', 'PAUSED', 'COMPLETED', 'CANCELED'],
  ALL_GRADES: ['OMNISCIENT', 'ADMIN', 'MODERATOR'],
  ALL_GRADE_UPDATES: ['PROMOTE', 'DEMOTE'],
  ALL_VOTE_DECISIONS: ['YES', 'NO', 'NEUTRAL'],
};

// Placeholder for Message type from diplomacy.engine.message
interface DiplomacyMessage { /* ... */ }

class DiplomacyException extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DiplomacyException";
  }
}

// Base Request Interfaces
export interface AbstractRequest {
  __type__: string; // Class name, e.g., "SignIn"
  level: typeof diploStrings.CONNECTION | typeof diploStrings.CHANNEL | typeof diploStrings.GAME | null;
  request_id: string;
  name: string; // Snake case name from JSON
  re_sent?: boolean; // DefaultValueType(bool, False)
}

export interface AbstractChannelRequest extends AbstractRequest {
  level: typeof diploStrings.CHANNEL;
  token: string;
}

export interface AbstractGameRequest extends AbstractChannelRequest {
  level: typeof diploStrings.GAME;
  game_id: string;
  game_role: string;
  phase: string; // Game short phase
  phase_dependent: boolean; // Default true for game requests
  // address_in_game: [string, string]; // property: (game_role, token)
}

// Specific Request Interfaces

// Connection Requests
export interface GetDaidePortRequest extends AbstractRequest {
  __type__: "GetDaidePort";
  level: null; // Or CONNECTION if that's more appropriate
  game_id: string;
}

export interface SignInRequest extends AbstractRequest {
  __type__: "SignIn";
  level: null; // Or CONNECTION
  username: string;
  password: string;
}

// Channel Requests
export interface CreateGameRequest extends AbstractChannelRequest {
  __type__: "CreateGame";
  game_id?: string | null;
  n_controls?: number | null;
  deadline?: number; // Default 300
  registration_password?: string | null;
  power_name?: string | null;
  state?: Record<string, any> | null;
  map_name?: string; // Default 'standard'
  rules?: Set<string> | null;
}

export interface DeleteAccountRequest extends AbstractChannelRequest {
  __type__: "DeleteAccount";
  username?: string | null;
}

export interface GetDummyWaitingPowersRequest extends AbstractChannelRequest {
  __type__: "GetDummyWaitingPowers";
  buffer_size: number;
}

export interface GetAvailableMapsRequest extends AbstractChannelRequest {
  __type__: "GetAvailableMaps";
}

export interface GetPlayablePowersRequest extends AbstractChannelRequest {
  __type__: "GetPlayablePowers";
  game_id: string;
}

export interface JoinGameRequest extends AbstractChannelRequest {
  __type__: "JoinGame";
  game_id: string;
  power_name?: string | null;
  registration_password?: string | null;
}

export interface JoinPowersRequest extends AbstractChannelRequest {
  __type__: "JoinPowers";
  game_id: string;
  power_names: Set<string>;
  registration_password?: string | null;
}

export interface ListGamesRequest extends AbstractChannelRequest {
  __type__: "ListGames";
  status?: typeof diploStrings.ALL_GAME_STATUSES[number] | null;
  map_name?: string | null;
  include_protected?: boolean; // Default True
  for_omniscience?: boolean; // Default False
  game_id?: string | null;
}

export interface GetGamesInfoRequest extends AbstractChannelRequest {
  __type__: "GetGamesInfo";
  games: string[];
}

export interface LogoutRequest extends AbstractChannelRequest {
  __type__: "Logout";
}

export interface UnknownTokenRequest extends AbstractChannelRequest {
  __type__: "UnknownToken";
}

export interface SetGradeRequest extends AbstractChannelRequest {
  __type__: "SetGrade";
  grade: typeof diploStrings.ALL_GRADES[number];
  grade_update: typeof diploStrings.ALL_GRADE_UPDATES[number];
  username: string;
  game_id?: string | null;
}

// Game Requests
export interface ClearCentersRequest extends AbstractGameRequest {
  __type__: "ClearCenters";
  power_name?: string | null;
}

export interface ClearOrdersRequest extends AbstractGameRequest {
  __type__: "ClearOrders";
  power_name?: string | null;
}

export interface ClearUnitsRequest extends AbstractGameRequest {
  __type__: "ClearUnits";
  power_name?: string | null;
}

export interface DeleteGameRequest extends AbstractGameRequest {
  __type__: "DeleteGame";
  phase_dependent: false;
}

export interface GetAllPossibleOrdersRequest extends AbstractGameRequest {
  __type__: "GetAllPossibleOrders";
}

export interface GetPhaseHistoryRequest extends AbstractGameRequest {
  __type__: "GetPhaseHistory";
  from_phase?: string | number | null;
  to_phase?: string | number | null;
  phase_dependent: false;
}

export interface LeaveGameRequest extends AbstractGameRequest {
  __type__: "LeaveGame";
}

export interface ProcessGameRequest extends AbstractGameRequest {
  __type__: "ProcessGame";
}

export interface QueryScheduleRequest extends AbstractGameRequest {
  __type__: "QuerySchedule";
}

export interface SaveGameRequest extends AbstractGameRequest {
  __type__: "SaveGame";
}

export interface SendGameMessageRequest extends AbstractGameRequest {
  __type__: "SendGameMessage";
  message: DiplomacyMessage; // Placeholder
}

export interface SetDummyPowersRequest extends AbstractGameRequest {
  __type__: "SetDummyPowers";
  username?: string | null;
  power_names?: string[] | null; // Python uses SequenceType, implies list/set
}

export interface SetGameStateRequest extends AbstractGameRequest {
  __type__: "SetGameState";
  state: Record<string, any>;
  orders: Record<string, string[]>;
  results: Record<string, string[]>;
  messages: Record<number, DiplomacyMessage>; // Python uses SortedDict, TS can use Record or Map
}

export interface SetGameStatusRequest extends AbstractGameRequest {
  __type__: "SetGameStatus";
  status: typeof diploStrings.ALL_GAME_STATUSES[number];
}

export interface SetOrdersRequest extends AbstractGameRequest {
  __type__: "SetOrders";
  power_name?: string | null;
  orders: string[];
  wait?: boolean | null;
}

export interface SetWaitFlagRequest extends AbstractGameRequest {
  __type__: "SetWaitFlag";
  power_name?: string | null;
  wait: boolean;
}

export interface SynchronizeRequest extends AbstractGameRequest {
  __type__: "Synchronize";
  timestamp: number;
  phase_dependent: false;
}

export interface VoteRequest extends AbstractGameRequest {
  __type__: "Vote";
  power_name?: string | null;
  vote: typeof diploStrings.ALL_VOTE_DECISIONS[number];
}


// Union type for all specific requests for type guarding
export type AnyRequest =
  | GetDaidePortRequest | SignInRequest | CreateGameRequest | DeleteAccountRequest
  | GetDummyWaitingPowersRequest | GetAvailableMapsRequest | GetPlayablePowersRequest
  | JoinGameRequest | JoinPowersRequest | ListGamesRequest | GetGamesInfoRequest
  | LogoutRequest | UnknownTokenRequest | SetGradeRequest | ClearCentersRequest
  | ClearOrdersRequest | ClearUnitsRequest | DeleteGameRequest | GetAllPossibleOrdersRequest
  | GetPhaseHistoryRequest | LeaveGameRequest | ProcessGameRequest | QueryScheduleRequest
  | SaveGameRequest | SendGameMessageRequest | SetDummyPowersRequest | SetGameStateRequest
  | SetGameStatusRequest | SetOrdersRequest | SetWaitFlagRequest | SynchronizeRequest | VoteRequest;


// snake_case to UpperCamelCase helper
function snakeToUpperCamel(str: string): string {
    return str.toLowerCase().replace(/([-_][a-z])/g, group =>
        group.toUpperCase().replace('-', '').replace('_', '')
    ).replace(/^[a-z]/, char => char.toUpperCase());
}

const requestTypeMap: Record<string, string> = {};
// Populate map from known snake_case names to UpperCamelCase __type__ names
// This assumes the 'name' field in JSON is snake_case.
Object.keys(diploStrings).forEach(key => { // Using diploStrings as a proxy for actual request names
    if (key === key.toUpperCase()) { // Heuristic: actual request names are usually not all caps
        const snakeName = key.toLowerCase(); // Example: GAME_ID -> game_id
        const camelName = snakeToUpperCamel(snakeName);
        // This mapping is not perfect, needs actual snake_case names if they differ from constants
        // For now, let's assume the __type__ will be directly derived if `name` field is UpperCamelCase
        // or we have a direct map if `name` field is snake_case.
        // The Python code uses globals()[expected_class_name], where expected_class_name is UpperCamelCase
        // derived from snake_case `name` field.
    }
});
// Manual mapping for actual request names if they are snake_case in JSON `name` field
const snakeToCamelRequestMap: Record<string, string> = {
    "get_daide_port": "GetDaidePort", "sign_in": "SignIn", "create_game": "CreateGame",
    "delete_account": "DeleteAccount", "get_dummy_waiting_powers": "GetDummyWaitingPowers",
    "get_available_maps": "GetAvailableMaps", "get_playable_powers": "GetPlayablePowers",
    "join_game": "JoinGame", "join_powers": "JoinPowers", "list_games": "ListGames",
    "get_games_info": "GetGamesInfo", "logout": "Logout", "unknown_token": "UnknownToken",
    "set_grade": "SetGrade", "clear_centers": "ClearCenters", "clear_orders": "ClearOrders",
    "clear_units": "ClearUnits", "delete_game": "DeleteGame", "get_all_possible_orders": "GetAllPossibleOrders",
    "get_phase_history": "GetPhaseHistory", "leave_game": "LeaveGame", "process_game": "ProcessGame",
    "query_schedule": "QuerySchedule", "save_game": "SaveGame", "send_game_message": "SendGameMessage",
    "set_dummy_powers": "SetDummyPowers", "set_game_state": "SetGameState", "set_game_status": "SetGameStatus",
    "set_orders": "SetOrders", "set_wait_flag": "SetWaitFlag", "synchronize": "Synchronize", "vote": "Vote"
};


export function parseRequest(json_request: any): AnyRequest {
  if (typeof json_request !== 'object' || json_request === null) {
    throw new DiplomacyException('Request parser expects a dict.');
  }
  const name_from_json = json_request[diploStrings.NAME] as string | undefined;
  if (!name_from_json) {
    throw new DiplomacyException('Request JSON missing "name" field.');
  }

  const typeName = snakeToCamelRequestMap[name_from_json.toLowerCase()];
  if (!typeName) {
      throw new DiplomacyException(`Unknown request name received: ${name_from_json}`);
  }

  // Add the __type__ property based on the mapped name for internal use
  // and ensure basic fields are present.
  const baseRequestData = {
      ...json_request,
      __type__: typeName,
      name: name_from_json, // Keep original name
      // level, request_id, etc. are assumed to be on json_request
  };

  // This is a simplified "parsing". It assumes the json_request object
  // already has the correct shape for the identified request type.
  return baseRequestData as AnyRequest;
}
