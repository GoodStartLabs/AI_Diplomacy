// diplomacy/engine/power.ts

import { DiplomacyGame } from "./game"; // Placeholder, to be created or properly typed
import { DiplomacyMap } from "./map";   // Placeholder

// Logger
const logger = {
  debug: (message: string, ...args: any[]) => console.debug('[Power]', message, ...args),
  info: (message: string, ...args: any[]) => console.info('[Power]', message, ...args),
  warn: (message: string, ...args: any[]) => console.warn('[Power]', message, ...args),
  error: (message: string, ...args: any[]) => console.error('[Power]', message, ...args),
};

// --- Placeholders for diplomacy.utils.* ---
const diploStrings = {
  ABBREV: 'abbrev', ADJUST: 'adjust', CENTERS: 'centers', CIVIL_DISORDER: 'civil_disorder',
  CONTROLLER: 'controller', HOMES: 'homes', INFLUENCE: 'influence', NAME: 'name',
  ORDER_IS_SET: 'order_is_set', ORDERS: 'orders', RETREATS: 'retreats', ROLE: 'role',
  TOKENS: 'tokens', UNITS: 'units', VOTE: 'vote', WAIT: 'wait',
  DUMMY: 'DUMMY', NEUTRAL: 'NEUTRAL', SERVER_TYPE: 'SERVER_TYPE',
  OBSERVER_TYPE: 'OBSERVER_TYPE', OMNISCIENT_TYPE: 'OMNISCIENT_TYPE',
  ALL_ROLE_TYPES: ['OBSERVER_TYPE', 'OMNISCIENT_TYPE', 'SERVER_TYPE'], // Plus power names
  ALL_VOTE_DECISIONS: ['YES', 'NO', 'NEUTRAL'],
  YES: 'YES', NO: 'NO',
};

const OrderSettings = {
  ORDER_NOT_SET: 0,
  ORDER_SET_EMPTY: 1,
  ORDER_SET: 2,
  ALL_SETTINGS: [0, 1, 2],
};

const commonUtils = {
  timestamp_microseconds: (): number => Date.now() * 1000, // Example
};

class DiplomacyException extends Error { constructor(message: string) { super(message); this.name = "DiplomacyException"; } }


export class PowerTs {
  game: DiplomacyGame | null; // Reference to the main game object
  name: string = '';
  abbrev: string | null = null;
  adjust: string[] = [];
  centers: string[] = [];
  units: string[] = [];
  influence: string[] = [];
  homes: string[] | null = null; // Can be null if not yet initialized or not applicable
  retreats: Record<string, string[]> = {}; // unit_loc_str -> possible_retreat_provinces[]
  goner: number = 0; // boolean-like (0 or 1)
  civil_disorder: number = 0; // boolean-like
  orders: Record<string, string> = {}; // unit_loc_str -> order_str OR "ORDER X" -> order_str
  role: string = ''; // Power name for players, or OBSERVER_TYPE, OMNISCIENT_TYPE, SERVER_TYPE
  controller: Map<number, string> = new Map(); // timestamp -> username or DUMMY
  vote: string = ''; // from ALL_VOTE_DECISIONS
  order_is_set: number = OrderSettings.ORDER_NOT_SET;
  wait: boolean = false;
  tokens: Set<string> = new Set(); // For server-side power: client tokens controlling this power

  constructor(game: DiplomacyGame | null = null, name: string = '', initialProps: Partial<PowerTs> = {}) {
    this.game = game;
    this.name = name;

    // Set defaults from Python's model or __init__
    this.role = initialProps.role || (name ? name : diploStrings.SERVER_TYPE); // If name provided, role is name (player)
    this.abbrev = initialProps.abbrev || null;
    this.adjust = initialProps.adjust || [];
    this.centers = initialProps.centers || [];
    this.civil_disorder = initialProps.civil_disorder || 0;
    if (initialProps.controller && initialProps.controller instanceof Map && initialProps.controller.size > 0) {
        this.controller = new Map(initialProps.controller);
    } else {
        this.controller.set(commonUtils.timestamp_microseconds(), diploStrings.DUMMY);
    }
    this.homes = initialProps.homes !== undefined ? initialProps.homes : null; // Keep null if not provided
    this.influence = initialProps.influence || [];
    this.order_is_set = initialProps.order_is_set !== undefined ? initialProps.order_is_set : OrderSettings.ORDER_NOT_SET;
    this.orders = initialProps.orders || {};
    this.retreats = initialProps.retreats || {};
    this.tokens = new Set(initialProps.tokens || []);
    this.units = initialProps.units || [];
    this.vote = initialProps.vote || diploStrings.NEUTRAL;
    this.wait = initialProps.wait !== undefined ? initialProps.wait : true; // Default wait is True for dummy/non-realtime
    this.goner = initialProps.goner || 0;

    if (this.role !== diploStrings.OBSERVER_TYPE &&
        this.role !== diploStrings.OMNISCIENT_TYPE &&
        this.role !== diploStrings.SERVER_TYPE &&
        this.role !== this.name) {
        // If role is not a special type, it should be the power's name
        logger.warn(`Power role "${this.role}" might be inconsistent with name "${this.name}". For players, role usually equals name.`);
    }
  }

  toStringCustom(): string {
    let text = `\n${this.name} (${this.role})`;
    text += `\nPLAYER ${this.get_controller()}`;
    if (this.civil_disorder) text += '\nCD';
    if (this.homes && this.homes.length > 0) text += `\nINHABITS ${this.homes.join(' ')}`;
    if (this.centers.length > 0) text += `\nOWNS ${this.centers.join(' ')}`;
    if (Object.keys(this.retreats).length > 0) {
      text += '\n' + Object.entries(this.retreats)
        .map(([unit, places]) => `${unit} --> ${places.join(', ')}`)
        .join('\n');
    }
    text = [text, ...this.units, ...this.adjust].join('\n');

    if (Object.keys(this.orders).length > 0) {
      text += '\nORDERS\n';
      text += Object.entries(this.orders)
        .map(([unit, order]) => (unit.startsWith('ORDER') || unit.startsWith('REORDER') || unit.startsWith('INVALID') ? '' : `${unit} `) + order)
        .join('\n');
    }
    return text;
  }

  customDeepCopy(gameCopy?: DiplomacyGame | null): PowerTs {
    const newPower = new PowerTs(gameCopy || null, this.name); // game reference handled by caller
    newPower.abbrev = this.abbrev;
    newPower.adjust = [...this.adjust];
    newPower.centers = [...this.centers];
    newPower.units = [...this.units];
    newPower.influence = [...this.influence];
    newPower.homes = this.homes ? [...this.homes] : null;
    newPower.retreats = JSON.parse(JSON.stringify(this.retreats)); // Deep copy for object of arrays
    newPower.goner = this.goner;
    newPower.civil_disorder = this.civil_disorder;
    newPower.orders = { ...this.orders };
    newPower.role = this.role;
    newPower.controller = new Map(this.controller);
    newPower.vote = this.vote;
    newPower.order_is_set = this.order_is_set;
    newPower.wait = this.wait;
    newPower.tokens = new Set(this.tokens);
    return newPower;
  }

  reinit(include_flags: number = 6): void { // 1=orders, 2=persistent, 4=transient
    const reinit_persistent = (include_flags & 2) !== 0;
    const reinit_transient = (include_flags & 4) !== 0;
    const reinit_orders = (include_flags & 1) !== 0;

    if (reinit_persistent) {
      this.abbrev = null; // Or re-fetch from map if initialize is called later
    }

    if (reinit_transient) {
      // In Python, this updated a game hash. Here, we just clear the lists.
      // The game hash update logic would be part of the GameTs class if implemented.
      if (this.game) { // Placeholder for game.update_hash logic
          (this.homes || []).forEach(home => this.game!.update_hash(this.name, { loc: home, is_home: true }));
          this.centers.forEach(center => this.game!.update_hash(this.name, { loc: center, is_center: true }));
          this.units.forEach(unit => this.game!.update_hash(this.name, { unit_type: unit[0], loc: unit.substring(2) }));
          Object.keys(this.retreats).forEach(dis_unit => this.game!.update_hash(this.name, { unit_type: dis_unit[0], loc: dis_unit.substring(2), is_dislodged: true }));
      }
      this.homes = null; // Or [] depending on desired state after reinit
      this.centers = [];
      this.units = [];
      this.influence = [];
      this.retreats = {};
    }

    if (reinit_orders) {
      this.civil_disorder = 0;
      this.adjust = [];
      this.orders = {};
      if (this.is_eliminated()) {
        this.order_is_set = OrderSettings.ORDER_SET_EMPTY;
        this.wait = false;
      } else {
        this.order_is_set = OrderSettings.ORDER_NOT_SET;
        this.wait = this.is_dummy() ? true : !(this.game && this.game.real_time); // Assuming game.real_time exists
      }
    }
    this.goner = 0; // Reset goner status
  }

  static compare(power_1: PowerTs, power_2: PowerTs): number {
    const role1 = power_1.role || "";
    const role2 = power_2.role || "";
    if (role1 < role2) return -1;
    if (role1 > role2) return 1;

    const name1 = power_1.name || "";
    const name2 = power_2.name || "";
    if (name1 < name2) return -1;
    if (name1 > name2) return 1;
    return 0;
  }

  initialize(game: DiplomacyGame): void {
    if (!this.is_server_power() && !this.is_player_power() && !this.is_dummy()) { // Simplified check, Python checks server_power
        logger.warn(`Initialize called on non-standard power role: ${this.role}`);
        // return; // Or handle as appropriate
    }

    this.game = game;
    this.order_is_set = OrderSettings.ORDER_NOT_SET;
    this.wait = this.is_dummy() ? true : !(this.game && this.game.real_time);

    const map = this.game.map as DiplomacyMap; // Cast to access map properties
    this.abbrev = map.abbrev[this.name] || this.name[0];

    if (this.homes === null) { // Only init if not already set (e.g. by map load)
        this.homes = [];
        (map.homes[this.name] || []).forEach(home => {
            this.game!.update_hash(this.name, { loc: home, is_home: true }); // Placeholder
            this.homes!.push(home);
        });
    }
    if (this.centers.length === 0) {
        (map.centers[this.name] || []).forEach(center => {
            game.update_hash(this.name, { loc: center, is_center: true }); // Placeholder
            this.centers.push(center);
        });
    }
    if (this.units.length === 0) {
        (map.units[this.name] || []).forEach(unit => {
            game.update_hash(this.name, { unit_type: unit[0], loc: unit.substring(2) }); // Placeholder
            this.units.push(unit);
            this.influence.push(unit.substring(2, 5)); // unit[2:5] is loc part
        });
    }
  }

  merge(other_power: PowerTs): void {
    if (!this.game || this.game !== other_power.game) {
        logger.error("Cannot merge powers from different games or without a game context.");
        return;
    }
    const game = this.game; // For update_hash calls

    other_power.units.forEach(unit => {
        this.units.push(unit);
        game.update_hash(this.name, { unit_type: unit[0], loc: unit.substring(2) });
        game.update_hash(other_power.name, { unit_type: unit[0], loc: unit.substring(2) });
    });
    other_power.units = [];

    Object.entries(other_power.retreats).forEach(([unit, retreats]) => {
        this.retreats[unit] = retreats;
        game.update_hash(this.name, { unit_type: unit[0], loc: unit.substring(2), is_dislodged: true });
        game.update_hash(other_power.name, { unit_type: unit[0], loc: unit.substring(2), is_dislodged: true });
    });
    other_power.retreats = {};

    other_power.influence.forEach(loc => {
        if (!this.influence.includes(loc)) this.influence.push(loc);
    });
    other_power.influence = [];

    other_power.centers.forEach(center => {
        if (!this.centers.includes(center)) this.centers.push(center);
        game.update_hash(this.name, { loc: center, is_center: true });
        game.update_hash(other_power.name, { loc: center, is_center: true });
    });
    other_power.centers = [];

    if (other_power.homes) {
        this.homes = this.homes || [];
        other_power.homes.forEach(home => {
            if (!this.homes!.includes(home)) this.homes!.push(home);
            game.update_hash(this.name, { loc: home, is_home: true });
            game.update_hash(other_power.name, { loc: home, is_home: true });
        });
    }
    other_power.homes = []; // Clears it, Python uses `list(other_power.homes)` then `other_power.homes.remove(home)`

    game.clear_cache(); // Placeholder
  }

  clear_units(): void {
    if (this.game) {
        this.units.forEach(unit => this.game!.update_hash(this.name, { unit_type: unit[0], loc: unit.substring(2) }));
        Object.keys(this.retreats).forEach(unit => this.game!.update_hash(this.name, { unit_type: unit[0], loc: unit.substring(2), is_dislodged: true }));
    }
    this.units = [];
    this.retreats = {};
    this.influence = []; // Clearing influence as it's tied to units
    this.game?.clear_cache();
  }

  clear_centers(): void {
    if (this.game) {
        this.centers.forEach(center => this.game!.update_hash(this.name, { loc: center, is_center: true }));
    }
    this.centers = [];
    this.game?.clear_cache();
  }

  clear_orders(): void {
    this.reinit(1); // 1 = orders flag
  }

  is_dummy(): boolean {
    const lastController = this.controller.size > 0 ? Array.from(this.controller.values())[this.controller.size - 1] : undefined;
    return lastController === diploStrings.DUMMY;
  }

  is_eliminated(): boolean {
    // Not eliminated if has units, centers, or retreats
    return this.units.length === 0 && this.centers.length === 0 && Object.keys(this.retreats).length === 0;
  }

  moves_submitted(): boolean {
    if (!this.game || this.game.phase_type !== 'M') { // Assuming game has phase_type property
        return true; // Not in a Movement phase, so considered "submitted" or not applicable
    }
    // True if orders are set or no units left to order
    return (this.order_is_set !== OrderSettings.ORDER_NOT_SET && this.order_is_set !== null) || this.units.length === 0;
  }

  // Network/Application Role Checkers
  is_observer_power(): boolean {
    return this.role === diploStrings.OBSERVER_TYPE;
  }

  is_omniscient_power(): boolean {
    return this.role === diploStrings.OMNISCIENT_TYPE;
  }

  is_player_power(): boolean {
    // In Python, role == self.name. Here, name is already normalized.
    // Role might be the original casing from map file if it was set that way.
    // For consistency, compare normalized versions or ensure role is also normalized on set.
    // Assuming this.role is the canonical role string (like an ENUM member or power name).
    return this.role === this.name;
  }

  is_server_power(): boolean {
    return this.role === diploStrings.SERVER_TYPE;
  }

  is_controlled(): boolean {
    const lastController = this.controller.size > 0 ? Array.from(this.controller.values())[this.controller.size - 1] : undefined;
    return lastController !== diploStrings.DUMMY;
  }

  does_not_wait(): boolean {
    // order_is_set is true if not ORDER_NOT_SET (0)
    // Python: self.order_is_set and not self.wait
    return (this.order_is_set !== OrderSettings.ORDER_NOT_SET && this.order_is_set !== null) && !this.wait;
  }

  // Controller Management
  update_controller(username: string, timestamp: number): void {
    this.controller.set(timestamp, username);
    // In Python, SortedDict would keep it sorted. Map iteration is by insertion order.
    // If exact sorted behavior of SortedDict.last_value() is critical beyond just getting the latest,
    // this might need adjustment or a sorted map implementation. For now, standard Map is used.
  }

  set_controlled(username: string | null): void {
    const currentTimestamp = commonUtils.timestamp_microseconds();
    const currentController = this.get_controller();

    if (username === null || username === diploStrings.DUMMY) {
      if (currentController !== diploStrings.DUMMY) {
        this.controller.set(currentTimestamp, diploStrings.DUMMY);
        this.tokens.clear();
        this.wait = true; // Default for dummy
        this.vote = diploStrings.NEUTRAL;
      }
    } else {
      if (currentController === diploStrings.DUMMY) {
        this.controller.set(currentTimestamp, username);
        this.wait = !(this.game && this.game.real_time); // Wait unless real-time game
      } else if (currentController !== username) {
        throw new DiplomacyException('Power already controlled by someone else. Kick previous controller before.');
      }
      // If already controlled by this username, do nothing.
    }
  }

  get_controller(): string {
    if (this.controller.size === 0) {
      return diploStrings.DUMMY; // Should ideally not happen if constructor sets it
    }
    // Get the last inserted item (latest timestamp)
    // This relies on Map preserving insertion order.
    const lastEntry = Array.from(this.controller.entries())[this.controller.size - 1];
    return lastEntry ? lastEntry[1] : diploStrings.DUMMY;
  }

  get_controller_timestamp(): number {
     if (this.controller.size === 0) {
      return 0;
    }
    const lastEntry = Array.from(this.controller.keys())[this.controller.size - 1];
    return lastEntry || 0;
  }

  is_controlled_by(username: string | null): boolean {
    // Python's constants.PRIVATE_BOT_USERNAME needs to be handled.
    // Assuming a similar constant exists in TS or is passed.
    const PRIVATE_BOT_USERNAME_TS_EQUIVALENT = "DAIDE_BOT"; // Example placeholder

    if (username === PRIVATE_BOT_USERNAME_TS_EQUIVALENT) {
      return this.is_dummy() && this.tokens.size > 0;
    }
    return this.get_controller() === username;
  }

  // Server-only token methods
  has_token(token: string): boolean {
    if (!this.is_server_power()) {
        logger.warn("has_token called on non-server power instance.");
        // Or throw error, depending on desired strictness
    }
    return this.tokens.has(token);
  }

  add_token(token: string): void {
    if (!this.is_server_power()) {
        logger.warn("add_token called on non-server power instance.");
        // return;
    }
    this.tokens.add(token);
  }

  remove_tokens(tokens_to_remove: Set<string> | string[]): void {
    if (!this.is_server_power()) {
        logger.warn("remove_tokens called on non-server power instance.");
        // return;
    }
    const tokensSet = tokens_to_remove instanceof Set ? tokens_to_remove : new Set(tokens_to_remove);
    tokensSet.forEach(token => this.tokens.delete(token));
  }
}
