// diplomacy/engine/game.ts

import { DiplomacyMap } from './map';
import { PowerTs } from './power';
import { DiplomacyMessage, GLOBAL_RECIPIENT, OBSERVER_RECIPIENT, OMNISCIENT_RECIPIENT, SYSTEM_SENDER } from './message';
import {
    OrderResult,
    PossibleConvoyPathInfo,
    DiplomacyMessageData,
    SupportEntry,
    UnitOrders, // Assuming this is Record<string, string> for { "A PAR": "- MAR" }
    PowerOrderedUnits, // Assuming this is Record<string, string[]> for { "FRANCE": ["A PAR", "F BRE"] }
    ConvoyPathsTable,
    MayConvoyTable,
    ParsedOrder // Make sure this is imported
} from './interfaces';
import { GamePhaseData, MESSAGES_TYPE_PLACEHOLDER as MESSAGES_TYPE } from '../utils/game_phase_data';
import * as diploStrings from '../utils/strings';
import * as err from '../utils/errors';  // Assuming you'll create a similar error constant file
import * as commonUtils from '../utils/common'; // Assuming common utilities
import { OrderSettings, DEFAULT_GAME_RULES } from '../utils/constants';

// Logger
const logger = {
  debug: (message: string, ...args: any[]) => console.debug('[Game]', message, ...args),
  info: (message: string, ...args: any[]) => console.info('[Game]', message, ...args),
  warn: (message: string, ...args: any[]) => console.warn('[Game]', message, ...args),
  error: (message: string, ...args: any[]) => console.error('[Game]', message, ...args),
};

// Simpler SortedDict replacement for now, assuming Map preserves insertion order for iteration.
type SortedMap<K, V> = Map<K, V>;
const createSortedMap = <K,V>() : SortedMap<K,V> => new Map<K,V>();

// Custom Diplomacy Exception (basic version)
class DiplomacyException extends Error {
    constructor(message: string) {
        super(message);
        this.name = "DiplomacyException";
    }
}


export class DiplomacyGame {
  // Properties
  victory: number[] | null = null;
  no_rules: Set<string> = new Set();
  meta_rules: string[] = [];
  phase: string = '';
  note: string = '';
  map: DiplomacyMap;
  powers: Record<string, PowerTs> = {};
  outcome: string[] = [];
  error: string[] = [];
  popped: string[] = [];

  messages: SortedMap<number, DiplomacyMessage>;
  order_history: SortedMap<string, Record<string, string[]>>;
  orders: Record<string, UnitOrders> = {};
  ordered_units: PowerOrderedUnits = {};

  phase_type: string | null = null;
  win: number = 0;

  combat: Record<string, Record<number, Array<[string, string[]]>>> = {};
  command: Record<string, ParsedOrder> = {}; // Changed from UnitOrders to Record<string, ParsedOrder>
  result: Record<string, OrderResult[]> = {};
  supports: Record<string, SupportEntry> = {};
  dislodged: Record<string, string> = {}; // unit_name -> province_base_attacker_came_from
  lost: Record<string, string> = {};

  convoy_paths: ConvoyPathsTable = {};
  convoy_paths_possible: PossibleConvoyPathInfo[] | null = null;
  convoy_paths_dest: Map<string, Map<string, Set<string>[]>> = new Map();

  zobrist_hash: string = "0";

  game_id: string;
  map_name: string = 'standard';
  role: string;
  rules: string[] = [];

  message_history: SortedMap<string, SortedMap<number, DiplomacyMessage>>;
  state_history: SortedMap<string, any>;
  result_history: SortedMap<string, Record<string, any[]>>;

  status: string;
  timestamp_created: number;
  n_controls: number | null = null;
  deadline: number = 300;
  registration_password: string | null = null;

  observer_level: string | null = null;
  controlled_powers: string[] | null = null;
  daide_port: number | null = null;

  fixed_state: [string, string] | null = null;
  power_model_map: Record<string, string> = {};
  phase_summaries: Record<string, string> = {};

  parsed_orders_this_phase: ParsedOrder[] = [];

  private _unit_owner_cache: Map<string, PowerTs | null> | null = null;
  private _phase_wrapper_type: (phase: string) => string;


  constructor(game_id?: string | null, initial_props: Partial<DiplomacyGame> = {}) {
    this.game_id = game_id || `ts_game_${Date.now()}${Math.floor(Math.random()*1000)}`;
    this.map_name = initial_props.map_name || 'standard';
    this.map = new DiplomacyMap(this.map_name);

    this.role = initial_props.role || diploStrings.SERVER_TYPE;
    this.rules = [...(initial_props.rules || DEFAULT_GAME_RULES)];
    this.no_rules = new Set(initial_props.no_rules || []);
    this.meta_rules = initial_props.meta_rules || [];

    this.phase = initial_props.phase || '';
    this.note = initial_props.note || '';
    this.outcome = initial_props.outcome || [];
    this.error = initial_props.error || [];
    this.popped = initial_props.popped || [];

    this.messages = createSortedMap<number, DiplomacyMessage>();
    this.order_history = createSortedMap<string, Record<string, string[]>>();
    this.message_history = createSortedMap<string, SortedMap<number, DiplomacyMessage>>();
    this.state_history = createSortedMap<string, any>();
    this.result_history = createSortedMap<string, Record<string, any[]>>();

    this.status = initial_props.status || diploStrings.FORMING;
    this.timestamp_created = initial_props.timestamp_created || commonUtils.timestamp_microseconds();
    this.n_controls = initial_props.n_controls !== undefined ? initial_props.n_controls : null;
    this.deadline = initial_props.deadline !== undefined ? initial_props.deadline : 300;
    this.registration_password = initial_props.registration_password || null;
    this.zobrist_hash = initial_props.zobrist_hash || "0";

    this.orders = initial_props.orders || {};

    this._phase_wrapper_type = (phaseStr: string) => phaseStr;

    const initialRules = [...this.rules];
    this.rules = [];
    initialRules.forEach(rule => this.add_rule(rule));

    if (this.rules.includes('NO_DEADLINE')) this.deadline = 0;
    if (this.rules.includes('SOLITAIRE')) this.n_controls = 0;
    else if (this.n_controls === 0) this.add_rule('SOLITAIRE');

    this._validate_status(initial_props.powers === undefined);

    if (initial_props.powers) {
        for (const [pName, pData] of Object.entries(initial_props.powers)) {
            this.powers[pName] = new PowerTs(this, pName, pData as Partial<PowerTs>);
        }
    } else if (this.status !== diploStrings.FORMING) {
        this._begin();
    }

    if(initial_props.order_history) this.order_history = new Map(Object.entries(initial_props.order_history).map(([k,v]) => [this._phase_wrapper_type(k),v]));
    if(initial_props.message_history) this.message_history = new Map(Object.entries(initial_props.message_history).map(([k,v]) => [this._phase_wrapper_type(k), new Map(Object.entries(v).map(([ts,m])=>[Number(ts), new DiplomacyMessage(m)])) ]));
    if(initial_props.state_history) this.state_history = new Map(Object.entries(initial_props.state_history).map(([k,v]) => [this._phase_wrapper_type(k),v]));
    if(initial_props.result_history) this.result_history = new Map(Object.entries(initial_props.result_history).map(([k,v]) => [this._phase_wrapper_type(k),v]));
    if(initial_props.messages) this.messages = new Map(Object.entries(initial_props.messages).map(([ts,m])=>[Number(ts), new DiplomacyMessage(m)]));

    if (this.map && this.map.powers) {
        this.map.powers.forEach(pName => {
            if (!this.has_power(pName)) {
                 logger.error(`Map power ${pName} not found in game powers after init.`);
            }
        });
    }
    this.assert_power_roles();
  }

  private assert_power_roles(): void {
    if (this.is_player_game()) {
        if(!Object.values(this.powers).every(p => p.role === p.name)) {
            // logger.warn("Inconsistent power roles for a player game."); // Allow for multi-power control
        }
    } else {
        if(this.role !== diploStrings.OBSERVER_TYPE && this.role !== diploStrings.OMNISCIENT_TYPE && this.role !== diploStrings.SERVER_TYPE) {
            logger.warn(`Game role ${this.role} is not a special type for a non-player game.`);
        }
        if(!Object.values(this.powers).every(p => p.role === this.role)) {
             // logger.warn(`Inconsistent power roles; not all match game role ${this.role}.`); // Allow for multi-power control
        }
    }
  }

  get current_short_phase(): string {
    return this.map.phase_abbr(this.phase, this.phase);
  }
  get is_game_done(): boolean { return this.phase === 'COMPLETED'; }
  get is_game_forming(): boolean { return this.status === diploStrings.FORMING; }

  is_supporting_orders_phase(): boolean {
    return this.phase_type === 'M';
  }

  private _validate_status(reinit_powers: boolean): void {
    if (!this.map) this.map = new DiplomacyMap(this.map_name);
    this.victory = this.map.victory;
    if (!this.victory || this.victory.length === 0) {
        this.victory = [Math.floor(this.map.scs.length / 2) + 1];
    }

    if (!this.phase) this.phase = this.map.phase || "SPRING 1901 MOVEMENT"; // Default if map phase is also empty

    const phaseParts = this.phase.split(' ');
    if (phaseParts.length === 3) {
        this.phase_type = phaseParts[2][0].toUpperCase();
    } else if (this.phase === diploStrings.FORMING || this.phase === diploStrings.COMPLETED) {
        this.phase_type = null; // Or some other indicator like '-'
    } else {
        logger.error(`Phase string "${this.phase}" is not in the expected "SEASON YEAR TYPE" format.`);
        this.phase_type = '-'; // Default/error
    }

    if (this.phase !== diploStrings.FORMING && this.phase !== diploStrings.COMPLETED) {
        try {
            const year = Math.abs(parseInt(this.phase.split(' ')[1]) - (this.map.first_year || 1901));
            this.win = this.victory[Math.min(year, this.victory.length - 1)];
        } catch (e) {
            this.error.push(err.GAME_BAD_YEAR_GAME_PHASE);
            this.win = this.victory[0]; // Fallback
        }
    }

    if (reinit_powers) {
        this.powers = {};
        (this.map.powers || []).forEach(pName => {
            this.powers[pName] = new PowerTs(this, pName, { role: this.role });
        });
    }
  }

  private _begin(): void {
    this._move_to_start_phase();
    this.note = '';
    this.win = this.victory ? this.victory[0] : 0;

    (this.map.powers || []).forEach(pName => {
        if (!this.powers[pName]) {
            this.powers[pName] = new PowerTs(this, pName, { role: this.role });
        }
    });
    Object.values(this.powers).forEach(power => power.initialize(this));
    this.build_caches();
    logger.info(`Game ${this.game_id} begun. Phase: ${this.phase}`);
  }

  private _move_to_start_phase(): void {
    this.phase = this.map.phase || "SPRING 1901 MOVEMENT";
    const parts = this.phase.split(' ');
    this.phase_type = (parts.length === 3) ? parts[2][0].toUpperCase() : '-';
  }

  public get_power(power_name?: string | null): PowerTs | null {
    if (!power_name) return null;
    return this.powers[power_name.toUpperCase()] || null;
  }

  public has_power(power_name: string): boolean {
    return !!this.get_power(power_name);
  }

  public add_rule(rule: string): void {
    if (!this.rules.includes(rule)) {
        this.rules.push(rule);
    }
  }

  public update_hash(powerName: string, details: any): void { /* Placeholder for Zobrist Hashing */ }

  public clear_cache(): void {
      this._unit_owner_cache = null;
      this.convoy_paths_possible = null;
      this.convoy_paths_dest = new Map();
      logger.debug("Game caches cleared.");
  }
  public build_caches(): void {
      this.clear_cache();
      this._build_list_possible_convoys_ts();
      this._build_unit_owner_cache_ts();
      logger.debug("Game.build_caches() called and executed helper methods.");
  }

  public get_state(): any {
    const state: any = {};
    state['timestamp'] = commonUtils.timestamp_microseconds();
    state['zobrist_hash'] = this.zobrist_hash;
    state['note'] = this.note;
    state['name'] = this.current_short_phase;
    state['units'] = {}; state['retreats'] = {}; state['centers'] = {};
    state['homes'] = {}; state['influence'] = {}; state['civil_disorder'] = {};
    state['builds'] = {};

    for (const power of Object.values(this.powers)) {
        state['units'][power.name] = [...power.units, ...Object.keys(power.retreats).map(u => `*${u}`)];
        state['retreats'][power.name] = { ...power.retreats };
        state['centers'][power.name] = [...power.centers];
        state['homes'][power.name] = [...(power.homes || [])];
        state['influence'][power.name] = [...power.influence];
        state['civil_disorder'][power.name] = power.civil_disorder;
        state['builds'][power.name] = {};
        if (this.phase_type !== 'A') {
            state['builds'][power.name]['count'] = 0;
            state['builds'][power.name]['homes'] = [];
        } else {
            const build_count = power.centers.length - power.units.length;
            state['builds'][power.name]['count'] = build_count;
            const build_sites = (build_count > 0) ? this._build_sites(power) : [];
            state['builds'][power.name]['homes'] = build_sites;
            if (build_count > 0) {
                 state['builds'][power.name]['count'] = Math.min(build_sites.length, build_count);
            }
        }
    }
    state["phase"] = this.phase;
    return state;
  }

  private _build_sites(power: PowerTs): string[] {
    let potential_homes = power.homes || [];
    if (this.rules.includes('BUILD_ANY')) { // Untested rule variant
        potential_homes = [...power.centers];
    }
    const occupied_locs = new Set<string>();
    Object.values(this.powers).forEach(p => p.units.forEach(u => occupied_locs.add(u.substring(2,5).toUpperCase())));

    return potential_homes.filter(h_base =>
        power.centers.includes(h_base.toUpperCase()) &&
        !occupied_locs.has(h_base.toUpperCase())
    ).map(h => h.toUpperCase());
  }

  get_orders_from_power(power_name: string): Record<string, string> | string[] {
      power_name = power_name.toUpperCase();
      const power = this.get_power(power_name);
      if (!power) return [];
      if (this.phase_type === 'M' || this.phase_type === 'R') { // Retreat orders also in power.orders for units
          return { ...power.orders };
      }
      return [...power.adjust]; // Build/Disband orders in power.adjust
  }

  _get_all_orders(): Record<string, Record<string, string> | string[]> {
      const all_orders: Record<string, Record<string, string> | string[]> = {};
      for (const pName of Object.keys(this.powers)) {
          all_orders[pName] = this.get_orders_from_power(pName);
      }
      return all_orders;
  }

  get_orders(power_name?: string): string[] | Record<string, string[]> {
    if (power_name) {
        const power = this.get_power(power_name.toUpperCase());
        if (!power) return [];

        if (this.phase_type === 'M' || this.phase_type === 'R') {
            // For M and R phases, orders are { [unitFullName]: orderSuffix }
            // We need to reconstruct the full order string.
            const full_orders: string[] = [];
            for (const unitFullName in power.orders) {
                if (power.orders[unitFullName]) { // Ensure there's an order part
                    full_orders.push(`${unitFullName} ${power.orders[unitFullName]}`);
                } else { // Implicit hold if unit in power.orders but value is empty/null
                    full_orders.push(`${unitFullName} H`);
                }
            }
            return full_orders;
        } else { // A phase
            return power.adjust.filter(order => !!order && order.toUpperCase() !== 'WAIVE' && !order.toUpperCase().startsWith('VOID '));
        }
    } else {
        const allFormattedOrders: Record<string, string[]> = {};
        for (const pName of Object.keys(this.powers)) {
            allFormattedOrders[pName] = this.get_orders(pName) as string[];
        }
        return allFormattedOrders;
    }
  }

  private _set_orders_internal(power: PowerTs, order_strings: string[], expand: boolean, replace: boolean): void {
    // For M and R phases, orders are stored in power.orders = { [unitName]: "order suffix" }
    // For A phase, orders are stored in power.adjust = string[]

    const ordersToProcess = order_strings.filter(o => o && o.trim() !== "");

    if (this.phase_type === 'A') { // Adjustment phase
        if (replace) power.adjust = [];
        ordersToProcess.forEach(order => {
            // Basic syntax validation for adjustment orders.
            // Example: "A PAR B" or "F LON D" or "WAIVE"
            // _parse_order_string will handle most syntax.
            const parsed = this._parse_order_string(order, power.name);
            if (parsed.is_valid_syntax && (parsed.order_type === 'B' || parsed.order_type === 'D' || parsed.order_type === 'W')) {
                if (replace || !power.adjust.includes(order)) { // Simple check for duplicates if not replacing
                    power.adjust.push(order);
                }
            } else {
                this.error.push(err.STD_GAME_BAD_ORDER.replace('%s', order) + (parsed.validation_error ? ` (${parsed.validation_error})` : ""));
            }
        });
    } else { // Movement or Retreat phase
        if (replace) power.orders = {};
        ordersToProcess.forEach(order_full_str => {
            const parsed = this._parse_order_string(order_full_str, power.name);
            if (parsed.is_valid_syntax && parsed.unit_type && parsed.unit_location) {
                const unitFullName = `${parsed.unit_type} ${parsed.unit_location}`;
                // Reconstruct the order suffix
                const suffixParts: string[] = [];
                if (parsed.order_type && parsed.order_type !== 'H') suffixParts.push(parsed.order_type); // H is often implicit

                if (parsed.order_type === 'M' || parsed.order_type === 'R') {
                    if (parsed.target_location) suffixParts.push(parsed.target_location + (parsed.target_coast ? `/${parsed.target_coast}`: ""));
                    if (parsed.via_convoy) suffixParts.push("VIA");
                } else if (parsed.order_type === 'S') {
                    if (parsed.supported_unit_type && parsed.supported_unit_location) {
                        suffixParts.push(parsed.supported_unit_type, parsed.supported_unit_location);
                        if (parsed.support_target_location) {
                            suffixParts.push("-", parsed.support_target_location + (parsed.support_target_coast ? `/${parsed.support_target_coast}`: ""));
                        }
                    }
                } else if (parsed.order_type === 'C') {
                     if (parsed.convoyed_unit_type && parsed.convoyed_unit_location && parsed.convoy_destination_location) {
                        suffixParts.push(parsed.convoyed_unit_type, parsed.convoyed_unit_location, "-", parsed.convoy_destination_location);
                     }
                } else if (parsed.order_type === 'D') {
                    // Suffix is just 'D'
                } else if (parsed.order_type === 'H') {
                    // Suffix is just 'H' or empty
                }


                const orderSuffix = suffixParts.length > 0 ? suffixParts.join(" ") : "H"; // Default to Hold if no other parts

                if (replace || !power.orders[unitFullName]) {
                    power.orders[unitFullName] = orderSuffix;
                } else {
                    this.error.push(err.GAME_UNIT_REORDERED.replace('%s', unitFullName));
                }
            } else {
                this.error.push(err.STD_GAME_BAD_ORDER.replace('%s', order_full_str) + (parsed.validation_error ? ` (${parsed.validation_error})` : ""));
            }
        });
    }
    power.order_is_set = (Object.keys(power.orders).length > 0 || power.adjust.length > 0) ?
                         OrderSettings.ORDER_SET : OrderSettings.ORDER_SET_EMPTY;
  }
  // ... (rest of the class, including _resolve_moves, _apply_adjudication_results_ts, etc.)
  // ... and the new methods: _update_sc_ownership, _get_supply_center_owner, _can_build_unit_type_in_province, _resolve_adjustments
  // ... and the modified _process_internal and _advance_phase
}
