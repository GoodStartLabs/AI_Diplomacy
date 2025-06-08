import * as dotenv from 'dotenv';

// Logger setup
const logger = {
  debug: (message: string) => console.debug(message),
  info: (message: string) => console.info(message),
  warn: (message: string) => console.warn(message),
  error: (message: string, error?: any) => console.error(message, error),
};

dotenv.config();

// Placeholder types for Diplomacy game objects
// These would ideally be imported from a 'diplomacy-ts' library

export interface DiplomacyGameMap {
  locs: string[]; // All locations including coasts, e.g., "STP/SC"
  loc_coasts: Record<string, string[]>; // Maps short province to list of its full names (e.g., STP -> [STP/NC, STP/SC, STP])
  loc_name: Record<string, string>; // Maps full loc to short province name (e.g. "STP/SC" -> "STP")
  loc_type: Record<string, string>; // Maps short province to type (LAND, WATER, COAST)
  scs: string[]; // List of short province names that are supply centers
  abuts(unit_type_char: 'A' | 'F', loc_full_source: string, order_type: string, loc_full_dest: string): boolean;
  // Add other map properties/methods as needed
}

export interface BoardState {
  units: Record<string, string[]>; // e.g., { "FRANCE": ["A PAR", "F BRE"] }
  centers: Record<string, string[]>; // e.g., { "FRANCE": ["PAR", "MAR"] }
  // Other board state properties
}

export interface DiplomacyGame { // Placeholder for the main game object
    map: DiplomacyGameMap;
    get_state(): BoardState;
    // Other game methods
}

// Type for the graph structure
export type DiplomacyGraphNode = {
  ARMY: string[];
  FLEET: string[];
};
export type DiplomacyGraph = Record<string, DiplomacyGraphNode>;


export function build_diplomacy_graph(game_map: DiplomacyGameMap): DiplomacyGraph {
    const graph: DiplomacyGraph = {};

    const unique_short_names: Set<string> = new Set();
    for (const loc of game_map.locs) {
        const short_name = loc.split('/')[0].substring(0, 3).toUpperCase();
        if (short_name.length === 3) {
            unique_short_names.add(short_name);
        }
    }

    const all_short_province_names = Array.from(unique_short_names).sort();

    for (const province_name of all_short_province_names) {
        graph[province_name] = { ARMY: [], FLEET: [] };
    }

    for (const province_short_source of all_short_province_names) {
        const full_names_for_source = game_map.loc_coasts[province_short_source] || [province_short_source];

        for (const loc_full_source_variant of full_names_for_source) {
            // game_map.loc_abut in python code was used with province_short_source,
            // but game_map.abuts needs full location names.
            // We need to iterate over all possible destination provinces and check abutment.
            for (const adj_short_name_normalized of all_short_province_names) {
                if (adj_short_name_normalized === province_short_source) continue;

                const full_names_for_adj_dest = game_map.loc_coasts[adj_short_name_normalized] || [adj_short_name_normalized];

                // Check for ARMY movement
                if (full_names_for_adj_dest.some(full_dest_variant =>
                    game_map.abuts('A', loc_full_source_variant, '-', full_dest_variant))) {
                    if (!graph[province_short_source].ARMY.includes(adj_short_name_normalized)) {
                        graph[province_short_source].ARMY.push(adj_short_name_normalized);
                    }
                }

                // Check for FLEET movement
                if (full_names_for_adj_dest.some(full_dest_variant =>
                    game_map.abuts('F', loc_full_source_variant, '-', full_dest_variant))) {
                    if (!graph[province_short_source].FLEET.includes(adj_short_name_normalized)) {
                        graph[province_short_source].FLEET.push(adj_short_name_normalized);
                    }
                }
            }
        }
    }

    for (const province_short in graph) {
        graph[province_short].ARMY = Array.from(new Set(graph[province_short].ARMY)).sort();
        graph[province_short].FLEET = Array.from(new Set(graph[province_short].FLEET)).sort();
    }

    return graph;
}

export function bfs_shortest_path(
    graph: DiplomacyGraph,
    board_state: BoardState, // Currently unused in this specific BFS, but kept for signature
    game_map: DiplomacyGameMap,
    start_loc_full: string,
    unit_type: 'ARMY' | 'FLEET',
    is_target_func: (loc_short: string, current_board_state: BoardState) => boolean
): string[] | null {

    let start_loc_short = game_map.loc_name[start_loc_full] || start_loc_full;
    start_loc_short = start_loc_short.substring(0, 3).toUpperCase();

    if (!graph[start_loc_short]) {
        logger.warn(`BFS: Start province ${start_loc_short} (from ${start_loc_full}) not in graph. Pathfinding may fail.`);
        return null;
    }

    const queue: Array<[string, string[]]> = [[start_loc_short, [start_loc_short]]];
    const visited_nodes: Set<string> = new Set([start_loc_short]);

    while (queue.length > 0) {
        const [current_loc_short, path] = queue.shift()!; // Non-null assertion due to length check

        if (is_target_func(current_loc_short, board_state)) {
            return path;
        }

        const possible_neighbors_short = graph[current_loc_short]?.[unit_type] || [];

        for (const next_loc_short of possible_neighbors_short) {
            if (!visited_nodes.has(next_loc_short)) {
                if (!graph[next_loc_short]) {
                    logger.warn(`BFS: Neighbor ${next_loc_short} of ${current_loc_short} not in graph. Skipping.`);
                    continue;
                }
                visited_nodes.add(next_loc_short);
                const new_path = [...path, next_loc_short];
                queue.push([next_loc_short, new_path]);
            }
        }
    }
    return null;
}

// --- Helper functions for context generation ---
export function get_unit_at_location(board_state: BoardState, location_full: string): string | null {
    for (const [power, unit_list] of Object.entries(board_state.units || {})) {
        for (const unit_str of unit_list) { // e.g., "A PAR", "F STP/SC"
            const parts = unit_str.split(" "); // ["A", "PAR"] or ["F", "STP/SC"]
            if (parts.length === 2) {
                const unit_map_loc = parts[1];
                if (unit_map_loc === location_full) {
                    return `${parts[0]} ${location_full} (${power})`;
                }
            }
        }
    }
    return null;
}

export function get_sc_controller(game_map: DiplomacyGameMap, board_state: BoardState, location_short: string): string | null {
    const loc_province_name = location_short.substring(0,3).toUpperCase(); // Ensure it's short form
    if (!game_map.scs.includes(loc_province_name)) {
        return null; // Not an SC
    }
    for (const [power, sc_list] of Object.entries(board_state.centers || {})) {
        if (sc_list.includes(loc_province_name)) {
            return power;
        }
    }
    return null; // Unowned SC
}

// --- Main context generation function and its helpers will be next ---
// For now, stubs for the more complex helpers and the main function:

export function get_shortest_path_to_friendly_unit(
    board_state: BoardState,
    graph: DiplomacyGraph,
    game_map: DiplomacyGameMap,
    power_name: string,
    start_unit_loc_full: string,
    start_unit_type: 'ARMY' | 'FLEET'
): [string, string[]] | null {
    const is_target_friendly = (loc_short: string, current_board_state: BoardState): boolean => {
        const full_locs_for_short = game_map.loc_coasts[loc_short] || [loc_short];
        for (const full_loc_variant of full_locs_for_short) {
            const unit_at_loc = get_unit_at_location(current_board_state, full_loc_variant);
            if (unit_at_loc && unit_at_loc.includes(`(${power_name})`) && full_loc_variant !== start_unit_loc_full) {
                return true;
            }
        }
        return false;
    };

    const path_short_names = bfs_shortest_path(graph, board_state, game_map, start_unit_loc_full, start_unit_type, is_target_friendly);

    if (path_short_names && path_short_names.length > 1) {
        const target_loc_short = path_short_names[path_short_names.length - 1];
        let friendly_unit_str = "UNKNOWN_FRIENDLY_UNIT";

        const full_locs_for_target_short = game_map.loc_coasts[target_loc_short] || [target_loc_short];
        for (const fl_variant of full_locs_for_target_short) {
            const unit_str = get_unit_at_location(board_state, fl_variant);
            if (unit_str && unit_str.includes(`(${power_name})`)) {
                friendly_unit_str = unit_str;
                break;
            }
        }
        return [friendly_unit_str, path_short_names];
    }
    return null;
}

export function get_nearest_enemy_units(
    board_state: BoardState,
    graph: DiplomacyGraph,
    game_map: DiplomacyGameMap,
    power_name: string,
    start_unit_loc_full: string,
    start_unit_type: 'ARMY' | 'FLEET',
    n: number = 3
): Array<[string, string[]]> {
    const enemy_paths: Array<[string, string[]]> = [];

    const all_enemy_unit_locations_full: Array<{ loc_full: string; unit_str_full: string }> = [];
    for (const [p_name, unit_list_for_power] of Object.entries(board_state.units || {})) {
        if (p_name !== power_name) {
            for (const unit_repr_from_state of unit_list_for_power) {
                const parts = unit_repr_from_state.split(" ");
                if (parts.length === 2) {
                    const loc_full = parts[1];
                    const full_unit_str_with_power = get_unit_at_location(board_state, loc_full);
                    if (full_unit_str_with_power) {
                         all_enemy_unit_locations_full.push({ loc_full, unit_str_full: full_unit_str_with_power });
                    }
                }
            }
        }
    }

    for (const { loc_full: target_enemy_loc_full, unit_str_full: enemy_unit_str } of all_enemy_unit_locations_full) {
        // Normalize target_enemy_loc_full to short form for is_specific_enemy_loc
        let target_enemy_loc_short = game_map.loc_name[target_enemy_loc_full] || target_enemy_loc_full;
        target_enemy_loc_short = target_enemy_loc_short.substring(0,3).toUpperCase();

        const is_specific_enemy_loc = (loc_short: string, current_board_state: BoardState): boolean => {
            return loc_short === target_enemy_loc_short;
        };

        const path_short_names = bfs_shortest_path(graph, board_state, game_map, start_unit_loc_full, start_unit_type, is_specific_enemy_loc);
        if (path_short_names) {
            enemy_paths.push([enemy_unit_str, path_short_names]);
        }
    }

    enemy_paths.sort((a, b) => a[1].length - b[1].length);
    return enemy_paths.slice(0, n);
}

export function get_nearest_uncontrolled_scs(
    game_map: DiplomacyGameMap,
    board_state: BoardState,
    graph: DiplomacyGraph,
    power_name: string,
    start_unit_loc_full: string,
    start_unit_type: 'ARMY' | 'FLEET',
    n: number = 3
): Array<[string, number, string[]]> { // Returns [sc_name_short_with_controller, distance, path_short_names][]
    const uncontrolled_sc_paths: Array<[string, number, string[]]> = [];

    const all_scs_short = game_map.scs; // Assuming this is a list of short province names

    for (const sc_loc_short of all_scs_short) {
        const controller = get_sc_controller(game_map, board_state, sc_loc_short);
        if (controller !== power_name) {
            const is_target_sc = (loc_short: string, current_board_state: BoardState): boolean => {
                return loc_short === sc_loc_short;
            };

            const path_short_names = bfs_shortest_path(graph, board_state, game_map, start_unit_loc_full, start_unit_type, is_target_sc);
            if (path_short_names) {
                // Path includes start, so distance is len - 1
                const distance = path_short_names.length - 1;
                uncontrolled_sc_paths.push([`${sc_loc_short} (Ctrl: ${controller || 'None'})`, distance, path_short_names]);
            }
        }
    }

    uncontrolled_sc_paths.sort((a, b) => {
        if (a[1] !== b[1]) { // Sort by distance
            return a[1] - b[1];
        }
        return a[0].localeCompare(b[0]); // Then by SC name for tie-breaking
    });
    return uncontrolled_sc_paths.slice(0, n);
}

export function get_adjacent_territory_details(
    game_map: DiplomacyGameMap,
    board_state: BoardState,
    unit_loc_full: string,
    unit_type: 'ARMY' | 'FLEET',
    graph: DiplomacyGraph
): string {
    const output_lines: string[] = [];

    let unit_loc_short = game_map.loc_name[unit_loc_full] || unit_loc_full;
    unit_loc_short = unit_loc_short.substring(0,3).toUpperCase();

    const adjacent_locs_short_for_unit = graph[unit_loc_short]?.[unit_type] || [];
    const processed_adj_provinces: Set<string> = new Set();

    for (const adj_loc_short of adjacent_locs_short_for_unit) {
        if (processed_adj_provinces.has(adj_loc_short)) {
            continue;
        }
        processed_adj_provinces.add(adj_loc_short);

        const adj_loc_type_raw = game_map.loc_type[adj_loc_short] || 'UNKNOWN';
        let adj_loc_type_display = adj_loc_type_raw.toUpperCase();
        if (adj_loc_type_display === 'COAST') adj_loc_type_display = 'COAST'; // Already good
        else if (adj_loc_type_display === 'LAND') adj_loc_type_display = 'LAND'; // Already good
        else if (adj_loc_type_display === 'WATER') adj_loc_type_display = 'WATER'; // Already good
        // else keep raw uppercase type for SHUT etc.

        let line = `  ${adj_loc_short} (${adj_loc_type_display})`;

        const sc_controller = get_sc_controller(game_map, board_state, adj_loc_short);
        if (sc_controller) {
            line += ` SC Control: ${sc_controller}`;
        }

        // Check for units in any part of the short location (e.g. STP/NC, STP/SC for STP)
        let unit_in_adj_loc_str: string | null = null;
        const full_variants_of_adj_short = game_map.loc_coasts[adj_loc_short] || [adj_loc_short];
        for (const fv_adj of full_variants_of_adj_short) {
            const temp_unit = get_unit_at_location(board_state, fv_adj);
            if (temp_unit) {
                unit_in_adj_loc_str = temp_unit;
                break;
            }
        }
        if (unit_in_adj_loc_str) {
            line += ` Units: ${unit_in_adj_loc_str}`;
        }
        output_lines.push(line);

        const further_adj_provinces_short_army = graph[adj_loc_short]?.ARMY || [];
        const further_adj_provinces_short_fleet = graph[adj_loc_short]?.FLEET || [];
        const further_adj_provinces_short = Array.from(new Set([...further_adj_provinces_short_army, ...further_adj_provinces_short_fleet]));

        const supporting_units_info: string[] = [];
        const processed_further_provinces: Set<string> = new Set();
        for (const further_adj_loc_short of further_adj_provinces_short) {
            if (further_adj_loc_short === adj_loc_short || further_adj_loc_short === unit_loc_short) {
                continue;
            }
            if (processed_further_provinces.has(further_adj_loc_short)) {
                continue;
            }
            processed_further_provinces.add(further_adj_loc_short);

            let unit_in_further_loc_str: string | null = null;
            const full_variants_of_further_short = game_map.loc_coasts[further_adj_loc_short] || [further_adj_loc_short];
            for (const fv_further of full_variants_of_further_short) {
                const temp_unit = get_unit_at_location(board_state, fv_further);
                if (temp_unit) {
                    unit_in_further_loc_str = temp_unit;
                    break;
                }
            }
            if (unit_in_further_loc_str) {
                supporting_units_info.push(unit_in_further_loc_str);
            }
        }

        if (supporting_units_info.length > 0) {
            output_lines.push(`    => Can support/move to: ${supporting_units_info.sort().join(', ')}`);
        }
    }
    return output_lines.join("\n");
}

export function generate_rich_order_context(game: DiplomacyGame, power_name: string, possible_orders_for_power: Record<string, string[]>): string {
    const board_state: BoardState = game.get_state();
    const game_map: DiplomacyGameMap = game.map;
    // Ensure graph is built only once if this function is called multiple times for the same game state/map
    // For now, building it each time as per original Python structure.
    // Consider caching or passing the graph if performance becomes an issue.
    const graph = build_diplomacy_graph(game_map);

    const final_context_lines: string[] = ["<PossibleOrdersContext>"];

    for (const [unit_loc_full, unit_specific_possible_orders] of Object.entries(possible_orders_for_power)) {
        const unit_str_full = get_unit_at_location(board_state, unit_loc_full);
        if (!unit_str_full) {
            logger.warn(`Could not find unit details for ${unit_loc_full} from possible_orders. Skipping context for this unit.`);
            continue;
        }

        const unit_type_char = unit_str_full.split(" ")[0]; // 'A' or 'F'
        const unit_type_long = unit_type_char === 'A' ? "ARMY" : "FLEET";

        let loc_province_short = game_map.loc_name[unit_loc_full] || unit_loc_full;
        loc_province_short = loc_province_short.substring(0,3).toUpperCase();

        const loc_type_raw = game_map.loc_type[loc_province_short] || "UNKNOWN";
        let loc_type_display = loc_type_raw.toUpperCase();
        if (loc_type_display === 'COAST') loc_type_display = 'COAST';
        else if (loc_type_display === 'LAND') loc_type_display = 'LAND';
        // else keep raw for WATER, SHUT etc.

        const current_unit_lines: string[] = [];
        current_unit_lines.push(`  <UnitContext loc="${unit_loc_full}">`);

        current_unit_lines.push('    <UnitInformation>');
        const sc_owner_at_loc = get_sc_controller(game_map, board_state, loc_province_short); // Use short name for SC check
        let header_content = `Strategic territory held by ${power_name}: ${unit_loc_full} (${loc_type_display})`;
        if (sc_owner_at_loc === power_name) {
            header_content += " (Controls SC)";
        } else if (sc_owner_at_loc) {
            header_content += ` (SC controlled by ${sc_owner_at_loc})`;
        }
        current_unit_lines.push(`      ${header_content}`);
        current_unit_lines.push(`      Units present: ${unit_str_full}`);
        current_unit_lines.push('    </UnitInformation>');

        current_unit_lines.push('    <PossibleMoves>');
        current_unit_lines.push("      Possible moves:");
        for (const order_str of unit_specific_possible_orders) {
            current_unit_lines.push(`        ${order_str}`);
        }
        current_unit_lines.push('    </PossibleMoves>');

        const enemy_units_info = get_nearest_enemy_units(board_state, graph, game_map, power_name, unit_loc_full, unit_type_long, 3);
        current_unit_lines.push('    <NearestEnemyUnits>');
        if (enemy_units_info.length > 0) {
            current_unit_lines.push("      Nearest units (not ours):");
            for (const [enemy_unit_str, enemy_path_short] of enemy_units_info) {
                const path_display = enemy_path_short.length > 1 ? `[${unit_loc_full}→${enemy_path_short.slice(1).join('→')}]` : `[${enemy_path_short[0]}] (already there or error in path)`;
                current_unit_lines.push(`        ${enemy_unit_str}, path=${path_display}`);
            }
        } else {
            current_unit_lines.push("      Nearest units (not ours): None found");
        }
        current_unit_lines.push('    </NearestEnemyUnits>');

        const uncontrolled_scs_info = get_nearest_uncontrolled_scs(game_map, board_state, graph, power_name, unit_loc_full, unit_type_long, 3);
        current_unit_lines.push('    <NearestUncontrolledSupplyCenters>');
        if (uncontrolled_scs_info.length > 0) {
            current_unit_lines.push("      Nearest supply centers (not controlled by us):");
            for (const [sc_str, dist, sc_path_short] of uncontrolled_scs_info) {
                 const path_display = sc_path_short.length > 1 ? `[${unit_loc_full}→${sc_path_short.slice(1).join('→')}]` : `[${sc_path_short[0]}]`;
                current_unit_lines.push(`        ${sc_str}, dist=${dist}, path=${path_display}`);
            }
        } else {
            current_unit_lines.push("      Nearest supply centers (not controlled by us): None found");
        }
        current_unit_lines.push('    </NearestUncontrolledSupplyCenters>');

        const adj_details_str = get_adjacent_territory_details(game_map, board_state, unit_loc_full, unit_type_long, graph);
        current_unit_lines.push('    <AdjacentTerritories>');
        if (adj_details_str && adj_details_str.trim() !== "") {
            current_unit_lines.push("      Adjacent territories (including units that can support/move to the adjacent territory):");
            // Indent each line of adj_details_str
            const indented_adj_details = adj_details_str.split('\n').map(line => `        ${line}`).join('\n');
            current_unit_lines.push(indented_adj_details);
        } else {
            current_unit_lines.push("      Adjacent territories: None relevant or all are empty/uncontested by direct threats.");
        }
        current_unit_lines.push('    </AdjacentTerritories>');

        current_unit_lines.push('  </UnitContext>');
        final_context_lines.push(...current_unit_lines);
    }

    final_context_lines.push("</PossibleOrdersContext>");
    return final_context_lines.join("\n");
}
