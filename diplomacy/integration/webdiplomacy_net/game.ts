// diplomacy/integration/webdiplomacy_net/game.ts

import { DiplomacyGame } from '../../../engine/game';
import { DiplomacyMap } from '../../../engine/map'; // For map.first_year
import { WebDiplomacyOrder } from './orders'; // To be created
import { CACHE, getMapData } from './utils';
import { GameAndPower } from '../base_api'; // Assuming this is the correct path

// --- Interfaces for webdiplomacy.net API data structures ---

export interface WebDiplomacyUnitDict {
    unitType: 'Army' | 'Fleet';
    terrID: number;
    countryID: number;
    retreating: 'Yes' | 'No';
    dislodged?: 'Yes' | 'No'; // Sometimes 'dislodged' is used instead of 'retreating' in order history
}

export interface WebDiplomacyCenterDict {
    terrID: number;
    countryID: number; // 0 for unowned
}

export interface WebDiplomacyOrderDict {
    countryID: number;
    unitType?: 'Army' | 'Fleet'; // Optional in some contexts like builds/disbands
    terrID?: number;             // Optional for WAIVE, DESTROY
    type: string;               // e.g., 'Hold', 'Move', 'Support hold', 'Build Army', etc.
    toTerrID?: number;
    fromTerrID?: number;        // For support move source
    viaConvoy?: 'Yes' | 'No';
    success?: 'Yes' | 'No';     // For order results
    dislodged?: 'Yes' | 'No';   // For order results
}

export interface WebDiplomacyPhaseOrdersDict { // Structure within 'phases' array for 'orders'
    countryID: number;
    order: string; // Raw order string as seen on webdiplomacy.net e.g. "A PAR H"
    details?: WebDiplomacyOrderDict; // This is usually how detailed orders are provided
                                     // but sometimes it's just a string, so parsing might be needed.
}


export interface WebDiplomacyPhaseDict {
    turn: number;
    phase: 'Diplomacy' | 'Retreats' | 'Builds' | 'Pre-Game' | 'Finished'; // From API doc
    units: WebDiplomacyUnitDict[];
    centers: WebDiplomacyCenterDict[];
    orders?: Record<string, string> | WebDiplomacyPhaseOrdersDict[]; // Orders can be a dictionary or array
                                                                    // dict: { "FRANCE": ["A PAR H", ...], ... }
                                                                    // array: [ { countryID: X, order: "A PAR H"}, ... ]
                                                                    // The provided Python code expects `orders` to be a list of order_dict.
    results?: any; // Captures order results if available
}

export interface WebDiplomacyStateDict {
    gameID: number;
    variantID: number; // map_id
    turn: number;
    phase: 'Pre-Game' | 'Diplomacy' | 'Retreats' | 'Builds' | 'Finished';
    gameOver: 'No' | 'Won' | 'Drawn' | string; // string for specific draw types
    phases: WebDiplomacyPhaseDict[];
    standoffs?: WebDiplomacyCenterDict[]; // Array of {terrID, countryID: 0} typically
    occupiedFrom?: Record<string, number>; // terrID (string) -> terrID (number)
                                          // e.g. { "6": 22 } means Paris (6) was attacked from Burgundy (22)
    chat?: any[]; // For chat messages, if ever needed
    members?: any[]; // For member details, if ever needed
}

// --- Helper Functions ---

export function turn_to_phase(turn: number, phase: 'Diplomacy' | 'Retreats' | 'Builds', mapFirstYear: number = 1901): string {
    const year = mapFirstYear + Math.floor(turn / 2);
    const season = turn % 2 === 0 ? 'S' : 'F';
    let phaseTypeChar: string;

    if (phase === 'Builds') {
        // Builds phase is typically Winter, but webdip API uses 'F' for turn calc and 'Builds' for phase string
        return `W${year}A`;
    }

    switch (phase) {
        case 'Diplomacy': phaseTypeChar = 'M'; break;
        case 'Retreats': phaseTypeChar = 'R'; break;
        // case 'Builds': phaseTypeChar = 'A'; break; // Handled above
        default: throw new Error(`Unknown phase string: ${phase}`);
    }
    return `${season}${year}${phaseTypeChar}`;
}

export function unit_dict_to_strings(unit_dict: WebDiplomacyUnitDict, map_id: number): [string | null, string | null] {
    const mapData = getMapData(map_id);
    if (!mapData || !mapData.ix_to_loc || !mapData.ix_to_power) {
        console.error(`unit_dict_to_strings: Map data not found for mapID ${map_id}`);
        return [null, null];
    }

    const { unitType, terrID, countryID, retreating, dislodged } = unit_dict;

    if (unitType !== 'Army' && unitType !== 'Fleet') {
        console.error(`Unknown unitType "${unitType}". Expected "Army" or "Fleet".`);
        return [null, null];
    }
    if (!mapData.ix_to_loc[terrID]) {
        console.error(`Unknown terrID "${terrID}" for mapID "${map_id}".`);
        return [null, null];
    }
    if (!mapData.ix_to_power[countryID]) {
        console.error(`Unknown countryID "${countryID}" for mapID "${map_id}".`);
        return [null, null];
    }

    const isRetreatingOrDislodged = retreating === 'Yes' || dislodged === 'Yes';
    const locName = mapData.ix_to_loc[terrID]!;
    const powerName = mapData.ix_to_power[countryID]!;
    const unitChar = unitType[0]; // 'A' or 'F'

    const unitString = `${isRetreatingOrDislodged ? '*' : ''}${unitChar} ${locName}`;
    return [powerName, unitString];
}

export function center_dict_to_strings(center_dict: WebDiplomacyCenterDict, map_id: number): [string | null, string | null] {
    const mapData = getMapData(map_id);
    if (!mapData || !mapData.ix_to_loc || !mapData.ix_to_power) {
        console.error(`center_dict_to_strings: Map data not found for mapID ${map_id}`);
        return [null, null];
    }
    const { terrID, countryID } = center_dict;

    if (!mapData.ix_to_loc[terrID]) {
        console.error(`Unknown terrID "${terrID}" for mapID "${map_id}".`);
        return [null, null];
    }
    // countryID 0 is unowned, which is valid
    if (countryID !== 0 && !mapData.ix_to_power[countryID]) {
        console.error(`Unknown countryID "${countryID}" for mapID "${map_id}".`);
        return [null, null];
    }

    const locName = mapData.ix_to_loc[terrID]!;
    const powerName = countryID === 0 ? 'UNOWNED' : mapData.ix_to_power[countryID]!;
    return [powerName, locName];
}

export function order_dict_to_strings(order_dict: WebDiplomacyOrderDict, currentPhaseStr: 'Diplomacy' | 'Retreats' | 'Builds', map_id: number, mapName: string): [string | null, string | null] {
    const mapData = getMapData(map_id);
    if (!mapData || !mapData.ix_to_power) {
        console.error(`order_dict_to_strings: Map data not found for mapID ${map_id}`);
        return [null, null];
    }
    const { countryID } = order_dict;
    if (!mapData.ix_to_power[countryID]) {
        console.error(`Unknown countryID "${countryID}" for mapID "${map_id}".`);
        return [null, null];
    }

    const powerName = mapData.ix_to_power[countryID]!;
    const phaseTypeChar = {'Diplomacy': 'M', 'Retreats': 'R', 'Builds': 'A'}[currentPhaseStr];

    // WebDiplomacyOrder expects the raw dict, map_id, and phase_type character
    const order = new WebDiplomacyOrder(order_dict, mapName, phaseTypeChar); // map_id is used by constructor to get mapData
    if (!order.isValid()) { // Add an isValid method or check if to_string is null/empty
        console.warn("Failed to parse order from dict:", order_dict);
        return [powerName, null]; // Return power name even if order is invalid, for context
    }
    return [powerName, order.to_string()];
}


interface ProcessedPhase {
    name: string; // e.g., S1901M
    units: Record<string, string[]>; // powerName -> [unitStr, ...]
    centers: Record<string, string[]>; // powerName -> [locStr, ...]
    orders: Record<string, string[]>; // powerName -> [orderStr, ...]
}

export function process_phase_dict(phase_dict: WebDiplomacyPhaseDict, map_id: number, mapName: string, mapFirstYear: number): ProcessedPhase {
    const phaseName = turn_to_phase(phase_dict.turn, phase_dict.phase, mapFirstYear);
    const result: ProcessedPhase = { name: phaseName, units: {}, centers: {}, orders: {} };

    (phase_dict.units || []).forEach(unit_d => {
        const [powerName, unitStr] = unit_dict_to_strings(unit_d, map_id);
        if (powerName && unitStr) {
            result.units[powerName] = result.units[powerName] || [];
            result.units[powerName].push(unitStr);
        }
    });

    (phase_dict.centers || []).forEach(center_d => {
        const [powerName, locStr] = center_dict_to_strings(center_d, map_id);
        if (powerName && locStr) {
            result.centers[powerName] = result.centers[powerName] || [];
            result.centers[powerName].push(locStr);
        }
    });

    // API `orders` can be an array of WebDiplomacyPhaseOrdersDict or a Record<string, string[]>
    // The Python code expects a list of order_dict. The provided `WebDiplomacyPhaseOrdersDict` seems more aligned.
    if (Array.isArray(phase_dict.orders)) {
        phase_dict.orders.forEach((order_entry: WebDiplomacyPhaseOrdersDict) => {
            // order_entry might be {countryID, order: "string"} or {countryID, details: WebDiplomacyOrderDict}
            // The Python order_dict_to_str expects the detailed WebDiplomacyOrderDict
            if (order_entry.details) {
                const [powerName, orderStr] = order_dict_to_strings(order_entry.details, phase_dict.phase, map_id, mapName);
                if (powerName && orderStr) {
                    result.orders[powerName] = result.orders[powerName] || [];
                    result.orders[powerName].push(orderStr);
                }
            } else if (typeof order_entry.order === 'string' && order_entry.countryID) {
                // If only raw string is available, we might need to parse it or handle it differently.
                // This case implies the Order class needs to handle string parsing too, or this needs more logic.
                // For now, assuming `details` is the primary way.
                 console.warn("Processing raw order string from API - ensure WebDiplomacyOrder can handle this if needed:", order_entry.order);
                 // const powerName = CACHE[map_id]?.ix_to_power?.[order_entry.countryID];
                 // if (powerName) {
                 //    result.orders[powerName] = result.orders[powerName] || [];
                 //    result.orders[powerName].push(order_entry.order); // Store raw if no details
                 // }
            }
        });
    }


    return result;
}

export function state_dict_to_game_and_power(state_dict: WebDiplomacyStateDict, country_id: number, max_phases?: number): GameAndPower | null {
    if (!state_dict) return null;

    const requiredFields: Array<keyof WebDiplomacyStateDict> = ['gameID', 'variantID', 'turn', 'phase', 'gameOver', 'phases'];
    if (requiredFields.some(field => !(field in state_dict))) {
        console.error('state_dict_to_game_and_power: Missing required fields in state_dict', state_dict);
        return null;
    }

    const mapData = getMapData(state_dict.variantID);
    if (!mapData || !mapData.ix_to_map || !mapData.ix_to_power || !mapData.ix_to_loc) {
        console.error(`state_dict_to_game_and_power: Map data not found for variantID ${state_dict.variantID}`);
        return null;
    }
    const mapName = mapData.ix_to_map[state_dict.variantID];
    const powerName = mapData.ix_to_power[country_id];
    if (!powerName) {
         console.error(`state_dict_to_game_and_power: Power name not found for countryID ${country_id} in map ${mapName}`);
        return null;
    }

    const game = new DiplomacyGame({game_id: String(state_dict.gameID), map_name: mapName});
    const mapFirstYear = game.map.first_year || 1901;


    let phasesToProcess = state_dict.phases;
    if (max_phases !== undefined && max_phases !== null) {
        phasesToProcess = phasesToProcess.slice(-max_phases);
    }

    const all_processed_phases = phasesToProcess.map(phase_d => process_phase_dict(phase_d, state_dict.variantID, mapName, mapFirstYear));

    // Replay phases except the last one
    for (let i = 0; i < all_processed_phases.length - 1; i++) {
        const phase_data = all_processed_phases[i];
        game.set_current_phase(phase_data.name);

        game.clear_units(); // Clear all units before setting for the phase
        for (const [pwr, units] of Object.entries(phase_data.units)) {
            if (pwr !== 'GLOBAL') game.set_units(pwr, units);
        }
        game.clear_centers(); // Clear all centers
        for (const [pwr, centers] of Object.entries(phase_data.centers)) {
             if (pwr !== 'GLOBAL') game.set_centers(pwr, centers);
        }
        for (const [pwr, orders] of Object.entries(phase_data.orders)) {
            if (pwr !== 'GLOBAL') game.set_orders(pwr, orders);
        }
        game.process();
    }

    // Set current phase state (the last one)
    if (all_processed_phases.length > 0) {
        const current_phase_data = all_processed_phases[all_processed_phases.length - 1];
        game.set_current_phase(current_phase_data.name);
        game.clear_units();
        for (const [pwr, units] of Object.entries(current_phase_data.units)) {
             if (pwr !== 'GLOBAL') game.set_units(pwr, units);
        }
        game.clear_centers();
        for (const [pwr, centers] of Object.entries(current_phase_data.centers)) {
             if (pwr !== 'GLOBAL') game.set_centers(pwr, centers);
        }
        // Orders for the current phase are not set into game.orders, as they are not yet processed.
        // They might be needed for display or for player's own view.
    }

    // Handle retreat phase specifics (standoffs, occupiedFrom)
    if (game.get_current_phase().slice(-1) === 'R') {
        const invalidRetreatLocs = new Set<string>();
        const attackSource: Record<string, string> = {}; // loc_base -> from_loc_base

        // Locs with units are invalid for retreats
        Object.values(game.powers).forEach(pwr => {
            pwr.units.forEach(unit => invalidRetreatLocs.add(unit.location.substring(0,3)));
        });

        if (state_dict.standoffs) {
            state_dict.standoffs.forEach(standoff_loc_dict => {
                const [, loc] = center_dict_to_strings(standoff_loc_dict, state_dict.variantID);
                if(loc) invalidRetreatLocs.add(loc.substring(0,3));
            });
        }
        if (state_dict.occupiedFrom && mapData.ix_to_loc) {
            for (const [loc_id_str, from_loc_id] of Object.entries(state_dict.occupiedFrom)) {
                const loc_name = mapData.ix_to_loc[parseInt(loc_id_str, 10)]?.substring(0,3);
                const from_loc_name = mapData.ix_to_loc[from_loc_id]?.substring(0,3);
                if (loc_name && from_loc_name) {
                    attackSource[loc_name] = from_loc_name;
                }
            }
        }

        Object.values(game.powers).forEach(pwr_obj => {
            const currentRetreats = game.get_retreats(pwr_obj.name); // Assuming game.get_retreats() exists
            if (currentRetreats) {
                const newRetreats: Record<string, string[]> = {};
                for (const [unitLoc, possibleRetreats] of Object.entries(currentRetreats)) {
                    const unitBaseLoc = unitLoc.substring(2,5); // "A PAR" -> "PAR"
                    newRetreats[unitLoc] = possibleRetreats.filter(retreat_loc_option => {
                        const retreat_base = retreat_loc_option.substring(0,3);
                        return !invalidRetreatLocs.has(retreat_base) &&
                               retreat_base !== (attackSource[unitBaseLoc] || '');
                    });
                }
                // game.set_retreats(pwr_obj.name, newRetreats); // Assuming a method to update retreats
                // This part is tricky: the engine's adjudicator normally calculates retreats.
                // Here, we are *correcting* the possible retreats based on API info not available to local adjudicator (standoffs).
                // The DiplomacyGame object might not store retreats this way directly.
                // It might be better to pass this info to the agent/player.
                // For now, we log a warning if a retreat is invalidated.
                // This logic is more about providing accurate options TO a player/bot rather than modifying game state post-adjudication.
            }
        });
    }


    return { game, powerName };
}
