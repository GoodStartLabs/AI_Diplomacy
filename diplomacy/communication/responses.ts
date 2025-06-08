// diplomacy/communication/responses.ts

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
  MESSAGE: 'message',
  ERROR_TYPE: 'error_type',
  DATA: 'data',
  GAME_ID: 'game_id',
  PHASE: 'phase',
  SCHEDULE: 'schedule',
  TIMESTAMP: 'timestamp',
  TIMESTAMP_CREATED: 'timestamp_created',
  MAP_NAME: 'map_name',
  OBSERVER_LEVEL: 'observer_level',
  MASTER_TYPE: 'master_type',
  OMNISCIENT_TYPE: 'omniscient_type',
  OBSERVER_TYPE: 'observer_type',
  CONTROLLED_POWERS: 'controlled_powers',
  RULES: 'rules',
  STATUS: 'status',
  ALL_GAME_STATUSES: ['FORMING', 'ACTIVE', 'PAUSED', 'COMPLETED', 'CANCELED'], // Example
  N_PLAYERS: 'n_players',
  N_CONTROLS: 'n_controls',
  DEADLINE: 'deadline',
  REGISTRATION_PASSWORD: 'registration_password', // In responses, it's a boolean
  POSSIBLE_ORDERS: 'possible_orders',
  ORDERABLE_LOCATIONS: 'orderable_locations',
};

// Placeholder types from other diplomacy modules
interface DiplomacyGame { /* ... */ }
interface DiplomacyGamePhaseData { /* ... */ }
interface DiplomacySchedulerEvent { /* ... */ }

// Placeholder for custom exceptions
class DiplomacyException extends Error { constructor(message: string) { super(message); this.name = "DiplomacyException"; } }
class ResponseException extends DiplomacyException { constructor(message: string) { super(message); this.name = "ResponseException"; } }
// Add other specific exception classes if needed, e.g., AuthenticationException, GameNotFoundException etc.
// For now, a generic ResponseException will be used if specific type is not found.
const diplomacyExceptions = {
    ResponseException,
    // Populate with actual exception classes from diplomacy.utils.exceptions
    // Example: AuthenticationException: class AuthenticationException extends ResponseException {}
};


// Base Response Interface
export interface AbstractResponse {
  __type__: string; // Class name, e.g., "Ok"
  request_id: string;
  name: string; // Snake case name from JSON, used for dispatching
}

// Specific Response Interfaces
export interface ErrorResponse extends AbstractResponse {
  __type__: "Error";
  message: string;
  error_type: string; // Class name of the Python exception
}

export interface OkResponse extends AbstractResponse {
  __type__: "Ok";
}

export interface NoResponse extends AbstractResponse {
  __type__: "NoResponse";
  // In Python, __bool__ is False. In TS, this might be indicated by a property or usage pattern.
}

export interface UniqueDataResponse<T = any> extends AbstractResponse {
  // __type__ will be specific like "DataToken", "DataMaps", etc.
  data: T;
}

// Specific UniqueData instances
export interface DataTokenResponse extends UniqueDataResponse<string> { __type__: "DataToken"; }
export interface DataMapsResponse extends UniqueDataResponse<Record<string, any>> { __type__: "DataMaps"; } // map_id -> {powers, scs, loc_type}
export interface DataPowerNamesResponse extends UniqueDataResponse<string[]> { __type__: "DataPowerNames"; }
export interface DataGameInfoStructure { // Structure for items in DataGamesResponse
    game_id: string;
    phase: string;
    timestamp: number;
    timestamp_created: number;
    map_name?: string | null;
    observer_level?: 'master_type' | 'omniscient_type' | 'observer_type' | null;
    controlled_powers?: string[] | null;
    rules?: string[] | null;
    status?: typeof diploStrings.ALL_GAME_STATUSES[number] | null;
    n_players?: number | null;
    n_controls?: number | null;
    deadline?: number | null;
    registration_password?: boolean | null; // Python side uses bool for this in response
}
export interface DataGamesResponse extends UniqueDataResponse<DataGameInfoStructure[]> { __type__: "DataGames"; }
export interface DataPortResponse extends UniqueDataResponse<number> { __type__: "DataPort"; }
export interface DataTimeStampResponse extends UniqueDataResponse<number> { __type__: "DataTimeStamp"; } // Microseconds
export interface DataGamePhasesResponse extends UniqueDataResponse<DiplomacyGamePhaseData[]> { __type__: "DataGamePhases"; }
export interface DataGameResponse extends UniqueDataResponse<DiplomacyGame> { __type__: "DataGame"; } // Placeholder for Game object
export interface DataSavedGameResponse extends UniqueDataResponse<Record<string, any>> { __type__: "DataSavedGame"; } // JSON dict
export interface DataGamesToPowerNamesResponse extends UniqueDataResponse<Record<string, string[]>> { __type__: "DataGamesToPowerNames"; }


export interface DataGameScheduleResponse extends AbstractResponse {
  __type__: "DataGameSchedule";
  game_id: string;
  phase: string;
  schedule: DiplomacySchedulerEvent; // Placeholder
}

export interface DataPossibleOrdersResponse extends AbstractResponse {
  __type__: "DataPossibleOrders";
  possible_orders: Record<string, string[]>; // location -> orders[]
  orderable_locations: Record<string, string[]>; // power_name -> locations[]
}


// Union type for all specific responses for type guarding
export type AnyResponse =
  | ErrorResponse | OkResponse | NoResponse
  | DataTokenResponse | DataMapsResponse | DataPowerNamesResponse | DataGamesResponse
  | DataPortResponse | DataTimeStampResponse | DataGamePhasesResponse | DataGameResponse
  | DataSavedGameResponse | DataGamesToPowerNamesResponse
  | DataGameScheduleResponse | DataPossibleOrdersResponse;


// snake_case to UpperCamelCase helper (if not already available from requests.ts)
function snakeToUpperCamel(str: string): string {
    return str.toLowerCase().replace(/([-_][a-z])/g, group =>
        group.toUpperCase().replace('-', '').replace('_', '')
    ).replace(/^[a-z]/, char => char.toUpperCase());
}

// Map snake_case names from JSON to UpperCamelCase __type__ names
const responseTypeMap: Record<string, string> = {
    "error": "Error", "ok": "Ok", "no_response": "NoResponse",
    "data_token": "DataToken", "data_maps": "DataMaps", "data_power_names": "DataPowerNames",
    "data_games": "DataGames", "data_port": "DataPort", "data_time_stamp": "DataTimeStamp",
    "data_game_phases": "DataGamePhases", "data_game": "DataGame", "data_saved_game": "DataSavedGame",
    "data_games_to_power_names": "DataGamesToPowerNames", "data_game_schedule": "DataGameSchedule",
    "data_possible_orders": "DataPossibleOrders",
    // Add any other specific response names if they differ from simple "Data<FieldName>"
};


export function parseResponse(json_response: any): AnyResponse {
  if (typeof json_response !== 'object' || json_response === null) {
    throw new ResponseException('Response parser expects a dict.');
  }
  const name_from_json = json_response[diploStrings.NAME] as string | undefined;
  if (!name_from_json) {
    // For 'Error' type, Python's Error class itself doesn't have 'name' in its __slots__ or params,
    // but _AbstractResponse does. Server must send 'name':'error'.
    throw new ResponseException('Response JSON missing "name" field.');
  }

  const typeName = responseTypeMap[name_from_json.toLowerCase()];
  if (!typeName) {
      throw new ResponseException(`Unknown response name received: ${name_from_json}`);
  }

  const responseData = {
      ...json_response,
      __type__: typeName,
      name: name_from_json, // Keep original name
  } as AnyResponse; // Cast to AnyResponse to satisfy further checks

  if (responseData.__type__ === "Error") {
    const errorResponse = responseData as ErrorResponse;
    // Try to find a specific exception class, otherwise use generic ResponseException
    // This requires diplomacyExceptions to be populated with actual exception classes.
    const ExceptionClass = (diplomacyExceptions as Record<string, typeof ResponseException>)[errorResponse.error_type] || ResponseException;
    throw new ExceptionClass(`${errorResponse.error_type}: ${errorResponse.message}`);
  }

  return responseData;
}
