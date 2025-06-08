// diplomacy/engine/map.ts

import * as fs from 'fs';
import * as path from 'path';
import { Buffer } from 'buffer'; // Not directly used yet, but good for general Node.js context

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

const KEYWORDS: Record<string, string> = { /* Populate with actual KEYWORDS */ };
const ALIASES: Record<string, string> = { /* Populate with actual ALIASES */ };

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
};

interface ConvoyPathData { /* ... */ }
const CONVOYS_PATH_CACHE: Record<string, ConvoyPathData> = {};
const get_convoy_paths_cache = (): Record<string, ConvoyPathData> => CONVOYS_PATH_CACHE;
const add_to_cache = (name: string): ConvoyPathData => { return {}; };

const UNDETERMINED = 0, POWER = 1, UNIT = 2, LOCATION = 3, COAST = 4, ORDER = 5, MOVE_SEP = 6, OTHER = 7;
const MAP_CACHE: Record<string, DiplomacyMap> = {};

export class DiplomacyMap {
  name: string;
  first_year: number = 1901;
  victory: number[] | null = null;
  phase: string | null = null;
  validated: number | null = null;
  flow_sign: number | null = null;
  root_map: string | null = null;
  abuts_cache: Record<string, number> = {};

  homes: Record<string, string[]> = {};
  loc_name: Record<string, string> = {};
  loc_type: Record<string, string> = {};
  loc_abut: Record<string, string[]> = {};
  loc_coasts: Record<string, string[]> = {};

  own_word: Record<string, string> = {};
  abbrev: Record<string, string> = {};
  centers: Record<string, string[]> = {};
  units: Record<string, string[]> = {};

  pow_name: Record<string, string> = {};
  rules: string[] = [];
  files: string[] = [];
  powers: string[] = [];
  scs: string[] = [];
  owns: string[] = [];
  inhabits: string[] = [];
  flow: string[] = [];
  dummies: string[] = [];
  locs: string[] = [];
  error: string[] = [];
  seq: string[] = [];
  phase_abbrev: Record<string, string> = {};

  unclear: Record<string, string> = {};
  unit_names: Record<string, string> = {'A': 'ARMY', 'F': 'FLEET'};
  keywords: Record<string, string>;
  aliases: Record<string, string>;

  convoy_paths: ConvoyPathData = {};
  dest_with_coasts: Record<string, string[]> = {};

  constructor(name: string = 'standard', use_cache: boolean = true) {
    if (use_cache && MAP_CACHE[name]) {
      Object.assign(this, MAP_CACHE[name]);
      return;
    }
    this.name = name;
    this.keywords = { ...KEYWORDS };
    this.aliases = { ...ALIASES };

    this.load();
    this.build_cache();
    this.validate();

    if (CONVOYS_PATH_CACHE[name]) {
        this.convoy_paths = CONVOYS_PATH_CACHE[name];
    } else if (use_cache) {
        CONVOYS_PATH_CACHE[name] = add_to_cache(name);
        this.convoy_paths = CONVOYS_PATH_CACHE[name];
    } else {
        this.convoy_paths = add_to_cache(name);
    }

    if (use_cache) {
      MAP_CACHE[name] = this;
    }
  }

  public load(file_name?: string): void {
    const effective_file_name = file_name || (this.name.endsWith('.map') ? this.name : `${this.name}.map`);
    let file_path: string;

    if (fs.existsSync(effective_file_name)) {
        file_path = effective_file_name;
    } else {
        file_path = path.join(settings.PACKAGE_DIR, 'maps', effective_file_name);
    }

    logger.info(`Loading map from: ${file_path}`);

    if (!fs.existsSync(file_path)) {
        this.error.push(err.MAP_FILE_NOT_FOUND.replace('%s', effective_file_name));
        logger.error(this.error[this.error.length-1]);
        return;
    }

    this.files.push(effective_file_name);

    const fileContent = fs.readFileSync(file_path, 'utf-8');
    const lines = fileContent.split(/\r?\n/);

    let current_power_context: string | null = null;
    let current_power_original_case: string | null = null;


    for (const line of lines) {
        const trimmedLine = line.trim();
        if (!trimmedLine || trimmedLine.startsWith('#')) {
            continue;
        }

        const words = trimmedLine.split(/\s+/);
        const directive = words[0].toUpperCase();

        switch (directive) {
            case 'VICTORY':
                try {
                    this.victory = words.slice(1).map(Number);
                    if (this.victory.some(isNaN)) throw new Error("Invalid number in VICTORY line");
                } catch { this.error.push(err.MAP_BAD_VICTORY_LINE); }
                break;
            case 'MAP':
                if (words.length !== 2) this.error.push(err.MAP_BAD_ROOT_MAP_LINE);
                else if (this.root_map) this.error.push(err.MAP_TWO_ROOT_MAPS);
                else this.root_map = words[1].split('.')[0];
                break;
            case 'USE': case 'USES':
                for (const new_file_to_include of words.slice(1)) {
                    let sub_file_name = new_file_to_include;
                    if (!sub_file_name.includes('.')) sub_file_name += '.map';
                    if (!this.files.includes(sub_file_name)) this.load(sub_file_name);
                    else this.error.push(err.MAP_FILE_MULT_USED.replace('%s', new_file_to_include));
                }
                break;
            case 'BEGIN':
                this.phase = words.slice(1).join(' ').toUpperCase();
                break;
            case 'UNITS': // Clear units for current power context
                if (current_power_context) this.units[current_power_context] = [];
                else this.error.push(err.MAP_UNITS_BEFORE_POWER);
                break;
            default:
                if (line.includes('=')) { // Location definition
                    const parts = trimmedLine.split('=');
                    if (parts.length !== 2) { this.error.push(err.MAP_BAD_ALIASES_IN_FILE.replace('%s', trimmedLine)); continue; }
                    const nameAndOldName = parts[0].trim(); const abbrevAndAliases = parts[1].trim().split(/\s+/);
                    const abbrev = abbrevAndAliases[0]; const aliases = abbrevAndAliases.slice(1);
                    const fullName = nameAndOldName; const normedFullName = this.norm(fullName);
                    if (this.keywords[fullName.toUpperCase()]) this.error.push(err.MAP_LOC_RESERVED_KEYWORD.replace('%s', fullName));

                    const abbrevUpper = abbrev.toUpperCase();
                    if (this.loc_name[fullName.toUpperCase()] || this.aliases[normedFullName.toUpperCase()] === abbrevUpper) {
                        if(this.loc_name[fullName.toUpperCase()] !== abbrevUpper || this.aliases[normedFullName.toUpperCase()] !== abbrevUpper)
                           this.error.push(err.MAP_DUP_LOC_OR_POWER.replace('%s', fullName));
                    } else {
                        this.loc_name[fullName.toUpperCase()] = abbrevUpper;
                        this.aliases[normedFullName.toUpperCase()] = abbrevUpper;
                        if (!this.locs.map(l=>l.toUpperCase()).includes(abbrevUpper)) this.locs.push(abbrev); // Store original case for locs list
                    }
                    aliases.forEach(alias => {
                        const isUnclear = alias.endsWith('?'); const cleanAlias = isUnclear ? alias.slice(0, -1) : alias;
                        const normedAlias = this.norm(cleanAlias);
                        if (isUnclear) this.unclear[normedAlias.toUpperCase()] = abbrevUpper;
                        else if (this.aliases[normedAlias.toUpperCase()] && this.aliases[normedAlias.toUpperCase()] !== abbrevUpper)
                            this.error.push(err.MAP_DUP_ALIAS_OR_POWER.replace('%s', alias));
                        else this.aliases[normedAlias.toUpperCase()] = abbrevUpper;
                    });
                } else if (['AMEND', 'WATER', 'LAND', 'COAST', 'PORT', 'SHUT'].includes(directive)) { // Terrain
                    if (words.length < 2) { this.error.push(`Malformed terrain: ${trimmedLine}`); continue; }
                    const place = words[1]; const placeUpper = place.toUpperCase(); const shortPlace = placeUpper.substring(0,3);
                    if (!this.locs.find(l=>l.toUpperCase() === placeUpper)) this.locs.push(place);
                    if(!this.loc_name[placeUpper]) this.loc_name[placeUpper] = shortPlace;

                    if (directive !== 'AMEND') this.loc_type[shortPlace] = directive;
                    else if (!this.loc_type[shortPlace]) this.error.push(err.MAP_NO_DATA_TO_AMEND_FOR.replace('%s', place));

                    this.loc_abut[place] = this.loc_abut[place] || [];
                    if (words.length > 2 && words[2].toUpperCase() === 'ABUTS') {
                        for (const dest of words.slice(3)) {
                            if (dest.startsWith('-')) {
                                const toRemove = dest.substring(1).toUpperCase();
                                this.loc_abut[place] = this.loc_abut[place].filter(adj => !adj.toUpperCase().startsWith(toRemove));
                            } else this.loc_abut[place].push(dest);
                        }
                    } else if (words.length > 2 && directive !== 'AMEND') this.error.push(err.MAP_NO_ABUTS_FOR.replace('%s', place));
                } else if (words.length > 0 && (this.keywords[directive] || ALIASES[directive] || this.pow_name[this.norm_power(directive)] || ['UNOWNED', 'NEUTRAL', 'CENTERS'].includes(directive))) { // Power or power-related
                    current_power_original_case = words[0]; // Store original case for own_word, abbrev
                    current_power_context = (directive === "UNOWNED" || directive === "NEUTRAL" || directive === "CENTERS") ? "UNOWNED" : this.norm_power(directive);

                    if (current_power_context !== "UNOWNED") {
                        if (!this.powers.includes(current_power_context)) {
                            this.powers.push(current_power_context);
                            this.pow_name[current_power_context] = current_power_original_case;
                            this.aliases[this.norm(current_power_original_case).toUpperCase()] = current_power_context;
                        }
                        // Handle (ownWord:abbrev)
                        if (words.length > 1 && words[1].startsWith('(') && words[1].endsWith(')')) {
                            const special = words[1].slice(1, -1);
                            const parts = special.split(':');
                            this.own_word[current_power_context] = parts[0] || current_power_original_case;
                            if (parts.length > 1) this.abbrev[current_power_context] = parts[1].substring(0,1).toUpperCase();
                            words.splice(1,1); // Remove processed part
                        } else {
                             this.own_word[current_power_context] = this.own_word[current_power_context] || current_power_original_case;
                        }
                         this.add_homes(current_power_context, words.slice(1), !this.inhabits.includes(current_power_context));
                         if (!this.inhabits.includes(current_power_context)) this.inhabits.push(current_power_context);

                    } else { // UNOWNED, NEUTRAL, CENTERS - implies homes for UNOWNED
                         this.add_homes("UNOWNED", words.slice(1), !this.inhabits.includes("UNOWNED"));
                         if (!this.inhabits.includes("UNOWNED")) this.inhabits.push("UNOWNED");
                    }
                } else if (current_power_context && (directive === 'A' || directive === 'F') && words.length === 2) { // Unit
                    const unitLoc = words[1].toUpperCase(); const unitString = `${directive} ${unitLoc}`;
                    this.units[current_power_context] = this.units[current_power_context] || [];
                    this.units[current_power_context] = this.units[current_power_context].filter(u => u.substring(2) !== unitLoc);
                    this.units[current_power_context].push(unitString);
                } else if (current_power_context && (directive === 'OWNS' || (current_power_context==="UNOWNED" && directive === 'CENTERS'))) {
                     const power_to_update_centers = current_power_context; // OWNS is under a power, CENTERS is for UNOWNED here
                     if (!this.owns.includes(power_to_update_centers)) this.owns.push(power_to_update_centers);
                     const centersOwned = words.slice(1).map(c => c.toUpperCase().substring(0,3));
                     if (directive === 'CENTERS' || !this.centers[power_to_update_centers]) this.centers[power_to_update_centers] = centersOwned;
                     else centersOwned.forEach(c => { if (!this.centers[power_to_update_centers].includes(c)) this.centers[power_to_update_centers].push(c); });
                } else if (current_power_context && (directive === 'INHABITS' || directive === 'HOME' || directive === 'HOMES')) {
                    let reinitializeHomes = directive === 'HOME' || directive === 'HOMES';
                    if (!this.inhabits.includes(current_power_context)) {
                        this.inhabits.push(current_power_context);
                        reinitializeHomes = true;
                    }
                    this.add_homes(current_power_context, words.slice(1), reinitializeHomes);
                }
                break;
        }
    }
    this.root_map = this.root_map || this.name.split('.')[0];
    this.phase = this.phase || 'SPRING 1901 MOVEMENT';
    if (this.flow.length === 0) this.flow = ['SPRING:MOVEMENT,RETREATS', 'FALL:MOVEMENT,RETREATS', 'WINTER:ADJUSTMENTS'];
    if (this.flow_sign === null) this.flow_sign = 1;
    if (this.seq.length === 0) this.seq = ['NEWYEAR', 'SPRING MOVEMENT', 'SPRING RETREATS', 'FALL MOVEMENT', 'FALL RETREATS', 'WINTER ADJUSTMENTS'];
    if (Object.keys(this.phase_abbrev).length === 0) this.phase_abbrev = {'M': 'MOVEMENT', 'R': 'RETREATS', 'A': 'ADJUSTMENTS'};

    logger.info(`Finished loading map: ${this.name}. Found ${this.locs.length} locations, ${this.powers.length} powers.`);
    if(this.error.length > 0) logger.warn("Errors during map load:", this.error.join("\n"));
  }

  public build_cache(): void {
    logger.info("Building map cache (loc_coasts, abuts_cache, dest_with_coasts)...");
    const temp_loc_coasts: Record<string, Set<string>> = {};
    for (const loc of this.locs) {
        const locUpper = loc.toUpperCase();
        const shortName = locUpper.substring(0, 3);
        if (!temp_loc_coasts[shortName]) {
            temp_loc_coasts[shortName] = new Set();
        }
        temp_loc_coasts[shortName].add(locUpper);
        temp_loc_coasts[shortName].add(shortName);
    }
    for (const shortName in temp_loc_coasts) {
        this.loc_coasts[shortName] = Array.from(temp_loc_coasts[shortName]).sort();
    }

    const unitTypesToCache = ['A', 'F'] as const;
    const orderTypesToCache = ['-', 'S', 'C'];

    const allMapLocationsToCache = new Set<string>();
    this.locs.forEach(loc => {
        const ucLoc = loc.toUpperCase();
        allMapLocationsToCache.add(ucLoc);
        if (ucLoc.includes('/')) {
            allMapLocationsToCache.add(ucLoc.substring(0,3));
        } else { // For non-coasted locs, ensure their short form (which is themselves) is present
            allMapLocationsToCache.add(ucLoc.substring(0,3));
        }
    });
    // Also add all loc_names derived from aliases, as they might be used in _abuts
    Object.values(this.loc_name).forEach(shortName => allMapLocationsToCache.add(shortName));


    for (const unit_type of unitTypesToCache) {
        for (const unit_loc_full of allMapLocationsToCache) {
            for (const other_loc_full of allMapLocationsToCache) {
                for (const order_type of orderTypesToCache) {
                    const queryTuple = `${unit_type},${unit_loc_full},${order_type},${other_loc_full}`;
                    this.abuts_cache[queryTuple] = this._abuts(unit_type, unit_loc_full, order_type, other_loc_full) ? 1 : 0;
                }
            }
        }
    }

    for (const loc_full of allMapLocationsToCache) {
        const dest_1_hops_mixed_case = this.abut_list(loc_full, true);
        const dest_1_hops_upper = dest_1_hops_mixed_case.map(d => d.toUpperCase());

        const destinationsWithAllTheirCoasts = new Set<string>();
        for (const dest_upper of dest_1_hops_upper) {
            const shortDest = dest_upper.substring(0,3);
            (this.loc_coasts[shortDest] || [dest_upper]).forEach(coastVariant => destinationsWithAllTheirCoasts.add(coastVariant));
        }
        this.dest_with_coasts[loc_full] = Array.from(destinationsWithAllTheirCoasts).sort();
    }
    logger.info("Map cache built.");
  }

  public validate(force: boolean = false): void {
    if (!force && this.validated) return;
    logger.info("Validating map data...");
    // ... Extensive validation logic from Python ...
    // This is a large method, for now, just mark as validated.
    this.validated = 1;
    if (this.error.length > 0) {
        logger.error("Map validation found errors (original errors from load):", this.error.join("\n"));
    }
    logger.warn("Map.validate() is a simplified stub. Full validation logic not implemented.");
  }

  // --- Utility and Info Methods ---
  public norm(phrase: string): string {
    let result = phrase.toUpperCase().replace(/\//g, ' /');
    result = result.replace(/ \/ /g, '/');

    const tokensToRemove = /[\.:\-\+,]/g;
    result = result.replace(tokensToRemove, ' ');

    const tokensToSpaceAround = /[\|\*\?!~\(\)\[\]=_^]/g;
    result = result.replace(tokensToSpaceAround, (match) => ` ${match} `);

    result = result.trim().split(/\s+/).map(keyword => this.keywords[keyword.toUpperCase()] || keyword).join(' ');
    return result;
  }

  public norm_power(power: string): string {
    return this.norm(power).replace(/ /g, '');
  }

  public area_type(loc: string): string | undefined {
    const upperLoc = loc.toUpperCase();
    // Ensure loc is treated as short name for loc_type lookup
    const shortLoc = upperLoc.substring(0,3);
    return this.loc_type[shortLoc];
  }

  public add_homes(power: string, homes_to_add: string[], reinit: boolean): void {
    const powerKey = this.norm_power(power).toUpperCase(); // Normalize for consistency

    if (reinit || !this.homes[powerKey]) {
        this.homes[powerKey] = [];
    }
    this.homes['UNOWNED'] = this.homes['UNOWNED'] || [];

    for (let home of homes_to_add) {
        let originalHomeSyntax = home; // For logging or error messages if needed
        let remove = false;
        while (home.startsWith('-')) {
            remove = !remove;
            home = home.substring(1);
        }
        home = home.toUpperCase().substring(0,3); // Normalize to short upper case
        if (!home) continue;

        // Remove from current power's homes if it exists
        const currentIdx = this.homes[powerKey].indexOf(home);
        if (currentIdx > -1) {
            this.homes[powerKey].splice(currentIdx, 1);
        }

        // Always ensure it's not in UNOWNED if being claimed or manipulated by a specific power
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
            // If explicitly removed from a specific power, and it's an SC, it becomes UNOWNED
            // (unless 'powerKey' was 'UNOWNED' itself, in which case it's just removed from there).
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

    const shortLocForTypeLookup = loc.substring(0,3); // Use base province for area_type
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
    const adjacencies = this.loc_abut[unitLocOriginalCase] || []; // Use original case key for loc_abut

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
        // Python: place[0] != up_loc[0] where up_loc = place.upper()[:3] means place is not all upper.
        if (place_found_in_adj !== place_found_in_adj.toUpperCase()) return false;
    }
    else if (unit_type === 'A') {
        if (order_type !== 'C' && other_loc_type === 'WATER') return false;
        // Python: place == place.title() means mixed case like "Bal"
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
            // Ensure year is represented correctly, e.g. 1901 -> 01 for S01M, but map stores full year.
            // The Python code `'%04d'` is for padding with zeros up to 4 digits, which is unusual for DAIDE abbr.
            // DAIDE usually S01M, not S1901M for abbreviation.
            // String(year).padStart(4, '0') would give "1901". String(year).slice(-2) might be "01".
            // Let's assume phase_abbr should be like S01M.
            const yearStr = String(year);
            const yearAbbr = yearStr.length > 2 ? yearStr.slice(-2) : yearStr.padStart(2,'0');

            return (`${parts[0][0]}${yearAbbr}${parts[2][0]}`).toUpperCase();
        } catch (e) { /* fall through to default */ }
    }
    return defaultVal;
  }

  public phase_long(phase_abbr: string, defaultVal: string = '?????'): string {
    if (phase_abbr.length < 4) return defaultVal; // S01M is 4 chars
    try {
        const season_char = phase_abbr[0].toUpperCase();
        const year_abbr_str = phase_abbr.substring(1, phase_abbr.length - 1);
        const type_char = phase_abbr[phase_abbr.length -1].toUpperCase();

        let year = parseInt(year_abbr_str, 10);
        if (year < 100) year += 1900; // Assuming '01' means 1901

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
      for (const file_name of [`${this.name}.svg`, `${this.root_map}.svg`]) {
          const svg_path = path.join(settings.PACKAGE_DIR, 'maps', 'svg', file_name);
          if (fs.existsSync(svg_path)) return svg_path;
      }
      return null;
  }
}
