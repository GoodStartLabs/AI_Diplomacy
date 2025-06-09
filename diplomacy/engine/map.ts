// diplomacy/engine/map.ts

import * as fs from 'fs';
import * as path from 'path';
import { Buffer } from 'buffer';

// --- Logger ---
const logger = {
  debug: (message: string, ...args: any[]) => console.debug('[Map]', message, ...args),
  info: (message: string, ...args: any[]) => console.info('[Map]', message, ...args),
  warn: (message: string, ...args: any[]) => console.warn('[Map]', message, ...args),
  error: (message: string, ...args: any[]) => console.error('[Map]', message, ...args),
};

// --- Placeholders for imported constants and modules ---
const settings = {
  PACKAGE_DIR: path.join(__dirname, '..', '..'),
};

// Constants for vet()
const UNDETERMINED = 0;
const POWER = 1;
const UNIT = 2;
const LOCATION = 3;
const COAST = 4;
const ORDER = 5;
const MOVE_SEP = 6;
const OTHER = 7;


const KEYWORDS: Record<string, string> = {
    "ARMY": "A", "FLEET": "F",
    "SUPPORTS": "S", "SUPPORT": "S", "SUPS": "S", "SUP": "S",
    "CONVOYS": "C", "CONVOY": "C", "CON": "C",
    "HOLDS": "H", "HOLD": "H",
    "MOVES": "-", "MOVE": "-", "M": "-", "TO": "-",  // "TO" can be ambiguous, but often implies move
    "RETREATS": "R", "RETREAT": "R", "RET": "R",
    "DISBANDS": "D", "DISBAND": "D", "DIS": "D",
    "BUILDS": "B", "BUILD": "B",
    "REMOVE": "D", // REMOVE maps to D for Disband
    "VIA": "VIA",
    "WAIVE": "WAIVE", "WAIVES": "WAIVE",
    // Seasons and years are not keywords for order parsing here
    // Coasts - these might be better handled by specific parsing logic if they appear in orders
    "NC": "/NC", "NORTH_COAST": "/NC", "NCS": "/NC",
    "SC": "/SC", "SOUTH_COAST": "/SC", "SCS": "/SC", // Note: SCS also conflicts with Supply Centers abbreviation
    "EC": "/EC", "EAST_COAST": "/EC", "ECS": "/EC",
    "WC": "/WC", "WEST_COAST": "/WC", "WCS": "/WC",
    // Order types - some already above
    "ORDER": "ORDER", // Placeholder if needed
    // Power names - will be dynamically added to aliases
};

// Standard aliases from a typical 'standard' map, can be augmented by map files
const ALIASES: Record<string, string> = {
    // Seas
    "ENGLISH_CHANNEL": "ECH", "ENG": "ECH",
    "IRISH_SEA": "IRI", "IRS": "IRI",
    "NORTH_SEA": "NTH", "NTS": "NTH",
    "NORWEGIAN_SEA": "NWG", "NWS": "NWG",
    "HELGOLAND_BIGHT": "HEL", "HEB": "HEL",
    "SKAGERRAK": "SKA",
    "BALTIC_SEA": "BAL",
    "GULF_OF_BOTHNIA": "GOB", "BOT": "GOB",
    "BARRENTS_SEA": "BAR",
    "MID-ATLANTIC_OCEAN": "MAO", "MID": "MAO", "MAT": "MAO",
    "WESTERN_MEDITERRANEAN": "WME", "WES": "WME",
    "GULF_OF_LYONS": "GOL", "LYO": "GOL",
    "TYRRHENIAN_SEA": "TYS", "TYN": "TYS",
    "IONIAN_SEA": "ION", "IOS": "ION",
    "ADRIATIC_SEA": "ADR", "ADS": "ADR",
    "AEGEAN_SEA": "AEG", "AES": "AEG",
    "EASTERN_MEDITERRANEAN": "EME", "EAS": "EME",
    "BLACK_SEA": "BLA", "BLS": "BLA",
    // इंग्लैंड
    "CLYDE": "CLY", "LONDON": "LON", "LIVERPOOL": "LVP", "WALES": "WAL", "YORKSHIRE": "YOR", "EDI": "EDI", "EDINBURGH": "EDI",
    // France
    "PICARDY": "PIC", "PARIS": "PAR", "BURGUNDY": "BUR", "BREST": "BRE", "GASCONY": "GAS", "MARSEILLES": "MAR",
    // Germany
    "KIEL": "KIE", "BERLIN": "BER", "PRUSSIA": "PRU", "SILESIA": "SIL", "MUNICH": "MUN", "RUHR": "RUH", "ALSACE": "ALS",
    // Italy
    "PIEDMONT": "PIE", "VENICE": "VEN", "TUSCANY": "TUS", "ROME": "ROM", "NAPLES": "NAP", "APULIA": "APU",
    // Austria-Hungary
    "TYROLIA": "TYR", "BOHEMIA": "BOH", "VIENNA": "VIE", "GALICIA": "GAL", "BUDAPEST": "BUD", "TRIESTE": "TRI",
    // Turkey
    "CONSTANTINOPLE": "CON", "ANKARA": "ANK", "SMYRNA": "SMY", "ARMENIA": "ARM", "SYRIA": "SYR",
    // Russia
    "ST_PETERSBURG": "STP", "STPETERSBURG": "STP", "STPETE": "STP", "ST_PETE": "STP",
    "FINLAND": "FIN", "LIVONIA": "LIV", "MOSCOW": "MOS", "UKRAINE": "UKR", "WARSAW": "WAR", "SEVASTOPOL": "SEV",
    // Neutral Supply Centers
    "NORWAY": "NWY", "NOR": "NWY", "SWEDEN": "SWE", "DENMARK": "DEN", "HOLLAND": "HOL", "BELGIUM": "BEL",
    "PORTUGAL": "POR", "SPAIN": "SPA", "TUNIS": "TUN", "GREECE": "GRE", "RUMANIA": "RUM", "SERBIA": "SER", "BULGARIA": "BUL",
    // Other Land Provinces
    "ALBANIA": "ALB", "NORTH_AFRICA": "NAF",
};


const err = {
  MAP_FILE_NOT_FOUND: "MAP_FILE_NOT_FOUND: Map file %s not found.",
  MAP_LEAST_TWO_POWERS: "MAP_LEAST_TWO_POWERS: Map must define at least two powers.",
  MAP_LOC_NOT_FOUND: "MAP_LOC_NOT_FOUND: Location %s referenced but not defined.",
  MAP_SITE_ABUTS_TWICE: "MAP_SITE_ABUTS_TWICE: Location %s abuts %s more than once.",
  MAP_NO_FULL_NAME: "MAP_NO_FULL_NAME: Location %s has no full name defined.",
  MAP_ONE_WAY_ADJ: "MAP_ONE_WAY_ADJ: Location %s lists %s as an adjacency, but not vice-versa.",
  MAP_MISSING_ADJ: "MAP_MISSING_ADJ: Missing adjacency between %s and %s.",
  MAP_BAD_HOME: "MAP_BAD_HOME: Power %s has an invalid home center: %s.",
  MAP_BAD_INITIAL_OWN_CENTER: "MAP_BAD_INITIAL_OWN_CENTER: Power %s has an invalid initially owned center: %s.",
  MAP_BAD_INITIAL_UNITS: "MAP_BAD_INITIAL_UNITS: Power %s has an invalid initial unit: %s.",
  MAP_CENTER_MULT_OWNED: "MAP_CENTER_MULT_OWNED: Center %s is owned by multiple powers or listed multiple times.",
  MAP_BAD_PHASE: "MAP_BAD_PHASE: Initial phase '%s' is invalid.",
  MAP_BAD_VICTORY_LINE: "MAP_BAD_VICTORY_LINE: Victory condition line is malformed.",
  MAP_BAD_ROOT_MAP_LINE: "MAP_BAD_ROOT_MAP_LINE: MAP directive is malformed.",
  MAP_TWO_ROOT_MAPS: "MAP_TWO_ROOT_MAPS: Multiple MAP directives found (root map already defined).",
  MAP_FILE_MULT_USED: "MAP_FILE_MULT_USED: Map file %s included multiple times via USE directive.",
  MAP_BAD_ALIASES_IN_FILE: "MAP_BAD_ALIASES_IN_FILE: Alias definition line for '%s' is malformed.",
  MAP_BAD_RENAME_DIRECTIVE: "MAP_BAD_RENAME_DIRECTIVE: Rename directive '%s' is malformed.",
  MAP_INVALID_LOC_ABBREV: "MAP_INVALID_LOC_ABBREV: Location abbreviation '%s' is invalid.",
  MAP_RENAME_NOT_SUPPORTED: "MAP_RENAME_NOT_SUPPORTED: Renaming locations or powers via 'old -> new' is not supported in this version.",
  MAP_LOC_RESERVED_KEYWORD: "MAP_LOC_RESERVED_KEYWORD: Location name '%s' is a reserved keyword.",
  MAP_DUP_LOC_OR_POWER: "MAP_DUP_LOC_OR_POWER: Duplicate location or power name, or alias conflict: %s.",
  MAP_DUP_ALIAS_OR_POWER: "MAP_DUP_ALIAS_OR_POWER: Duplicate alias or power name conflict: %s.",
  MAP_OWNS_BEFORE_POWER: "MAP_OWNS_BEFORE_POWER: %s directive found before a POWER directive. Current line: %s",
  MAP_INHABITS_BEFORE_POWER: "MAP_INHABITS_BEFORE_POWER: INHABITS directive found before a POWER directive. Current line: %s",
  MAP_HOME_BEFORE_POWER: "MAP_HOME_BEFORE_POWER: %s directive found before a POWER directive. Current line: %s",
  MAP_UNITS_BEFORE_POWER: "MAP_UNITS_BEFORE_POWER: UNITS directive found before a POWER directive.",
  MAP_UNIT_BEFORE_POWER: "MAP_UNIT_BEFORE_POWER: Unit definition found before a POWER directive.",
  MAP_INVALID_UNIT: "MAP_INVALID_UNIT: Unit definition '%s' is invalid.",
  MAP_DUMMY_REQ_LIST_POWERS: "MAP_DUMMY_REQ_LIST_POWERS: DUMMIES directive requires a list of powers or 'ALL'.",
  MAP_DUMMY_BEFORE_POWER: "MAP_DUMMY_BEFORE_POWER: DUMMY directive for a single power found without a preceding POWER directive.",
  MAP_NO_EXCEPT_AFTER_DUMMY_ALL: "MAP_NO_EXCEPT_AFTER_DUMMY_ALL: %s ALL must be followed by EXCEPT or end of line.",
  MAP_NO_POWER_AFTER_DUMMY_ALL_EXCEPT: "MAP_NO_POWER_AFTER_DUMMY_ALL_EXCEPT: %s ALL EXCEPT must be followed by power names.",
  MAP_NO_DATA_TO_AMEND_FOR: "MAP_NO_DATA_TO_AMEND_FOR: AMEND directive for '%s' found, but no existing data to amend.",
  MAP_NO_ABUTS_FOR: "MAP_NO_ABUTS_FOR: Terrain definition for '%s' is missing ABUTS keyword or has malformed adjacencies.",
  MAP_UNPLAYED_BEFORE_POWER: "MAP_UNPLAYED_BEFORE_POWER: UNPLAYED directive for a single power found without a preceding POWER directive.",
  MAP_NO_EXCEPT_AFTER_UNPLAYED_ALL: "MAP_NO_EXCEPT_AFTER_UNPLAYED_ALL: UNPLAYED ALL must be followed by EXCEPT or end of line.",
  MAP_NO_POWER_AFTER_UNPLAYED_ALL_EXCEPT: "MAP_NO_POWER_AFTER_UNPLAYED_ALL_EXCEPT: UNPLAYED ALL EXCEPT must be followed by power names.",
  MAP_RENAMING_UNOWNED_DIR_NOT_ALLOWED: "MAP_RENAMING_UNOWNED_DIR_NOT_ALLOWED: Renaming UNOWNED or NEUTRAL is not allowed.",
  MAP_RENAMING_UNDEF_POWER: "MAP_RENAMING_UNDEF_POWER: Attempting to rename undefined power: %s.",
  MAP_POWER_NAME_EMPTY_KEYWORD: "MAP_POWER_NAME_EMPTY_KEYWORD: Power name '%s' normalizes to an empty string or keyword.",
  MAP_POWER_NAME_CAN_BE_CONFUSED: "MAP_POWER_NAME_CAN_BE_CONFUSED: Power name '%s' (1 or 3 chars) can be confused with location or unit type.",
  MAP_ILLEGAL_POWER_ABBREV: "MAP_ILLEGAL_POWER_ABBREV: Power abbreviation is invalid (e.g., 'M' or '?').",
  MAP_NO_SUCH_POWER_TO_REMOVE: "MAP_NO_SUCH_POWER_TO_REMOVE: Attempting to remove non-existent power: %s.",
  MAP_INVALID_VARIANT_BLOCK: "MAP_INVALID_VARIANT_BLOCK: VARIANT block '%s' is malformed or not closed.",
  MAP_UNDEFINED_VARIANT: "MAP_UNDEFINED_VARIANT: VARIANT '%s' is used but not defined.",
  MAP_INVALID_FLOW: "MAP_INVALID_FLOW: FLOW directive '%s' is malformed.",
  MAP_INVALID_SEQ: "MAP_INVALID_SEQ: SEQ directive '%s' is malformed.",
  MAP_INVALID_FIRSTYEAR: "MAP_INVALID_FIRSTYEAR: FIRSTYEAR directive '%s' requires a number.",

};

// Define ConvoyPathData structure based on its usage in game.ts
// Game.ts expects: this.map.convoy_paths: Map<number_of_fleets, {start: string, fleets: Set<string>, dests: Set<string>}[]>
// This structure is complex and implies pre-computation.
// For now, ConvoyPathData will be this complex type.
export interface ConvoyPathInfo {
    start: string;
    fleets: Set<string>; // Set of fleet LOCATIONS (base names)
    dests: Set<string>;  // Set of destination LOCATIONS (base names)
}
export type ConvoyPathData = Map<number, ConvoyPathInfo[]>;


const CONVOYS_PATH_CACHE: Record<string, ConvoyPathData> = {};
const get_convoy_paths_cache = (): Record<string, ConvoyPathData> => CONVOYS_PATH_CACHE;

// This function is a placeholder for a complex convoy path generation algorithm
// or for loading pre-computed convoy paths.
const add_to_cache = (name: string): ConvoyPathData => {
    logger.warn(`Convoy path generation for map '${name}' is currently a STUB. No convoy paths will be available.`);
    return new Map<number, ConvoyPathInfo[]>();
};

const MAP_CACHE: Record<string, DiplomacyMap> = {};

export class DiplomacyMap {
  name: string;
  first_year: number = 1901;
  victory: number[] = [18]; // Default for standard map
  phase: string = 'SPRING 1901 MOVEMENT'; // Default initial phase
  validated: number | null = null;
  flow_sign: number = 1; // 1 for normal flow, -1 for reverse (not standard)
  root_map: string | null = null;
  abuts_cache: Record<string, number> = {}; // unit_type,loc1,order_type,loc2 -> 0 or 1

  homes: Record<string, string[]> = {}; // power_name -> [loc_base_uc, ...]
  loc_name: Record<string, string> = {}; // loc_full_uc_or_with_coast -> loc_base_uc
  loc_type: Record<string, string> = {}; // loc_base_uc -> type (LAND, COAST, WATER, PORT) (SHUT special)
  loc_abut: Record<string, string[]> = {}; // loc_full_uc_or_with_coast -> [adj_loc_full_uc_or_with_coast, ...]
  loc_coasts: Record<string, string[]> = {}; // loc_base_uc -> [loc_base_uc/NC, loc_base_uc/SC, ...] OR [loc_base_uc] if no coasts

  own_word: Record<string, string> = {}; // power_name_norm -> display_name
  abbrev: Record<string, string> = {};   // power_name_norm -> single_char_abbrev
  centers: Record<string, string[]> = {};// power_name_norm -> [loc_base_uc, ...] (initially owned SCs)
  units: Record<string, string[]> = {};  // power_name_norm -> ["A PAR", "F BRE/NC", ...] (initial units)

  pow_name: Record<string, string> = {}; // power_name_norm -> original_case_from_map_file
  rules: string[] = []; // List of active rules from map file
  files: string[] = []; // List of map files loaded (to prevent cycles)
  powers: string[] = []; // List of power_name_norm
  scs: string[] = [];    // List of loc_base_uc that are supply centers

  // Properties from Python's Map that were less clear or might be superseded:
  // owns: string[] = []; // List of powers that can own SCs? Seems redundant with keys of this.centers.
  // inhabits: string[] = []; // List of powers that have home SCs? Redundant with keys of this.homes.

  flow: string[] = ['SPRING:MOVEMENT,RETREATS', 'FALL:MOVEMENT,RETREATS', 'WINTER:ADJUSTMENTS']; // Default game flow
  dummies: string[] = []; // List of power_name_norm that are dummies
  unplayed: string[] = []; // List of power_name_norm that are unplayed

  // locs: string[] = []; // List of original case location names. More useful to store canonical forms.
  // Instead, map_data.nodes.keys() can provide all canonical location representations.
  map_data: {
      nodes: Map<string, { type: string, sc: boolean, coasts?: Set<string> }>, // loc_full_uc_or_with_coast -> details
      adj: Map<string, Set<string>> // loc_full_uc_or_with_coast -> Set of adjacent loc_full_uc_or_with_coast
  } = { nodes: new Map(), adj: new Map() };


  error: string[] = []; // Errors encountered during loading/validation
  seq: string[] = ['NEWYEAR', 'SPRING MOVEMENT', 'SPRING RETREATS', 'FALL MOVEMENT', 'FALL RETREATS', 'FALL ADJUSTMENTS']; // Default phase sequence
  // WINTER ADJUSTMENTS is also common, map file can override via FLOW/SEQ.
  // Standard sequence (from DATC test cases) often implies Fall Adjustments.

  phase_abbrev: Record<string, string> = {'M': 'MOVEMENT', 'R': 'RETREATS', 'A': 'ADJUSTMENTS'};


  unclear: Record<string, string> = {}; // alias_norm_uc -> loc_base_uc (for ambiguous aliases)
  unit_names: Record<string, string> = {'A': 'ARMY', 'F': 'FLEET'};
  keywords: Record<string, string>; // Loaded from constants, can be augmented by map file
  aliases: Record<string, string>;   // Loaded from constants, can be augmented by map file

  convoy_paths: ConvoyPathData = new Map(); // Stores pre-calculated convoy paths.
  dest_with_coasts: Record<string, string[]> = {}; // loc_full_uc_or_with_coast -> [all_coastal_variants_of_adj_locs]

  constructor(name: string = 'standard', use_cache: boolean = true) {
    if (use_cache && MAP_CACHE[name]) {
      Object.assign(this, MAP_CACHE[name]); // Re-assign all properties from cached instance
      return;
    }
    this.name = name;
    // Initialize with copies of the default constants, these can be augmented by map file directives if any.
    this.keywords = { ...DEFAULT_KEYWORDS };
    this.aliases = { ...DEFAULT_ALIASES };

    // this.load(); // Will be called explicitly after constructor setup if needed, or implicitly by constructor

    // Initialize map_data based on loaded locs, loc_type, loc_abut, loc_coasts, scs
    this._initialize_map_data();

    this.build_cache();
    this.validate();

    // Convoy paths are complex; using stubbed version for now.
    if (use_cache && CONVOYS_PATH_CACHE[name]) {
        this.convoy_paths = CONVOYS_PATH_CACHE[name];
    } else {
        this.convoy_paths = add_to_cache(name); // This is currently a stub
        if (use_cache) {
            CONVOYS_PATH_CACHE[name] = this.convoy_paths;
        }
    }

    if (use_cache) {
      MAP_CACHE[name] = this;
    }
  }

  private _initialize_map_data(): void {
    this.map_data.nodes.clear();
    this.map_data.adj.clear();

    // After `load()` and `finalizeLoadedData()`, `this.locs` contains all canonical location names (e.g., PAR, STP, STP/NC).
    // `this.loc_type` has base names as keys (e.g., STP).
    // `this.scs` has base names of SCs.
    // `this.loc_coasts` has base names as keys and lists all its canonical variants (e.g., STP -> [STP, STP/NC, STP/SC]).
    // `this.loc_abut` has canonical names as keys and lists of canonical adjacent names.

    // Populate nodes
    for (const loc_canon of this.locs) { // loc_canon is already a canonical name like PAR, STP, STP/NC
        const base_name = loc_canon.substring(0, 3); // e.g., PAR from PAR, STP from STP/NC
        const type = this.loc_type[base_name] || 'UNKNOWN';
        const is_sc = this.scs.includes(base_name);

        let coastsSet: Set<string> | undefined = undefined;
        if (type === 'COAST' || type === 'PORT') {
            // All variants for this base_name are in this.loc_coasts[base_name]
            // We need to extract just the coast part (e.g., NC, SC) for the 'coasts' property of the node.
            const all_variants_for_base = this.loc_coasts[base_name];
            if (all_variants_for_base && all_variants_for_base.some(v => v.includes('/'))) {
                coastsSet = new Set();
                all_variants_for_base.forEach(variant => {
                    if (variant.includes('/')) {
                        coastsSet!.add(variant.split('/')[1]);
                    }
                });
            }
        }

        this.map_data.nodes.set(loc_canon, {
            type: type,
            sc: is_sc,
            ...(coastsSet && coastsSet.size > 0 && { coasts: coastsSet }),
        });
        // Ensure an entry for adjacencies is created for all nodes
        if (!this.map_data.adj.has(loc_canon)) {
            this.map_data.adj.set(loc_canon, new Set());
        }
    }

    // Populate adjacencies
    // this.loc_abut should now have canonical keys and values after finalizeLoadedData()
    for (const canon_loc_source in this.loc_abut) {
        if (this.map_data.nodes.has(canon_loc_source)) { // Ensure source location is a valid node
            const adj_set = this.map_data.adj.get(canon_loc_source) || new Set<string>();
            const adj_loc_list = this.loc_abut[canon_loc_source];

            adj_loc_list.forEach(canon_loc_target => {
                if (this.map_data.nodes.has(canon_loc_target)) { // Ensure target location is a valid node
                    adj_set.add(canon_loc_target);
                } else {
                    logger.warn(`_initialize_map_data: Adjacency target '${canon_loc_target}' for source '${canon_loc_source}' not found in map_data.nodes. Skipping.`);
                    this.error.push(`Adjacency target '${canon_loc_target}' for source '${canon_loc_source}' not found in map_data.nodes.`);
                }
            });
            this.map_data.adj.set(canon_loc_source, adj_set);
        } else {
             logger.warn(`_initialize_map_data: Adjacency source '${canon_loc_source}' not found in map_data.nodes. Skipping its adjacencies.`);
             this.error.push(`Adjacency source '${canon_loc_source}' not found in map_data.nodes.`);
        }
    }
  }

  // Helper to find the canonical representation (UPPERCASE_BASE or UPPERCASE_BASE/COAST)
  // This is primarily used during the construction of map_data.nodes if needed,
  // but loc_str should ideally be canonical by the time it's used here.
  private find_canonical_location_representation(loc_str: string): string | null {
      const uc_loc = loc_str.toUpperCase();
      // Check if uc_loc (e.g. "SPA/NC", "PAR") is directly a node
      if (this.map_data.nodes.has(uc_loc)) return uc_loc;

      // Check if its base (e.g. "SPA" from "SPA/NC") is a node
      // This is useful if loc_str was like "spa" and map_data has "SPA"
      const base_loc = uc_loc.substring(0,3);
      if (this.map_data.nodes.has(base_loc)) return base_loc;

      // Fallback: check this.locs (which is the definitive list of canonical names after load)
      if (this.locs.includes(uc_loc)) return uc_loc;
      if (this.locs.includes(base_loc)) return base_loc;

      logger.warn(`find_canonical_location_representation: Could not find canonical form for '${loc_str}'.`);
      return null;
  }


    this.name = name;
    // Initialize with copies of the default constants, these can be augmented by map file directives if any.
    this.keywords = { ...DEFAULT_KEYWORDS };
    this.aliases = { ...DEFAULT_ALIASES };

    this.load(); // This will populate this.locs, this.powers, this.scs, etc.

    // Initialize map_data based on loaded locs, loc_type, loc_abut, loc_coasts, scs
    this._initialize_map_data();

    this.build_cache();
    this.validate();

    // Convoy paths are complex; using stubbed version for now.
    if (use_cache && CONVOYS_PATH_CACHE[name]) {
        this.convoy_paths = CONVOYS_PATH_CACHE[name];
    } else {
        this.convoy_paths = add_to_cache(name); // This is currently a stub
        if (use_cache) {
            CONVOYS_PATH_CACHE[name] = this.convoy_paths;
        }
    }

    if (use_cache) {
      MAP_CACHE[name] = this;
    }
  }

  public norm(phrase: string): string {
    // Handle coasts like "SPA/SC" -> "SPA /SC" then tokenized to "SPA", "/SC"
    // Or "SPA / SC" -> "SPA", "/SC"
    let result = phrase.toUpperCase();

    // Space out slashes for coast processing, but ensure "word/coast" isn't spaced if already correct.
    result = result.replace(/([A-Z0-9]{3})\s*\/\s*((?:N|S|E|W)C)/g, '$1 /$2'); // e.g. "SPA / SC" -> "SPA /SC"
    result = result.replace(/([A-Z0-9]{3})\/((?:N|S|E|W)C)/g, '$1 /$2');    // e.g. "SPA/SC" -> "SPA /SC"

    // Replace punctuation (except internal slashes in coasts like /NC) with spaces
    const tokensToRemoveOrReplaceWithSpace = /[\.:\-\+,()\[\]]/g;
    result = result.replace(tokensToRemoveOrReplaceWithSpace, ' ');

    // Space out other special characters if they are not part of a word
    const tokensToSpaceAround = /([\|\*\?!~=_^])/g;
    result = result.replace(tokensToSpaceAround, ' $1 ');

    const tokens = result.trim().split(/\s+/);
    const finalTokens: string[] = [];

    for (const token of tokens) {
        if (!token) continue;
        const ucToken = token.toUpperCase();

        // 1. Keyword replacement
        let currentToken = this.keywords[ucToken] || ucToken;

        // 2. Alias replacement (primarily for locations, could also include powers if defined in aliases)
        // Ensure aliases themselves are not keywords that were already replaced.
        // e.g. if "ENG" is an alias for "ECH" but also a keyword for "ENGLISH CHANNEL"
        // The order of these operations (keywords vs aliases) can matter.
        // Standard approach: specific aliases first, then general keywords.
        // However, our KEYWORDS also include things like "ARMY" -> "A".
        // Let's assume for now: if it became a single letter keyword, it's likely final.
        // Otherwise, try alias.
        if (currentToken.length > 1 || currentToken.startsWith("/")) { // Don't re-alias single-letter results like 'A', 'F', or coasts
            currentToken = this.aliases[currentToken] || currentToken;
        }
        finalTokens.push(currentToken);
    }
    return finalTokens.join(' ');
  }

  public norm_power(power: string): string {
    // Normalize for keywords/aliases, then remove spaces to get a single token power name
    const normed = this.norm(power);
    return normed.replace(/\s+/g, '').toUpperCase();
  }

  public area_type(loc: string, no_coast_ok: boolean = false): string | undefined {
    const upperLoc = loc.toUpperCase();
    let shortLoc = upperLoc.substring(0,3);
    if (no_coast_ok && upperLoc.includes('/')) {
        shortLoc = upperLoc.split('/')[0].substring(0,3);
    } else if (upperLoc.includes('/')) { // Specific coast, type must be COAST or PORT
        const base = upperLoc.split('/')[0].substring(0,3);
        const type = this.loc_type[base];
        return (type === 'COAST' || type === 'PORT') ? type : undefined;
    }
    return this.loc_type[shortLoc];
  }

  public is_coastal(province_base_uc: string): boolean {
    return this.loc_coasts[province_base_uc] && this.loc_coasts[province_base_uc].some(loc => loc.includes('/'));
  }

  public get_all_sea_provinces(): string[] {
    const seaProvinces: string[] = [];
    this.map_data.nodes.forEach((node, loc) => {
        if (node.type === 'WATER' || node.type === 'SEA') { // Assuming 'WATER' and 'SEA' are synonymous from map files
            seaProvinces.push(loc);
        }
    });
    return seaProvinces;
  }

  // Interface for map_data.nodes values
  public get_location_node(name: string): { type: string, sc: boolean, coasts?: Set<string> } | null {
    const ucName = name.toUpperCase();
    // Try direct match (e.g., "SPA/NC" or "PAR")
    if (this.map_data.nodes.has(ucName)) {
        return this.map_data.nodes.get(ucName)!;
    }
    // Try base name if a specific coast was requested but not found directly
    if (ucName.includes("/")) {
        const baseName = ucName.substring(0,3);
        if (this.map_data.nodes.has(baseName)) {
            return this.map_data.nodes.get(baseName)!;
        }
    }
    // Try looking up via alias to get a base name
    const normedName = this.norm(name).toUpperCase(); // Norm to handle aliases
    if (this.map_data.nodes.has(normedName)) { // Normed might be an abbrev
        return this.map_data.nodes.get(normedName)!;
    }
    if (normedName.includes('/')) {
        const baseNormed = normedName.substring(0,3);
        if (this.map_data.nodes.has(baseNormed)) {
            return this.map_data.nodes.get(baseNormed)!;
        }
    }
    // Final attempt: check original loc_name mapping for full names to abbrevs
    const shortNameFromLocName = this.loc_name[name.toUpperCase()];
    if (shortNameFromLocName && this.map_data.nodes.has(shortNameFromLocName)) {
        return this.map_data.nodes.get(shortNameFromLocName)!;
    }

    return null;
  }

  public load(fileName?: string): void {
    const filePathToLoad = fileName || (this.name.endsWith('.map') ? this.name : `${this.name}.map`);
    let actualFilePath: string;

    if (fs.existsSync(filePathToLoad)) {
        actualFilePath = filePathToLoad;
    } else {
        actualFilePath = path.join(settings.PACKAGE_DIR, 'maps', filePathToLoad);
    }

    if (!fs.existsSync(actualFilePath)) {
        this.error.push(err.MAP_FILE_NOT_FOUND.replace('%s', filePathToLoad));
        logger.error(err.MAP_FILE_NOT_FOUND.replace('%s', filePathToLoad));
        return;
    }

    if (this.files.includes(actualFilePath) && this.files[0] !== actualFilePath ) { // Allow re-loading the root_map once if it's the first in files list
        // This check is to prevent true recursion where USE A -> B -> A
        // But root map might be USEd by a sub-map, which is fine.
        // A simple cycle check: if we are trying to load a file that's already in this.files *and* it's not the very first file (root_map initial load)
        if (this.files.indexOf(actualFilePath) < this.files.length -1 ) { // if it's not the last added thing, it's a true cycle.
             this.error.push(err.MAP_FILE_MULT_USED.replace('%s', actualFilePath) + " (Cycle detected)");
             logger.warn(err.MAP_FILE_MULT_USED.replace('%s', actualFilePath) + " (Cycle detected)");
            return;
        }
    }
    if (!this.files.includes(actualFilePath)) { // Add only if not present
        this.files.push(actualFilePath);
    }

    if (!this.root_map) {
        this.root_map = path.basename(actualFilePath, '.map');
    }

    logger.info(`Loading map file: ${actualFilePath}`);
    const fileContent = fs.readFileSync(actualFilePath, 'utf-8');
    const lines = fileContent.split(/\r?\n/);

    let currentPowerContext: string | null = null;
    let variantCondition: string | null = null;

    for (const line of lines) {
        const trimmedLine = line.trim();
        if (!trimmedLine || trimmedLine.startsWith('#')) {
            continue;
        }

        let words = trimmedLine.split(/\s+/);
        const originalDirective = words[0]; // Keep original case for some checks if needed
        const directive = originalDirective.toUpperCase();

        if (variantCondition && variantCondition !== 'ALL' && directive !== 'VARIANT' && words[words.length -1].toUpperCase() !== variantCondition) {
            continue;
        }
        if (variantCondition && directive !== 'VARIANT' && words.length > 0 && words[words.length-1].toUpperCase() === variantCondition) {
            words = words.slice(0, -1);
            if (words.length === 0) continue;
        }


        switch (directive) {
            case 'VARIANT':
                if (words.length > 1) {
                    variantCondition = words[1].toUpperCase();
                    if (variantCondition === 'END') variantCondition = null;
                } else {
                    this.error.push(err.MAP_INVALID_VARIANT_BLOCK.replace('%s', trimmedLine));
                }
                break;
            case 'VICTORY':
                if (words.length > 1 && !isNaN(parseInt(words[1], 10))) {
                    this.victory = words.slice(1).map(Number);
                } else {
                    this.error.push(err.MAP_BAD_VICTORY_LINE + ` Line: ${trimmedLine}`);
                }
                break;

            case 'USE':
            case 'USES':
            case 'MAP':
                if (directive === 'MAP') {
                    if (words.length === 2) {
                        const mapName = words[1].endsWith('.map') ? words[1] : `${words[1]}.map`;
                        const newRoot = words[1].split('.')[0];
                        // Root map is the first map loaded. If MAP directive encountered later, it's an error if it changes root_map.
                        if (this.root_map && this.root_map !== newRoot && this.files[0] !== actualFilePath) {
                             this.error.push(err.MAP_TWO_ROOT_MAPS + ` Trying to set to ${newRoot}, already ${this.root_map}`);
                        } else if (!this.root_map || (this.files.length === 1 && this.files[0] === actualFilePath)){
                            this.root_map = newRoot;
                        }
                         this.load(mapName);
                    } else {
                        this.error.push(err.MAP_BAD_ROOT_MAP_LINE + ` Line: ${trimmedLine}`);
                    }
                } else {
                    words.slice(1).forEach(fileToUse => {
                        const mapNameToUse = fileToUse.endsWith('.map') ? fileToUse : `${fileToUse}.map`;
                        this.load(mapNameToUse);
                    });
                }
                break;

            case 'BEGIN':
                this.phase = words.slice(1).join(' ').toUpperCase();
                break;
            case 'FIRSTYEAR':
                 if (words.length === 2 && !isNaN(parseInt(words[1]))) {
                    this.first_year = parseInt(words[1]);
                 } else {
                    this.error.push(err.MAP_INVALID_FIRSTYEAR.replace('%s', trimmedLine));
                 }
                 break;
            case 'FLOW':
                if (words.length > 1) {
                     // FLOW SPRING:MOVEMENT,RETREATS FALL:MOVEMENT,RETREATS WINTER:ADJUSTMENTS
                     // Python code stores this as a list of strings, split by space after FLOW
                    this.flow = trimmedLine.substring(words[0].length).trim().split(/\s+/).map(s => s.toUpperCase());
                } else {
                    this.error.push(err.MAP_INVALID_FLOW.replace('%s', trimmedLine));
                }
                break;
            case 'SEQ':
                 if (words.length > 1) {
                    this.seq = [];
                    let currentSeasonEntry = "";
                    for(let i=1; i<words.length; ++i) {
                        const wordUC = words[i].toUpperCase();
                        // Seasons start a new entry. Phase types are appended.
                        if (['NEWYEAR', 'IFYEARDIV', 'SPRING', 'SUMMER', 'FALL', 'WINTER', 'AUTUMN'].includes(wordUC)) {
                            if (currentSeasonEntry) this.seq.push(currentSeasonEntry.trim());
                            currentSeasonEntry = wordUC;
                        } else { // Append phase type like MOVEMENT, RETREATS, ADJUSTMENTS
                            currentSeasonEntry += " " + wordUC;
                        }
                    }
                    if (currentSeasonEntry) this.seq.push(currentSeasonEntry.trim());
                 } else {
                    this.error.push(err.MAP_INVALID_SEQ.replace('%s', trimmedLine));
                 }
                 break;
            case 'RULE':
            case 'RULES':
                this.rules.push(...words.slice(1).map(r => r.toUpperCase()));
                break;

            default: // Could be Location/Alias definition, Terrain definition, or Power definition
                if (trimmedLine.includes('=')) {
                    const parts = trimmedLine.split('=', 2);
                    const fullNameAndOld = parts[0].trim();
                    const abbrevAndAliasesRaw = parts[1].trim();
                    const abbrevAndAliases = abbrevAndAliasesRaw.split(/\s+/);
                    const abbrev = abbrevAndAliases[0].toUpperCase();

                    let fullName = fullNameAndOld;
                    if (fullNameAndOld.includes('->')) {
                         this.error.push(err.MAP_RENAME_NOT_SUPPORTED + ` Line: ${trimmedLine}`);
                         const renameParts = fullNameAndOld.split('->', 2);
                         fullName = renameParts[1].trim();
                    }

                    const fullNameUC = fullName.toUpperCase();
                    if (this.keywords[fullNameUC] || (this.aliases[this.norm(fullNameUC)] && this.aliases[this.norm(fullNameUC)] !== abbrev)) {
                         // Allow re-defining an alias to the same abbreviation, but error if it changes or conflicts with a keyword.
                        if (this.aliases[this.norm(fullNameUC)] !== abbrev) {
                            this.error.push(err.MAP_DUP_LOC_OR_POWER.replace('%s', fullNameUC) +  ` Line: ${trimmedLine}`);
                        }
                    }
                    this.loc_name[fullNameUC] = abbrev;
                    this.aliases[this.norm(fullNameUC)] = abbrev;
                    this.aliases[abbrev] = abbrev; // Abbrev maps to itself

                    abbrevAndAliases.slice(1).forEach(alias => {
                        let actualAlias = alias;
                        let isUnclear = false;
                        if (alias.endsWith('?')) {
                            isUnclear = true;
                            actualAlias = alias.slice(0, -1);
                        }
                        const normedAlias = this.norm(actualAlias).toUpperCase();
                        if (isUnclear) {
                            this.unclear[normedAlias] = abbrev;
                        } else {
                            if (this.aliases[normedAlias] && this.aliases[normedAlias] !== abbrev) {
                                this.error.push(err.MAP_DUP_ALIAS_OR_POWER.replace('%s', actualAlias) + ` Line: ${trimmedLine}`);
                            }
                            this.aliases[normedAlias] = abbrev;
                        }
                    });
                    if (!this.locs.includes(abbrev)) this.locs.push(abbrev);


                } else if (['LAND', 'WATER', 'COAST', 'PORT', 'SHUT', 'AMEND'].includes(directive)) {
                    if (words.length >= 2) {
                        const locOriginalCaseFromFile = words[1];
                        const locCanonical = locOriginalCaseFromFile.toUpperCase(); // Store locs as UC e.g. PAR, SPA/SC

                        if (directive !== 'AMEND') {
                            this.loc_type[locCanonical.substring(0,3)] = directive;
                        } else if (!this.loc_type[locCanonical.substring(0,3)]) {
                            this.error.push(err.MAP_NO_DATA_TO_AMEND_FOR.replace('%s', locCanonical) + ` Line: ${trimmedLine}`);
                        }

                        if (!this.locs.includes(locCanonical)) this.locs.push(locCanonical);

                        const baseLoc = locCanonical.substring(0, 3);
                        if (locCanonical.includes('/')) { // e.g. SPA/SC
                            this.loc_coasts[baseLoc] = this.loc_coasts[baseLoc] || [];
                            if (!this.loc_coasts[baseLoc].includes(locCanonical)) {
                                this.loc_coasts[baseLoc].push(locCanonical);
                            }
                        } else { // e.g. PAR, or SPA (if SPA can be accessed w/o specific coast)
                             // If SPA has specific coasts like SPA/NC, then SPA itself might also be a valid general coastal prov.
                            this.loc_coasts[locCanonical] = this.loc_coasts[locCanonical] || [locCanonical];
                        }
                        // Store adjacencies with the original case from file as key for now, will normalize later
                        this.loc_abut[locOriginalCaseFromFile] = this.loc_abut[locOriginalCaseFromFile] || [];

                        const abutsIndex = words.findIndex(w => w.toUpperCase() === 'ABUTS');
                        if (abutsIndex !== -1) {
                            const abuts = words.slice(abutsIndex + 1);
                            abuts.forEach(abutFromFile => { // abutFromFile is original case
                                if (abutFromFile.startsWith('-')) {
                                    const abutToRemove = abutFromFile.substring(1);
                                    this.loc_abut[locOriginalCaseFromFile] = this.loc_abut[locOriginalCaseFromFile].filter(
                                        existingAbut => !existingAbut.toUpperCase().startsWith(abutToRemove.toUpperCase())
                                    );
                                } else {
                                    if (!this.loc_abut[locOriginalCaseFromFile].map(a => a.toUpperCase()).includes(abutFromFile.toUpperCase())) {
                                        this.loc_abut[locOriginalCaseFromFile].push(abutFromFile);
                                    }
                                }
                            });
                        } else if (words.length > 2 && directive !== "AMEND" && directive !== "SHUT") {
                             // SHUT might not have ABUTS. AMEND might only change type.
                             this.error.push(err.MAP_NO_ABUTS_FOR.replace('%s', locCanonical) + ` Line: ${trimmedLine}`);
                        }
                    } else {
                         this.error.push(`Malformed terrain directive: ${trimmedLine}`);
                    }
                } else { // Power definition: e.g. ENGLAND (ENGLISH:E) LON LVP EDI ...
                    let powerNameInDirective = words[0];
                    let powerSpecificsIndex = 1;
                    let homeCenterStartIndex = 1;

                    if (words.length > 2 && words[1] === '->') { // oldName -> newName
                        this.error.push(err.MAP_RENAME_NOT_SUPPORTED + ` Line: ${trimmedLine}`);
                        powerNameInDirective = words[2];
                        powerSpecificsIndex = 3;
                        homeCenterStartIndex = 3;
                    }

                    currentPowerContext = this.norm_power(powerNameInDirective);

                    if (powerNameInDirective.toUpperCase() === 'UNOWNED' || powerNameInDirective.toUpperCase() === 'NEUTRAL') {
                        currentPowerContext = 'UNOWNED';
                    } else {
                        if (!this.powers.includes(currentPowerContext)) {
                            this.powers.push(currentPowerContext);
                        }
                        this.pow_name[currentPowerContext] = powerNameInDirective;
                        this.own_word[currentPowerContext] = currentPowerContext;
                        this.abbrev[currentPowerContext] = currentPowerContext.substring(0, 1).toUpperCase();
                    }

                    // Check for (OwnWord:Abbrev)
                    if (words.length > powerSpecificsIndex && words[powerSpecificsIndex].startsWith('(') && words[powerSpecificsIndex].endsWith(')')) {
                        const specifics = words[powerSpecificsIndex].slice(1, -1);
                        homeCenterStartIndex = powerSpecificsIndex + 1;
                        const parts = specifics.split(':',2); // Split only on first colon
                        this.own_word[currentPowerContext] = parts[0] || currentPowerContext;
                        if (parts.length > 1 && parts[1]) {
                            this.abbrev[currentPowerContext] = parts[1].toUpperCase();
                            if (this.abbrev[currentPowerContext].length !== 1 || ['M', '?'].includes(this.abbrev[currentPowerContext])) {
                                this.error.push(err.MAP_ILLEGAL_POWER_ABBREV + ` For ${currentPowerContext} in ${trimmedLine}`);
                            }
                        }
                    }
                    // Remainder are home centers (original case from file)
                    const homeCentersOriginalCase = words.slice(homeCenterStartIndex);
                    this.add_homes(currentPowerContext, homeCentersOriginalCase, true); // true for reinit
                    // Homes are SCs
                    homeCentersOriginalCase.forEach(hcRaw => {
                        const hcBase = hcRaw.replace(/^-+/,'').toUpperCase().substring(0,3); // Remove leading '-' for SC list
                        if (hcBase && !this.scs.includes(hcBase)) this.scs.push(hcBase);
                    });
                }
                break;

            case 'OWNS': // OWNS center...
            case 'CENTERS': // CENTERS [center...]
                if (!currentPowerContext) {
                    this.error.push(err.MAP_OWNS_BEFORE_POWER.replace('%s', directive).replace('%s', trimmedLine));
                } else {
                    const centersToAdd = words.slice(1).map(c => c.toUpperCase().substring(0,3));
                    if (directive === 'CENTERS' || !this.centers[currentPowerContext]) { // CENTERS reinitializes
                        this.centers[currentPowerContext] = [];
                    }
                    centersToAdd.forEach(c => {
                        if (c && !this.centers[currentPowerContext].includes(c)) this.centers[currentPowerContext].push(c);
                        if (c && !this.scs.includes(c)) this.scs.push(c);
                    });
                }
                break;

            case 'INHABITS': // Appends homes
            case 'HOME':     // Reinitializes homes
            case 'HOMES':    // Reinitializes homes
                 if (!currentPowerContext) {
                    this.error.push(err.MAP_HOME_BEFORE_POWER.replace('%s', directive).replace('%s', trimmedLine));
                } else {
                    const homesToAddOriginalCase = words.slice(1);
                    this.add_homes(currentPowerContext, homesToAddOriginalCase, directive !== 'INHABITS');
                    homesToAddOriginalCase.forEach(hRaw => {
                        if (!hRaw.startsWith('-')) {
                           const hcBase = hRaw.toUpperCase().substring(0,3);
                           if (hcBase && !this.scs.includes(hcBase)) this.scs.push(hcBase);
                        }
                    });
                }
                break;

            case 'UNITS':
                if (!currentPowerContext) this.error.push(err.MAP_UNITS_BEFORE_POWER + ` Line: ${trimmedLine}`);
                else this.units[currentPowerContext] = [];
                break;

            case 'A':
            case 'F':
                if (!currentPowerContext) {
                    this.error.push(err.MAP_UNIT_BEFORE_POWER + ` Line: ${trimmedLine}`);
                } else if (words.length === 2) {
                    const unitLocRawFromFile = words[1]; // e.g. PAR, Bre, spa/sc
                    const unitStringCanonical = `${directive} ${unitLocRawFromFile.toUpperCase()}`;

                    const unitLocShortForClear = unitLocRawFromFile.substring(0,3).toUpperCase();
                    for (const pwr in this.units) { // Clear any unit in same base loc for any power
                        this.units[pwr] = this.units[pwr].filter(u => u.substring(2,5) !== unitLocShortForClear);
                    }
                    this.units[currentPowerContext] = this.units[currentPowerContext] || [];
                    this.units[currentPowerContext].push(unitStringCanonical);
                } else {
                    this.error.push(err.MAP_INVALID_UNIT.replace('%s', trimmedLine));
                }
                break;
            case 'DUMMY':
            case 'DUMMIES':
                const isPlural = directive === 'DUMMIES';
                if (words.length === 1) {
                    if (isPlural) this.error.push(err.MAP_DUMMY_REQ_LIST_POWERS + ` Line: ${trimmedLine}`);
                    else if (!currentPowerContext) this.error.push(err.MAP_DUMMY_BEFORE_POWER + ` Line: ${trimmedLine}`);
                    else if (currentPowerContext !== 'UNOWNED' && !this.dummies.includes(currentPowerContext)) this.dummies.push(currentPowerContext);
                } else {
                    const oldPowerContext = currentPowerContext;
                    currentPowerContext = null; // DUMMY with list resets power context
                    if (words[1].toUpperCase() === 'ALL') {
                        let exceptions: string[] = [];
                        if (words.length > 3 && words[2].toUpperCase() === 'EXCEPT') {
                            exceptions = words.slice(3).map(p => this.norm_power(p));
                        } else if (words.length === 2) { // DUMMY ALL
                           // No exceptions
                        } else if (words.length > 2 && words[2].toUpperCase() !== 'EXCEPT') {
                            this.error.push(err.MAP_NO_EXCEPT_AFTER_DUMMY_ALL.replace('%s', directive) + ` Line: ${trimmedLine}`);
                        } else if (words.length === 3 && words[2].toUpperCase() === 'EXCEPT') { // DUMMY ALL EXCEPT (no powers listed)
                             this.error.push(err.MAP_NO_POWER_AFTER_DUMMY_ALL_EXCEPT.replace('%s', directive) + ` Line: ${trimmedLine}`);
                        }
                        // Use this.powers as the source of "ALL"
                        this.dummies.push(...this.powers.filter(p => p !== 'UNOWNED' && !exceptions.includes(p) && !this.dummies.includes(p)));
                    } else {
                        this.dummies.push(...words.slice(1).map(p => this.norm_power(p)).filter(p => p !== 'UNOWNED' && !this.dummies.includes(p)));
                    }
                    currentPowerContext = oldPowerContext; // Restore power context if it was set
                }
                break;
            case 'UNPLAYED':
                const gonerPowers: string[] = [];
                if (words.length === 1) {
                    if (!currentPowerContext) this.error.push(err.MAP_UNPLAYED_BEFORE_POWER + ` Line: ${trimmedLine}`);
                    else if (currentPowerContext !== 'UNOWNED') gonerPowers.push(currentPowerContext);
                } else {
                    const oldPowerContext = currentPowerContext;
                    currentPowerContext = null;
                    if (words[1].toUpperCase() === 'ALL') {
                        let exceptions: string[] = [];
                        if (words.length > 3 && words[2].toUpperCase() === 'EXCEPT') {
                            exceptions = words.slice(3).map(p => this.norm_power(p));
                        } else if (words.length === 2) { /* ALL */ }
                        else if (words.length > 2 && words[2].toUpperCase() !== 'EXCEPT') this.error.push(err.MAP_NO_EXCEPT_AFTER_UNPLAYED_ALL + ` Line: ${trimmedLine}`);
                        else if (words.length === 3 && words[2].toUpperCase() === 'EXCEPT') this.error.push(err.MAP_NO_POWER_AFTER_UNPLAYED_ALL_EXCEPT + ` Line: ${trimmedLine}`);

                        gonerPowers.push(...this.powers.filter(p => p !== 'UNOWNED' && !exceptions.includes(p)));
                    } else {
                        gonerPowers.push(...words.slice(1).map(p => this.norm_power(p)).filter(p => p !== 'UNOWNED'));
                    }
                     currentPowerContext = oldPowerContext;
                }
                gonerPowers.forEach(goner => {
                    if (this.pow_name[goner]) delete this.pow_name[goner];
                    if (this.own_word[goner]) delete this.own_word[goner];
                    if (this.homes[goner]) delete this.homes[goner];
                    if (this.centers[goner]) delete this.centers[goner];
                    if (this.units[goner]) delete this.units[goner];
                    if (this.abbrev[goner]) delete this.abbrev[goner];
                    this.powers = this.powers.filter(p => p !== goner);
                    this.dummies = this.dummies.filter(p => p !== goner);
                });
                break;

            case 'DROP':
                 words.slice(1).forEach(placeToDropRaw => {
                    const placeToDrop = placeToDropRaw.toUpperCase(); // DROP uses UC prefix matching
                    this.drop(placeToDrop);
                 });
                 break;
        }
    }

    // Post-load normalization and finalization
    this.finalizeLoadedData();

    logger.info(`Finished loading map file: ${actualFilePath}`);
    if (this.error.length > 0) {
        const uniqueErrors = Array.from(new Set(this.error));
        logger.warn(`Errors during map load for ${actualFilePath}: \n${uniqueErrors.join('\n')}`);
        this.error = uniqueErrors;
    }
  }

  private finalizeLoadedData(): void {
    // Ensure all loc_coasts have base names if they only have specific coasts and base is a valid loc
    Object.keys(this.loc_coasts).forEach(baseLoc => { // baseLoc is UC e.g. SPA, PAR
        const coasts = this.loc_coasts[baseLoc]; // coasts are UC e.g. [SPA/NC, SPA/SC] or [PAR]
        // If 'SPA' is a defined location type (this.loc_type[SPA] exists) and it has specific coasts (SPA/NC),
        // but 'SPA' itself is not in its list of coasts, add it.
        // This means 'SPA' can be referred to generally.
        if (this.loc_type[baseLoc] && coasts.some(c => c.includes('/')) && !coasts.includes(baseLoc)) {
           coasts.push(baseLoc);
        }
        // Ensure all listed coastal variants are also present in the main this.locs list
        coasts.forEach(c_variant => { if (!this.locs.includes(c_variant)) this.locs.push(c_variant);});
    });

    // Consolidate and normalize this.locs to unique, uppercase names
    const finalLocs = new Set<string>();
    this.locs.forEach(loc => finalLocs.add(loc.toUpperCase()));
    Object.values(this.loc_name).forEach(abbrev => finalLocs.add(abbrev.toUpperCase()));
    Object.keys(this.loc_type).forEach(abbrev => finalLocs.add(abbrev.toUpperCase()));
    this.locs = Array.from(finalLocs).sort();

    // Normalize keys and values in loc_abut. Keys were original case from file. Values also.
    const normalized_loc_abut: Record<string, string[]> = {};
    for(const loc_key_original_case in this.loc_abut) {
        const ucKeyCanonical = this.find_canonical_location_representation_from_mixed_case(loc_key_original_case);
        if (!ucKeyCanonical) {
            this.error.push(`Unknown location key ${loc_key_original_case} in loc_abut.`);
            continue;
        }

        const abutValuesCanonical = this.loc_abut[loc_key_original_case].map(val_original_case => {
            const ucVal = this.find_canonical_location_representation_from_mixed_case(val_original_case);
            if (!ucVal) this.error.push(`Unknown location value ${val_original_case} in loc_abut for ${loc_key_original_case}.`);
            return ucVal;
        }).filter(Boolean) as string[];

        normalized_loc_abut[ucKeyCanonical] = normalized_loc_abut[ucKeyCanonical] || [];
        abutValuesCanonical.forEach(val => {
            if(!normalized_loc_abut[ucKeyCanonical].includes(val)) normalized_loc_abut[ucKeyCanonical].push(val);
        });
    }
    this.loc_abut = normalized_loc_abut;

    // Ensure all SCs are uppercase base names and sorted.
    this.scs = Array.from(new Set(this.scs.map(sc => sc.toUpperCase().substring(0,3)))).sort();

    // Ensure all powers (from homes, centers, units) are in main this.powers list and sorted.
    const allPowerKeys = new Set<string>(this.powers.map(p => this.norm_power(p)));
    [this.homes, this.centers, this.units].forEach(collection => {
        Object.keys(collection).forEach(p_raw => {
            const normedPower = this.norm_power(p_raw);
            if (normedPower !== 'UNOWNED') allPowerKeys.add(normedPower);
        });
    });
    this.powers = Array.from(allPowerKeys).filter(p => p !== 'UNOWNED').sort();
    // Ensure default records for all official powers if not fully defined by map
    this.powers.forEach(p => {
        if (!this.pow_name[p]) this.pow_name[p] = p; // Default to normalized name if no original case
        if (!this.own_word[p]) this.own_word[p] = p;
        if (!this.abbrev[p]) this.abbrev[p] = p.substring(0,1);
        if (!this.homes[p]) this.homes[p] = [];
        if (!this.centers[p]) this.centers[p] = [];
        if (!this.units[p]) this.units[p] = [];
    });
    if (!this.homes['UNOWNED']) this.homes['UNOWNED'] = [];
  }

  // Helper to resolve potentially mixed-case location strings from map file to canonical UC form
  private find_canonical_location_representation_from_mixed_case(loc_str_mixed_case: string): string | null {
      const uc_loc = loc_str_mixed_case.toUpperCase(); // e.g. "spa/sc" -> "SPA/SC", "StP" -> "STP"

      // 1. Check if the UC string is already a known canonical location (e.g. "SPA/SC" or "PAR")
      if (this.locs.includes(uc_loc)) return uc_loc;

      // 2. Check if the base of the UC string (e.g. "SPA" from "SPA/SC") is a known canonical location
      const base_loc_uc = uc_loc.substring(0,3);
      if (this.locs.includes(base_loc_uc)) return base_loc_uc;

      // 3. Check loc_name which maps full names (original or UC) to abbreviations (UC)
      //    e.g. this.loc_name["St Petersburg"] = "STP" or this.loc_name["ST PETERSBURG"] = "STP"
      const abbrevFromOriginalFullName = this.loc_name[loc_str_mixed_case]; // Key is as in file
      if (abbrevFromOriginalFullName && this.locs.includes(abbrevFromOriginalFullName)) return abbrevFromOriginalFullName;

      const abbrevFromUCFullName = this.loc_name[uc_loc]; // Key is UC version of file string
      if (abbrevFromUCFullName && this.locs.includes(abbrevFromUCFullName)) return abbrevFromUCFullName;

      // 4. If all else fails, and it looks like a base name (3 chars), assume it's canonical if in locs
      if (uc_loc.length === 3 && this.locs.includes(uc_loc)) return uc_loc;

      // Could not find a direct canonical mapping. This might be an error or an undefined loc.
      return null;
  }

  private drop(place_to_drop_raw: string): void {
    // place_to_drop_raw could be "SPA", "spa/sc", "St Petersburg"
    // We need to determine the set of canonical location names this refers to.
    // For "SPA", it means "SPA", "SPA/NC", "SPA/SC". For "spa/sc", just "SPA/SC".
    // For "St Petersburg", it means "STP", "STP/NC", "STP/SC".

    const uc_prefix_or_full = place_to_drop_raw.toUpperCase();
    const related_canonical_locs_to_drop = new Set<string>();

    if (uc_prefix_or_full.includes('/')) { // Specific coast like SPA/SC
        related_canonical_locs_to_drop.add(uc_prefix_or_full);
    } else {
        const base_to_drop = uc_prefix_or_full.substring(0,3);
        this.locs.forEach(l_canon => {
            if (l_canon.startsWith(base_to_drop)) {
                related_canonical_locs_to_drop.add(l_canon);
            }
        });
        // Also consider if place_to_drop_raw was a full name like "Paris"
        const abbrev = this.loc_name[place_to_drop_raw] || this.loc_name[uc_prefix_or_full];
        if (abbrev) {
             this.locs.forEach(l_canon => {
                if (l_canon.startsWith(abbrev.toUpperCase())) {
                    related_canonical_locs_to_drop.add(l_canon);
                }
            });
        }
    }

    if (related_canonical_locs_to_drop.size === 0 && this.locs.includes(uc_prefix_or_full)) {
        // If it was a simple abbrev like "PAR" and no coasts, add it.
        related_canonical_locs_to_drop.add(uc_prefix_or_full);
    }


    logger.info(`Dropping locations: ${Array.from(related_canonical_locs_to_drop).join(', ')}`);

    this.locs = this.locs.filter(l => !related_canonical_locs_to_drop.has(l));

    for (const fullName in this.loc_name) {
        if (related_canonical_locs_to_drop.has(this.loc_name[fullName])) {
            delete this.loc_name[fullName];
        }
    }
    for (const alias in this.aliases) {
        if (related_canonical_locs_to_drop.has(this.aliases[alias])) {
            delete this.aliases[alias];
        }
    }
     for (const unclearAlias in this.unclear) {
        if (related_canonical_locs_to_drop.has(this.unclear[unclearAlias])) {
            delete this.unclear[unclearAlias];
        }
    }
    for (const power in this.homes) {
        this.homes[power] = this.homes[power].filter(home_base => !related_canonical_locs_to_drop.has(home_base)); // homes are base
    }
     for (const power in this.units) { // units store canonical full loc "A PAR", "F SPA/SC"
        this.units[power] = this.units[power].filter(unit_str => {
            const unit_loc_full = unit_str.substring(2);
            return !related_canonical_locs_to_drop.has(unit_loc_full);
        });
    }
    this.scs = this.scs.filter(sc_base => !related_canonical_locs_to_drop.has(sc_base)); // scs are base
    for (const power in this.centers) {
        this.centers[power] = this.centers[power].filter(center_base => !related_canonical_locs_to_drop.has(center_base)); // centers are base
    }

    for (const loc_canon_key in this.loc_abut) { // keys are canonical
        if (related_canonical_locs_to_drop.has(loc_canon_key)) {
            delete this.loc_abut[loc_canon_key];
        } else {
            this.loc_abut[loc_canon_key] = this.loc_abut[loc_canon_key].filter(adj_canon => !related_canonical_locs_to_drop.has(adj_canon));
        }
    }
    related_canonical_locs_to_drop.forEach(loc_to_drop_canon => {
        const base_loc_to_drop = loc_to_drop_canon.substring(0,3);
        if (this.loc_type[base_loc_to_drop]) { // Type is by base name
            delete this.loc_type[base_loc_to_drop];
        }
        if (this.loc_coasts[base_loc_to_drop]) { // Coasts are by base name
            this.loc_coasts[base_loc_to_drop] = this.loc_coasts[base_loc_to_drop].filter(
                c_variant => !related_canonical_locs_to_drop.has(c_variant)
            );
            if(this.loc_coasts[base_loc_to_drop].length === 0) delete this.loc_coasts[base_loc_to_drop];
        }
        // If dropping a specific coast like SPA/SC, and SPA (base) still has other coasts (SPA/NC)
        // then loc_type[SPA] and loc_coasts[SPA] should remain but without SPA/SC.
        // If dropping SPA (base), then loc_type[SPA] and loc_coasts[SPA] are fully removed.
        // The current logic handles this by iterating all related_canonical_locs_to_drop.
    });
    // This makes map_data inconsistent. Call _initialize_map_data() again after all drops if needed.
  }


  public add_homes(power: string, homes_to_add: string[], reinit: boolean): void {
    const powerKey = this.norm_power(power).toUpperCase();

    if (reinit || !this.homes[powerKey]) {
        this.homes[powerKey] = [];
    }
    // Ensure UNOWNED is initialized, critical for logic below
    this.homes['UNOWNED'] = this.homes['UNOWNED'] || [];


    for (let home_directive of homes_to_add) { // e.g. "MOS", "-PAR", "STP/SC" (though add_homes should get base names)
        let remove = false;
        while (home_directive.startsWith('-')) {
            remove = !remove;
            home_directive = home_directive.substring(1);
        }
        // Homes are always base province names (e.g. STP from STP/SC)
        const homeBase = home_directive.toUpperCase().substring(0,3);
        if (!homeBase) continue;

        // Manage power's homes
        const currentIdxInPowerHomes = this.homes[powerKey].indexOf(homeBase);
        if (currentIdxInPowerHomes > -1) { // Exists in power's homes
            if (remove) this.homes[powerKey].splice(currentIdxInPowerHomes, 1);
        } else { // Not in power's homes
            if (!remove) this.homes[powerKey].push(homeBase);
        }

        // Manage UNOWNED list:
        // An SC becomes UNOWNED if no non-dummy power claims it as a home.
        // Python: if power_name != 'UNOWNED': self.homes['UNOWNED'].append(home) ... if not remove: self.homes[power].append(home)
        // This implies UNOWNED initially gets all homes, then they are removed if a power claims them.
        // Let's refine: if adding to a specific power, remove from UNOWNED.
        // If removing from a specific power, add to UNOWNED IFF it's an SC and no other power has it as home.
        if (this.scs.includes(homeBase)) { // Only SCs can be homes and thus matter for UNOWNED homes list
            const unownedIdx = this.homes['UNOWNED'].indexOf(homeBase);

            if (powerKey !== 'UNOWNED') {
                if (!remove) { // Adding home to a power
                    if (unownedIdx > -1) this.homes['UNOWNED'].splice(unownedIdx, 1); // Remove from UNOWNED
                } else { // Removing home from a power
                    // Add to UNOWNED only if no other *active* power holds it as a home.
                    let isHeldByOtherPower = false;
                    for (const pwr in this.homes) {
                        if (pwr !== 'UNOWNED' && pwr !== powerKey && this.homes[pwr].includes(homeBase)) {
                            isHeldByOtherPower = true;
                            break;
                        }
                    }
                    if (!isHeldByOtherPower && unownedIdx === -1) {
                        this.homes['UNOWNED'].push(homeBase);
                    }
                }
            } else { // Directly manipulating UNOWNED list (e.g. UNOWNED MOS -PAR)
                 if (remove && unownedIdx > -1) { // UNOWNED -PAR
                     this.homes['UNOWNED'].splice(unownedIdx, 1);
                 }
                 if (!remove && unownedIdx === -1) { // UNOWNED MOS
                     this.homes['UNOWNED'].push(homeBase);
                 }
            }
        }
    }
  }


  public is_valid_unit(unit_str: string, no_coast_ok: boolean = false, shut_ok: boolean = false): boolean {
    const parts = unit_str.toUpperCase().split(" ");
    if (parts.length !== 2) return false;

    const unit_type = parts[0];
    const loc_with_coast_info = parts[1]; // Can be "PAR", "SPA/SC"

    const base_loc = loc_with_coast_info.substring(0,3);
    const areaType = this.loc_type[base_loc]; // Type is always for the base province

    if (areaType === 'SHUT') {
        return shut_ok ? true : false;
    }
    if (!areaType) return false; // Unknown location

    if (unit_type === '?') {
        return true; // Any known location is fine for '?'
    }

    if (unit_type === 'A') {
        return !loc_with_coast_info.includes('/') &&
               (areaType === 'LAND' || areaType === 'COAST' || areaType === 'PORT');
    }

    if (unit_type === 'F') {
        if (!(areaType === 'WATER' || areaType === 'COAST' || areaType === 'PORT')) return false;

        if (!loc_with_coast_info.includes('/')) { // e.g. "F SPA"
            const possible_coasts = this.loc_coasts[base_loc] || [];
            const has_specific_coasts = possible_coasts.some(c => c.includes('/'));

            if (has_specific_coasts && !no_coast_ok) {
                // If SPA has SPA/NC, SPA/SC, then "F SPA" is only valid if "SPA" itself is listed in loc_coasts[SPA]
                // or if no_coast_ok is true.
                // Python's map.is_valid_unit has `loc.lower() not in self.loc_abut` check for fleets.
                // self.loc_abut keys are original case or lower case non-coastal locs.
                // This implies that if 'spa' (lowercase) is a key in loc_abut, then 'F SPA' is invalid.
                // This typically means 'spa' is the non-coastal land bridge.
                // For TS, let's check if the base_loc itself is a valid coastal choice if specific coasts exist.
                if (!possible_coasts.includes(base_loc)) return false;
            }
        } else { // e.g. "F SPA/SC" - specific coast
            const coasts_for_base = this.loc_coasts[base_loc] || [];
            if (!coasts_for_base.includes(loc_with_coast_info)) {
                return false;
            }
        }
        return true;
    }
    return false;
  }

  /**
   * Validates the loaded map data for consistency.
   * Populates this.error with any issues found.
   * Sets this.validated = 1 after running.
   * @param force - If true, re-validates even if already validated.
   */
  public validate(force: number = 0): void {
    if (!force && this.validated) {
        return;
    }
    this.error = []; // Clear previous errors for a fresh validation pass
    logger.info("Validating map data...");
    const current_errors: string[] = []; // Use a temporary error list for this validation pass

    // Check powers
    if (this.powers.length < 2) {
        current_errors.push(err.MAP_LEAST_TWO_POWERS);
    }

    // Validate area types and names
    const allShortLocNamesCanonical = new Set(Object.keys(this.loc_type));
    this.locs.forEach(locOriginalCase => {
        const locUpper = locOriginalCase.toUpperCase();
        const shortName = locUpper.substring(0,3);
        if (!this.loc_type[shortName] && !this.powers.map(p => this.norm_power(p)).includes(shortName)) {
            current_errors.push(err.MAP_LOC_NOT_FOUND.replace('%s', locOriginalCase));
        }
    });


    // Validating adjacencies (loc_abut keys should be canonical locs)
    for (const placeUpper of Object.keys(this.loc_abut)) {
        const placeShortUpper = placeUpper.substring(0,3);

        if (!allShortLocNamesCanonical.has(placeShortUpper) && !this.locs.some(l => l.toUpperCase().startsWith(placeShortUpper))) {
             current_errors.push(err.MAP_LOC_NOT_FOUND.replace('%s', placeUpper + " (as key in loc_abut)"));
        }

        const abuts = this.loc_abut[placeUpper];
        const up_abuts_short = abuts.map(loc => loc.toUpperCase().substring(0,3));
        for (const abutTarget of abuts) { // abutTarget should be canonical UC form
            const abutTargetUpperShort = abutTarget.toUpperCase().substring(0,3);
            if (!allShortLocNamesCanonical.has(abutTargetUpperShort) && !this.locs.some(l => l.toUpperCase().startsWith(abutTargetUpperShort))) {
                current_errors.push(err.MAP_LOC_NOT_FOUND.replace('%s', abutTarget + ` (in ${placeUpper} ABUTS)`));
            }
            if (up_abuts_short.filter(s => s === abutTargetUpperShort).length > 1) {
                const msg = err.MAP_SITE_ABUTS_TWICE.replace('%s', placeUpper).replace('%s', abutTargetUpperShort);
                if (!current_errors.includes(msg)) current_errors.push(msg);
            }

            const targetAbutsBack = this.loc_abut[abutTarget] || [];
            if (!targetAbutsBack.includes(placeUpper)) {
                 // This check is complex due to map specific rules (e.g. one way water adj for coasts)
                 // Python's _abuts and later validation handles this.
                 // For now, simple check. If A->B, B must ->A (mostly)
                 // current_errors.push(err.MAP_ONE_WAY_ADJ.replace('%s', placeUpper).replace('%s', abutTarget));
            }
        }
    }

    // Validate SCs
    this.scs.forEach(sc => {
        if (!this.loc_type[sc.toUpperCase()]) {
            current_errors.push(err.MAP_LOC_NOT_FOUND.replace('%s', `${sc} (as SC)`));
        }
    });

    // Validate homes
    Object.entries(this.homes).forEach(([powerName, homeScs]) => {
        if (powerName === "UNOWNED") return;
        homeScs.forEach(homeSc => {
            if (!this.scs.includes(homeSc)) {
                current_errors.push(err.MAP_BAD_HOME.replace('%s', powerName).replace('%s', homeSc + " (not listed in SCs)"));
            }
            if (!this.loc_type[homeSc]) {
                 current_errors.push(err.MAP_BAD_HOME.replace('%s', powerName).replace('%s', `${homeSc} (not a defined loc)`));
            }
        });
    });

    // Validate initial centers and units (from this.centers, this.units)
    Object.entries(this.centers).forEach(([powerName, centerList]) => {
        if (powerName === "UNOWNED") return;
        centerList.forEach(sc => {
            if (!this.loc_type[sc]) current_errors.push(err.MAP_BAD_INITIAL_OWN_CENTER.replace('%s', powerName).replace('%s', sc));
            if (!this.scs.includes(sc)) current_errors.push(err.MAP_BAD_INITIAL_OWN_CENTER.replace('%s', powerName).replace('%s', sc + " (not an SC)"));
        });
    });
    Object.entries(this.units).forEach(([powerName, unitList]) => {
        unitList.forEach(unitStr => {
            if (!this.is_valid_unit(unitStr)) current_errors.push(err.MAP_BAD_INITIAL_UNITS.replace('%s', powerName).replace('%s', unitStr));
        });
    });

    const ownedScCounts: Record<string, string[]> = {};
    Object.entries(this.centers).forEach(([powerName, scList]) => {
        if (powerName === "UNOWNED") return;
        scList.forEach(sc => {
            ownedScCounts[sc] = ownedScCounts[sc] || [];
            ownedScCounts[sc].push(powerName);
        });
    });
    for (const sc in ownedScCounts) {
        if (ownedScCounts[sc].length > 1) {
            current_errors.push(err.MAP_CENTER_MULT_OWNED.replace('%s', sc + ` (owned by ${ownedScCounts[sc].join(', ')})`));
        }
    }
    if (this.homes['UNOWNED']) {
        this.homes['UNOWNED'].forEach(unownedHome => {
            Object.entries(this.homes).forEach(([pwr, ownedHomes]) => {
                if (pwr !== 'UNOWNED' && ownedHomes.includes(unownedHome)) {
                     current_errors.push(err.MAP_CENTER_MULT_OWNED.replace('%s', unownedHome + ` (listed as UNOWNED home and ${pwr}'s home)`));
                }
            });
        });
    }

    if (this.phase) {
        const phaseParts = this.phase.split(' ');
        if (phaseParts.length !== 3) {
            current_errors.push(err.MAP_BAD_PHASE.replace('%s', this.phase));
        } else {
            try {
                const year = parseInt(phaseParts[1], 10);
                if (isNaN(year)) { // Check if first_year was set if phase is just e.g. "SPRING MOVEMENT"
                     if (this.first_year === undefined || this.first_year === null) {
                        current_errors.push(err.MAP_BAD_PHASE.replace('%s', this.phase + " (year invalid/missing and no FIRSTYEAR)"));
                     }
                     // If first_year is set, we can assume phase uses it.
                } else {
                    this.first_year = year; // Phase specific year overrides FIRSTYEAR directive.
                }
            } catch (e) {
                current_errors.push(err.MAP_BAD_PHASE.replace('%s', this.phase + " (year parsing failed)"));
            }
            const phaseType = phaseParts[2].toUpperCase();
            if (!Object.values(this.phase_abbrev).includes(phaseType)){
                 current_errors.push(err.MAP_BAD_PHASE.replace('%s', this.phase + ` (unknown phase type ${phaseType})`));
            }
        }
    } else {
        current_errors.push(err.MAP_BAD_PHASE.replace('%s', "(No phase defined)"));
    }


    this.error.push(...current_errors);
    this.validated = 1;
    if (this.error.length > 0) {
        const uniqueErrors = Array.from(new Set(this.error));
        logger.error("Map validation found errors:", uniqueErrors.join("\n"));
        this.error = uniqueErrors;
    } else {
        logger.info("Map validation passed.");
    }
  }

  /**
   * Get the type of a province (e.g., 'LAND', 'WATER', 'COAST', 'PORT').
   * This is a simplified version of area_type, usually taking a base province name.
   * @param province_base_name The base name of the province (e.g. PAR, MAR).
   * @returns Province type string or undefined if not found.
   */
  get_province_type(province_base_name: string): string | undefined { // Corresponds to Python's area_type
    const uc_base_name = province_base_name.substring(0,3).toUpperCase();
    return this.loc_type[uc_base_name];
  }

  /**
    if (this.powers.length < 2) {
        current_errors.push(err.MAP_LEAST_TWO_POWERS);
    }

    // Validate area types and names
    const allShortLocNames = new Set(Object.values(this.loc_name));
    this.locs.forEach(locOriginalCase => {
        const locUpper = locOriginalCase.toUpperCase();
        const shortName = locUpper.substring(0,3);
        if (!this.loc_type[shortName] && !this.powers.includes(shortName) /* Power names can be locs */) {
            current_errors.push(err.MAP_LOC_NOT_FOUND.replace('%s', locOriginalCase));
        }
        if(this.loc_name[locUpper] !== shortName && !locUpper.includes('/')) { // Full name maps to its short form
            // This condition might be too strict if loc_name can map e.g. "English Channel" to "ECH"
            // Python code: if place.upper() not in self.loc_name.values(): error
            // This means all short names (values in loc_name) must be derivable from a full name (key in loc_name)
            // The current structure in TS: loc_name maps FULL_UPPER -> SHORT_UPPER
            // locs contains original case.
            // This check seems to be about ensuring all locs (from list) have a full name definition if they are abbreviations
            // or that their full name is registered if they are full names.
            // For now, let's ensure every short name in loc_type and loc_abut keys (after normalization) is in allShortLocNames.
        }
    });


    // Validating adjacencies (loc_abut)
    for (const placeOriginalCase of Object.keys(this.loc_abut)) {
        const placeUpper = placeOriginalCase.toUpperCase();
        const placeShortUpper = placeUpper.substring(0,3);

        if (!allShortLocNames.has(placeShortUpper) && !this.locs.some(l => l.toUpperCase().startsWith(placeShortUpper))) {
             current_errors.push(err.MAP_LOC_NOT_FOUND.replace('%s', placeOriginalCase + " (as key in loc_abut)"));
        }
        if (!this.loc_name[placeUpper] && !placeUpper.includes('/')) { // Check if full name for this abut key is registered
            // This error is from python: if place.upper() not in self.loc_name.values():
            // which means the key of loc_abut should be a value in loc_name (a short name)
            // Our loc_abut keys are original case from file. Let's assume they should be normalizable to a defined loc.
             if (!allShortLocNames.has(placeShortUpper)) {
                // This check is tricky with current structure. Python's map has more normalized internal keys.
                // current_errors.push(err.MAP_NO_FULL_NAME.replace('%s', placeOriginalCase));
             }
        }

        const abuts = this.loc_abut[placeOriginalCase];
        const up_abuts_short = abuts.map(loc => loc.toUpperCase().substring(0,3));
        for (const abutTarget of abuts) {
            const abutTargetUpperShort = abutTarget.toUpperCase().substring(0,3);
            if (!allShortLocNames.has(abutTargetUpperShort) && !this.locs.some(l => l.toUpperCase().startsWith(abutTargetUpperShort))) {
                current_errors.push(err.MAP_LOC_NOT_FOUND.replace('%s', abutTarget + ` (in ${placeOriginalCase} ABUTS)`));
            }
            if (up_abuts_short.filter(s => s === abutTargetUpperShort).length > 1) {
                const msg = err.MAP_SITE_ABUTS_TWICE.replace('%s', placeOriginalCase).replace('%s', abutTargetUpperShort);
                if (!current_errors.includes(msg)) current_errors.push(msg);
            }
            // One-way adjacency check (complex, requires iterating all other loc_abut entries)
        }
    }

    // Validate SCs
    this.scs.forEach(sc => {
        if (!this.loc_type[sc.toUpperCase()]) { // SCs are short names
            current_errors.push(err.MAP_LOC_NOT_FOUND.replace('%s', `${sc} (as SC)`));
        }
    });

    // Validate homes
    Object.entries(this.homes).forEach(([powerName, homeScs]) => {
        if (powerName === "UNOWNED") return;
        homeScs.forEach(homeSc => {
            if (!this.scs.includes(homeSc)) {
                current_errors.push(err.MAP_BAD_HOME.replace('%s', powerName).replace('%s', homeSc));
            }
            if (!this.loc_type[homeSc]) {
                 current_errors.push(err.MAP_BAD_HOME.replace('%s', powerName).replace('%s', `${homeSc} (not a defined loc)`));
            }
        });
    });

    // Validate initial centers and units (from this.centers, this.units)
    Object.entries(this.centers).forEach(([powerName, centerList]) => {
        if (powerName === "UNOWNED") return;
        centerList.forEach(sc => {
            if (!this.loc_type[sc]) current_errors.push(err.MAP_BAD_INITIAL_OWN_CENTER.replace('%s', powerName).replace('%s', sc));
        });
    });
    Object.entries(this.units).forEach(([powerName, unitList]) => {
        unitList.forEach(unitStr => {
            if (!this.is_valid_unit(unitStr)) current_errors.push(err.MAP_BAD_INITIAL_UNITS.replace('%s', powerName).replace('%s', unitStr));
        });
    });


    this.error.push(...current_errors); // Add new errors found in this pass
    this.validated = 1;
    if (this.error.length > 0) {
        logger.error("Map validation found errors:", Array.from(new Set(this.error)).join("\n")); // Show unique errors
    } else {
        logger.info("Map validation passed.");
    }
  }

  public norm(phrase: string): string {
    let result = phrase.toUpperCase();

    // Normalize slashes for coasts: "SPA/SC" -> "SPA /SC", "SPA / SC" -> "SPA /SC"
    // This helps tokenize coasts correctly, e.g. "/SC" becomes a token.
    result = result.replace(/([A-Z0-9]{3})\s*\/\s*((?:N|S|E|W)C)/g, '$1 /$2'); // e.g. "SPA / SC" -> "SPA /SC"
    result = result.replace(/([A-Z0-9]{3})\/((?:N|S|E|W)C)/g, '$1 /$2');    // e.g. "SPA/SC" -> "SPA /SC"

    // Replace punctuation (except internal slashes in coasts like /NC) with spaces
    const tokensToRemoveOrReplaceWithSpace = /[\.:\-\+,()\[\]]/g;
    result = result.replace(tokensToRemoveOrReplaceWithSpace, ' ');

    // Space out other special characters if they are not part of a word
    const tokensToSpaceAround = /([\|\*\?!~=_^])/g;
    result = result.replace(tokensToSpaceAround, ' $1 ');

    const tokens = result.trim().split(/\s+/);
    const finalTokens: string[] = [];

    for (const token of tokens) {
        if (!token) continue;
        const ucToken = token.toUpperCase();

        // 1. Keyword replacement
        let currentToken = this.keywords[ucToken] || ucToken;

        // 2. Alias replacement (primarily for locations, could also include powers if defined in aliases)
        // Ensure aliases themselves are not keywords that were already replaced.
        // e.g. if "ENG" is an alias for "ECH" but also a keyword for "ENGLISH CHANNEL"
        // The order of these operations (keywords vs aliases) can matter.
        // Standard approach: specific aliases first, then general keywords.
        // However, our KEYWORDS also include things like "ARMY" -> "A".
        // Let's assume for now: if it became a single letter keyword, it's likely final.
        // Otherwise, try alias.
        if (currentToken.length > 1 || currentToken.startsWith("/")) { // Don't re-alias single-letter results like 'A', 'F', or coasts
            currentToken = this.aliases[currentToken] || currentToken;
        }
        finalTokens.push(currentToken);
    }
    return finalTokens.join(' ');
  }

  public norm_power(power: string): string {
    // Normalize for keywords/aliases, then remove spaces to get a single token power name
    const normed = this.norm(power);
    return normed.replace(/\s+/g, '').toUpperCase();
  }

  public area_type(loc: string, no_coast_ok: boolean = false): string | undefined {
    const upperLoc = loc.toUpperCase();
    let shortLoc = upperLoc.substring(0,3);
    if (no_coast_ok && upperLoc.includes('/')) {
        shortLoc = upperLoc.split('/')[0].substring(0,3);
    } else if (upperLoc.includes('/')) { // Specific coast, type must be COAST or PORT
        const base = upperLoc.split('/')[0].substring(0,3);
        const type = this.loc_type[base];
        return (type === 'COAST' || type === 'PORT') ? type : undefined;
    }
    return this.loc_type[shortLoc];
  }

  public is_coastal(province_base_uc: string): boolean {
    return this.loc_coasts[province_base_uc] && this.loc_coasts[province_base_uc].some(loc => loc.includes('/'));
  }

  public get_all_sea_provinces(): string[] {
    const seaProvinces: string[] = [];
    this.map_data.nodes.forEach((node, loc) => {
        if (node.type === 'WATER' || node.type === 'SEA') { // Assuming 'WATER' and 'SEA' are synonymous from map files
            seaProvinces.push(loc);
        }
    });
    return seaProvinces;
  }

  // Interface for map_data.nodes values
  public get_location_node(name: string): { type: string, sc: boolean, coasts?: Set<string> } | null {
    const ucName = name.toUpperCase();
    // Try direct match (e.g., "SPA/NC" or "PAR")
    if (this.map_data.nodes.has(ucName)) {
        return this.map_data.nodes.get(ucName)!;
    }
    // Try base name if a specific coast was requested but not found directly
    if (ucName.includes("/")) {
        const baseName = ucName.substring(0,3);
        if (this.map_data.nodes.has(baseName)) {
            return this.map_data.nodes.get(baseName)!;
        }
    }
    // Try looking up via alias to get a base name
    const normed = this.norm(name).toUpperCase(); // Norm to handle aliases
    if (this.map_data.nodes.has(normed)) { // Normed might be an abbrev
        return this.map_data.nodes.get(normed)!;
    }
    if (normed.includes('/')) {
        const baseNormed = normed.substring(0,3);
        if (this.map_data.nodes.has(baseNormed)) {
            return this.map_data.nodes.get(baseNormed)!;
        }
    }
    return null;
  }


  public add_homes(power: string, homes_to_add: string[], reinit: boolean): void {
    const powerKey = this.norm_power(power).toUpperCase();

    if (reinit || !this.homes[powerKey]) {
        this.homes[powerKey] = [];
    }
    this.homes['UNOWNED'] = this.homes['UNOWNED'] || [];

    for (let home of homes_to_add) {
        let remove = false;
        while (home.startsWith('-')) {
            remove = !remove;
            home = home.substring(1);
        }
        home = home.toUpperCase().substring(0,3);
        if (!home) continue;

        const currentIdx = this.homes[powerKey].indexOf(home);
        if (currentIdx > -1) {
            this.homes[powerKey].splice(currentIdx, 1);
        }

        if (powerKey !== 'UNOWNED') {
            const unownedIdx = this.homes['UNOWNED'].indexOf(home);
            if (unownedIdx > -1) {
                this.homes['UNOWNED'].splice(unownedIdx, 1);
            }
        }

        if (!remove) {
            if (!this.homes[powerKey].includes(home)) {
                 this.homes[powerKey].push(home);
            }
        } else {
            if (powerKey !== 'UNOWNED' && this.scs.includes(home) && !this.homes['UNOWNED'].includes(home)) {
                 this.homes['UNOWNED'].push(home);
            }
        }
    }
  }


  public is_valid_unit(unit_str: string, no_coast_ok: boolean = false, shut_ok: boolean = false): boolean {
    const parts = unit_str.toUpperCase().split(" ");
    if (parts.length !== 2) return false;

    const unit_type = parts[0];
    const loc = parts[1];

    const shortLocForTypeLookup = loc.substring(0,3);
    const areaType = this.area_type(shortLocForTypeLookup);

    if (areaType === 'SHUT') {
        return shut_ok ? true : false;
    }
    if (unit_type === '?') {
        return areaType !== undefined && areaType !== null;
    }
    if (unit_type === 'A') {
        return !loc.includes('/') && (areaType === 'LAND' || areaType === 'COAST' || areaType === 'PORT');
    }
    if (unit_type === 'F') {
        const isNonCoastedVersionOfCoastedProv = !loc.includes('/') && (this.loc_coasts[loc]?.length || 0) > 1 && this.loc_coasts[loc][0] !== loc;

        if (!no_coast_ok && isNonCoastedVersionOfCoastedProv) {
            return false;
        }
        return areaType === 'WATER' || areaType === 'COAST' || areaType === 'PORT';
    }
    return false;
  }

  /**
   * Get the type of a province (e.g., 'LAND', 'SEA', 'COAST').
   * @param province_name The name of the province (normalized, base name e.g. PAR, MAR).
   * @returns Province type string or null if not found.
   */
  get_province_type(province_name: string): 'LAND' | 'SEA' | 'COAST' | null {
    const loc_base = province_name.substring(0, 3).toUpperCase();
    const area = this.locs[loc_base]; // this.locs should store AreaDefinition like objects
    // Assuming AreaDefinition has properties like 'sea' and 'coast' based on prior map parsing logic
    // This might need adjustment based on the actual structure of this.locs[loc_base] objects
    if (!area) { // If loc_base is not directly in this.locs, it might be an alias or full name
        const shortName = this.loc_name[loc_base] || loc_base; // Convert potential full name to abbrev
        const areaDef = this.locs.find(l => (this.loc_name[l.toUpperCase()] || l.toUpperCase().substring(0,3)) === shortName);
        if(areaDef && (areaDef as any).sea) return 'SEA';
        if(areaDef && (areaDef as any).coast) return 'COAST';
        if(areaDef) return 'LAND';
        return null;
    }


    if ((area as any).sea) return 'SEA'; // Type assertion if 'sea'/'coast' not directly on string value
    if ((area as any).coast) return 'COAST';
    return 'LAND';
  }

  /**
   * Check if a unit type can move to/occupy a given province type.
   * @param unit_type 'A' or 'F'.
   * @param target_province_type 'LAND', 'SEA', or 'COAST'.
   * @returns True if valid, false otherwise.
   */
  is_valid_move_for_unit_type(unit_type: 'A' | 'F', target_province_type: 'LAND' | 'SEA' | 'COAST'): boolean {
    if (unit_type === 'A') {
        return target_province_type === 'LAND' || target_province_type === 'COAST';
    } else if (unit_type === 'F') {
        return target_province_type === 'SEA' || target_province_type === 'COAST';
    }
    return false;
  }

  /**
   * Finds all coasts for a given location (base name or specific coast).
   * Returns a list of canonical coastal variants (e.g., ["BUL/EC", "BUL/SC"])
   * or the location itself if it has no distinct coasts (e.g., ["PAR"]).
   * @param loc_str - The name of a location (e.g., 'BUL', 'SPA/NC').
   * @returns Returns the list of all coasts, including the location itself if it's non-coastal or a general coastal ref.
   */
  public find_coasts(loc_str: string): string[] {
    const loc_uc = loc_str.toUpperCase();
    const base_loc = loc_uc.substring(0, 3);

    // this.loc_coasts stores: base_loc_uc -> [loc_base_uc/NC, loc_base_uc/SC, ...] OR [loc_base_uc]
    // If the input is already a specific coast (e.g. "SPA/NC"), return it directly if valid.
    if (loc_uc.includes('/')) {
        if (this.loc_coasts[base_loc]?.includes(loc_uc)) {
            return [loc_uc];
        } else { // Invalid specific coast or base_loc not in loc_coasts
            return [];
        }
    }
    // Input is a base name (e.g. "SPA" or "PAR")
    return this.loc_coasts[base_loc] || [base_loc]; // Default to [base_loc] if no specific coasts defined
  }


  public build_cache(): void {
    logger.info("Building map caches (loc_coasts, abuts_cache, dest_with_coasts)...");
    this.abuts_cache = {};
    this.dest_with_coasts = {};

    // 1. Finalize loc_coasts (Python does this in build_cache)
    //    Assuming this.locs contains all canonical location names (e.g. PAR, LON, STP, STP/NC, STP/SC)
    //    And this.loc_type is populated for all base provinces.
    //    This step ensures loc_coasts[BASE_PROVINCE] = [ALL_CANONICAL_VARIANTS_OF_BASE_PROVINCE]
    const temp_loc_coasts: Record<string, string[]> = {};
    for (const loc_canon of this.locs) { // loc_canon is like PAR, STP, STP/NC
        const base_loc = loc_canon.substring(0,3);
        temp_loc_coasts[base_loc] = temp_loc_coasts[base_loc] || [];
        if (!temp_loc_coasts[base_loc].includes(loc_canon)) {
            temp_loc_coasts[base_loc].push(loc_canon);
        }
    }
    this.loc_coasts = temp_loc_coasts;


    // 2. Building abuts_cache
    //    Requires this.locs to be the complete list of all canonical locations (PAR, SPA, SPA/NC, SPA/SC)
    //    Requires _abuts to correctly use these canonical names.
    const unitTypes: Array<'A' | 'F'> = ['A', 'F'];
    const orderTypes: string[] = ['-', 'S', 'C']; // Move, Support, Convoy

    for (const unit_type of unitTypes) {
        for (const unit_loc_canon of this.locs) { // unit_loc_canon is PAR, SPA, SPA/NC etc.
            for (const other_loc_canon of this.locs) { // other_loc_canon is also PAR, SPA, SPA/NC
                for (const order_type of orderTypes) {
                    const queryTuple = `${unit_type},${unit_loc_canon},${order_type},${other_loc_canon}`;
                    // _abuts should take canonical forms directly.
                    // The result of _abuts is boolean, so convert to 0 or 1.
                    this.abuts_cache[queryTuple] = this._abuts(unit_type, unit_loc_canon, order_type, other_loc_canon) ? 1 : 0;
                }
            }
        }
    }

    // 3. Building dest_with_coasts
    //    For each loc in this.locs (canonical form), find all reachable locations (1 hop)
    //    and then list all their coastal variants.
    for (const loc_canon of this.locs) { // e.g., PAR, BUL, BUL/EC, BUL/SC
        // abut_list expects a canonical location name.
        // incl_no_coast=true ensures that if 'SPA' is given, adjacent 'POR' (if POR has no coasts) and 'MAO' are returned.
        // If 'SPA/NC' is given, it should return adjacencies specific to SPA/NC.
        // The Python `abut_list` uses `self.loc_abut` which can have mixed-case keys based on file.
        // Our this.loc_abut should have canonical UC keys after load().
        const one_hop_adj_locs_mixed_case = this.abut_list(loc_canon, true);
                                                                    // true: include non-coastal base if it has coasts e.g. SPA for SPA/NC

        const all_coastal_variants_of_dests = new Set<string>();
        one_hop_adj_locs_mixed_case.forEach(adj_loc_mixed_case => {
            // adj_loc_mixed_case could be 'Par', 'spa', 'Spa/NC'. Need its canonical forms.
            const adj_base_canon = adj_loc_mixed_case.substring(0,3).toUpperCase();
            const coasts_of_adj = this.find_coasts(adj_base_canon); // find_coasts expects base or specific coast
            coasts_of_adj.forEach(variant => all_coastal_variants_of_dests.add(variant));
        });
        this.dest_with_coasts[loc_canon] = Array.from(all_coastal_variants_of_dests);
    }
    logger.info("Map caches built.");
  }


  public abut_list(site: string, incl_no_coast: boolean = false): string[] {
    const siteOriginalCase = this.locs.find(l => l.toUpperCase() === site.toUpperCase()) || site;
    let abut_list: string[] = this.loc_abut[siteOriginalCase] || [];

    if (incl_no_coast) {
        const result_with_no_coast = new Set<string>(abut_list);
        for (const loc of abut_list) {
            if (loc.includes('/')) {
                result_with_no_coast.add(loc.substring(0, 3));
            }
        }
        return Array.from(result_with_no_coast);
    }
    return [...abut_list];
  }

  private _abuts(unit_type: 'A' | 'F' | '?', unit_loc_full: string, order_type: string, other_loc_full: string): boolean {
    unit_loc_full = unit_loc_full.toUpperCase();
    other_loc_full = other_loc_full.toUpperCase();

    if (!this.is_valid_unit(`${unit_type} ${unit_loc_full}`)) {
        return false;
    }

    let effective_other_loc = other_loc_full;
    if (other_loc_full.includes('/')) {
        if (order_type === 'S') {
            effective_other_loc = other_loc_full.substring(0, 3);
        } else if (unit_type === 'A') {
            return false;
        }
    }

    const unitLocOriginalCase = this.locs.find(l => l.toUpperCase() === unit_loc_full) || unit_loc_full;
    const adjacencies = this.loc_abut[unitLocOriginalCase] || [];

    let place_found_in_adj: string | undefined = undefined;
    for (const adj_from_list of adjacencies) {
        const adj_from_list_upper = adj_from_list.toUpperCase();
        const adj_short_upper = adj_from_list_upper.substring(0,3);

        if (effective_other_loc === adj_from_list_upper || effective_other_loc === adj_short_upper) {
            place_found_in_adj = adj_from_list;
            break;
        }
    }

    if (!place_found_in_adj) {
        return false;
    }

    const other_loc_type = this.area_type(effective_other_loc.substring(0,3));
    if (other_loc_type === 'SHUT') return false;
    if (unit_type === '?') return true;

    if (unit_type === 'F') {
        if (other_loc_type === 'LAND') return false;
        // Python: place[0] != up_loc[0]  (original case from abut list vs UC other_loc)
        // This means if adjacency in map file was 'par' for 'BAL', F BAL cannot go to PAR.
        // My adjacencies in this.loc_abut are now canonical UC.
        // This check from python: (place[0] != up_loc[0]) is tricky.
        // It means if self.loc_abut['VEN'] = ['tus', 'ADR'], then F VEN to tus (TUS) is not allowed.
        // This implies the original case of the abutment in the map file matters for fleets.
        // My current this.loc_abut stores UC names. This detail might be lost.
        // For now, let's assume this.loc_abut stores what's needed or _abuts gets more complex.
        // Python: or order_type != 'S' and other_loc not in self.loc_type
        // This means for non-Support orders, the target must be a defined location type.
        // My other_loc_type checks this.
        if (order_type !== 'S' && !this.loc_type[effective_other_loc.substring(0,3)]) return false;


    }
    else if (unit_type === 'A') {
        if (order_type !== 'C' && other_loc_type === 'WATER') return false;
        // Python: place == place.title() -- means mixed case like 'Mar' (Marseilles) not allowed for army.
        // This is another case where original map file casing for abuts is used.
        // If this.loc_abut now stores only UC, this check is hard.
        // For now, assuming this detail is handled by map file correctness and canonicalization.
    }
    return true;
  }

  public abuts(unit_type: 'A' | 'F' | '?', unit_loc: string, order_type: string, other_loc: string): boolean {
    const queryTuple = `${unit_type},${unit_loc.toUpperCase()},${order_type.toUpperCase()},${other_loc.toUpperCase()}`;
    const cachedResult = this.abuts_cache[queryTuple];
    if (cachedResult !== undefined) {
        return cachedResult === 1;
    }
    // If it's not in cache, it implies it might be an invalid query or needs calculation.
    // Python's _abuts is called by build_cache. A direct call to abuts() implies cache lookup.
    // If we reach here, it means the specific combination wasn't pre-cached, which could be an issue
    // if self.locs used for cache generation was incomplete, or if locs passed are non-canonical.
    // For safety, calculate on the fly, but warn, as this indicates a potential gap in cache generation or query.
    logger.warn(`Abuts cache miss for: ${queryTuple}. Calculating on the fly. Ensure locs are canonical.`);
    return this._abuts(unit_type, unit_loc, order_type, other_loc);
  }


  public phase_abbr(phase: string, defaultVal: string = '?????'): string {
    } else if (unit_type === 'F') {
        return target_province_type === 'SEA' || target_province_type === 'COAST';
    }
    return false;
  }

  public abut_list(site: string, incl_no_coast: boolean = false): string[] {
    const siteOriginalCase = this.locs.find(l => l.toUpperCase() === site.toUpperCase()) || site;
    let abut_list: string[] = this.loc_abut[siteOriginalCase] || [];

    if (incl_no_coast) {
        const result_with_no_coast = new Set<string>(abut_list);
        for (const loc of abut_list) {
            if (loc.includes('/')) {
                result_with_no_coast.add(loc.substring(0, 3));
            }
        }
        return Array.from(result_with_no_coast);
    }
    return [...abut_list];
  }

  private _abuts(unit_type: 'A' | 'F' | '?', unit_loc_full: string, order_type: string, other_loc_full: string): boolean {
    unit_loc_full = unit_loc_full.toUpperCase();
    other_loc_full = other_loc_full.toUpperCase();

    if (!this.is_valid_unit(`${unit_type} ${unit_loc_full}`)) {
        return false;
    }

    let effective_other_loc = other_loc_full;
    if (other_loc_full.includes('/')) {
        if (order_type === 'S') {
            effective_other_loc = other_loc_full.substring(0, 3);
        } else if (unit_type === 'A') {
            return false;
        }
    }

    const unitLocOriginalCase = this.locs.find(l => l.toUpperCase() === unit_loc_full) || unit_loc_full;
    const adjacencies = this.loc_abut[unitLocOriginalCase] || [];

    let place_found_in_adj: string | undefined = undefined;
    for (const adj_from_list of adjacencies) {
        const adj_from_list_upper = adj_from_list.toUpperCase();
        const adj_short_upper = adj_from_list_upper.substring(0,3);

        if (effective_other_loc === adj_from_list_upper || effective_other_loc === adj_short_upper) {
            place_found_in_adj = adj_from_list;
            break;
        }
    }

    if (!place_found_in_adj) {
        return false;
    }

    const other_loc_type = this.area_type(effective_other_loc.substring(0,3));
    if (other_loc_type === 'SHUT') return false;
    if (unit_type === '?') return true;

    if (unit_type === 'F') {
        if (other_loc_type === 'LAND') return false;
        if (place_found_in_adj !== place_found_in_adj.toUpperCase()) return false;
    }
    else if (unit_type === 'A') {
        if (order_type !== 'C' && other_loc_type === 'WATER') return false;
        if (place_found_in_adj.length > 0 &&
            place_found_in_adj[0] === place_found_in_adj[0].toUpperCase() &&
            place_found_in_adj.slice(1) === place_found_in_adj.slice(1).toLowerCase() &&
            place_found_in_adj.toUpperCase() !== place_found_in_adj
            ) {
            return false;
        }
    }
    return true;
  }

  public abuts(unit_type: 'A' | 'F' | '?', unit_loc: string, order_type: string, other_loc: string): boolean {
    const queryTuple = `${unit_type},${unit_loc.toUpperCase()},${order_type.toUpperCase()},${other_loc.toUpperCase()}`;
    const cachedResult = this.abuts_cache[queryTuple];
    if (cachedResult !== undefined) {
        return cachedResult === 1;
    }
    logger.warn(`Abuts cache miss for: ${queryTuple}. Calculating on the fly.`);
    return this._abuts(unit_type, unit_loc, order_type, other_loc);
  }


  public phase_abbr(phase: string, defaultVal: string = '?????'): string {
    if (phase === 'FORMING' || phase === 'COMPLETED') {
        return phase;
    }
    const parts = phase.split(' ');
    if (parts.length === 3) {
        try {
            const year = parseInt(parts[1]);
            const yearStr = String(year);
            const yearAbbr = yearStr.length > 2 ? yearStr.slice(-2) : yearStr.padStart(2,'0');

            return (`${parts[0][0]}${yearAbbr}${parts[2][0]}`).toUpperCase();
        } catch (e) { /* fall through to default */ }
    }
    return defaultVal;
  }

  public phase_long(phase_abbr: string, defaultVal: string = '?????'): string {
    if (phase_abbr.length < 4) return defaultVal;
    try {
        const season_char = phase_abbr[0].toUpperCase();
        const year_abbr_str = phase_abbr.substring(1, phase_abbr.length - 1);
        const type_char = phase_abbr[phase_abbr.length -1].toUpperCase();

        let year = parseInt(year_abbr_str, 10);
        if (year < 100) year += 1900;

        for (const season_def of this.seq) {
            const parts = season_def.split(' ');
            if (parts.length === 2 && parts[0][0].toUpperCase() === season_char && parts[1][0].toUpperCase() === type_char) {
                return `${parts[0]} ${year} ${parts[1]}`.toUpperCase();
            }
        }
    } catch(e) { /* fall through */ }
    return defaultVal;
  }

  get svg_path(): string | null {
      for (const file_name of [`${this.name}.svg`, `${this.root_map || this.name}.svg`]) { // Fallback for root_map
          const svg_path = path.join(settings.PACKAGE_DIR, 'maps', 'svg', file_name);
          if (fs.existsSync(svg_path)) return svg_path;
      }
      return null;
  }

  // --- Start of Parsing Utilities ---

  /**
   * Compacts a full sentence into a list of short words (canonical forms).
   * e.g. 'England: Fleet Western Mediterranean -> Tyrrhenian Sea. (*bounce*)'
   * becomes ['ENGLAND', 'F', 'WES', '-', 'TYS', '|'] (example, actual output depends on norm, aliases)
   */
  public compact(phrase: string): string[] {
    let processedPhrase = phrase;
    // Check if first part of phrase (before colon) is a power, and remove it if that's the case.
    const colonIndex = phrase.indexOf(':');
    if (colonIndex !== -1) {
        const firstPart = phrase.substring(0, colonIndex);
        // Recursively call compact and vet to check if it's a power
        const firstPartResult = this.vet(this.compact(firstPart));
        if (firstPartResult.length === 1 && firstPartResult[0][1] === POWER) {
            processedPhrase = phrase.substring(colonIndex + 1);
        }
    }

    // Normalize the phrase (this applies keywords and some basic aliases)
    const normedWords = this.norm(processedPhrase).split(/\s+/).filter(w => w); // Split and remove empty strings
    const result: string[] = [];
    let currentWords = normedWords;

    while (currentWords.length > 0) {
        const [aliasFound, wordsConsumed] = this.alias(currentWords);
        if (aliasFound) {
            // aliasFound might be multiple words itself if an alias maps to "word1 word2"
            result.push(...aliasFound.split(/\s+/).filter(w => w));
        } else if (currentWords.length > 0 && wordsConsumed === 0) {
            // Safety: if alias consumes 0 words, manually advance to prevent infinite loop
            result.push(currentWords[0]);
            currentWords = currentWords.slice(1);
            continue;
        } else if (!aliasFound && wordsConsumed > 0 && currentWords.length > 0) {
           // This case means words were consumed (e.g. brackets) but no specific alias string was returned.
           // The words are already sliced based on wordsConsumed.
        }


        if (wordsConsumed > 0) {
             currentWords = currentWords.slice(wordsConsumed);
        } else if (currentWords.length > 0) {
            logger.warn("Stuck in compact, word not consumed:", currentWords[0]);
            result.push(currentWords[0]);
            currentWords = currentWords.slice(1);
        }
    }
    return result;
  }

  /**
   * Replaces multi-word sequences with their acronyms/aliases.
   * Processes one alias at a time from the start of the `word` array.
   * @param words - The current list of words (assumed to be normed individually but not yet multi-word aliased).
   * @returns [alias, wordsConsumed] - alias is the shortened string (can be multiple words if alias maps to that),
   *          wordsConsumed is the number of words from the input `words` array that were consumed.
   */
  private alias(words: string[]): [string | null, number] {
    if (!words || words.length === 0) {
        return [null, 0];
    }

    const firstWord = words[0];
    if (firstWord === '(' || firstWord === '[') {
        const closingBracket = firstWord === '(' ? ')' : ']';
        let j = -1;
        for (let k = 1; k < words.length; k++) {
            if (words[k] === closingBracket) {
                j = k;
                break;
            }
        }
        if (j !== -1) {
            if (j === 1) return [null, 2];

            const contentInsideBrackets = words.slice(1, j);
            // Python's alias logic for content within brackets is recursive and complex,
            // especially with `word2 = word[2:j - 1]` if `word[1] + word[j - 1] == '**'`
            // and `alias2 = self.aliases.get(' '.join(word2) + ' \\', '')`.
            // For simplicity, we join the content and recursively call `compact` then `vet`.
            // This might not perfectly replicate extremely specific DAIDE sub-dialect parsing within brackets.
            const compactedContent = this.compact(contentInsideBrackets.join(' '));
            return [compactedContent.join(' '), j + 1]; // Return processed content and consumed length
        } else {
            return [this._resolve_unclear(firstWord), 1];
        }
    }


    for (let i = words.length; i > 0; i--) {
        const key = words.slice(0, i).join(' ');
        if (this.aliases[key]) {
            let aliasValue = this.aliases[key];
            if (i < words.length) {
                const nextWord = words[i];
                if (nextWord.startsWith('/') && aliasValue.length === 3 && /^[A-Z]{3}$/.test(aliasValue)) {
                    const combined = aliasValue + nextWord;
                    const isKnownCombinedLocation = this.locs.includes(combined) ||
                                                 Object.values(this.aliases).includes(combined) ||
                                                 this.loc_name[combined.toUpperCase()]; // Check if combined is a full name for an abbrev
                    if (isKnownCombinedLocation) {
                        return [this._resolve_unclear(combined), i + 1];
                    }
                }
            }
            return [this._resolve_unclear(aliasValue), i];
        }
    }

    return [this._resolve_unclear(words[0]), 1];
  }

  /**
   * Resolves if an alias might be an unclear power name (e.g. "ENG" could be England or ECH).
   * If `alias` is in `this.powers` and also in `this.unclear`, returns the unclear mapping.
   * Otherwise, returns the alias unchanged.
   */
  private _resolve_unclear(alias: string): string {
    const ucAlias = alias.toUpperCase();
    if (this.powers.includes(ucAlias) && this.unclear[ucAlias]) {
        return this.unclear[ucAlias];
    }
    return alias;
  }

  /**
   * Determines the type of every word in a compacted order phrase.
   * Types: 0-Undetermined, 1-Power, 2-Unit, 3-Location, 4-Coastal loc, 5-Order, 6-Move Op, 7-Other.
   * @param word - The list of words to vet (e.g., ['A', 'POR', 'S', 'SPA/NC']).
   * @param strict - If true, verifies words exist (not fully implemented here like Python's negative types).
   * @returns A list of tuples (e.g., [['A', 2], ['POR', 3], ['S', 5], ['SPA/NC', 4]]).
   */
  public vet(word: string[], strict: boolean = false): Array<[string, number]> {
    const result: Array<[string, number]> = [];
    for (const thing of word) {
        let dataType: number;
        const ucThing = thing.toUpperCase();

        if (ucThing.includes(' ')) {
            dataType = UNDETERMINED;
        } else if (ucThing.length === 1) {
            if (this.unit_names[ucThing]) dataType = UNIT;
            else if (/[A-Z0-9]/.test(ucThing)) dataType = ORDER; // S, H, C, R, D, B. M gets converted to '-' by norm usually.
            else if ('-=_^'.includes(ucThing)) dataType = MOVE_SEP;
            else dataType = OTHER; // | * ? ! ~ + ( ) [ ] handled by alias method usually
        } else if (ucThing.includes('/')) {
            // Standard coast: 3-letter loc + / + 2-letter coast = 6 chars (e.g., STP/SC)
            if (ucThing.indexOf('/') === 3 && ucThing.length === 6 && /^[A-Z]{2}$/.test(ucThing.substring(4))) {
                 dataType = COAST;
            } else {
                 dataType = POWER; // Or malformed/unrecognized
            }
        } else if (ucThing === 'VIA') {
            dataType = ORDER;
        } else if (ucThing.length === 3 && /^[A-Z]{3}$/.test(ucThing)) {
            // Could be a location or a 3-letter power name.
            // Prioritize known locations. If not a location, might be a power.
            if (this.locs.includes(ucThing) || Object.values(this.aliases).includes(ucThing)) { // Check if it's a known loc abbrev
                dataType = LOCATION;
            } else if (this.powers.includes(this.norm_power(ucThing))) { // Check if it's a known power
                dataType = POWER;
            } else { // Default to LOCATION for 3-letter words not immediately ID'd as powers (as per Python's bias)
                dataType = LOCATION;
            }
        } else {
            const normedPower = this.norm_power(ucThing);
            if (this.powers.includes(normedPower)) {
                 dataType = POWER;
            } else if (this.aliases[ucThing] && this.locs.includes(this.aliases[ucThing].toUpperCase())) {
                 dataType = LOCATION;
            } else { // Default to POWER for multi-char unknown tokens (Python's default)
                 dataType = POWER;
            }
        }
        result.push([thing, dataType]);
    }
    return result;
  }

  /**
   * This function is used to parse commands by rearranging vetted words.
   * @param words The list of *strings* to be vetted and rearranged.
   * @return The list of words (strings) in the correct order to be processed.
   */
  public rearrange(words: string[]): string[] {
    let resultTuples = this.vet(['|', ...words, '|']);

    if (resultTuples.length > 0) resultTuples[0] = ['|', UNDETERMINED];
    while (resultTuples.length > 2 && resultTuples[resultTuples.length - 2][1] === OTHER) {
        resultTuples.splice(resultTuples.length - 2, 1);
    }
    if (resultTuples.length === 2 && resultTuples[0][0] === '|' && resultTuples[1][0] === '|') return [];

    if (resultTuples.length > 0) resultTuples[0] = ['|', OTHER];
    while (resultTuples.length > 1 && resultTuples[1][1] === OTHER) {
        resultTuples.splice(1, 1);
    }

    // Simplified reordering:
    // 1. Power before Unit
    // 2. Order after Unit + Location(s)
    // 3. Hyphens between locations

    // Power before Unit
    for (let i = 1; i < resultTuples.length -1; i++) { // Skip placeholders
        if (resultTuples[i][1] === POWER && i > 0 && resultTuples[i-1][1] === UNIT) {
            const powerToken = resultTuples.splice(i,1)[0];
            resultTuples.splice(i-1, 0, powerToken);
        } else if (resultTuples[i][1] === POWER && resultTuples[i][0].toUpperCase() in this.unclear && resultTuples[i-1][1] === UNIT) {
            // If power is unclear and follows a unit, it's a location.
            resultTuples[i] = [this.unclear[resultTuples[i][0].toUpperCase()], LOCATION];
        }
    }

    // Order after Unit + Location(s)
    // This is complex. Python's logic involves multiple passes and specific token handling.
    // A simplified approach: find the primary unit-location block, then move the main order token.
    let firstUnitIdx = -1, firstLocIdx = -1, lastLocIdx = -1, orderIdx = -1;
    for (let i = 1; i < resultTuples.length -1; i++) {
        const type = resultTuples[i][1];
        if (type === UNIT && firstUnitIdx === -1) firstUnitIdx = i;
        else if ((type === LOCATION || type === COAST)) {
            if (firstLocIdx === -1) firstLocIdx = i;
            lastLocIdx = i;
        } else if (type === ORDER && orderIdx === -1) {
            orderIdx = i;
        }
    }

    if (orderIdx !== -1 && lastLocIdx !== -1 && orderIdx < lastLocIdx) {
        // If order is before the end of the location sequence it applies to.
        // e.g. A PAR S BUD -> A PAR BUD S (if S is the main order)
        // This needs to distinguish main order (H,S,M,C) from sub-orders like VIA.
        // For simplicity, if an ORDER token is before the last location of a unit spec, move it after.
        const orderTokenToMove = resultTuples.splice(orderIdx, 1)[0];
        resultTuples.splice(lastLocIdx + 1, 0, orderTokenToMove);
    }


    // Insert hyphens ('-') between subsequent locations if no other operator/order is present
    const finalResultWithHyphens: Array<[string, number]> = [];
    if (resultTuples.length > 0) finalResultWithHyphens.push(resultTuples[0]);

    for (let i = 1; i < resultTuples.length; i++) {
        const prevTokenTuple = finalResultWithHyphens[finalResultWithHyphens.length -1];
        const currentTokenTuple = resultTuples[i];

        const prevType = prevTokenTuple[1];
        const currentType = currentTokenTuple[1];

        if ((prevType === LOCATION || prevType === COAST) &&
            (currentType === LOCATION || currentType === COAST)) {
            finalResultWithHyphens.push(['-', MOVE_SEP]);
        }
        finalResultWithHyphens.push(currentTokenTuple);
    }
    resultTuples = finalResultWithHyphens;

    if (resultTuples.length > 0 && resultTuples[0][0] === '|') resultTuples.shift();
    if (resultTuples.length > 0 && resultTuples[resultTuples.length - 1][0] === '|') resultTuples.pop();

    return resultTuples.map(item => item[0]);
  }

  /**
   * Returns the default coast for a fleet move order that can only be to a single coast.
   * e.g. F GRE - BUL returns F GRE - BUL/SC (if BUL/SC is the only valid fleet move from GRE to BUL area)
   * @param word - A list of tokens (e.g. ['F', 'GRE', '-', 'BUL'])
   * @returns The updated list of tokens (e.g. ['F', 'GRE', '-', 'BUL/SC'])
   */
  public default_coast(word: string[]): string[] {
    if (word.length === 4 && word[0].toUpperCase() === 'F' && word[2] === '-' && !word[3].includes('/')) {
        const unit_loc_uc = word[1].toUpperCase();
        const target_loc_base_uc = word[3].toUpperCase();
        let single_matching_coast: string | null = null;
        let multiple_options_exist = false;

        const adjacencies = this.loc_abut[unit_loc_uc] || [];

        for (const adj_loc_canon of adjacencies) {
            if (adj_loc_canon.startsWith(target_loc_base_uc)) {
                if (this._abuts('F', unit_loc_uc, '-', adj_loc_canon)) {
                    if (adj_loc_canon.includes('/')) {
                        if (single_matching_coast && single_matching_coast !== adj_loc_canon) {
                            multiple_options_exist = true; break;
                        }
                        single_matching_coast = adj_loc_canon;
                    } else {
                        if (single_matching_coast && single_matching_coast.includes('/')) {
                            // Already found a specific coast (e.g. BUL/SC), and now found base (BUL). Ambiguous.
                            multiple_options_exist = true; break;
                        }
                        // If current single_matching_coast is null, or is the same base, or is different base (error in logic before)
                        // This path means base province itself is a valid destination.
                        if (single_matching_coast && single_matching_coast !== adj_loc_canon) {
                             multiple_options_exist = true; break;
                        }
                        single_matching_coast = adj_loc_canon;
                    }
                }
            }
        }
        if (single_matching_coast && !multiple_options_exist && single_matching_coast.includes('/')) {
            word[3] = single_matching_coast;
        }
    }
    return word;
  }

  // --- End of Parsing Utilities ---

  public find_next_phase(phase: string, phase_type: string | null = null, skip: number = 0): string {
    const now = phase.split(' ');
    if (now.length < 3) return phase; // Cannot determine next for FORMING/COMPLETED or malformed

    let year = parseInt(now[1], 10);
    const currentPhaseKey = `${now[0].toUpperCase()} ${now[2].toUpperCase()}`;
    let currentPhaseIndex = this.seq.findIndex(s => s === currentPhaseKey);

    if (currentPhaseIndex === -1) {
        logger.warn(`Current phase key '${currentPhaseKey}' not found in sequence: ${this.seq.join(', ')}`);
        return ''; // Phase not in sequence
    }

    let phasesToSkip = skip;
    let iterations = 0; // Safety break for very long sequences or weird skips

    // eslint-disable-next-line no-constant-condition
    while (true) {
        iterations++;
        if (iterations > this.seq.length * (phasesToSkip + 2) + 5) { // Safety break
             logger.error("find_next_phase exceeded max iterations, possible infinite loop with SEQ/skip logic.");
             return '';
        }

        currentPhaseIndex = (currentPhaseIndex + 1) % this.seq.length;
        const nextPhaseParts = this.seq[currentPhaseIndex].split(' '); // e.g., ["SPRING", "MOVEMENT"] or ["NEWYEAR"]

        if (nextPhaseParts[0] === 'IFYEARDIV') {
            // Not fully implemented from Python's complex IFYEARDIV with mod check.
            // For now, assume it means skip this seq entry if year doesn't meet a condition.
            // This would require parsing new[1] like "2" or "2=0" (div, mod)
            // Simple skip for now.
            continue;
        } else if (nextPhaseParts[0] === 'NEWYEAR') {
            year += (nextPhaseParts.length > 1 ? parseInt(nextPhaseParts[1], 10) : 1);
        } else { // Regular phase (e.g., SPRING MOVEMENT)
            const nextPhaseFullType = nextPhaseParts[1]; // e.g. MOVEMENT
            const nextPhaseSeason = nextPhaseParts[0];   // e.g. SPRING

            // Check if this phase matches the desired phase_type (M, R, A)
            if (phase_type === null || (nextPhaseFullType && nextPhaseFullType[0].toUpperCase() === phase_type.toUpperCase())) {
                if (phasesToSkip === 0) {
                    return `${nextPhaseSeason} ${year} ${nextPhaseFullType}`;
                }
                phasesToSkip--;
            }
        }
    }
  }

  public find_previous_phase(phase: string, phase_type: string | null = null, skip: number = 0): string {
    const now = phase.split(' ');
    if (now.length < 3) return phase;

    let year = parseInt(now[1], 10);
    const currentPhaseKey = `${now[0].toUpperCase()} ${now[2].toUpperCase()}`;
    let currentPhaseIndex = this.seq.findIndex(s => s === currentPhaseKey);

    if (currentPhaseIndex === -1) {
        logger.warn(`Current phase key '${currentPhaseKey}' not found in sequence: ${this.seq.join(', ')}`);
        return '';
    }

    let phasesToSkip = skip;
    let iterations = 0;

    // eslint-disable-next-line no-constant-condition
    while (true) {
        iterations++;
        if (iterations > this.seq.length * (phasesToSkip + 2) + 5) {
             logger.error("find_previous_phase exceeded max iterations.");
             return '';
        }

        currentPhaseIndex = (currentPhaseIndex - 1 + this.seq.length) % this.seq.length;
        const prevPhaseParts = this.seq[currentPhaseIndex].split(' ');

        if (prevPhaseParts[0] === 'IFYEARDIV') {
            // Similar to find_next_phase, complex IFYEARDIV logic not fully ported.
            // This directive affects phase progression based on year divisibility.
            // For now, just moving past it. A full implementation would adjust 'year' or loop.
            continue;
        } else if (prevPhaseParts[0] === 'NEWYEAR') {
            year -= (prevPhaseParts.length > 1 ? parseInt(prevPhaseParts[1], 10) : 1);
        } else { // Regular phase
            const prevPhaseFullType = prevPhaseParts[1];
            const prevPhaseSeason = prevPhaseParts[0];

            if (phase_type === null || (prevPhaseFullType && prevPhaseFullType[0].toUpperCase() === phase_type.toUpperCase())) {
                if (phasesToSkip === 0) {
                    return `${prevPhaseSeason} ${year} ${prevPhaseFullType}`;
                }
                phasesToSkip--;
            }
        }
    }
  }

  public compare_phases(phase1_str: string, phase2_str: string): number {
    let p1 = phase1_str;
    let p2 = phase2_str;

    // Handle 'S1901?' type abbreviations if necessary (Python specific)
    // My phase_long and phase_abbr handle standard forms. Assume inputs are full or S1901M style.

    if (p1.split(' ').length === 1 && p1 !== 'FORMING' && p1 !== 'COMPLETED') {
        p1 = this.phase_long(p1, p1); // Convert S1901M to SPRING 1901 MOVEMENT
    }
    if (p2.split(' ').length === 1 && p2 !== 'FORMING' && p2 !== 'COMPLETED') {
        p2 = this.phase_long(p2, p2);
    }

    if (p1 === p2) return 0;

    const p1_parts = p1.split(' ');
    const p2_parts = p2.split(' ');

    // Handle FORMING and COMPLETED states
    const getPhaseOrderVal = (parts: string[], fullStr: string): number => {
        if (parts.length < 3) {
            if (fullStr === 'FORMING') return 1;
            if (fullStr === 'COMPLETED') return 3;
            return 0; // Unknown
        }
        return 2; // Normal phase
    };

    const order1 = getPhaseOrderVal(p1_parts, p1);
    const order2 = getPhaseOrderVal(p2_parts, p2);

    if (order1 !== order2) {
        return order1 > order2 ? 1 : -1;
    }
    if (order1 !== 2) return 0; // Both are FORMING or COMPLETED and equal, or both unknown and equal

    // Both are normal phases, compare year then season index
    const year1 = parseInt(p1_parts[1], 10);
    const year2 = parseInt(p2_parts[1], 10);

    if (year1 !== year2) {
        return (year1 > year2 ? 1 : -1) * (this.flow_sign || 1);
    }

    // Years are the same, compare season index based on this.seq
    const phaseKey1 = `${p1_parts[0].toUpperCase()} ${p1_parts[2].toUpperCase()}`;
    const phaseKey2 = `${p2_parts[0].toUpperCase()} ${p2_parts[2].toUpperCase()}`;

    const index1 = this.seq.findIndex(s => s === phaseKey1);
    const index2 = this.seq.findIndex(s => s === phaseKey2);

    if (index1 === -1 || index2 === -1) {
        logger.warn("Phase comparison with phase not in sequence:", phaseKey1, phaseKey2, this.seq);
        return 0; // Cannot compare if one is not in sequence
    }

    // Python's logic for NEWYEAR between seasons is complex:
    // if season_ix1 > season_ix2: return -1 if 'NEWYEAR' in [x.split()[0] for x in self.seq[(season_ix2) + (1):season_ix1]] else 1
    // This implies if NEWYEAR is crossed, the order inverts for that year.
    // This is typically handled by the year increment/decrement in find_next/prev_phase.
    // A direct comparison of indices within the same year should be sufficient here.
    if (index1 > index2) return 1 * (this.flow_sign || 1);
    if (index1 < index2) return -1 * (this.flow_sign || 1);

    return 0;
  }


  public phase_abbr(phase: string, defaultVal: string = '?????'): string {
