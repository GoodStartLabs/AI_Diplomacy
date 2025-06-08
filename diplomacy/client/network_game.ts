// diplomacy/client/network_game.ts

import { Channel } from './channel'; // Assuming Channel is exported from channel.ts

// Logger setup
const logger = {
  debug: (message: string) => console.debug(message),
  info: (message: string) => console.info(message),
  warn: (message: string) => console.warn(message),
  error: (message: string, error?: any) => console.error(message, error),
};

// --- Placeholder for diplomacy.engine.game.Game ---
// This is a simplified placeholder. A real conversion would need a more detailed Game class.
class BaseGame {
  // Properties that NetworkGame constructor expects from received_game.get_model()
  [key: string]: any; // Allow any properties for the spread in constructor

  constructor(initial_state?: any) {
    if (initial_state) {
      Object.assign(this, initial_state);
    }
    // Initialize other base Game properties if necessary
  }

  // Placeholder for a method NetworkGame.synchronize uses
  get_latest_timestamp(): number | string | null {
    // This should return the latest known timestamp of the game state
    // to help the server determine what data is new for this client.
    // Example: could be based on phases, messages, etc.
    logger.warn("BaseGame.get_latest_timestamp() placeholder called.");
    return null;
  }

  // Placeholder static-like methods for role checking (from game_instances_set.ts)
  // These would ideally be part of the actual Game class definition.
  static is_player_game(game: { role: string }): boolean {
    return game.role === game.role.toUpperCase() && !['OBSERVER', 'OMNISCIENT'].includes(game.role);
  }
  static is_observer_game(game: { role: string }): boolean {
    return game.role === 'OBSERVER';
  }
  static is_omniscient_game(game: { role: string }): boolean {
    return game.role === 'OMNISCIENT';
  }
}


// --- Placeholder for diplomacy.communication.notifications ---
interface BaseDiplomacyNotification {
  __type__: string; // To identify notification type, e.g., "ClearedCenters"
  // Common notification fields
}
// Example specific notification types (many more would be needed)
interface ClearedCentersNotification extends BaseDiplomacyNotification { __type__: "ClearedCenters"; /* ... specific fields */ }
interface GameMessageReceivedNotification extends BaseDiplomacyNotification { __type__: "GameMessageReceived"; /* ... */ }
interface GameProcessedNotification extends BaseDiplomacyNotification { __type__: "GameProcessed"; /* ... */ }
interface GamePhaseUpdateNotification extends BaseDiplomacyNotification { __type__: "GamePhaseUpdate"; /* ... */ }
interface GameStatusUpdateNotification extends BaseDiplomacyNotification { __type__: "GameStatusUpdate"; /* ... */ }
interface OmniscientUpdatedNotification extends BaseDiplomacyNotification { __type__: "OmniscientUpdated"; /* ... */ }
interface PowerOrdersFlagNotification extends BaseDiplomacyNotification { __type__: "PowerOrdersFlag"; /* ... */ }
interface PowerOrdersUpdateNotification extends BaseDiplomacyNotification { __type__: "PowerOrdersUpdate"; /* ... */ }
interface PowerVoteUpdatedNotification extends BaseDiplomacyNotification { __type__: "PowerVoteUpdated"; /* ... */ }
interface PowerWaitFlagNotification extends BaseDiplomacyNotification { __type__: "PowerWaitFlag"; /* ... */ }
interface PowersControllersNotification extends BaseDiplomacyNotification { __type__: "PowersControllers"; /* ... */ }
interface VoteCountUpdatedNotification extends BaseDiplomacyNotification { __type__: "VoteCountUpdated"; /* ... */ }
interface VoteUpdatedNotification extends BaseDiplomacyNotification { __type__: "VoteUpdated"; /* ... */ }
interface GameDeletedNotification extends BaseDiplomacyNotification { __type__: "GameDeleted"; /* ... */ }


const notificationsPlaceholders = {
    ClearedCenters: { __type__: "ClearedCenters" } as ClearedCentersNotification,
    ClearedOrders: { __type__: "ClearedOrders" } as BaseDiplomacyNotification, // Assuming similar structure
    ClearedUnits: { __type__: "ClearedUnits" } as BaseDiplomacyNotification,
    GameDeleted: { __type__: "GameDeleted" } as GameDeletedNotification,
    GameMessageReceived: { __type__: "GameMessageReceived" } as GameMessageReceivedNotification,
    GameProcessed: { __type__: "GameProcessed" } as GameProcessedNotification,
    GamePhaseUpdate: { __type__: "GamePhaseUpdate" } as GamePhaseUpdateNotification,
    GameStatusUpdate: { __type__: "GameStatusUpdate" } as GameStatusUpdateNotification,
    OmniscientUpdated: { __type__: "OmniscientUpdated" } as OmniscientUpdatedNotification,
    PowerOrdersFlag: { __type__: "PowerOrdersFlag" } as PowerOrdersFlagNotification,
    PowerOrdersUpdate: { __type__: "PowerOrdersUpdate" } as PowerOrdersUpdateNotification,
    PowerVoteUpdated: { __type__: "PowerVoteUpdated" } as PowerVoteUpdatedNotification,
    PowerWaitFlag: { __type__: "PowerWaitFlag" } as PowerWaitFlagNotification,
    PowersControllers: { __type__: "PowersControllers" } as PowersControllersNotification,
    VoteCountUpdated: { __type__: "VoteCountUpdated" } as VoteCountUpdatedNotification,
    VoteUpdated: { __type__: "VoteUpdated" } as VoteUpdatedNotification,
};
type NotificationConstructor = new (...args: any[]) => BaseDiplomacyNotification;


// --- Placeholder for diplomacy.utils.exceptions ---
class DiplomacyException extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DiplomacyException";
  }
}

// Type for notification callbacks
type NotificationCallback = (network_game: NetworkGame, notification: BaseDiplomacyNotification) => void;


// Helper function to create game request methods
function createGameRequestMethod(channelMethod: Function): (kwargs: Record<string, any>) => Promise<any> {
  // In Python, channel_method had __request_name__ and __request_params__
  // We'll skip those for simplicity in TS placeholders, but they could be added if Channel methods are more fleshed out.
  return async function(this: NetworkGame, kwargs: Record<string, any> = {}): Promise<any> {
    if (!this.channel) {
      throw new DiplomacyException('Invalid client game: channel is not set.');
    }
    // The channel method itself is already an async function that takes (game, kwargs)
    // e.g., this.channel._get_phase_history(this, **kwargs)
    return channelMethod.call(this.channel, this, kwargs);
  };
}

// Helper function to create callback setting methods
function createCallbackSettingMethod(NotificationClassPlaceholder: { __type__: string }): (notification_callback: NotificationCallback) => void {
  return function(this: NetworkGame, notification_callback: NotificationCallback): void {
    this.add_notification_callback(NotificationClassPlaceholder.__type__, notification_callback);
  };
}

// Helper function to create callback clearing methods
function createCallbackClearingMethod(NotificationClassPlaceholder: { __type__: string }): () => void {
  return function(this: NetworkGame): void {
    this.clear_notification_callbacks(NotificationClassPlaceholder.__type__);
  };
}


export class NetworkGame extends BaseGame {
  channel: Channel | null; // Can be null if game is invalidated or left
  notification_callbacks: Map<string, NotificationCallback[]>; // Notification type string to list of callbacks
  data: any; // As per Python's __slots__

  constructor(channel: Channel, received_game: BaseGame) {
    // Initialize parent class with Jsonable attributes from received game.
    // Assuming received_game has a get_model() method or properties directly.
    // For simplicity, we'll spread received_game if it's a plain object.
    // If get_model() is essential, received_game type needs to reflect that.
    let initial_attrs: any = {};
    if (typeof (received_game as any).get_model === 'function') {
        initial_attrs = (received_game as any).get_model();
    } else {
        // Fallback: attempt to spread properties. This is risky if received_game is complex.
        initial_attrs = { ...received_game };
    }
    super(initial_attrs);

    this.channel = channel;
    this.notification_callbacks = new Map<string, NotificationCallback[]>();
    this.data = null; // Initialize data property
  }

  // Public API - Game Request Methods
  // These assume that the Channel class has methods like _get_phase_history, _leave_game, etc.
  // and these methods are designed to be called with (game_instance, kwargs)
  get_phase_history = createGameRequestMethod(Channel.prototype._get_phase_history);
  leave = createGameRequestMethod(Channel.prototype._leave_game);
  send_game_message = createGameRequestMethod(Channel.prototype._send_game_message);
  set_orders = createGameRequestMethod(Channel.prototype._set_orders);

  clear_centers = createGameRequestMethod(Channel.prototype._clear_centers);
  clear_orders = createGameRequestMethod(Channel.prototype._clear_orders);
  clear_units = createGameRequestMethod(Channel.prototype._clear_units);

  wait = createGameRequestMethod(Channel.prototype._wait);
  no_wait = createGameRequestMethod(Channel.prototype._no_wait);
  vote = createGameRequestMethod(Channel.prototype._vote);
  save = createGameRequestMethod(Channel.prototype._save);

  synchronize(): Promise<any> {
    if (!this.channel) {
      throw new DiplomacyException('Invalid client game: channel is not set.');
    }
    // Channel._synchronize expects (game, kwargs), where kwargs includes timestamp
    return this.channel._synchronize(this, { timestamp: this.get_latest_timestamp() });
  }

  // Admin / Moderator API
  delete = createGameRequestMethod(Channel.prototype._delete_game);
  kick_powers = createGameRequestMethod(Channel.prototype._kick_powers);
  set_state = createGameRequestMethod(Channel.prototype._set_state);
  process = createGameRequestMethod(Channel.prototype._process);
  query_schedule = createGameRequestMethod(Channel.prototype._query_schedule);
  start = createGameRequestMethod(Channel.prototype._start);
  pause = createGameRequestMethod(Channel.prototype._pause);
  resume = createGameRequestMethod(Channel.prototype._resume);
  cancel = createGameRequestMethod(Channel.prototype._cancel);
  draw = createGameRequestMethod(Channel.prototype._draw);


  // Notification callback settings
  add_on_cleared_centers = createCallbackSettingMethod(notificationsPlaceholders.ClearedCenters);
  add_on_cleared_orders = createCallbackSettingMethod(notificationsPlaceholders.ClearedOrders);
  add_on_cleared_units = createCallbackSettingMethod(notificationsPlaceholders.ClearedUnits);
  add_on_game_deleted = createCallbackSettingMethod(notificationsPlaceholders.GameDeleted);
  add_on_game_message_received = createCallbackSettingMethod(notificationsPlaceholders.GameMessageReceived);
  add_on_game_processed = createCallbackSettingMethod(notificationsPlaceholders.GameProcessed);
  add_on_game_phase_update = createCallbackSettingMethod(notificationsPlaceholders.GamePhaseUpdate);
  add_on_game_status_update = createCallbackSettingMethod(notificationsPlaceholders.GameStatusUpdate);
  add_on_omniscient_updated = createCallbackSettingMethod(notificationsPlaceholders.OmniscientUpdated);
  add_on_power_orders_flag = createCallbackSettingMethod(notificationsPlaceholders.PowerOrdersFlag);
  add_on_power_orders_update = createCallbackSettingMethod(notificationsPlaceholders.PowerOrdersUpdate);
  add_on_power_vote_updated = createCallbackSettingMethod(notificationsPlaceholders.PowerVoteUpdated);
  add_on_power_wait_flag = createCallbackSettingMethod(notificationsPlaceholders.PowerWaitFlag);
  add_on_powers_controllers = createCallbackSettingMethod(notificationsPlaceholders.PowersControllers);
  add_on_vote_count_updated = createCallbackSettingMethod(notificationsPlaceholders.VoteCountUpdated);
  add_on_vote_updated = createCallbackSettingMethod(notificationsPlaceholders.VoteUpdated);

  clear_on_cleared_centers = createCallbackClearingMethod(notificationsPlaceholders.ClearedCenters);
  clear_on_cleared_orders = createCallbackClearingMethod(notificationsPlaceholders.ClearedOrders);
  clear_on_cleared_units = createCallbackClearingMethod(notificationsPlaceholders.ClearedUnits);
  clear_on_game_deleted = createCallbackClearingMethod(notificationsPlaceholders.GameDeleted);
  clear_on_game_message_received = createCallbackClearingMethod(notificationsPlaceholders.GameMessageReceived);
  clear_on_game_processed = createCallbackClearingMethod(notificationsPlaceholders.GameProcessed);
  clear_on_game_phase_update = createCallbackClearingMethod(notificationsPlaceholders.GamePhaseUpdate);
  clear_on_game_status_update = createCallbackClearingMethod(notificationsPlaceholders.GameStatusUpdate);
  clear_on_omniscient_updated = createCallbackClearingMethod(notificationsPlaceholders.OmniscientUpdated);
  clear_on_power_orders_flag = createCallbackClearingMethod(notificationsPlaceholders.PowerOrdersFlag);
  clear_on_power_orders_update = createCallbackClearingMethod(notificationsPlaceholders.PowerOrdersUpdate);
  clear_on_power_vote_updated = createCallbackClearingMethod(notificationsPlaceholders.PowerVoteUpdated);
  clear_on_power_wait_flag = createCallbackClearingMethod(notificationsPlaceholders.PowerWaitFlag);
  clear_on_powers_controllers = createCallbackClearingMethod(notificationsPlaceholders.PowersControllers);
  clear_on_vote_count_updated = createCallbackClearingMethod(notificationsPlaceholders.VoteCountUpdated);
  clear_on_vote_updated = createCallbackClearingMethod(notificationsPlaceholders.VoteUpdated);


  add_notification_callback(notification_type: string, notification_callback: NotificationCallback): void {
    if (typeof notification_callback !== 'function') {
        logger.error("Provided notification_callback is not a function.");
        return;
    }
    if (!this.notification_callbacks.has(notification_type)) {
      this.notification_callbacks.set(notification_type, []);
    }
    this.notification_callbacks.get(notification_type)!.push(notification_callback);
  }

  clear_notification_callbacks(notification_type: string): void {
    this.notification_callbacks.delete(notification_type);
  }

  notify(notification: BaseDiplomacyNotification): void {
    const callbacks = this.notification_callbacks.get(notification.__type__) || [];
    for (const callback of callbacks) {
      try {
        callback(this, notification);
      } catch (e: any) {
        logger.error(`Error executing notification callback for ${notification.__type__}: ${e.message}`, e);
      }
    }
  }
}
