from dotenv import load_dotenv
import logging
import random

logger = logging.getLogger("utils")
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

load_dotenv()


def assign_models_to_powers(randomize=True):
    """
    Example usage: define which model each power uses.
    Return a dict: { power_name: model_id, ... }
    """
    # If True, we'll randomize the model assignment.
    """model_list = [
        "o3-mini",
        "claude-3-5-sonnet-20241022",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gpt-4o",
        "gpt-4o-mini",
        "claude-3-5-haiku-20241022",
        "claude-3-7-sonnet-20250219",
        "gemini-1.5-pro",

    ]"""
    model_list = [
        "o3-mini",
        "gemini-1.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-pro",
        "gpt-4o-mini",
        "claude-3-5-haiku-20241022",
    ]
    POWERS = ['AUSTRIA', 'ENGLAND', 'FRANCE', 'GERMANY', 'ITALY', 'RUSSIA', 'TURKEY']
    if randomize:
        # Create a copy of model_list to draw from
        available_models = model_list.copy()
        result = {}
        for power in POWERS:
            # If we've used all models, replenish the available models
            if not available_models:
                available_models = model_list.copy()
            # Select and remove a random model from available ones
            model = random.choice(available_models)
            available_models.remove(model)
            result[power] = model
        logger.debug(f"CONFIG | Generated randomized power-model mapping for {len(POWERS)} powers")
        return result
    else:
        logger.debug(f"CONFIG | Using fixed power-model mapping with {len(model_list)} models")
        return {
            power: model_list[i] for i, power in enumerate(POWERS)
        }


def gather_possible_orders(game, power_name):
    """
    Returns a dictionary mapping each orderable location to the list of valid orders.
    """
    orderable_locs = game.get_orderable_locations(power_name)
    all_possible = game.get_all_possible_orders()

    result = {}
    for loc in orderable_locs:
        result[loc] = all_possible.get(loc, [])
    
    order_count = sum(len(orders) for orders in result.values())
    logger.debug(f"ORDERS | {power_name} | Found {len(result)} orderable locations with {order_count} total possible orders")
    return result


def get_valid_orders(
    game,
    client,
    board_state,
    power_name,
    possible_orders,
    game_history,
    phase_summaries,
    model_error_stats,
):
    """
    Tries up to 'max_retries' to generate and validate orders.
    If invalid, we append the error feedback to the conversation
    context for the next retry. If still invalid, return fallback.
    """
    # Track invalid orders for feedback
    invalid_info = []

    # Ask the LLM for orders
    logger.debug(f"ORDERS | {power_name} | Requesting orders from {client.model_name}")
    orders = client.get_orders(
        game=game,
        board_state=board_state,
        power_name=power_name,
        possible_orders=possible_orders,
        conversation_text=game_history,
        phase_summaries=phase_summaries,
        model_error_stats=model_error_stats,
    )

    # Validate each order
    for move in orders:
        # Example move: "A PAR H" -> unit="A PAR", order_part="H"
        tokens = move.split(" ", 2)
        if len(tokens) < 3:
            invalid_info.append(
                f"Order '{move}' is malformed; expected 'A PAR H' style."
            )
            continue
        unit = " ".join(tokens[:2])  # e.g. "A PAR"
        order_part = tokens[2]  # e.g. "H" or "S A MAR"

        # Use the internal game validation method
        if order_part == "B":
            validity = 1  # hack because game._valid_order doesn't support 'B'
        else:
            validity = game._valid_order(
                game.powers[power_name], unit, order_part, report=1
            )

        if validity == 1:
            # All orders are fully valid
            logger.debug(f"ORDERS | {power_name} | Validated {len(orders)} orders successfully")
            return orders
        else:
            logger.warning(
                f"ORDERS | {power_name} | Failed validation: '{move}' is invalid"
            )
            model_error_stats[power_name]["order_decoding_errors"] += 1
            logger.debug(f"ORDERS | {power_name} | Using fallback orders")
            fallback = client.fallback_orders(possible_orders)
            return fallback


def expand_phase_info(game, board_state):
    """
    Convert a phase like 'S1901M' into a more descriptive string:
       'Spring 1901 Movement (early game): Units can move, support, or convoy...'
    This function also references the current year to classify early/mid/late game.
    """
    phase_abbrev = board_state["phase"]  # e.g. 'S1901M'
    # Basic mapping of abbreviations
    season_map = {
        'S': "Spring",
        'F': "Fall",
        'W': "Winter",
    }
    phase_type_map = {
        'M': "Movement",
        'R': "Retreat",
        'A': "Adjustment",  # builds/disbands
    }
    
    season_char = phase_abbrev[0]  # S / F / W
    year = int(phase_abbrev[1:5])  # 1901
    phase_char = phase_abbrev[-1]  # M / R / A
    
    season_str = season_map.get(season_char, "Unknown Season")
    phase_str = phase_type_map.get(phase_char, "Unknown Phase")
    
    # Approximate game stage
    if year <= 1902:
        stage = "early game"
    elif year <= 1906:
        stage = "mid game"
    else:
        stage = "late game"
    
    # Phase-specific action text
    if phase_char == 'M':
        actions = "Players issue move, support, or convoy orders."
    elif phase_char == 'R':
        actions = "Dislodged units must retreat or disband."
    elif phase_char == 'A':
        actions = "Powers may build new units if they have more centers than units, otherwise disband if fewer."
    else:
        actions = "Unknown phase actions."
    
    return f"{season_str} {year} {phase_str} ({stage}): {actions}"


def format_location_with_expansion(game, loc, include_adjacency=False):
    """
    Return a string like 'Paris (PAR) [LAND]',
    optionally including a list of adjacent locations if include_adjacency=True.
    """
    full_name = next((name for name, abbrev in game.map.loc_name.items() if abbrev == loc), loc)
    loc_type = game.map.loc_type.get(loc, "UNKNOWN")
    formatted = f"{full_name} ({loc}) [{loc_type}]"
    
    if include_adjacency:
        adjacent_locs = game.map.loc_abut.get(loc, [])
        if adjacent_locs:
            adjacent_info = []
            for adj_loc in adjacent_locs:
                adj_full_name = game.map.loc_name.get(adj_loc, adj_loc)
                adj_type = game.map.loc_type.get(adj_loc, "UNKNOWN")
                adjacent_info.append(f"{adj_full_name} ({adj_loc}) [{adj_type}]")
            formatted += f"\n  Adjacent to: {', '.join(adjacent_info)}"
    
    return formatted


def format_power_units_and_centers(game, power_name, board_state):
    """
    Show a summarized view of a given power's units and supply centers, 
    with expansions of location names, plus a quick 'strength' count.
    Also includes information about neutral centers.
    """
    # Add neutral centers info
    output = ""
    if power_name == "NEUTRAL":
        all_controlled = set()
        for centers in board_state["centers"].values():
            all_controlled.update(centers)
        neutral_centers = [sc for sc in game.map.scs if sc not in all_controlled]
        
        if neutral_centers:
            output = "  Neutral Supply Centers:\n"
            for c in neutral_centers:
                output += f"    {format_location_with_expansion(game, c)}\n"
    else:
        units_info = board_state["units"].get(power_name, [])
        centers_info = board_state["centers"].get(power_name, [])
        
        output = f"{power_name} FORCES:\n"
        
        if units_info:
            output += "  Units:\n"
            for unit in units_info:
                # Example unit: "A PAR"
                # First char is 'A' or 'F'; substring after space is the location
                parts = unit.split(" ", 1)
                if len(parts) == 2:
                    unit_type, loc = parts
                    output += f"    {unit_type} in {format_location_with_expansion(game, loc)}\n"
                else:
                    output += f"    {unit}\n"
        else:
            output += "  Units: None\n"
        
        if centers_info:
            output += "  Supply Centers:\n"
            for c in centers_info:
                output += f"    {format_location_with_expansion(game, c)}\n"
        else:
            output += "  Supply Centers: None\n"
        
        
        # Summaries
        output += f"  Current Strength: {len(centers_info)} centers, {len(units_info)} units\n\n"
    return output


def organize_history_by_relationship(conversation_text: str) -> str:
    """
    This simplified version takes the entire conversation text
    (e.g., from game_history.get_game_history(power_name)) and returns it.
    
    Previously, we assumed we had a structured list of messages, but in practice,
    game_history is just a string, so we skip relationship-based grouping.
    
    In the future, if 'GameHistory' becomes more structured, we can parse it here.
    """
    if not conversation_text.strip():
        return "(No game history yet)\n"
    
    # For now, we can simply return the conversation text
    # or do minimal formatting as we see fit.
    output = "COMMUNICATION HISTORY:\n\n"
    output += conversation_text.strip() + "\n"
    return output


def format_possible_orders(game, possible_orders):
    """
    Display orders with strategic context, maintaining the exact order syntax
    while adding meaningful descriptions about their tactical purpose.
    """
    # First pass - analyze game state for strategic context
    supply_centers = set(game.map.scs)
    power_centers = {}
    contested_regions = set()
    
    # Gather supply center ownership
    for power_name, centers in game.get_centers().items():
        for center in centers:
            power_centers[center] = power_name
    
    # Identify contested regions (simplified approach)
    # A more sophisticated implementation would analyze unit adjacencies
    
    # Classify orders by strategic purpose
    strategic_orders = {
        "OFFENSIVE": [],  # Orders that can capture centers or threaten enemy units
        "DEFENSIVE": [],  # Orders that protect your centers or units
        "TACTICAL": [],   # Orders that improve position without immediate captures
        "SUPPORT": []     # Support orders
    }
    
    # Process each order
    for loc, orders in possible_orders.items():
        for order in orders:
            order_parts = order.split()
            order_type = None
            
            # Determine order type
            if " H" in order:
                order_type = "DEFENSIVE"
            elif " S " in order:
                order_type = "SUPPORT"
            elif " - " in order:
                # Get destination
                dest = order_parts[-1].split(" VIA")[0] if " VIA" in order else order_parts[-1]
                
                # Check if destination is a supply center
                if dest[:3] in supply_centers:
                    # If center is neutral or enemy-owned, it's offensive
                    if dest[:3] not in power_centers or power_centers[dest[:3]] != game.role:
                        order_type = "OFFENSIVE"
                    else:
                        order_type = "DEFENSIVE"  # Moving to own supply center
                else:
                    order_type = "TACTICAL"  # Non-center destination
            elif " C " in order:
                order_type = "SUPPORT"  # Classify convoy as support
            
            # Generate strategic description
            description = generate_order_description(game, order, order_type, power_centers, supply_centers)
            
            # Add to appropriate category
            if order_type:
                strategic_orders[order_type].append((order, description))
    
    # Generate formatted output
    output = "POSSIBLE ORDERS:\n\n"
    
    # Add offensive moves first - these are highest priority
    if strategic_orders["OFFENSIVE"]:
        output += "Offensive Moves (capture territory):\n"
        for order, desc in strategic_orders["OFFENSIVE"]:
            output += f"  {order} {desc}\n"
        output += "\n"
    
    # Add defensive moves
    if strategic_orders["DEFENSIVE"]:
        output += "Defensive Moves (protect territory):\n"
        for order, desc in strategic_orders["DEFENSIVE"]:
            output += f"  {order} {desc}\n"
        output += "\n"
    
    # Add tactical positioning moves
    if strategic_orders["TACTICAL"]:
        output += "Tactical Moves (improve position):\n"
        for order, desc in strategic_orders["TACTICAL"]:
            output += f"  {order} {desc}\n"
        output += "\n"
    
    # Add support moves
    if strategic_orders["SUPPORT"]:
        output += "Support Options (strengthen attacks/defense):\n"
        for order, desc in strategic_orders["SUPPORT"]:
            output += f"  {order} {desc}\n"
    
    # Log order counts for debugging
    logger.debug(f"ORDERS | Strategic classification: " + 
                 f"Offensive: {len(strategic_orders['OFFENSIVE'])}, " +
                 f"Defensive: {len(strategic_orders['DEFENSIVE'])}, " +
                 f"Tactical: {len(strategic_orders['TACTICAL'])}, " +
                 f"Support: {len(strategic_orders['SUPPORT'])}")
    
    return output


def generate_order_description(game, order, order_type, power_centers, supply_centers):
    """
    Generate a strategic description for an order based on its type and context.
    """
    order_parts = order.split()
    
    # Hold orders
    if order_type == "DEFENSIVE" and " H" in order:
        unit_loc = order_parts[1]
        if unit_loc[:3] in supply_centers:
            if unit_loc[:3] in power_centers and power_centers[unit_loc[:3]] == game.role:
                return "(secure your supply center)"
            else:
                return "(maintain position at supply center)"
        return "(maintain strategic position)"
    
    # Move orders
    elif order_type in ["OFFENSIVE", "TACTICAL", "DEFENSIVE"] and " - " in order:
        unit_type = order_parts[0]  # A or F
        unit_loc = order_parts[1]
        dest = order_parts[3].split(" VIA")[0] if len(order_parts) > 3 and "VIA" in order_parts[-1] else order_parts[3]
        
        # Moving to a supply center
        if dest[:3] in supply_centers:
            if dest[:3] not in power_centers:
                return f"(capture neutral supply center)"
            else:
                target_power = power_centers[dest[:3]]
                return f"(attack {target_power}'s supply center)"
        
        # Moving to a non-supply center
        if unit_type == "A":
            # Army moves to tactical positions
            return f"(strategic positioning)"
        else:
            # Fleet moves often about sea control
            return f"(secure sea route)"
    
    # Support orders
    elif order_type == "SUPPORT" and " S " in order:
        # Find the unit being supported and its action
        supported_part = " ".join(order_parts[3:])
        
        if " - " in supported_part:
            # Supporting a move
            supported_unit = order_parts[3]
            supported_dest = order_parts[-1]
            
            if supported_dest[:3] in supply_centers:
                if supported_dest[:3] not in power_centers:
                    return f"(support capture of neutral center)"
                else:
                    target_power = power_centers[supported_dest[:3]]
                    return f"(strengthen attack on {target_power})"
            return "(strengthen attack)"
        else:
            # Supporting a hold
            return "(reinforce defense)"
    
    # Convoy orders
    elif " C " in order:
        return "(enable army transport by sea)"
    
    # Default
    return ""


def format_convoy_paths(game, convoy_paths_possible, power_name):
    """
    Format convoy paths in a concise, actionable format focusing on strategic value.
    Input format: List of (start_loc, {required_fleets}, {possible_destinations})
    """
    # check if convoy_paths_possible is empty dictionary or list or none
    output = ""
    if not convoy_paths_possible:
        return "CONVOY POSSIBILITIES: None available.\n"

    # Get our units and centers
    our_units = set(game.get_units(power_name))
    our_armies = {unit[2:5] for unit in our_units if unit.startswith('A ')}
    our_fleets = {unit[2:5] for unit in our_units if unit.startswith('F ')}
    our_centers = set(game.get_centers(power_name))
    
    # Get all powers' units and centers
    power_units = {}
    power_centers = {}
    for pwr in game.powers:
        power_units[pwr] = {unit[2:5] for unit in game.get_units(pwr)}
        power_centers[pwr] = set(game.get_centers(pwr))

    # Make sea regions more readable
    sea_regions = {
        'NTH': "North Sea", 'MAO': "Mid-Atlantic", 'TYS': "Tyrrhenian Sea",
        'BLA': "Black Sea", 'SKA': "Skagerrak", 'ION': "Ionian Sea",
        'EAS': "Eastern Med", 'WES': "Western Med", 'BAL': "Baltic Sea",
        'BOT': "Gulf of Bothnia", 'ADR': "Adriatic Sea", 'AEG': "Aegean Sea",
        'ENG': "English Channel"
    }

    # Create a strategic analysis of convoy options
    strategic_convoys = {
        "Your Army Convoys": [],     # Convoys using your armies
        "Your Fleet Support": [],    # Using your fleets to convoy others
        "Threats": []                # Convoys that could threaten your positions
    }
    
    # Track processed convoys to avoid redundancy
    processed = set()
    
    # First pass: aggregate by sea region and filter for relevance
    region_convoy_map = {}
    
    for start, fleets, destinations in convoy_paths_possible:
        # Skip if no destinations or required fleets
        if not destinations or not fleets:
            continue
            
        # Identify army owner
        army_owner = None
        for pwr, locs in power_units.items():
            if start in locs:
                army_owner = pwr
                break
                
        # Skip redundant convoy paths (already processed similar paths)
        key = (start, tuple(sorted(fleets)), tuple(sorted(destinations)))
        if key in processed:
            continue
        processed.add(key)
        
        # Get count of our fleets in this convoy
        our_fleet_count = sum(1 for f in fleets if f in our_fleets)
        
        # Gather destinations by ownership for more concise grouping
        dest_by_owner = {}
        for dest in destinations:
            dest_owner = None
            for pwr, centers in power_centers.items():
                if dest in centers:
                    dest_owner = pwr
                    break
            dest_owner = dest_owner or "Neutral"
            dest_by_owner.setdefault(dest_owner, []).append(dest)
            
        # Determine strategic category
        if start in our_armies:
            # Our army can be convoyed
            strategic_convoys["Your Army Convoys"].append((start, fleets, dest_by_owner))
        elif our_fleet_count > 0:
            # We can help convoy someone else's army
            strategic_convoys["Your Fleet Support"].append((army_owner, start, fleets, dest_by_owner))
        elif any(dest in our_centers for dest_list in dest_by_owner.values() for dest in dest_list):
            # Someone could convoy to attack our centers
            strategic_convoys["Threats"].append((army_owner, start, fleets, dest_by_owner))
            
        # Also organize by region for secondary grouping
        region_key = "+".join(sorted(fleets))
        region_convoy_map.setdefault(region_key, []).append((start, destinations))

    # Generate the output
    output = "CONVOY POSSIBILITIES:\n"
    
    # Your army convoys (highest priority)
    if strategic_convoys["Your Army Convoys"]:
        output += "\n🚢 Your Army Convoy Options:\n"
        for start, fleets, dest_by_owner in strategic_convoys["Your Army Convoys"]:
            # Format a concise path
            sea_path = " + ".join(sea_regions.get(f, f) for f in sorted(fleets))
            # Group destinations by owner for cleaner display
            dest_summary = []
            for owner, dests in dest_by_owner.items():
                if owner == "Neutral":
                    dest_summary.append(f"Neutral: {', '.join(dests)}")
                else:
                    dest_summary.append(f"{owner}: {', '.join(dests)}")
            
            output += f"  • A {start} via {sea_path} → {'; '.join(dest_summary)}\n"
    
    # Your fleet support (medium priority)
    if strategic_convoys["Your Fleet Support"]:
        output += "\n🌊 Your Fleets Can Enable:\n"
        # Group by power to reduce repetition
        by_power = {}
        for power, start, fleets, dest_by_owner in strategic_convoys["Your Fleet Support"]:
            by_power.setdefault(power or "Unknown", []).append((start, fleets, dest_by_owner))
        
        for power, convoys in by_power.items():
            if len(convoys) > 3:  # If too many options, summarize
                output += f"  • {power}'s armies: {len(convoys)} possible convoys (use as negotiation leverage)\n"
            else:
                for start, fleets, dest_by_owner in convoys:
                    # Compress destination display
                    dest_count = sum(len(dests) for dests in dest_by_owner.values())
                    if dest_count > 3:
                        dest_display = f"{dest_count} possible destinations"
                    else:
                        dest_display = ", ".join(d for dlist in dest_by_owner.values() for d in dlist)
                    
                    sea_path = " + ".join(sea_regions.get(f, f) for f in sorted(fleets))
                    output += f"  • {power}'s A {start} via {sea_path} → {dest_display}\n"
    
    # Threats (show only critical ones)
    if strategic_convoys["Threats"]:
        output += "\n⚠️ Potential Threats:\n"
        threat_count = 0
        for power, start, fleets, dest_by_owner in strategic_convoys["Threats"]:
            # Only show threats to our supply centers
            our_threatened = []
            for dest_list in dest_by_owner.values():
                our_threatened.extend([d for d in dest_list if d in our_centers])
            
            if our_threatened:
                threat_count += 1
                if threat_count <= 3:  # Limit to most critical threats
                    sea_path = " + ".join(sea_regions.get(f, f) for f in sorted(fleets))
                    output += f"  • {power or 'Unknown'}'s A {start} via {sea_path} → {', '.join(our_threatened)}\n"
        
        if threat_count > 3:
            output += f"  • Plus {threat_count - 3} more potential threats\n"
            
    # Add a summary of sea regions activity
    if region_convoy_map:
        output += "\n🌐 Active Convoy Regions:\n"
        for region_key, convoys in region_convoy_map.items():
            if len(region_key.split("+")) > 1:
                # Multi-region convoys are strategically important
                regions = [sea_regions.get(r, r) for r in region_key.split("+")]
                start_count = len(set(start for start, _ in convoys))
                dest_count = len(set(d for _, dests in convoys for d in dests))
                output += f"  • {' + '.join(regions)}: {start_count} armies → {dest_count} destinations\n"
    
    # Log convoy analysis for debugging
    conv_counts = {k: len(v) for k, v in strategic_convoys.items()}
    logger.debug(f"CONVOYS | {power_name} | Analysis: " + 
                 ", ".join(f"{k}: {v}" for k, v in conv_counts.items()))
    
    return output

def generate_threat_assessment(game, board_state, power_name):
    """
    High-level function that tries to identify immediate threats 
    from adjacent enemy units to your units or centers.
    """
    our_units = set(loc.split(" ", 1)[1] for loc in board_state["units"].get(power_name, []))
    our_centers = set(board_state["centers"].get(power_name, []))
    
    threats = []
    for enemy_power, enemy_units in board_state["units"].items():
        if enemy_power == power_name:
            continue
        for unit_code in enemy_units:
            try:
                # e.g. "A MUN"
                parts = unit_code.split(" ", 1)
                enemy_loc = parts[1].strip()
            except IndexError:
                continue
            
            # check adjacency to our units or centers
            neighbors = game.map.loc_abut.get(enemy_loc, [])
            threatened = []
            for nbr in neighbors:
                if nbr in our_units:
                    threatened.append(f"our unit @ {nbr}")
                elif nbr in our_centers:
                    threatened.append(f"our center @ {nbr}")
            
            if threatened:
                threats.append((enemy_power, unit_code, threatened))
    
    output = "THREAT ASSESSMENT:\n"
    if not threats:
        output += "  No immediate threats detected.\n\n"
        logger.debug(f"THREATS | {power_name} | No immediate threats detected")
        return output
    
    # Log threat counts for debugging
    logger.debug(f"THREATS | {power_name} | Detected {len(threats)} threats from {len(set(t[0] for t in threats))} powers")
    
    for (enemy_pwr, code, targets) in threats:
        output += f"  {enemy_pwr}'s {code} threatens {', '.join(targets)}\n"
    output += "\n"
    return output


def generate_sc_projection(game, board_state, power_name):
    """
    Estimate potential gains from neutral or weakly held enemy SCs, plus 
    highlight which of your centers are at risk (no unit present).
    """
    our_units = set(loc.split(" ", 1)[1] for loc in board_state["units"].get(power_name, []))
    our_centers = set(board_state["centers"].get(power_name, []))
    all_centers_control = board_state["centers"]  # dict of power -> list of centers
    all_controlled = set()
    for c_list in all_centers_control.values():
        all_controlled.update(c_list)
    
    # Potential neutral SC gains
    neutral_gains = []
    for sc in game.map.scs:
        if sc not in all_controlled:  # neutral
            # see if we have a unit adjacent
            neighbors = game.map.loc_abut.get(sc, [])
            if any(nbr in our_units for nbr in neighbors):
                neutral_gains.append(sc)
    
    # Weakly held enemy SC
    contestable = []
    for e_pwr, e_centers in board_state["centers"].items():
        if e_pwr == power_name:
            continue
        enemy_units = set(loc.split(" ", 1)[1] for loc in board_state["units"].get(e_pwr, []))
        for c in e_centers:
            # if no enemy unit is physically there
            if c not in enemy_units:
                # see if we have a unit adjacent
                neighbors = game.map.loc_abut.get(c, [])
                if any(nbr in our_units for nbr in neighbors):
                    contestable.append((c, e_pwr))
    
    # Our centers at risk (no unit present)
    at_risk = [own_sc for own_sc in our_centers if own_sc not in our_units]
    
    # Format final
    output = "SUPPLY CENTER PROJECTION:\n"
    output += f"  Current Count: {len(our_centers)}\n"
    
    if neutral_gains:
        output += "  Potential neutral gains:\n"
        for sc in neutral_gains:
            output += f"    {format_location_with_expansion(game, sc)}\n"
    
    if contestable:
        output += "  Contestable enemy centers:\n"
        for c, e_pwr in contestable:
            output += f"    {format_location_with_expansion(game, c)} (currently owned by {e_pwr})\n"
    
    if at_risk:
        output += "  Centers at risk (no defending unit):\n"
        for sc in at_risk:
            output += f"    {format_location_with_expansion(game, sc)}\n"
    
    best_case = len(our_centers) + len(neutral_gains) + len(contestable)
    worst_case = len(our_centers) - len(at_risk)
    output += f"  Next-phase range: {worst_case} to {best_case} centers\n\n"
    
    # Log SC projection for debugging
    logger.debug(f"SC_PROJ | {power_name} | " +
                 f"Current: {len(our_centers)}, " +
                 f"Neutral gains: {len(neutral_gains)}, " +
                 f"Contestable: {len(contestable)}, " + 
                 f"At risk: {len(at_risk)}, " +
                 f"Range: {worst_case}-{best_case}")
    
    return output
