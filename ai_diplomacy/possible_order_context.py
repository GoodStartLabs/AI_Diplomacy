# ai_diplomacy/possible_order_context.py

from collections import deque
from typing import Dict, List, Callable, Optional, Any, Set, Tuple
from diplomacy.engine.map import Map as GameMap
from diplomacy.engine.game import Game as BoardState
from loguru import logger

# Placeholder for actual map type from diplomacy.engine.map.Map
# GameMap = Any
# Type hint for board_state dictionary from game.get_state()
# BoardState = Dict[str, Any]


def build_diplomacy_graph(game_map: GameMap) -> Dict[str, Dict[str, List[str]]]:
    """
    Builds a graph where keys are SHORT province names (e.g., 'PAR', 'STP').
    Adjacency lists also contain SHORT province names.
    This graph is used for BFS pathfinding.
    """
    graph: Dict[str, Dict[str, List[str]]] = {}

    # Deriving a clean list of unique, 3-letter, uppercase short province names
    # game_map.locs contains all locations, including coasts e.g. "STP/SC"
    unique_short_names = set()
    for loc in game_map.locs:
        short_name = loc.split("/")[0][:3].upper()  # Take first 3 chars and uppercase
        if len(short_name) == 3:  # Ensure it's a 3-letter name
            unique_short_names.add(short_name)

    all_short_province_names = sorted(list(unique_short_names))

    # Initialize graph with all valid short province names as keys
    for province_name in all_short_province_names:
        graph[province_name] = {"ARMY": [], "FLEET": []}

    for province_short_source in all_short_province_names:  # e.g. 'PAR', 'STP'
        # Get all full names for this source province (e.g. 'STP' -> ['STP/NC', 'STP/SC', 'STP'])
        full_names_for_source = game_map.loc_coasts.get(
            province_short_source, [province_short_source]
        )

        for (
            loc_full_source_variant
        ) in full_names_for_source:  # e.g. 'STP/NC', then 'STP/SC', then 'STP'
            # province_short_source is already the short name like 'STP'
            # game_map.loc_abut provides general adjacencies, which might include specific coasts or lowercase names
            for raw_adj_loc_from_loc_abut in game_map.loc_abut.get(
                province_short_source, []
            ):
                # Normalize this raw adjacent location to its short, uppercase form
                adj_short_name_normalized = raw_adj_loc_from_loc_abut[:3].upper()

                # Get all full names for this *normalized* adjacent short name (e.g. 'BUL' -> ['BUL/EC', 'BUL/SC', 'BUL'])
                full_names_for_adj_dest = game_map.loc_coasts.get(
                    adj_short_name_normalized, [adj_short_name_normalized]
                )

                # Check for ARMY movement
                unit_char_army = "A"
                if any(
                    game_map.abuts(
                        unit_char_army,
                        loc_full_source_variant,  # Specific full source, e.g. 'STP/NC'
                        "-",  # Order type for move
                        full_dest_variant,  # Specific full destination, e.g. 'MOS' or 'FIN'
                    )
                    for full_dest_variant in full_names_for_adj_dest
                ):
                    if (
                        adj_short_name_normalized
                        not in graph[province_short_source]["ARMY"]
                    ):
                        graph[province_short_source]["ARMY"].append(
                            adj_short_name_normalized
                        )

                # Check for FLEET movement
                unit_char_fleet = "F"
                if any(
                    game_map.abuts(
                        unit_char_fleet,
                        loc_full_source_variant,  # Specific full source, e.g. 'STP/NC'
                        "-",  # Order type for move
                        full_dest_variant,  # Specific full destination, e.g. 'BAR' or 'NWY'
                    )
                    for full_dest_variant in full_names_for_adj_dest
                ):
                    if (
                        adj_short_name_normalized
                        not in graph[province_short_source]["FLEET"]
                    ):
                        graph[province_short_source]["FLEET"].append(
                            adj_short_name_normalized
                        )

    # Remove duplicates from adjacency lists (just in case)
    for province_short in graph:
        if "ARMY" in graph[province_short]:
            graph[province_short]["ARMY"] = sorted(
                list(set(graph[province_short]["ARMY"]))
            )
        if "FLEET" in graph[province_short]:
            graph[province_short]["FLEET"] = sorted(
                list(set(graph[province_short]["FLEET"]))
            )

    return graph


def bfs_shortest_path(
    graph: Dict[str, Dict[str, List[str]]],
    board_state: BoardState,
    game_map: GameMap,  # Added game_map
    start_loc_full: str,  # This is a FULL location name like 'VIE' or 'STP/SC'
    unit_type: str,
    is_target_func: Callable[[str, BoardState], bool],  # Expects SHORT name for loc
) -> Optional[List[str]]:  # Returns path of SHORT names
    """Performs BFS to find the shortest path from start_loc to a target satisfying is_target_func."""

    # Convert full start location to short province name
    start_loc_short = game_map.loc_name.get(start_loc_full, start_loc_full)
    if (
        "/" in start_loc_short
    ):  # If it was STP/SC, loc_name gives STP. If it was VIE, loc_name gives VIE.
        start_loc_short = start_loc_short[:3]
    # If start_loc_full was already short (e.g. 'VIE'), get might return it as is, or its value if it was a key.
    # A simpler way for non-coastal full (like 'VIE') or already short:
    if "/" not in start_loc_full:
        start_loc_short = start_loc_full[:3]  # Ensures 'VIE' -> 'VIE', 'PAR' -> 'PAR'
    else:  # Has '/', e.g. 'STP/SC'
        start_loc_short = start_loc_full[:3]  # 'STP/SC' -> 'STP'

    if start_loc_short not in graph:
        logger.warning(
            f"BFS: Start province {start_loc_short} (from {start_loc_full}) not in graph. Pathfinding may fail."
        )
        return None

    queue: deque[Tuple[str, List[str]]] = deque([(start_loc_short, [start_loc_short])])
    visited_nodes: Set[str] = {start_loc_short}

    while queue:
        current_loc_short, path = queue.popleft()

        # is_target_func expects a short location name
        if is_target_func(current_loc_short, board_state):
            return path  # Path of short names

        # possible_neighbors are SHORT names from the graph
        possible_neighbors_short = graph.get(current_loc_short, {}).get(unit_type, [])

        for next_loc_short in possible_neighbors_short:
            if next_loc_short not in visited_nodes:
                if (
                    next_loc_short not in graph
                ):  # Defensive check for neighbors not in graph keys
                    logger.warning(
                        f"BFS: Neighbor {next_loc_short} of {current_loc_short} not in graph. Skipping."
                    )
                    continue
                visited_nodes.add(next_loc_short)
                new_path = path + [next_loc_short]
                queue.append((next_loc_short, new_path))
    return None


# --- Helper functions for context generation ---
def get_unit_at_location(board_state: BoardState, location: str) -> Optional[str]:
    """Returns the full unit string (e.g., 'A PAR (FRA)') if a unit is at the location, else None."""
    for power, unit_list in board_state.get("units", {}).items():
        for unit_str in unit_list:  # e.g., "A PAR", "F STP/SC"
            parts = unit_str.split(" ")
            if len(parts) == 2:
                unit_map_loc = parts[1]
                if unit_map_loc == location:
                    return f"{parts[0]} {location} ({power})"
    return None


def get_sc_controller(
    game_map: GameMap, board_state: BoardState, location: str
) -> Optional[str]:
    """Returns the controlling power's name if the location is an SC, else None."""
    # Normalize location to base province name, as SCs are tied to provinces, not specific coasts
    loc_province_name = game_map.loc_name.get(location, location).upper()[:3]
    if loc_province_name not in game_map.scs:
        return None
    for power, sc_list in board_state.get("centers", {}).items():
        if loc_province_name in sc_list:
            return power
    return None  # Unowned SC


def get_shortest_path_to_friendly_unit(
    board_state: BoardState,
    graph: Dict[str, Dict[str, List[str]]],
    game_map: GameMap,  # Added game_map
    power_name: str,
    start_unit_loc_full: str,
    start_unit_type: str,
) -> Optional[Tuple[str, List[str]]]:
    """Finds the shortest path to any friendly unit of the same power."""

    def is_target_friendly(loc_short: str, current_board_state: BoardState) -> bool:
        # loc_short is a short province name. Need to check all its full locations.
        full_locs_for_short = game_map.loc_coasts.get(loc_short, [loc_short])
        for full_loc_variant in full_locs_for_short:
            unit_at_loc = get_unit_at_location(current_board_state, full_loc_variant)
            if (
                unit_at_loc
                and unit_at_loc.split(" ")[2][1:4] == power_name
                and full_loc_variant != start_unit_loc_full
            ):
                return True
        return False

    path_short_names = bfs_shortest_path(
        graph,
        board_state,
        game_map,
        start_unit_loc_full,
        start_unit_type,
        is_target_friendly,
    )
    if (
        path_short_names and len(path_short_names) > 1
    ):  # Path includes start, so > 1 means a distinct friendly unit found
        target_loc_short = path_short_names[-1]
        # Find the actual friendly unit string at one of the full locations of target_loc_short
        friendly_unit_str = "UNKNOWN_FRIENDLY_UNIT"
        full_locs_for_target_short = game_map.loc_coasts.get(
            target_loc_short, [target_loc_short]
        )
        for fl_variant in full_locs_for_target_short:
            unit_str = get_unit_at_location(board_state, fl_variant)
            if unit_str and unit_str.split(" ")[2][1:4] == power_name:
                friendly_unit_str = unit_str
                break
        return friendly_unit_str, path_short_names
    return None


def get_nearest_enemy_units(
    board_state: BoardState,
    graph: Dict[str, Dict[str, List[str]]],
    game_map: GameMap,  # Added game_map
    power_name: str,
    start_unit_loc_full: str,
    start_unit_type: str,
    n: int = 3,
) -> List[Tuple[str, List[str]]]:
    """Finds up to N nearest enemy units, sorted by path length."""
    enemy_paths: List[Tuple[str, List[str]]] = []  # (enemy_unit_str, path_short_names)

    all_enemy_unit_locations_full: List[
        Tuple[str, str]
    ] = []  # (loc_full, unit_str_full)
    # board_state.get("units", {}) has format: { "POWER_NAME": ["A PAR", "F BRE"], ... }
    for p_name, unit_list_for_power in board_state.get("units", {}).items():
        if p_name != power_name:  # If it's an enemy power
            for (
                unit_repr_from_state
            ) in unit_list_for_power:  # e.g., "A PAR" or "F STP/SC"
                parts = unit_repr_from_state.split(" ")
                if len(parts) == 2:
                    # unit_type_char = parts[0] # 'A' or 'F'
                    loc_full = parts[1]  # 'PAR' or 'STP/SC'

                    # Use get_unit_at_location to get the consistent full unit string like "A PAR (POWER_NAME)"
                    full_unit_str_with_power = get_unit_at_location(
                        board_state, loc_full
                    )
                    if (
                        full_unit_str_with_power
                    ):  # Should find the unit if iteration is correct
                        all_enemy_unit_locations_full.append(
                            (loc_full, full_unit_str_with_power)
                        )

    for target_enemy_loc_full, enemy_unit_str in all_enemy_unit_locations_full:
        target_enemy_loc_short = game_map.loc_name.get(
            target_enemy_loc_full, target_enemy_loc_full
        )
        if "/" in target_enemy_loc_short:
            target_enemy_loc_short = target_enemy_loc_short[:3]
        if "/" not in target_enemy_loc_full:
            target_enemy_loc_short = target_enemy_loc_full[:3]
        else:
            target_enemy_loc_short = target_enemy_loc_full[:3]

        def is_specific_enemy_loc(
            loc_short: str, current_board_state: BoardState
        ) -> bool:
            # Check if loc_short corresponds to target_enemy_loc_full
            return loc_short == target_enemy_loc_short

        path_short_names = bfs_shortest_path(
            graph,
            board_state,
            game_map,
            start_unit_loc_full,
            start_unit_type,
            is_specific_enemy_loc,
        )
        if path_short_names:
            enemy_paths.append((enemy_unit_str, path_short_names))

    enemy_paths.sort(key=lambda x: len(x[1]))  # Sort by path length
    return enemy_paths[:n]


def get_nearest_uncontrolled_scs(
    game_map: GameMap,
    board_state: BoardState,
    graph: Dict[str, Dict[str, List[str]]],
    power_name: str,
    start_unit_loc_full: str,
    start_unit_type: str,
    n: int = 3,
) -> List[Tuple[str, int, List[str]]]:  # (sc_name_short, distance, path_short_names)
    """Finds up to N nearest SCs not controlled by power_name, sorted by path length."""
    uncontrolled_sc_paths: List[Tuple[str, int, List[str]]] = []

    all_scs_short = game_map.scs  # This is a list of short province names that are SCs

    for sc_loc_short in all_scs_short:
        controller = get_sc_controller(game_map, board_state, sc_loc_short)
        if controller != power_name:

            def is_target_sc(loc_short: str, current_board_state: BoardState) -> bool:
                return loc_short == sc_loc_short

            path_short_names = bfs_shortest_path(
                graph,
                board_state,
                game_map,
                start_unit_loc_full,
                start_unit_type,
                is_target_sc,
            )
            if path_short_names:
                # Path includes start, so distance is len - 1
                uncontrolled_sc_paths.append(
                    (
                        f"{sc_loc_short} (Ctrl: {controller or 'None'})",
                        len(path_short_names) - 1,
                        path_short_names,
                    )
                )

    # Sort by distance (path length - 1), then by SC name for tie-breaking
    uncontrolled_sc_paths.sort(key=lambda x: (x[1], x[0]))
    return uncontrolled_sc_paths[:n]


def get_adjacent_territory_details(
    game_map: GameMap,
    board_state: BoardState,
    unit_loc_full: str,  # The location of the unit whose adjacencies we're checking
    unit_type: str,  # ARMY or FLEET of the unit at unit_loc_full
    graph: Dict[str, Dict[str, List[str]]],
) -> str:
    """Generates a string describing adjacent territories and units that can interact with them."""
    output_lines: List[str] = []
    # Get adjacencies for the current unit's type
    # The graph already stores processed adjacencies (e.g. army can't go to sea)
    # For armies, graph[unit_loc_full]['ARMY'] gives short province names
    # For fleets, graph[unit_loc_full]['FLEET'] gives full loc names (incl coasts)
    # THIS COMMENT IS NOW OUTDATED. Graph uses short names for keys and values.
    unit_loc_short = game_map.loc_name.get(unit_loc_full, unit_loc_full)
    if "/" in unit_loc_short:
        unit_loc_short = unit_loc_short[:3]
    if "/" not in unit_loc_full:
        unit_loc_short = unit_loc_full[:3]
    else:
        unit_loc_short = unit_loc_full[:3]

    adjacent_locs_short_for_unit = graph.get(unit_loc_short, {}).get(unit_type, [])

    processed_adj_provinces = (
        set()
    )  # To handle cases like STP/NC and STP/SC both being adjacent to BOT

    for adj_loc_short in adjacent_locs_short_for_unit:  # adj_loc_short is already short
        # adj_province_short = game_map.loc_name.get(adj_loc_full, adj_loc_full).upper()[:3] # No longer needed
        if (
            adj_loc_short in processed_adj_provinces
        ):  # adj_loc_short is already short and upper implicitly by map data
            continue
        processed_adj_provinces.add(adj_loc_short)

        adj_loc_type = game_map.loc_type.get(adj_loc_short, "UNKNOWN").upper()
        if adj_loc_type == "COAST" or adj_loc_type == "LAND":
            adj_loc_type_display = "LAND" if adj_loc_type == "LAND" else "COAST"
        elif adj_loc_type == "WATER":
            adj_loc_type_display = "WATER"
        else:  # SHUT etc.
            adj_loc_type_display = adj_loc_type

        line = f"  {adj_loc_short} ({adj_loc_type_display})"

        sc_controller = get_sc_controller(game_map, board_state, adj_loc_short)
        if sc_controller:
            line += f" SC Control: {sc_controller}"

        unit_in_adj_loc = get_unit_at_location(board_state, adj_loc_short)
        if unit_in_adj_loc:
            line += f" Units: {unit_in_adj_loc}"
        output_lines.append(line)

        # "Can support/move to" - Simplified: list units in *further* adjacent provinces
        # A true "can support/move to" would require checking possible orders of those further units.
        # further_adj_provinces are short names from the graph
        further_adj_provinces_short = graph.get(adj_loc_short, {}).get(
            "ARMY", []
        ) + graph.get(adj_loc_short, {}).get("FLEET", [])

        supporting_units_info = []
        processed_further_provinces = set()
        for further_adj_loc_short in further_adj_provinces_short:
            # further_adj_province_short = game_map.loc_name.get(further_adj_loc_full, further_adj_loc_full).upper()[:3]
            # No conversion needed, it's already short
            if (
                further_adj_loc_short == adj_loc_short
                or further_adj_loc_short == unit_loc_short
            ):  # Don't list itself or origin
                continue
            if further_adj_loc_short in processed_further_provinces:
                continue
            processed_further_provinces.add(further_adj_loc_short)

            # Check for units in this further adjacent province (any coast)
            # This is a bit broad. We should check units in the specific 'further_adj_loc_full'
            # unit_in_further_loc = get_unit_at_location(board_state, further_adj_loc_full)
            # We have further_adj_loc_short. Need to check all its full variants.
            unit_in_further_loc = ""
            full_variants_of_further_short = game_map.loc_coasts.get(
                further_adj_loc_short, [further_adj_loc_short]
            )
            for fv_further in full_variants_of_further_short:
                temp_unit = get_unit_at_location(board_state, fv_further)
                if temp_unit:
                    unit_in_further_loc = temp_unit
                    break  # Found a unit in one of the coasts/base

            # if not unit_in_further_loc and further_adj_loc_full != further_adj_province_short:
            #      unit_in_further_loc = get_unit_at_location(board_state, further_adj_province_short)

            if unit_in_further_loc:
                supporting_units_info.append(unit_in_further_loc)

        if supporting_units_info:
            output_lines.append(
                f"    => Can support/move to: {', '.join(sorted(list(set(supporting_units_info))))}"
            )

    return "\n".join(output_lines)


# --- Main context generation function ---
def generate_rich_order_context(
    game: Any, power_name: str, possible_orders_for_power: Dict[str, List[str]]
) -> str:
    """
    Generates a strategic overview context string.
    Details units and SCs for power_name, including possible orders and simplified adjacencies for its units.
    Provides summaries of units and SCs for all other powers.
    """
    board_state: BoardState = game.get_state()
    game_map: GameMap = game.map
    graph = build_diplomacy_graph(game_map)

    final_context_lines: List[str] = ["<PossibleOrdersContext>"]

    # Iterate through units that have orders (keys of possible_orders_for_power are unit locations)
    for (
        unit_loc_full,
        unit_specific_possible_orders,
    ) in possible_orders_for_power.items():
        unit_str_full = get_unit_at_location(board_state, unit_loc_full)
        if (
            not unit_str_full
        ):  # Should not happen if unit_loc_full is from possible_orders keys
            continue

        unit_type_char = unit_str_full.split(" ")[0]  # 'A' or 'F'
        unit_type_long = "ARMY" if unit_type_char == "A" else "FLEET"

        loc_province_short = game_map.loc_name.get(
            unit_loc_full, unit_loc_full
        ).upper()[:3]
        loc_type_short = game_map.loc_type.get(loc_province_short, "UNKNOWN").upper()
        if loc_type_short == "COAST" or loc_type_short == "LAND":
            loc_type_display = "LAND" if loc_type_short == "LAND" else "COAST"
        else:
            loc_type_display = loc_type_short

        current_unit_lines: List[str] = []
        current_unit_lines.append(f'  <UnitContext loc="{unit_loc_full}">')

        # Unit Information section
        current_unit_lines.append("    <UnitInformation>")
        sc_owner_at_loc = get_sc_controller(game_map, board_state, unit_loc_full)
        header_content = f"Strategic territory held by {power_name}: {unit_loc_full} ({loc_type_display})"
        if sc_owner_at_loc == power_name:
            header_content += " (Controls SC)"
        elif sc_owner_at_loc:
            header_content += f" (SC controlled by {sc_owner_at_loc})"
        current_unit_lines.append(f"      {header_content}")
        current_unit_lines.append(f"      Units present: {unit_str_full}")
        current_unit_lines.append("    </UnitInformation>")

        # Possible moves section
        current_unit_lines.append("    <PossibleMoves>")
        current_unit_lines.append("      Possible moves:")
        for order_str in unit_specific_possible_orders:
            current_unit_lines.append(f"        {order_str}")
        current_unit_lines.append("    </PossibleMoves>")

        # Nearest enemy units section
        enemy_units_info = get_nearest_enemy_units(
            board_state, graph, game_map, power_name, unit_loc_full, unit_type_long, n=3
        )
        current_unit_lines.append("    <NearestEnemyUnits>")
        if enemy_units_info:
            current_unit_lines.append("      Nearest units (not ours):")
            for enemy_unit_str, enemy_path_short in enemy_units_info:
                current_unit_lines.append(
                    f"        {enemy_unit_str}, path=[{unit_loc_full}→{('→'.join(enemy_path_short[1:])) if len(enemy_path_short) > 1 else enemy_path_short[0]}]"
                )
        else:
            current_unit_lines.append("      Nearest units (not ours): None found")
        current_unit_lines.append("    </NearestEnemyUnits>")

        # Nearest supply centers (not controlled by us) section
        uncontrolled_scs_info = get_nearest_uncontrolled_scs(
            game_map, board_state, graph, power_name, unit_loc_full, unit_type_long, n=3
        )
        current_unit_lines.append("    <NearestUncontrolledSupplyCenters>")
        if uncontrolled_scs_info:
            current_unit_lines.append(
                "      Nearest supply centers (not controlled by us):"
            )
            for sc_str, dist, sc_path_short in uncontrolled_scs_info:
                current_unit_lines.append(
                    f"        {sc_str}, dist={dist}, path=[{unit_loc_full}→{('→'.join(sc_path_short[1:])) if len(sc_path_short) > 1 else sc_path_short[0]}]"
                )
        else:
            current_unit_lines.append(
                "      Nearest supply centers (not controlled by us): None found"
            )
        current_unit_lines.append("    </NearestUncontrolledSupplyCenters>")

        # Adjacent territories details section
        adj_details_str = get_adjacent_territory_details(
            game_map, board_state, unit_loc_full, unit_type_long, graph
        )
        current_unit_lines.append("    <AdjacentTerritories>")
        if adj_details_str:
            current_unit_lines.append(
                "      Adjacent territories (including units that can support/move to the adjacent territory):"
            )
            # Assuming adj_details_str is already formatted with newlines and indentation for its content
            # We might need to indent adj_details_str if it's a single block of text
            # For now, let's add a standard indent to each line of adj_details_str if it contains newlines
            if "\n" in adj_details_str:
                indented_adj_details = "\n".join(
                    [f"        {line}" for line in adj_details_str.split("\n")]
                )
                current_unit_lines.append(indented_adj_details)
            else:
                current_unit_lines.append(f"        {adj_details_str}")
        else:
            current_unit_lines.append(
                "      Adjacent territories: None relevant or all are empty/uncontested by direct threats."
            )  # Added more descriptive else
        current_unit_lines.append("    </AdjacentTerritories>")

        current_unit_lines.append("  </UnitContext>")
        final_context_lines.extend(current_unit_lines)

    final_context_lines.append("</PossibleOrdersContext>")
    return "\n".join(final_context_lines)
