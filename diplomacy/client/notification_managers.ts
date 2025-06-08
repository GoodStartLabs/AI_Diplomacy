// diplomacy/client/notification_managers.ts

import { Connection } from './connection'; // Assuming it's in the same directory
import { Channel } from './channel';
import { NetworkGame } from './network_game';

// Logger setup
const logger = {
  debug: (message: string) => console.debug(message),
  info: (message: string) => console.info(message),
  warn: (message: string) => console.warn(message),
  error: (message: string, error?: any) => console.error(message, error),
};

// --- Placeholder for diplomacy.engine.game.Game static-like methods ---
// These would typically be static methods on a translated Game class or instance methods.
// For now, they are standalone functions taking the game instance as the first argument.
const GameEngine = {
  clear_centers: (game: NetworkGame, power_name: string) => { logger.debug(`GameEngine.clear_centers called for ${power_name} on game ${game.game_id}`); game.clear_centers(power_name); },
  clear_orders: (game: NetworkGame, power_name: string) => { logger.debug(`GameEngine.clear_orders called for ${power_name} on game ${game.game_id}`); game.clear_orders(power_name);},
  clear_units: (game: NetworkGame, power_name: string) => { logger.debug(`GameEngine.clear_units called for ${power_name} on game ${game.game_id}`); game.clear_units(power_name); },
  update_powers_controllers: (game: NetworkGame, powers: any, timestamps: any) => { logger.debug(`GameEngine.update_powers_controllers called on game ${game.game_id}`); game.update_powers_controllers(powers, timestamps); },
  add_message: (game: NetworkGame, message: any) => { logger.debug(`GameEngine.add_message called on game ${game.game_id}`); game.add_message(message); },
  set_phase_data: (game: NetworkGame, phase_data: any[], clear_history: boolean = true) => { logger.debug(`GameEngine.set_phase_data called on game ${game.game_id}`); game.set_phase_data(phase_data, clear_history); },
  extend_phase_history: (game: NetworkGame, phase_data: any) => { logger.debug(`GameEngine.extend_phase_history called on game ${game.game_id}`); game.extend_phase_history(phase_data); },
  set_status: (game: NetworkGame, status: string) => { logger.debug(`GameEngine.set_status called on game ${game.game_id} to ${status}`); game.set_status(status); },
  set_orders: (game: NetworkGame, power_name: string, orders: string[]) => { logger.debug(`GameEngine.set_orders called for ${power_name} on game ${game.game_id}`); game.set_orders(power_name, orders); },
  get_power: (game: NetworkGame, power_name: string): { vote?: string, name: string, order_is_set?: boolean } | undefined => { // Added name to power
    logger.debug(`GameEngine.get_power called for ${power_name} on game ${game.game_id}`);
    return game.get_power(power_name); // Assume NetworkGame has get_power
   },
  set_wait: (game: NetworkGame, power_name: string, wait: boolean) => { logger.debug(`GameEngine.set_wait called for ${power_name} on game ${game.game_id} to ${wait}`); game.set_wait(power_name, wait); },
  is_player_game: (game: NetworkGame): boolean => NetworkGame.is_player_game(game), // Assuming static methods on NetworkGame placeholder
  is_observer_game: (game: NetworkGame): boolean => NetworkGame.is_observer_game(game),
  is_omniscient_game: (game: NetworkGame): boolean => NetworkGame.is_omniscient_game(game),
};

// --- Placeholder for diplomacy.communication.notifications ---
// Using a common base and specific interfaces for clarity
export interface BaseNotification {
  __type__: string; // Unique type identifier for each notification
  token: string; // For channel-level notifications
  level: string; // 'CHANNEL' or 'GAME'
  name?: string; // For logging, taken from Python's notification.name
}
export interface GameNotification extends BaseNotification {
  game_id: string;
  game_role: string; // Role associated with this notification context
}
export interface AccountDeletedNotification extends BaseNotification { __type__: "AccountDeleted"; }
export interface ClearedCentersNotification extends GameNotification { __type__: "ClearedCenters"; power_name: string; }
export interface ClearedOrdersNotification extends GameNotification { __type__: "ClearedOrders"; power_name: string; }
export interface ClearedUnitsNotification extends GameNotification { __type__: "ClearedUnits"; power_name: string; }
export interface GameDeletedNotification extends GameNotification { __type__: "GameDeleted"; }
export interface GameMessageReceivedNotification extends GameNotification { __type__: "GameMessageReceived"; message: any; } // `message` type needs to be defined
export interface GameProcessedNotification extends GameNotification { __type__: "GameProcessed"; previous_phase_data: any; current_phase_data: any; }
export interface GamePhaseUpdateNotification extends GameNotification { __type__: "GamePhaseUpdate"; phase_data_type: string; phase_data: any; }
export interface GameStatusUpdateNotification extends GameNotification { __type__: "GameStatusUpdate"; status: string; }
export interface OmniscientUpdatedNotification extends GameNotification { __type__: "OmniscientUpdated"; grade_update: string; game: any; /* game is a new Game object */ }
export interface PowerOrdersFlagNotification extends GameNotification { __type__: "PowerOrdersFlag"; power_name: string; order_is_set: boolean; }
export interface PowerOrdersUpdateNotification extends GameNotification { __type__: "PowerOrdersUpdate"; power_name: string; orders: string[]; }
export interface PowersControllersNotification extends GameNotification { __type__: "PowersControllers"; powers: any; timestamps: any; }
export interface PowerVoteUpdatedNotification extends GameNotification { __type__: "PowerVoteUpdated"; vote: string; }
export interface PowerWaitFlagNotification extends GameNotification { __type__: "PowerWaitFlag"; power_name: string; wait: boolean; }
export interface VoteCountUpdatedNotification extends GameNotification { __type__: "VoteCountUpdated"; /* ... */ }
export interface VoteUpdatedNotification extends GameNotification { __type__: "VoteUpdated"; vote: Record<string, string>; }


// --- Placeholder for diplomacy.utils.strings and exceptions ---
const diploStrings = {
  CHANNEL: 'CHANNEL',
  GAME: 'GAME',
  STATE_HISTORY: 'STATE_HISTORY', // Used in on_game_phase_update
  PROMOTE: 'PROMOTE', // Used in on_omniscient_updated
  DEMOTE: 'DEMOTE',   // Used in on_omniscient_updated
};
class DiplomacyException extends Error { constructor(message: string) { super(message); this.name = "DiplomacyException"; } }


// Helper to get the game instance to notify
function _get_game_to_notify(connection: Connection, notification: GameNotification): NetworkGame | null {
  const channel_ref = connection.channels.get(notification.token);
  const channel = channel_ref?.deref();
  if (channel && channel.game_id_to_instances[notification.game_id]) {
    return channel.game_id_to_instances[notification.game_id].get(notification.game_role) || null;
  }
  return null;
}

// Notification Handlers
function on_account_deleted(channel: Channel, notification: AccountDeletedNotification): void {
  logger.info(`Handling AccountDeleted for token ${notification.token}`);
  channel.connection.channels.delete(channel.token); // Connection needs to expose this or have a method
}

function on_cleared_centers(game: NetworkGame, notification: ClearedCentersNotification): void {
  GameEngine.clear_centers(game, notification.power_name);
}

function on_cleared_orders(game: NetworkGame, notification: ClearedOrdersNotification): void {
  GameEngine.clear_orders(game, notification.power_name);
}

function on_cleared_units(game: NetworkGame, notification: ClearedUnitsNotification): void {
  GameEngine.clear_units(game, notification.power_name);
}

function on_powers_controllers(game: NetworkGame, notification: PowersControllersNotification): void {
  // Assuming game.power is available and has name & get_controller()
  const power = game.get_power(game.role); // Assuming role is the power name for player games
  if (GameEngine.is_player_game(game) && power && notification.powers[power.name] !== power.get_controller()) {
    game.channel?.game_id_to_instances[game.game_id]?.remove(power.name);
  } else {
    GameEngine.update_powers_controllers(game, notification.powers, notification.timestamps);
  }
}

function on_game_deleted(game: NetworkGame, notification: GameDeletedNotification): void {
  if (!game.channel) return;
  const game_instances_set = game.channel.game_id_to_instances[game.game_id];
  if (!game_instances_set) return;

  if (GameEngine.is_player_game(game)) {
    const power = game.get_power(game.role);
    if (power) game_instances_set.remove(power.name);
  } else {
    game_instances_set.remove_special();
  }
}

function on_game_message_received(game: NetworkGame, notification: GameMessageReceivedNotification): void {
  GameEngine.add_message(game, notification.message);
}

function on_game_processed(game: NetworkGame, notification: GameProcessedNotification): void {
  GameEngine.set_phase_data(game, [notification.previous_phase_data, notification.current_phase_data], false);
}

function on_game_phase_update(game: NetworkGame, notification: GamePhaseUpdateNotification): void {
  if (notification.phase_data_type === diploStrings.STATE_HISTORY) {
    GameEngine.extend_phase_history(game, notification.phase_data);
  } else {
    GameEngine.set_phase_data(game, notification.phase_data, true); // Default clear_history is true
  }
}

function on_game_status_update(game: NetworkGame, notification: GameStatusUpdateNotification): void {
  GameEngine.set_status(game, notification.status);
}

function on_omniscient_updated(game: NetworkGame, notification: OmniscientUpdatedNotification): void {
  if (!GameEngine.is_player_game(game)) { // Should be observer or omniscient already
    const current_is_observer = GameEngine.is_observer_game(game);
    const new_game_is_omniscient = GameEngine.is_omniscient_game(notification.game as NetworkGame); // Cast needed

    if (current_is_observer) {
      if (notification.grade_update !== diploStrings.PROMOTE || !new_game_is_omniscient) {
        throw new DiplomacyException("Invalid OmniscientUpdated: Observer promotion error.");
      }
    } else { // Was omniscient
      if (notification.grade_update !== diploStrings.DEMOTE || new_game_is_omniscient) { // new game should be observer
         throw new DiplomacyException("Invalid OmniscientUpdated: Omniscient demotion error.");
      }
    }

    const channel = game.channel;
    if (!channel) return;

    const game_id = notification.game_id; // or game.game_id
    const old_role = game.role;

    // Invalidate old game instance's channel link
    game.channel = null;
    channel.game_id_to_instances[game_id]?.remove(old_role);

    const new_game_instance = new NetworkGame(channel, notification.game as any); // Cast received_game
    new_game_instance.notification_callbacks = new Map(Object.entries(game.notification_callbacks).map(([key, value]) => [key, [...value]]));
    new_game_instance.data = game.data;

    channel.game_id_to_instances[game_id]?.add(new_game_instance);
  } else {
     logger.warn("OmniscientUpdated notification received for a player game, which is unexpected.");
  }
}

function on_power_orders_update(game: NetworkGame, notification: PowerOrdersUpdateNotification): void {
  GameEngine.set_orders(game, notification.power_name, notification.orders);
}

function on_power_orders_flag(game: NetworkGame, notification: PowerOrdersFlagNotification): void {
  const power_in_game = game.get_power(notification.power_name);
  if (GameEngine.is_player_game(game) && game.role !== notification.power_name && power_in_game) {
    power_in_game.order_is_set = notification.order_is_set;
  } else if (!GameEngine.is_player_game(game) && power_in_game) {
    // For observer/omniscient, update the flag on the power object within the game state
     power_in_game.order_is_set = notification.order_is_set;
  } else {
     logger.warn(`PowerOrdersFlag for self or unknown power ${notification.power_name} in game ${game.game_id}`);
  }
}

function on_power_vote_updated(game: NetworkGame, notification: PowerVoteUpdatedNotification): void {
  if (GameEngine.is_player_game(game)) {
    const power = game.get_power(game.role);
    if(power) power.vote = notification.vote;
  }
}

function on_power_wait_flag(game: NetworkGame, notification: PowerWaitFlagNotification): void {
  GameEngine.set_wait(game, notification.power_name, notification.wait);
}

function on_vote_count_updated(game: NetworkGame, notification: VoteCountUpdatedNotification): void {
  if (!GameEngine.is_observer_game(game)) {
      logger.warn("VoteCountUpdated received for non-observer game.");
  }
  // Actual update logic for vote count on game object would go here if applicable
}

function on_vote_updated(game: NetworkGame, notification: VoteUpdatedNotification): void {
  if (!GameEngine.is_omniscient_game(game)) {
      logger.warn("VoteUpdated received for non-omniscient game.");
      return;
  }
  for (const [power_name, vote_value] of Object.entries(notification.vote)) {
    const power = GameEngine.get_power(game, power_name);
    if (power) power.vote = vote_value;
  }
}

// Mapping from notification __type__ string to handler function
const NOTIFICATION_HANDLER_MAP: Record<string, (obj: Channel | NetworkGame, notification: any) => void> = {
  "AccountDeleted": on_account_deleted as (obj: Channel, notification: AccountDeletedNotification) => void,
  "ClearedCenters": on_cleared_centers,
  "ClearedOrders": on_cleared_orders,
  "ClearedUnits": on_cleared_units,
  "GameDeleted": on_game_deleted,
  "GameMessageReceived": on_game_message_received,
  "GameProcessed": on_game_processed,
  "GamePhaseUpdate": on_game_phase_update,
  "GameStatusUpdate": on_game_status_update,
  "OmniscientUpdated": on_omniscient_updated,
  "PowerOrdersFlag": on_power_orders_flag,
  "PowerOrdersUpdate": on_power_orders_update,
  "PowersControllers": on_powers_controllers,
  "PowerVoteUpdated": on_power_vote_updated,
  "PowerWaitFlag": on_power_wait_flag,
  "VoteCountUpdated": on_vote_count_updated,
  "VoteUpdated": on_vote_updated,
};

export function handle_notification(connection: Connection, notification: BaseNotification & { game_id?: string, game_role?: string }): void {
  let object_to_notify: Channel | NetworkGame | null = null;

  if (notification.level === diploStrings.CHANNEL) {
    const channel_ref = connection.channels.get(notification.token);
    object_to_notify = channel_ref?.deref() || null;
  } else if (notification.level === diploStrings.GAME && notification.game_id && notification.game_role) {
    object_to_notify = _get_game_to_notify(connection, notification as GameNotification);
  }

  if (!object_to_notify) {
    logger.error(`Could not find object to notify for notification: ${notification.name || notification.__type__} (Token: ${notification.token})`);
    return;
  }

  const handler = NOTIFICATION_HANDLER_MAP[notification.__type__];
  if (!handler) {
    throw new DiplomacyException(`No handler available for notification class ${notification.__type__}`);
  }

  handler(object_to_notify, notification);

  if (notification.level === diploStrings.GAME && object_to_notify instanceof NetworkGame) {
    object_to_notify.notify(notification as GameNotification); // Ensure it's a GameNotification
  }
}
