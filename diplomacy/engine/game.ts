// diplomacy/engine/game.ts

import { DiplomacyMap } from './map';
import { PowerTs } from './power';
import { DiplomacyMessage, GLOBAL_RECIPIENT, OBSERVER_RECIPIENT, OMNISCIENT_RECIPIENT, SYSTEM_SENDER } from './message';
// import { Renderer } from './renderer'; // Placeholder
import { GamePhaseData, MESSAGES_TYPE_PLACEHOLDER as MESSAGES_TYPE } from '../utils/game_phase_data'; // Assuming GamePhaseData is in utils or a dedicated file
import * as diploStrings from '../utils/strings'; // Placeholder, eventually specific strings
import * as err from '../utils/errors';     // Placeholder
import * as common from '../utils/common';   // Placeholder
import * as parsing from '../utils/parsing'; // Placeholder
import { OrderSettings, DEFAULT_GAME_RULES } from '../utils/constants'; // Placeholder

// Logger
const logger = {
  debug: (message: string, ...args: any[]) => console.debug('[Game]', message, ...args),
  info: (message: string, ...args: any[]) => console.info('[Game]', message, ...args),
  warn: (message: string, ...args: any[]) => console.warn('[Game]', message, ...args),
  error: (message: string, ...args: any[]) => console.error('[Game]', message, ...args),
};

// Simpler SortedDict replacement for now, assuming Map preserves insertion order for iteration.
// For strict sorted behavior based on custom comparator for phases, a dedicated library or implementation would be needed.
type SortedMap<K, V> = Map<K, V>;
const createSortedMap = <K,V>() : SortedMap<K,V> => new Map<K,V>();


export class DiplomacyGame {
  // Properties from __slots__ and __init__
  victory: number[] | null = null;
  no_rules: Set<string> = new Set();
  meta_rules: string[] = [];
  phase: string = '';
  note: string = '';
  map: DiplomacyMap;
  powers: Record<string, PowerTs> = {}; // power_name -> PowerTs instance
  outcome: string[] = [];
  error: string[] = []; // Stores error messages (strings, not Error objects from Python)
  popped: string[] = []; // list of units that were disbanded because they couldn't retreat

  messages: SortedMap<number, DiplomacyMessage>; // timestamp -> Message
  order_history: SortedMap<string, Record<string, string[]>>; // phase_short_name -> power_name -> orders
  orders: Record<string, string> = {}; // unit_str -> order_string (current phase)
  ordered_units: Record<string, string[]> = {}; // power_name -> list of units that received orders

  phase_type: string | null = null; // 'M', 'R', 'A', or '-'
  win: number = 0; // Min centers to win based on current year and victory conditions

  // Adjudication-related properties
  combat: Record<string, Record<number, Array<[string, string[]]>>> = {};
  command: Record<string, string> = {}; // unit_str -> full_order_str (finalized for processing)
  result: Record<string, any[]> = {}; // unit_str -> list of result codes/objects
  supports: Record<string, [number, string[]]> = {}; // unit_str -> [count, non_dislodging_supporters[]]
  dislodged: Record<string, string> = {}; // dislodged_unit_str -> attacking_loc_short
  lost: Record<string, string> = {}; // lost_center_loc_short -> original_owner_name

  convoy_paths: Record<string, string[][]> = {};
  convoy_paths_possible: Array<[string, Set<string>, Set<string>]> | null = null;
  convoy_paths_dest: Record<string, Record<string, Set<string>[]>> | null = null;

  zobrist_hash: string = "0"; // Python uses int, JS can use string for large numbers
  // renderer: Renderer | null = null; // Placeholder

  game_id: string;
  map_name: string = 'standard';
  role: string; // Current player's role (power_name, OBSERVER, OMNISCIENT, SERVER)
  rules: string[] = [];

  message_history: SortedMap<string, SortedMap<number, DiplomacyMessage>>;
  state_history: SortedMap<string, any>; // phase_short_name -> game_state_dict
  result_history: SortedMap<string, Record<string, any[]>>; // phase_short_name -> unit_str -> results

  status: string; // FORMING, ACTIVE, PAUSED, COMPLETED, CANCELED
  timestamp_created: number;
  n_controls: number | null = null; // Expected number of human players
  deadline: number = 300; // seconds
  registration_password: string | null = null; // Hashed password

  // Client-specific game properties (placeholders, might be on a derived class)
  observer_level: string | null = null;
  controlled_powers: string[] | null = null;
  daide_port: number | null = null;

  fixed_state: [string, string] | null = null; // [phase_abbr, zobrist_hash] for context manager
  power_model_map: Record<string, string> = {}; // For AI agents
  phase_summaries: Record<string, string> = {}; // phase_short_name -> summary_text

  // Caches
  private _unit_owner_cache: Map<string, PowerTs | null> | null = null; // key: "unit_str,coast_req_bool"

  // For SortedDict phase key wrapping
  private _phase_wrapper_type: (phase: string) => string;


  constructor(game_id?: string | null, initial_props: Partial<DiplomacyGame> = {}) {
    // Initialize many properties from initial_props or defaults
    this.game_id = game_id || `ts_game_${Date.now()}${Math.floor(Math.random()*1000)}`;
    this.map_name = initial_props.map_name || 'standard';
    this.map = new DiplomacyMap(this.map_name); // Load map

    this.role = initial_props.role || diploStrings.SERVER_TYPE;
    this.rules = [...(initial_props.rules || DEFAULT_GAME_RULES)]; // Process rules via add_rule later
    this.no_rules = new Set(initial_props.no_rules || []);
    this.meta_rules = initial_props.meta_rules || [];

    this.phase = initial_props.phase || ''; // Will be set by _begin or set_state
    this.note = initial_props.note || '';
    this.outcome = initial_props.outcome || [];
    this.error = initial_props.error || [];
    this.popped = initial_props.popped || [];

    this.messages = createSortedMap<number, DiplomacyMessage>(); // TODO: Handle initial messages if any
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

    // Phase wrapper for sorted history keys
    // In TS, if keys are strings like "S1901M", standard string sort might not be chronological.
    // The Python version uses a custom class that implements __lt__ based on map.compare_phases.
    // For TS Map, keys are iterated in insertion order. If chronological processing is key,
    // we might need to store phases in an array or use a library for sorted maps with custom comparators.
    // For now, this is a conceptual placeholder.
    this._phase_wrapper_type = (phaseStr: string) => phaseStr;


    // Process initial rules (Python does this via property setter or __init__ loop)
    const initialRules = [...this.rules]; // copy before clearing
    this.rules = [];
    initialRules.forEach(rule => this.add_rule(rule));

    if (this.rules.includes('NO_DEADLINE')) this.deadline = 0;
    if (this.rules.includes('SOLITAIRE')) this.n_controls = 0;
    else if (this.n_controls === 0) this.add_rule('SOLITAIRE');

    // Validate status and initialize powers if game is new
    this._validate_status(initial_props.powers === undefined); // reinit_powers if not loading from existing state

    if (initial_props.powers) {
        for (const [pName, pData] of Object.entries(initial_props.powers)) {
            // Assuming pData is partial data for PowerTs constructor
            this.powers[pName] = new PowerTs(this, pName, pData as Partial<PowerTs>);
        }
    } else if (this.status !== diploStrings.FORMING) { // If not forming and no powers given, _begin initializes them
        this._begin();
    }

    // Wrap history fields from initial_props if they exist
    if(initial_props.order_history) this.order_history = new Map(Object.entries(initial_props.order_history).map(([k,v]) => [this._phase_wrapper_type(k),v]));
    if(initial_props.message_history) this.message_history = new Map(Object.entries(initial_props.message_history).map(([k,v]) => [this._phase_wrapper_type(k), new Map(Object.entries(v).map(([ts,m])=>[Number(ts), new DiplomacyMessage(m)])) ]));
    if(initial_props.state_history) this.state_history = new Map(Object.entries(initial_props.state_history).map(([k,v]) => [this._phase_wrapper_type(k),v]));
    if(initial_props.result_history) this.result_history = new Map(Object.entries(initial_props.result_history).map(([k,v]) => [this._phase_wrapper_type(k),v]));
    if(initial_props.messages) this.messages = new Map(Object.entries(initial_props.messages).map(([ts,m])=>[Number(ts), new DiplomacyMessage(m)]));


    // Final checks from Python __init__
    if (this.map && this.map.powers) { // map should be loaded by now
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
            logger.warn("Inconsistent power roles for a player game.");
        }
    } else {
        if(this.role !== diploStrings.OBSERVER_TYPE && this.role !== diploStrings.OMNISCIENT_TYPE && this.role !== diploStrings.SERVER_TYPE) {
            logger.warn(`Game role ${this.role} is not a special type for a non-player game.`);
        }
        if(!Object.values(this.powers).every(p => p.role === this.role)) {
             logger.warn(`Inconsistent power roles; not all match game role ${this.role}.`);
        }
    }
  }

  // --- Basic Property Getters ---
  get current_short_phase(): string {
    return this.map.phase_abbr(this.phase, this.phase);
  }
  get is_game_done(): boolean { return this.phase === 'COMPLETED'; }
  get is_game_forming(): boolean { return this.status === diploStrings.FORMING; }
  // ... other is_game_... status getters

  // --- Core Methods (Stubs for now) ---
  private _validate_status(reinit_powers: boolean): void {
    logger.debug(`Validating status. Current: ${this.status}, reinit_powers: ${reinit_powers}`);
    if (!this.map) this.map = new DiplomacyMap(this.map_name); // Ensure map is loaded
    this.victory = this.map.victory;
    if (!this.victory || this.victory.length === 0) {
        this.victory = [Math.floor(this.map.scs.length / 2) + 1];
    }

    if (!this.phase) this.phase = this.map.phase;

    const phaseParts = this.phase.split(' ');
    if (phaseParts.length === 3) {
        this.phase_type = phaseParts[2][0]; // M, R, A
    } else {
        this.phase_type = '-'; // For FORMING, COMPLETED
    }

    if (this.phase !== diploStrings.FORMING && this.phase !== diploStrings.COMPLETED) {
        try {
            const year = Math.abs(parseInt(this.phase.split(' ')[1]) - this.map.first_year);
            this.win = this.victory[Math.min(year, this.victory.length - 1)];
        } catch (e) { this.error.push(err.GAME_BAD_YEAR_GAME_PHASE); }
    }

    if (reinit_powers) {
        this.powers = {}; // Clear existing if any
        this.map.powers.forEach(pName => {
            this.powers[pName] = new PowerTs(this, pName, { role: this.role });
            // Initialize is called in _begin or if powers are passed in initial_props
        });
    }
  }

  private _begin(): void {
    this._move_to_start_phase();
    this.note = '';
    this.win = this.victory ? this.victory[0] : 0;

    this.map.powers.forEach(pName => {
        if (!this.powers[pName]) {
            this.powers[pName] = new PowerTs(this, pName, { role: this.role });
        }
    });
    Object.values(this.powers).forEach(power => power.initialize(this));
    this.build_caches();
    logger.info(`Game ${this.game_id} begun. Phase: ${this.phase}`);
  }

  private _move_to_start_phase(): void {
    this.phase = this.map.phase; // Get initial phase from map
    this.phase_type = this.phase.split(' ')[2][0];
  }

  public get_power(power_name?: string | null): PowerTs | null {
    if (!power_name) return null;
    return this.powers[power_name.toUpperCase()] || null;
  }

  public has_power(power_name: string): boolean {
    return !!this.get_power(power_name);
  }

  public add_rule(rule: string): void {
    // Simplified rule addition. Full logic from Python is complex.
    if (!this.rules.includes(rule)) {
        this.rules.push(rule);
    }
  }

  // Placeholder for game.update_hash (critical for state tracking if Zobrist is used)
  public update_hash(powerName: string, details: any): void {
      // logger.debug(`update_hash called for ${powerName}`, details);
  }
  // Placeholder for game.clear_cache (called after state changes)
  public clear_cache(): void {
      this._unit_owner_cache = null;
      this.convoy_paths_possible = null;
      this.convoy_paths_dest = null;
      // logger.debug("Game caches cleared.");
  }

  public build_caches(): void {
    this.clear_cache();
    // this._build_list_possible_convoys(); // Placeholder
    // this._build_unit_owner_cache();     // Placeholder
    logger.warn("Game.build_caches() is a simplified stub.");
  }

  public get_state(): any {
    // Simplified version of Python's get_state
    const state: any = {};
    state['timestamp'] = commonUtils.timestamp_microseconds();
    state['zobrist_hash'] = this.zobrist_hash;
    state['note'] = this.note;
    state['name'] = this.current_short_phase; // Uses property getter
    state['units'] = {};
    state['retreats'] = {};
    state['centers'] = {};
    state['homes'] = {};
    state['influence'] = {};
    state['civil_disorder'] = {};
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
        } else {
            state['builds'][power.name]['count'] = power.centers.length - power.units.length;
        }
        state['builds'][power.name]['homes'] = (this.phase_type === 'A' && state['builds'][power.name]['count'] > 0)
            ? this._build_sites(power)
            : [];
        if (this.phase_type === 'A' && state['builds'][power.name]['count'] > 0) {
             state['builds'][power.name]['count'] = Math.min(state['builds'][power.name]['homes'].length, state['builds'][power.name]['count']);
        }
    }
    state["phase"] = this.phase; // Full phase string
    return state;
  }

  private _build_sites(power: PowerTs): string[] {
    // Simplified placeholder for _build_sites logic
    logger.warn("_build_sites is a simplified stub.");
    let potential_homes = power.homes || [];
    if (this.rules.includes('BUILD_ANY')) { // BUILD_ANY rule check
        potential_homes = power.centers;
    }
    const occupied_locs = new Set<string>();
    Object.values(this.powers).forEach(p => p.units.forEach(u => occupied_locs.add(u.substring(2,5))));

    return potential_homes.filter(h => power.centers.includes(h) && !occupied_locs.has(h));
  }


  // Many methods like process, _resolve_moves, _valid_order, etc. are very complex and omitted for this initial structure.
  // These would be added incrementally.
}
