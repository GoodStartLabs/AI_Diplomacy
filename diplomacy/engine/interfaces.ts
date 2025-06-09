// diplomacy/engine/interfaces.ts

import { PowerTs } from './power'; // For _unit_owner_cache if defined here
import { DiplomacyMessage } from './message'; // For message history types

// From diplomacy.utils.order_results
export enum OrderResult {
    OK = 'ok', // Assuming '' or OK from python is 'ok'
    NO_CONVOY = 'no convoy',
    BOUNCE = 'bounce',
    VOID = 'void',
    CUT = 'cut',
    DISLODGED = 'dislodged',
    DISRUPTED = 'disrupted',
    DISBAND = 'disband',
    MAYBE = 'maybe', // Used in intermediate steps
    // Add any other results if they appear
}

// Placeholder for what DiplomacyMessage.toJSON() might return
// This should align with the actual toJSON implementation in message.ts
export interface DiplomacyMessageData {
    phase: string;
    sender: string;
    recipient: string;
    message: string;
    time_sent?: number;
    // any other fields from toJSON()
}

export interface GameStateHistoryEntry {
    timestamp: number;
    zobrist_hash: string;
    note: string;
    name: string; // short phase name e.g. S1901M
    units: Record<string, string[]>; // { FRANCE: ["A PAR", "*F BRE"], ... }
    retreats: Record<string, Record<string, string[]>>; // { FRANCE: { "F BRE": ["ENG", "MAO"] }, ... }
    centers: Record<string, string[]>; // { FRANCE: ["PAR", "MAR"], ... }
    homes: Record<string, string[]>;
    influence: Record<string, string[]>;
    civil_disorder: Record<string, number>; // Or boolean, depending on Python version
    builds: Record<string, { count: number; homes: string[] }>;
    phase: string; // long phase name
}

export interface SupportEntry {
    count: number;
    from: string[]; // list of units whose support does NOT count toward dislodgment
}

// Used in Game.combat
// Format: {loc: { attack_strength: [ ['src loc unit', [supporting_unit_locs_not_counting_for_dislodgement]] ]}}
// e.g. { 'MUN': { 1 : [ ['A MUN', [] ], ['A RUH', [] ] ], 2 : [ ['A SIL', ['A BOH']] ] } }
export interface CombatSiteEntry {
    [attackStrength: number]: Array<[string, string[]]>; // unit_name_at_src_loc, list_of_supporting_unit_locs
}
export type CombatTable = Record<string, CombatSiteEntry>; // loc_being_attacked_or_held

/**
 * Stores information about possible convoy paths based on current fleet locations.
 * Used in `Game.convoy_paths_possible`.
 */
export interface PossibleConvoyPathInfo {
    start: string;          // Starting location of the army
    fleetsRequired: Set<string>; // Set of fleet locations required for this path segment
    possibleDests: Set<string>;  // Set of destination locations reachable via these fleets from start
}

// Cache for _unit_owner
// Key: unit string (e.g., "A PAR", "F STP/SC") or unit string without coast (e.g., "F STP")
// Value: PowerTs instance or null
export type UnitOwnerCache = Map<string, PowerTs | null>;

// For Game.orders (mapping unit to its order string)
export type UnitOrders = Record<string, string>;

// For Game.ordered_units (mapping power name to list of its units that have orders)
export type PowerOrderedUnits = Record<string, string[]>;

// For Game.convoy_paths (mapping army unit to list of possible paths)
// Each path is a list of locations: [start_loc, fleet1_loc, fleet2_loc, ..., end_loc]
export type ConvoyPathsTable = Record<string, string[][]>;

// For may_convoy variable in _resolve_moves
// Maps an army unit (string) to a list of fleet locations (strings) that are involved in some valid path for it
export type MayConvoyTable = Record<string, string[]>;

// Structured Order Representation
export interface ParsedOrder {
    order_string: string;
    is_valid_syntax: boolean;
    validation_error?: string;

    unit_power?: string;
    unit_location?: string;
    unit_type?: 'A' | 'F';

    order_type?: 'H' | 'M' | 'S' | 'C' | 'B' | 'D' | 'W' | 'R'; // Hold, Move, Support, Convoy, Build, Disband, Waive, Retreat

    // For Move orders
    target_location?: string;
    target_coast?: string;

    // For Support orders
    supported_unit_location?: string;
    supported_unit_type?: 'A' | 'F';
    support_target_location?: string;
    support_target_coast?: string;

    // For Convoy orders
    convoyed_unit_location?: string;
    convoyed_unit_type?: 'A' | 'F';
    convoy_destination_location?: string;

    // For Build orders
    build_unit_type?: 'A' | 'F';

    via_convoy?: boolean;

    // For rule validation
    is_valid_rule?: boolean;
    rule_validation_error?: string;
}
