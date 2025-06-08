// diplomacy/communication/notifications.ts

// --- Logger (Optional, but good for consistency) ---
const logger = {
  debug: (message: string) => console.debug(message),
  info: (message: string) => console.info(message),
  warn: (message: string) => console.warn(message),
  error: (message: string, error?: any) => console.error(message, error),
};

// --- Placeholders for diplomacy.utils.* ---
// (strings, common, exceptions, parsing, constants, GamePhaseData, etc.)
// These would be imported or defined in shared type/utility files.

const diploStrings = {
  NOTIFICATION_ID: 'notification_id',
  NAME: 'name', // Used to determine notification type from JSON
  TOKEN: 'token',
  GAME_ID: 'game_id',
  GAME_ROLE: 'game_role',
  POWER_NAME: 'power_name',
  CHANNEL: 'CHANNEL',
  GAME: 'GAME',
  ALL_COMM_LEVELS: ['CHANNEL', 'GAME', 'CONNECTION'], // Example
  GRADE_UPDATE: 'grade_update',
  ALL_GRADE_UPDATES: ['PROMOTE', 'DEMOTE'], // Example
  GAME_OBJ: 'game', // Renamed from 'game' to avoid conflict with game_id in some contexts
  COUNT_VOTED: 'count_voted',
  COUNT_EXPECTED: 'count_expected',
  VOTE: 'vote',
  ALL_VOTE_DECISIONS: ['YES', 'NO', 'NEUTRAL'], // Example
  POWERS: 'powers',
  TIMESTAMPS: 'timestamps',
  PREVIOUS_PHASE_DATA: 'previous_phase_data',
  CURRENT_PHASE_DATA: 'current_phase_data',
  PHASE_DATA: 'phase_data',
  PHASE_DATA_TYPE: 'phase_data_type',
  ALL_STATE_TYPES: ['STATE_HISTORY', 'STATE', 'PHASE'], // Example
  STATUS: 'status',
  ALL_GAME_STATUSES: ['FORMING', 'ACTIVE', 'PAUSED', 'COMPLETED', 'CANCELED'], // Example
  MESSAGE: 'message',
  ORDERS: 'orders',
  ORDER_IS_SET: 'order_is_set',
  WAIT: 'wait',
};

// Placeholder for Game, Message, GamePhaseData types
interface DiplomacyGame { /* ... */ }
interface DiplomacyMessage { /* ... */ }
interface DiplomacyGamePhaseData { /* ... */ }

// Placeholder for OrderSettings constants
const OrderSettings = {
    ALL_SETTINGS: [0, 1, 2], // ORDER_NOT_SET, ORDER_SET_EMPTY, ORDER_SET
};

class DiplomacyException extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DiplomacyException";
  }
}


// Base Notification Interfaces
export interface AbstractNotification {
  __type__: string; // Class name, e.g., "AccountDeleted"
  level: typeof diploStrings.CHANNEL | typeof diploStrings.GAME | typeof diploStrings.CONNECTION;
  notification_id: string;
  token: string;
  name: string; // Corresponds to the __type__ for dispatching in parse_dict
}

export interface ChannelNotification extends AbstractNotification {
  level: typeof diploStrings.CHANNEL;
}

export interface GameNotification extends AbstractNotification {
  level: typeof diploStrings.GAME;
  game_id: string;
  game_role: string;
  power_name?: string | null; // Optional, as per Python
}

// Specific Notification Interfaces
export interface AccountDeletedNotification extends ChannelNotification {
  __type__: "AccountDeleted";
}

export interface OmniscientUpdatedNotification extends GameNotification {
  __type__: "OmniscientUpdated";
  grade_update: 'PROMOTE' | 'DEMOTE'; // from ALL_GRADE_UPDATES
  game: DiplomacyGame; // Placeholder for Game object structure
}

export interface ClearedCentersNotification extends GameNotification {
  __type__: "ClearedCenters";
  // power_name is already in GameNotification and used by handler
}

export interface ClearedOrdersNotification extends GameNotification {
  __type__: "ClearedOrders";
  // power_name is already in GameNotification
}

export interface ClearedUnitsNotification extends GameNotification {
  __type__: "ClearedUnits";
  // power_name is already in GameNotification
}

export interface VoteCountUpdatedNotification extends GameNotification {
  __type__: "VoteCountUpdated";
  count_voted: number;
  count_expected: number;
}

export interface VoteUpdatedNotification extends GameNotification {
  __type__: "VoteUpdated";
  vote: Record<string, 'YES' | 'NO' | 'NEUTRAL'>; // from ALL_VOTE_DECISIONS
}

export interface PowerVoteUpdatedNotification extends VoteCountUpdatedNotification { // Extends VoteCountUpdated
  __type__: "PowerVoteUpdated";
  vote: 'YES' | 'NO' | 'NEUTRAL';
}

export interface PowersControllersNotification extends GameNotification {
  __type__: "PowersControllers";
  powers: Record<string, string | null>; // power_name -> controller_name (or null)
  timestamps: Record<string, number>;   // power_name -> timestamp
}

export interface GameDeletedNotification extends GameNotification {
  __type__: "GameDeleted";
}

export interface GameProcessedNotification extends GameNotification {
  __type__: "GameProcessed";
  previous_phase_data: DiplomacyGamePhaseData;
  current_phase_data: DiplomacyGamePhaseData;
}

export interface GamePhaseUpdateNotification extends GameNotification {
  __type__: "GamePhaseUpdate";
  phase_data: DiplomacyGamePhaseData;
  phase_data_type: 'STATE_HISTORY' | 'STATE' | 'PHASE'; // from ALL_STATE_TYPES
}

export interface GameStatusUpdateNotification extends GameNotification {
  __type__: "GameStatusUpdate";
  status: 'FORMING' | 'ACTIVE' | 'PAUSED' | 'COMPLETED' | 'CANCELED'; // from ALL_GAME_STATUSES
}

export interface GameMessageReceivedNotification extends GameNotification {
  __type__: "GameMessageReceived";
  message: DiplomacyMessage; // Placeholder
}

export interface PowerOrdersUpdateNotification extends GameNotification {
  __type__: "PowerOrdersUpdate";
  orders?: string[] | null; // Optional list of strings
}

export interface PowerOrdersFlagNotification extends GameNotification {
  __type__: "PowerOrdersFlag";
  order_is_set: 0 | 1 | 2; // from OrderSettings.ALL_SETTINGS
}

export interface PowerWaitFlagNotification extends GameNotification {
  __type__: "PowerWaitFlag";
  wait: boolean;
}

// Union type for all specific notifications for type guarding
export type AnyNotification =
  | AccountDeletedNotification
  | OmniscientUpdatedNotification
  | ClearedCentersNotification
  | ClearedOrdersNotification
  | ClearedUnitsNotification
  | VoteCountUpdatedNotification
  | VoteUpdatedNotification
  | PowerVoteUpdatedNotification
  | PowersControllersNotification
  | GameDeletedNotification
  | GameProcessedNotification
  | GamePhaseUpdateNotification
  | GameStatusUpdateNotification
  | GameMessageReceivedNotification
  | PowerOrdersUpdateNotification
  | PowerOrdersFlagNotification
  | PowerWaitFlagNotification;


// names in python are e.g. AccountDeleted, GamePhaseUpdate
// these are converted from snake_case from the 'name' field in JSON.
// So, the `name` field in the JSON (e.g., "account_deleted") is key.
// We'll assume the __type__ will be the UpperCamelCase version for internal consistency.
const notificationTypeMap: Record<string, string> = {
    "account_deleted": "AccountDeleted",
    "omniscient_updated": "OmniscientUpdated",
    "cleared_centers": "ClearedCenters",
    "cleared_orders": "ClearedOrders",
    "cleared_units": "ClearedUnits",
    "vote_count_updated": "VoteCountUpdated",
    "vote_updated": "VoteUpdated",
    "power_vote_updated": "PowerVoteUpdated",
    "powers_controllers": "PowersControllers",
    "game_deleted": "GameDeleted",
    "game_processed": "GameProcessed",
    "game_phase_update": "GamePhaseUpdate",
    "game_status_update": "GameStatusUpdate",
    "game_message_received": "GameMessageReceived",
    "power_orders_update": "PowerOrdersUpdate",
    "power_orders_flag": "PowerOrdersFlag",
    "power_wait_flag": "PowerWaitFlag",
};


export function parseNotification(json_notification: any): AnyNotification {
  if (typeof json_notification !== 'object' || json_notification === null) {
    throw new DiplomacyException('Notification parser expects a dict.');
  }
  const name_from_json = json_notification[diploStrings.NAME] as string | undefined;
  if (!name_from_json) {
    throw new DiplomacyException('Notification JSON missing "name" field.');
  }

  const typeName = notificationTypeMap[name_from_json.toLowerCase()];
  if (!typeName) {
      throw new DiplomacyException(`Unknown notification name received: ${name_from_json}`);
  }

  // Add the __type__ property based on the mapped name for internal use
  // and ensure basic fields are present. The specific fields for each type
  // are assumed to be present as per the interface.
  const notification_id = json_notification[diploStrings.NOTIFICATION_ID] as string;
  const token = json_notification[diploStrings.TOKEN] as string;

  let level: typeof diploStrings.CHANNEL | typeof diploStrings.GAME | typeof diploStrings.CONNECTION;
  // Determine level based on type or an explicit field if available
  // This logic might need refinement based on how level is determined in Python _AbstractNotification
  // For now, assume GameNotifications have game_id.
  if (json_notification[diploStrings.GAME_ID]) {
      level = diploStrings.GAME as typeof diploStrings.GAME;
  } else {
      level = diploStrings.CHANNEL as typeof diploStrings.CHANNEL;
  }


  // Basic validation and casting
  // In a real scenario, comprehensive validation for each type would be needed.
  const baseNotificationData = {
      ...json_notification,
      __type__: typeName,
      notification_id,
      token,
      name: name_from_json, // Keep original name field as well
      level,
  };

  // This is a simplified "parsing". It assumes the json_notification object
  // already has the correct shape for the identified notification type.
  // More robust parsing would involve checking fields for each type.
  return baseNotificationData as AnyNotification;
}
