# ai_diplomacy/possible_order_context.py

from collections import deque
from typing import Dict, List, Callable, Optional, Any, Set, Tuple
from diplomacy.engine.map import Map as GameMap
from diplomacy.engine.game import Game as BoardState
import logging
import re

# Placeholder for actual map type from diplomacy.engine.map.Map
# GameMap = Any
# Type hint for board_state dictionary from game.get_state()
# BoardState = Dict[str, Any]

logger = logging.getLogger(__name__)


def build_diplomacy_graph(game_map: GameMap) -> Dict[str, Dict[str, List[str]]]:
    """
    Return graph[PROV]['ARMY'|'FLEET'] = list of 3-letter neighbour provinces.
    Works for dual-coast provinces by interrogating `abuts()` directly instead
    of relying on loc_abut.
    """
    # ── collect all 3-letter province codes ───────────────────────────────
    provs: Set[str] = {
        loc.split("/")[0][:3].upper()  # 'BUL/EC' -> 'BUL'
        for loc in game_map.locs
        if len(loc.split("/")[0]) == 3
    }

    graph: Dict[str, Dict[str, List[str]]] = {p: {"ARMY": [], "FLEET": []} for p in provs}

    # ── helper: list every concrete variant of a province ─────────────────
    def variants(code: str) -> List[str]:
        lst = list(game_map.loc_coasts.get(code, []))
        if code not in lst:
            lst.append(code)  # ensure base node included
        return lst

    # ── populate adjacency by brute-force queries to `abuts()` ────────────
    for src in provs:
        src_vers = variants(src)

        for dest in provs:
            if dest == src:
                continue
            dest_vers = variants(dest)

            # ARMY — only bases count as the origin (armies can’t sit on /EC)
            if any(
                game_map.abuts("A", src, "-", dv)  # src is the base node
                for dv in dest_vers
            ):
                graph[src]["ARMY"].append(dest)

            # FLEET — any src variant that can host a fleet is valid
            if any(game_map.abuts("F", sv, "-", dv) for sv in src_vers for dv in dest_vers):
                graph[src]["FLEET"].append(dest)

    # ── tidy up duplicates / order ---------------------------------------
    for p in graph:
        graph[p]["ARMY"] = sorted(set(graph[p]["ARMY"]))
        graph[p]["FLEET"] = sorted(set(graph[p]["FLEET"]))

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
    if "/" in start_loc_short:  # If it was STP/SC, loc_name gives STP. If it was VIE, loc_name gives VIE.
        start_loc_short = start_loc_short[:3]
    # If start_loc_full was already short (e.g. 'VIE'), get might return it as is, or its value if it was a key.
    # A simpler way for non-coastal full (like 'VIE') or already short:
    if "/" not in start_loc_full:
        start_loc_short = start_loc_full[:3]  # Ensures 'VIE' -> 'VIE', 'PAR' -> 'PAR'
    else:  # Has '/', e.g. 'STP/SC'
        start_loc_short = start_loc_full[:3]  # 'STP/SC' -> 'STP'

    if start_loc_short not in graph:
        logger.warning(f"BFS: Start province {start_loc_short} (from {start_loc_full}) not in graph. Pathfinding may fail.")
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
                if next_loc_short not in graph:  # Defensive check for neighbors not in graph keys
                    logger.warning(f"BFS: Neighbor {next_loc_short} of {current_loc_short} not in graph. Skipping.")
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


def get_sc_controller(game_map: GameMap, board_state: BoardState, location: str) -> Optional[str]:
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
            if unit_at_loc and unit_at_loc.split(" ")[2][1:4] == power_name and full_loc_variant != start_unit_loc_full:
                return True
        return False

    path_short_names = bfs_shortest_path(graph, board_state, game_map, start_unit_loc_full, start_unit_type, is_target_friendly)
    if path_short_names and len(path_short_names) > 1:  # Path includes start, so > 1 means a distinct friendly unit found
        target_loc_short = path_short_names[-1]
        # Find the actual friendly unit string at one of the full locations of target_loc_short
        friendly_unit_str = "UNKNOWN_FRIENDLY_UNIT"
        full_locs_for_target_short = game_map.loc_coasts.get(target_loc_short, [target_loc_short])
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

    all_enemy_unit_locations_full: List[Tuple[str, str]] = []  # (loc_full, unit_str_full)
    # board_state.get("units", {}) has format: { "POWER_NAME": ["A PAR", "F BRE"], ... }
    for p_name, unit_list_for_power in board_state.get("units", {}).items():
        if p_name != power_name:  # If it's an enemy power
            for unit_repr_from_state in unit_list_for_power:  # e.g., "A PAR" or "F STP/SC"
                parts = unit_repr_from_state.split(" ")
                if len(parts) == 2:
                    # unit_type_char = parts[0] # 'A' or 'F'
                    loc_full = parts[1]  # 'PAR' or 'STP/SC'

                    # Use get_unit_at_location to get the consistent full unit string like "A PAR (POWER_NAME)"
                    full_unit_str_with_power = get_unit_at_location(board_state, loc_full)
                    if full_unit_str_with_power:  # Should find the unit if iteration is correct
                        all_enemy_unit_locations_full.append((loc_full, full_unit_str_with_power))

    for target_enemy_loc_full, enemy_unit_str in all_enemy_unit_locations_full:
        target_enemy_loc_short = game_map.loc_name.get(target_enemy_loc_full, target_enemy_loc_full)
        if "/" in target_enemy_loc_short:
            target_enemy_loc_short = target_enemy_loc_short[:3]
        if "/" not in target_enemy_loc_full:
            target_enemy_loc_short = target_enemy_loc_full[:3]
        else:
            target_enemy_loc_short = target_enemy_loc_full[:3]

        def is_specific_enemy_loc(loc_short: str, current_board_state: BoardState) -> bool:
            # Check if loc_short corresponds to target_enemy_loc_full
            return loc_short == target_enemy_loc_short

        path_short_names = bfs_shortest_path(graph, board_state, game_map, start_unit_loc_full, start_unit_type, is_specific_enemy_loc)
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
) -> List[Tuple[str, int, List[str]]]:
    """
    Return up to N nearest supply centres not controlled by `power_name`,
    excluding centres that are the unit’s own province (distance 0) or
    adjacent in one move (distance 1).

    Each tuple is (sc_code + ctrl_tag, distance, path_of_short_codes).
    """
    results: List[Tuple[str, int, List[str]]] = []

    for sc_short in game_map.scs:  # all SC province codes
        controller = get_sc_controller(game_map, board_state, sc_short)
        if controller == power_name:
            continue  # already ours

        # helper for BFS target test
        def is_target(loc_short: str, _state: BoardState) -> bool:
            return loc_short == sc_short

        path = bfs_shortest_path(
            graph,
            board_state,
            game_map,
            start_unit_loc_full,
            start_unit_type,
            is_target,
        )
        if not path:
            continue  # unreachable

        distance = len(path) - 1  # moves needed

        # skip distance 0 (same province) and 1 (adjacent)
        if distance <= 1:
            continue

        tag = f"{sc_short} (Ctrl: {controller or 'None'})"
        results.append((tag, distance, path))

    # sort by distance, then SC code for tie-breaks
    results.sort(key=lambda x: (x[1], x[0]))
    return results[:n]


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

    processed_adj_provinces = set()  # To handle cases like STP/NC and STP/SC both being adjacent to BOT

    for adj_loc_short in adjacent_locs_short_for_unit:  # adj_loc_short is already short
        # adj_province_short = game_map.loc_name.get(adj_loc_full, adj_loc_full).upper()[:3] # No longer needed
        if adj_loc_short in processed_adj_provinces:  # adj_loc_short is already short and upper implicitly by map data
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
        further_adj_provinces_short = graph.get(adj_loc_short, {}).get("ARMY", []) + graph.get(adj_loc_short, {}).get("FLEET", [])

        supporting_units_info = []
        processed_further_provinces = set()
        for further_adj_loc_short in further_adj_provinces_short:
            # further_adj_province_short = game_map.loc_name.get(further_adj_loc_full, further_adj_loc_full).upper()[:3]
            # No conversion needed, it's already short
            if further_adj_loc_short == adj_loc_short or further_adj_loc_short == unit_loc_short:  # Don't list itself or origin
                continue
            if further_adj_loc_short in processed_further_provinces:
                continue
            processed_further_provinces.add(further_adj_loc_short)

            # Check for units in this further adjacent province (any coast)
            # This is a bit broad. We should check units in the specific 'further_adj_loc_full'
            # unit_in_further_loc = get_unit_at_location(board_state, further_adj_loc_full)
            # We have further_adj_loc_short. Need to check all its full variants.
            unit_in_further_loc = ""
            full_variants_of_further_short = game_map.loc_coasts.get(further_adj_loc_short, [further_adj_loc_short])
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
            output_lines.append(f"    => Can support/move to: {', '.join(sorted(list(set(supporting_units_info))))}")

    return "\n".join(output_lines)


# --- Main context generation function ---
def generate_rich_order_context_xml(game: Any, power_name: str, possible_orders_for_power: Dict[str, List[str]]) -> str:
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
    for unit_loc_full, unit_specific_possible_orders in possible_orders_for_power.items():
        unit_str_full = get_unit_at_location(board_state, unit_loc_full)
        if not unit_str_full:  # Should not happen if unit_loc_full is from possible_orders keys
            continue

        unit_type_char = unit_str_full.split(" ")[0]  # 'A' or 'F'
        unit_type_long = "ARMY" if unit_type_char == "A" else "FLEET"

        loc_province_short = game_map.loc_name.get(unit_loc_full, unit_loc_full).upper()[:3]
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
        enemy_units_info = get_nearest_enemy_units(board_state, graph, game_map, power_name, unit_loc_full, unit_type_long, n=3)
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
        uncontrolled_scs_info = get_nearest_uncontrolled_scs(game_map, board_state, graph, power_name, unit_loc_full, unit_type_long, n=3)
        current_unit_lines.append("    <NearestUncontrolledSupplyCenters>")
        if uncontrolled_scs_info:
            current_unit_lines.append("      Nearest supply centers (not controlled by us):")
            for sc_str, dist, sc_path_short in uncontrolled_scs_info:
                current_unit_lines.append(
                    f"        {sc_str}, dist={dist}, path=[{unit_loc_full}→{('→'.join(sc_path_short[1:])) if len(sc_path_short) > 1 else sc_path_short[0]}]"
                )
        else:
            current_unit_lines.append("      Nearest supply centers (not controlled by us): None found")
        current_unit_lines.append("    </NearestUncontrolledSupplyCenters>")

        # Adjacent territories details section
        adj_details_str = get_adjacent_territory_details(game_map, board_state, unit_loc_full, unit_type_long, graph)
        current_unit_lines.append("    <AdjacentTerritories>")
        if adj_details_str:
            current_unit_lines.append("      Adjacent territories (including units that can support/move to the adjacent territory):")
            # Assuming adj_details_str is already formatted with newlines and indentation for its content
            # We might need to indent adj_details_str if it's a single block of text
            # For now, let's add a standard indent to each line of adj_details_str if it contains newlines
            if "\n" in adj_details_str:
                indented_adj_details = "\n".join([f"        {line}" for line in adj_details_str.split("\n")])
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


# ---------------------------------------------------------------------------
# Regex and tiny helpers
# ---------------------------------------------------------------------------

from typing import Tuple, List, Dict, Optional, Any

# ── order-syntax matchers ─────────────────────────────────────────────────
_SIMPLE_MOVE_RE = re.compile(r"^[AF] [A-Z]{3}(?:/[A-Z]{2})? - [A-Z]{3}(?:/[A-Z]{2})?$")
_HOLD_RE = re.compile(r"^[AF] [A-Z]{3}(?:/[A-Z]{2})? H$")  # NEW
_RETREAT_RE = re.compile(r"^[AF] [A-Z]{3}(?:/[A-Z]{2})? R [A-Z]{3}(?:/[A-Z]{2})?$")
_ADJUST_RE = re.compile(r"^[AF] [A-Z]{3}(?:/[A-Z]{2})? [BD]$")  # build / disband


def _is_hold_order(order: str) -> bool:  # NEW
    return bool(_HOLD_RE.match(order.strip()))


def _norm_power(name: str) -> str:
    """Trim & uppercase for reliable comparisons."""
    return name.strip().upper()


def _is_simple_move(order: str) -> bool:
    return bool(_SIMPLE_MOVE_RE.match(order.strip()))


def _is_retreat_order(order: str) -> bool:
    return bool(_RETREAT_RE.match(order.strip()))


def _is_adjust_order(order: str) -> bool:
    return bool(_ADJUST_RE.match(order.strip()))


def _split_move(order: str) -> Tuple[str, str]:
    """Return ('A BUD', 'TRI') from 'A BUD - TRI' (validated move only)."""
    unit_part, dest = order.split(" - ")
    return unit_part.strip(), dest.strip()


# ---------------------------------------------------------------------------
# Gather *all* friendly support orders for a given move
# ---------------------------------------------------------------------------


def _all_support_examples(
    mover: str,
    dest: str,
    all_orders: Dict[str, List[str]],
) -> List[str]:
    """
    Return *every* order of the form 'A/F XYZ S <mover> - <dest>'
    issued by our other units. Order of return is input order.
    """
    target = f"{mover} - {dest}"
    supports: List[str] = []

    for loc, orders in all_orders.items():
        if mover.endswith(loc):
            continue  # skip the moving unit itself
        for o in orders:
            if " S " in o and target in o:
                supports.append(o.strip())

    return supports


def _all_support_hold_examples(
    holder: str,
    all_orders: Dict[str, List[str]],
) -> List[str]:
    """
    Return every order of the form 'A/F XYZ S <holder>' that supports
    <holder> to HOLD, excluding the holding unit itself.
    """
    target = f" S {holder}"
    supports: List[str] = []

    for loc, orders in all_orders.items():
        if holder.endswith(loc):  # skip the holding unit
            continue
        for o in orders:
            if o.strip().endswith(target):
                supports.append(o.strip())
    return supports


# ---------------------------------------------------------------------------
# Province-type resolver (handles short codes, coasts, seas)
# ---------------------------------------------------------------------------


def _province_type_display(game_map, prov_short: str) -> str:
    """
    Return 'LAND', 'COAST', or 'WATER' for the 3-letter province code.
    Falls back to 'UNKNOWN' only if nothing matches.
    """
    for full in game_map.loc_coasts.get(prov_short, [prov_short]):
        t = game_map.loc_type.get(full)
        if not t:
            continue
        t = t.upper()
        if t in ("LAND", "L"):
            return "LAND"
        if t in ("COAST", "C"):
            return "COAST"
        if t in ("WATER", "SEA", "W"):
            return "WATER"
    return "UNKNOWN"


def _dest_occupancy_desc(
    dest_short: str,
    game_map,
    board_state,
    our_power: str,
) -> str:
    """'(occupied by X)', '(occupied by X — you!)', or '(unoccupied)'"""
    occupant: Optional[str] = None
    for full in game_map.loc_coasts.get(dest_short, [dest_short]):
        u = get_unit_at_location(board_state, full)
        if u:
            occupant = u.split(" ")[-1].strip("()")
            break
    if occupant is None:
        return "(unoccupied)"
    if occupant == our_power:
        return f"(occupied by {occupant} — you!)"
    return f"(occupied by {occupant})"


# ---------------------------------------------------------------------------
# Adjacent-territory lines (used by movement-phase builder)
# ---------------------------------------------------------------------------


def _adjacent_territory_lines(
    graph,
    game_map,
    board_state,
    unit_loc_full: str,
    mover_descr: str,
    our_power: str,
) -> List[str]:
    lines: List[str] = []
    indent1 = "  "
    indent2 = "    "

    unit_loc_short = game_map.loc_name.get(unit_loc_full, unit_loc_full)[:3]
    mover_type_key = "ARMY" if mover_descr.startswith("A") else "FLEET"
    adjacents = graph.get(unit_loc_short, {}).get(mover_type_key, [])

    for adj in adjacents:
        typ_display = _province_type_display(game_map, adj)

        base_parts = [f"{indent1}{adj} ({typ_display})"]

        sc_ctrl = get_sc_controller(game_map, board_state, adj)
        if sc_ctrl:
            base_parts.append(f"SC Control: {sc_ctrl}")

        unit_here = None
        for full in game_map.loc_coasts.get(adj, [adj]):
            unit_here = get_unit_at_location(board_state, full)
            if unit_here:
                break
        if unit_here:
            base_parts.append(f"Units: {unit_here}")

        lines.append(" ".join(base_parts))

        # second analytical line if occupied
        if unit_here:
            pwr = unit_here.split(" ")[-1].strip("()")
            if pwr == our_power:
                friend_descr = unit_here.split(" (")[0]
                lines.append(f"{indent2}Support hold: {mover_descr} S {friend_descr}")
            else:
                lines.append(f"{indent2}-> {unit_here} can support or contest {mover_descr}’s moves and vice-versa")

    return lines


# ---------------------------------------------------------------------------
# Movement-phase generator (UNCHANGED LOGIC)
# ---------------------------------------------------------------------------


def _generate_rich_order_context_movement(
    game: Any,
    power_name: str,
    possible_orders_for_power: Dict[str, List[str]],
) -> str:
    """
    Produce the <Territory …> blocks *exactly* as before for movement phases.
    """
    board_state = game.get_state()
    game_map = game.map
    graph = build_diplomacy_graph(game_map)

    blocks: List[str] = []
    me = _norm_power(power_name)

    for unit_loc_full, orders in possible_orders_for_power.items():
        unit_full_str = get_unit_at_location(board_state, unit_loc_full)
        if not unit_full_str:
            continue

        unit_power = unit_full_str.split(" ")[-1].strip("()")
        if _norm_power(unit_power) != me:
            continue  # Skip units that aren’t ours

        mover_descr, _ = _split_move(f"{unit_full_str.split(' ')[0]} {unit_loc_full} - {unit_loc_full}")

        prov_short = game_map.loc_name.get(unit_loc_full, unit_loc_full)[:3]
        prov_type_disp = _province_type_display(game_map, prov_short)
        sc_tag = " (SC)" if prov_short in game_map.scs else ""

        owner = get_sc_controller(game_map, board_state, unit_loc_full) or "None"
        owner_line = f"Held by {owner} (You)" if owner == power_name else f"Held by {owner}"

        ind = "  "
        block: List[str] = [f"<Territory {prov_short}>"]
        block.append(f"{ind}({prov_type_disp}){sc_tag}")
        block.append(f"{ind}{owner_line}")
        block.append(f"{ind}Units present: {unit_full_str}")

        # ----- Adjacent territories -----
        block.append("# Adjacent territories:")
        block.extend(_adjacent_territory_lines(graph, game_map, board_state, unit_loc_full, mover_descr, power_name))

        # ----- Nearest enemy units -----
        block.append("# Nearest units (not ours):")
        enemies = get_nearest_enemy_units(
            board_state,
            graph,
            game_map,
            power_name,
            unit_loc_full,
            "ARMY" if mover_descr.startswith("A") else "FLEET",
            n=3,
        )
        for u, path in enemies:
            path_disp = "→".join([unit_loc_full] + path[1:])
            block.append(f"{ind}{u}, path [{path_disp}]")

        # ----- Nearest uncontrolled SCs -----
        block.append("# Nearest supply centers (not controlled by us):")
        scs = get_nearest_uncontrolled_scs(
            game_map,
            board_state,
            graph,
            power_name,
            unit_loc_full,
            "ARMY" if mover_descr.startswith("A") else "FLEET",
            n=3,
        )
        for sc_str, dist, sc_path in scs:
            path_disp = "→".join([unit_loc_full] + sc_path[1:])
            sc_fmt = sc_str.replace("Ctrl:", "Controlled by")
            block.append(f"{ind}{sc_fmt}, path [{path_disp}]")

        # ----- Possible moves -----
        block.append(f"# Possible {mover_descr} unit movements & supports:")

        simple_moves = [o for o in orders if _is_simple_move(o)]
        hold_orders = [o for o in orders if _is_hold_order(o)]  # NEW

        if not simple_moves and not hold_orders:
            block.append(f"{ind}None")
        else:
            # ---- Moves (same behaviour as before) ----
            for mv in simple_moves:
                mover, dest = _split_move(mv)
                occ = _dest_occupancy_desc(dest.split("/")[0][:3], game_map, board_state, power_name)
                block.append(f"{ind}{mv} {occ}")

                for s in _all_support_examples(mover, dest, possible_orders_for_power):
                    block.append(f"{ind * 2}Available Support: {s}")

            # ---- Holds (new) ----
            for hd in hold_orders:
                holder = hd.split(" H")[0]  # e.g., 'F DEN'
                block.append(f"{ind}{hd}")

                for s in _all_support_hold_examples(holder, possible_orders_for_power):
                    block.append(f"{ind * 2}Available Support: {s}")

        block.append(f"</Territory {prov_short}>")
        blocks.append("\n".join(block))

    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# Retreat-phase builder – echo orders verbatim, no tags
# ---------------------------------------------------------------------------


def _generate_rich_order_context_retreat(
    game: Any,
    power_name: str,
    possible_orders_for_power: Dict[str, List[str]],
) -> str:
    """
    Flatten all retreat / disband orders into one list:
        A PAR R PIC
        A PAR D
        F NTH R HEL
    If the engine supplies nothing, return the standard placeholder.
    """
    lines: List[str] = []
    for orders in possible_orders_for_power.values():
        for o in orders:
            lines.append(o.strip())

    return "\n".join(lines) if lines else "(No dislodged units)"


# ---------------------------------------------------------------------------
# Adjustment-phase builder – summary line + orders, no WAIVEs, no tags
# ---------------------------------------------------------------------------


def _generate_rich_order_context_adjustment(
    game: Any,
    power_name: str,
    possible_orders_for_power: Dict[str, List[str]],
) -> str:
    """
    * First line states how many builds are allowed or disbands required.
    * Echo every B/D order exactly as supplied, skipping WAIVE.
    * No wrapper tags.
    """
    board_state = game.get_state()
    sc_owned = len(board_state.get("centers", {}).get(power_name, []))
    units_num = len(board_state.get("units", {}).get(power_name, []))
    delta = sc_owned - units_num  # +ve ⇒ builds, -ve ⇒ disbands

    # ----- summary line ----------------------------------------------------
    if delta > 0:
        summary = f"Builds available: {delta}"
    elif delta < 0:
        summary = f"Disbands required: {-delta}"
    else:
        summary = "No builds or disbands required"

    # ----- collect orders (skip WAIVE) -------------------------------------
    lines: List[str] = [summary]
    for orders in possible_orders_for_power.values():
        for o in orders:
            if "WAIVE" in o.upper():
                continue
            lines.append(o.strip())

    # If nothing but the summary, just return the summary.
    return "\n".join(lines) if len(lines) > 1 else summary


# ---------------------------------------------------------------------------
# Condensed summary builder – now groups friendly supports under *their* move
# ---------------------------------------------------------------------------
def _generate_condensed_move_summary(
    game: Any,
    power_name: str,
    possible_orders_for_power: Dict[str, List[str]],
) -> str:
    """
    Compact, human-readable list of every legal order for *our* units,
    grouping each friendly support beneath the move / hold it aids.

    Example:

        ## F NAO possible orders:
        F NAO - CLY
        F NAO - LVP
            A WAL S F NAO - LVP
        F NAO - NWG
        F NAO H
    """
    board_state = game.get_state()

    # ---- build a quick lookup of *our* unit descriptors -------------------
    our_unit_descs: Set[str] = set()
    for u in board_state.get("units", {}).get(power_name, []):
        kind, loc_full = u.split(" ")
        base = loc_full.split("/")[0]        # STP from STP/SC
        our_unit_descs.update({f"{kind} {loc_full}", f"{kind} {base}"})

    lines: List[str] = [
        "# Summary of possible orders (not including supports of other powers' units):"
    ]

    # deterministic unit order
    for loc in sorted(possible_orders_for_power.keys()):
        unit_full = get_unit_at_location(board_state, loc)
        if not unit_full:
            continue
        unit_desc = unit_full.split(" (")[0].strip()          # e.g. 'F BRE'
        if unit_desc not in our_unit_descs:                   # safety guard
            continue

        orders = possible_orders_for_power[loc]
        simple_moves = [o for o in orders if _is_simple_move(o)]
        hold_orders  = [o for o in orders if _is_hold_order(o)]

        lines.append(f"## {unit_desc} possible orders:")

        # ---- helper: attach friendly supports to a reference order --------
        def _friendly_supports_for(target_order: str) -> List[str]:
            """Return supports (from any of our units) that aid <target_order>."""
            if " - " in target_order:        # it's a MOVE
                mover, dest = _split_move(target_order)
                supps = _all_support_examples(mover, dest, possible_orders_for_power)
            else:                            # it's a HOLD
                holder = target_order.split(" H")[0]
                supps = _all_support_hold_examples(holder, possible_orders_for_power)

            # keep only supports whose *target* unit is ours
            friendly: List[str] = []
            for s in supps:
                tgt = (
                    s.split(" S ", 1)[1]           # chop before ' S '
                      .split(" - ")[0]
                      .split(" H")[0]
                      .strip()
                )
                if tgt in our_unit_descs:
                    friendly.append(s)
            return friendly

        # ---- emit moves (each followed by its friendly supports) ----------
        for mv in simple_moves:
            lines.append(mv)
            for s in _friendly_supports_for(mv):
                lines.append(f"    {s}")

        # ---- emit holds ---------------------------------------------------
        for hd in hold_orders:
            lines.append(hd)
            for s in _friendly_supports_for(hd):
                lines.append(f"    {s}")

    return "\n".join(lines)



# ---------------------------------------------------------------------------
# Public entry-point – unchanged behaviour except stricter unit filtering
# ---------------------------------------------------------------------------
def generate_rich_order_context(
    game: Any,
    power_name: str,
    possible_orders_for_power: Dict[str, List[str]],
    *,
    include_full: bool = True,
    include_summary: bool = False,
) -> str:
    """
    Dispatch to phase-specific builders and (optionally) append the condensed
    move summary.

    Args:
        include_full    – emit the full rich context (default True)
        include_summary – emit the condensed per-unit order list (default False)
    """

    #if power_name.lower() == 'germany':
    #    include_summary = True
    #    include_full = True

    phase_type = game.current_short_phase[-1]
    sections: List[str] = []

    # --- full context ------------------------------------------------------
    if include_full:
        if phase_type == "M":
            sections.append(
                _generate_rich_order_context_movement(
                    game, power_name, possible_orders_for_power
                )
            )
        elif phase_type == "R":
            sections.append(
                _generate_rich_order_context_retreat(
                    game, power_name, possible_orders_for_power
                )
            )
        elif phase_type == "A":
            sections.append(
                _generate_rich_order_context_adjustment(
                    game, power_name, possible_orders_for_power
                )
            )
        else:
            # unknown → treat as movement
            sections.append(
                _generate_rich_order_context_movement(
                    game, power_name, possible_orders_for_power
                )
            )

    # --- condensed summary (movement only) --------------------------------
    if include_summary and phase_type == "M":
        sections.append(
            _generate_condensed_move_summary(
                game, power_name, possible_orders_for_power
            )
        )

    return "\n\n".join(sections).strip()
