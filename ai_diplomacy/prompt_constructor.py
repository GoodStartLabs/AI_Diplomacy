"""
Module for constructing prompts for LLM interactions in the Diplomacy game.
"""

import logging
from typing import Dict, List, Optional, Any  # Added Any for game type placeholder

from config import config
from .utils import load_prompt, get_prompt_path, get_board_state
from .possible_order_context import (
    generate_rich_order_context,
    generate_rich_order_context_xml,
)
from .game_history import GameHistory  # Assuming GameHistory is correctly importable

# placeholder for diplomacy.Game to avoid circular or direct dependency if not needed for typehinting only
# from diplomacy import Game # Uncomment if 'Game' type hint is crucial and available

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Or inherit from parent logger

# --- Home-center lookup -------------------------------------------
HOME_CENTERS: dict[str, list[str]] = {
    "AUSTRIA": ["Budapest", "Trieste", "Vienna"],
    "ENGLAND": ["Edinburgh", "Liverpool", "London"],
    "FRANCE": ["Brest", "Marseilles", "Paris"],
    "GERMANY": ["Berlin", "Kiel", "Munich"],
    "ITALY": ["Naples", "Rome", "Venice"],
    "RUSSIA": ["Moscow", "Saint Petersburg", "Sevastopol", "Warsaw"],
    "TURKEY": ["Ankara", "Constantinople", "Smyrna"],
}


def build_context_prompt(
    game: Any,  # diplomacy.Game object
    board_state: dict,
    power_name: str,
    possible_orders: Dict[str, List[str]],
    game_history: GameHistory,
    agent_goals: Optional[List[str]] = None,
    agent_relationships: Optional[Dict[str, str]] = None,
    agent_private_diary: Optional[str] = None,
    prompts_dir: Optional[str] = None,
    include_messages: Optional[bool] = True,
    display_phase: Optional[str] = None,
    include_order_history: Optional[str] = True,
    include_possible_moves_summary: Optional[str] = False,
) -> str:
    """Builds the detailed context part of the prompt.

    Args:
        game: The game object.
        board_state: Current state of the board.
        power_name: The name of the power for whom the context is being built.
        possible_orders: Dictionary of possible orders.
        game_history: History of the game (messages, etc.).
        agent_goals: Optional list of agent's goals.
        agent_relationships: Optional dictionary of agent's relationships with other powers.
        agent_private_diary: Optional string of agent's private diary.
        prompts_dir: Optional path to the prompts directory.

    Returns:
        A string containing the formatted context.
    """
    context_template = load_prompt("context_prompt.txt", prompts_dir=prompts_dir)

    # === Agent State Debug Logging ===
    if agent_goals:
        logger.debug(f"Using goals for {power_name}: {agent_goals}")
    if agent_relationships:
        logger.debug(f"Using relationships for {power_name}: {agent_relationships}")
    if agent_private_diary:
        logger.debug(f"Using private diary for {power_name}: {agent_private_diary[:200]}...")
    # ================================

    # Get our units and centers (not directly used in template, but good for context understanding)
    # units_info = board_state["units"].get(power_name, [])
    # centers_info = board_state["centers"].get(power_name, [])

    # Get the current phase
    year_phase = board_state["phase"]  # e.g. 'S1901M'

    # Decide which context builder to use.
    _use_simple = config.SIMPLE_PROMPTS
    if possible_orders is None:
        possible_orders_context_str = "(not relevant in this context)"
    else:
        if _use_simple:
            possible_orders_context_str = generate_rich_order_context(game, power_name, possible_orders, include_summary=include_possible_moves_summary)
        else:
            possible_orders_context_str = generate_rich_order_context_xml(game, power_name, possible_orders)

    if include_messages:
        messages_this_round_text = game_history.get_messages_this_round(power_name=power_name, current_phase_name=year_phase)
        if not messages_this_round_text.strip():
            messages_this_round_text = "\n(No messages this round)\n"
    else:
        messages_this_round_text = "\n"

    # Separate active and eliminated powers for clarity
    active_powers = [p for p in game.powers.keys() if not game.powers[p].is_eliminated()]
    eliminated_powers = [p for p in game.powers.keys() if game.powers[p].is_eliminated()]

    units_repr, centers_repr = get_board_state(board_state, game)

    # Build {home_centers}
    home_centers_str = ", ".join(HOME_CENTERS.get(power_name.upper(), []))

    order_history_str = game_history.get_order_history_for_prompt(
        game=game,  # Pass the game object for normalization
        power_name=power_name,
        current_phase_name=year_phase,
        num_movement_phases_to_show=1,
    )

    if not include_order_history:
        order_history_str = "" # !! setting to blank for ablation. REMEMBER TO REVERT!

    # Replace token only if it exists (template may not include it)
    if "{home_centers}" in context_template:
        context_template = context_template.replace("{home_centers}", home_centers_str)

    # Following the pattern for home_centers, use replace for safety
    if "{order_history}" in context_template:
        context_template = context_template.replace("{order_history}", order_history_str)

    if display_phase is None:
        display_phase = year_phase

    # Check if max_year is in the template and handle it
    if "{max_year}" in context_template:
        # For now, we'll use a default value or extract from game if available
        # This could be passed as a parameter or extracted from game settings
        max_year = getattr(game, 'max_year', 1935)  # Default to 1935 if not available
        context_template = context_template.replace("{max_year}", str(max_year))

    context = context_template.format(
        power_name=power_name,
        current_phase=display_phase,
        all_unit_locations=units_repr,
        all_supply_centers=centers_repr,
        messages_this_round=messages_this_round_text,
        possible_orders=possible_orders_context_str,
        agent_goals="\n".join(f"- {g}" for g in agent_goals) if agent_goals else "None specified",
        agent_relationships="\n".join(f"- {p}: {s}" for p, s in agent_relationships.items()) if agent_relationships else "None specified",
        agent_private_diary=agent_private_diary if agent_private_diary else "(No diary entries yet)",
    )

    return context


def construct_order_generation_prompt(
    system_prompt: str,
    game: Any,  # diplomacy.Game object
    board_state: dict,
    power_name: str,
    possible_orders: Dict[str, List[str]],
    game_history: GameHistory,
    agent_goals: Optional[List[str]] = None,
    agent_relationships: Optional[Dict[str, str]] = None,
    agent_private_diary_str: Optional[str] = None,
    prompts_dir: Optional[str] = None,
) -> str:
    """Constructs the final prompt for order generation.

    Args:
        system_prompt: The base system prompt for the LLM.
        game: The game object.
        board_state: Current state of the board.
        power_name: The name of the power for whom the prompt is being built.
        possible_orders: Dictionary of possible orders.
        game_history: History of the game (messages, etc.).
        agent_goals: Optional list of agent's goals.
        agent_relationships: Optional dictionary of agent's relationships with other powers.
        agent_private_diary_str: Optional string of agent's private diary.
        prompts_dir: Optional path to the prompts directory.

    Returns:
        A string containing the complete prompt for the LLM.
    """
    # Load prompts
    _ = load_prompt("few_shot_example.txt", prompts_dir=prompts_dir)  # Loaded but not used, as per original logic
    # Pick the phase-specific instruction file (using unformatted versions)
    phase_code = board_state["phase"][-1]  # 'M' (movement), 'R', or 'A' / 'B'
    
    # Determine base instruction file name
    if phase_code == "M":
        base_instruction_file = "order_instructions_movement_phase"
    elif phase_code in ("A", "B"):  # builds / adjustments
        base_instruction_file = "order_instructions_adjustment_phase"
    elif phase_code == "R":  # retreats
        base_instruction_file = "order_instructions_retreat_phase"
    else:  # unexpected – default to movement rules
        base_instruction_file = "order_instructions_movement_phase"
    
    # Check if country-specific prompts are enabled
    if config.COUNTRY_SPECIFIC_PROMPTS:
        # Try to load country-specific version first
        country_specific_file = get_prompt_path(f"{base_instruction_file}_{power_name.lower()}.txt")
        instructions = load_prompt(country_specific_file, prompts_dir=prompts_dir)
        
        # Fall back to generic if country-specific not found
        if not instructions:
            instructions_file = get_prompt_path(f"{base_instruction_file}.txt")
            instructions = load_prompt(instructions_file, prompts_dir=prompts_dir)
    else:
        # Load generic instruction file
        instructions_file = get_prompt_path(f"{base_instruction_file}.txt")
        instructions = load_prompt(instructions_file, prompts_dir=prompts_dir)
    _use_simple = config.SIMPLE_PROMPTS

    include_order_history = False # defaulting to not include order history in order generation prompt for now
    #if power_name.lower() == 'france':
    #    include_order_history = True # REVERT THIS

    # Build the context prompt
    context = build_context_prompt(
        game,
        board_state,
        power_name,
        possible_orders,
        game_history,
        agent_goals=agent_goals,
        agent_relationships=agent_relationships,
        agent_private_diary=agent_private_diary_str,
        prompts_dir=prompts_dir,
        include_messages=not _use_simple,  # include only when *not* simple
        include_order_history=include_order_history,
        include_possible_moves_summary=True,
    )

    # delete unused section from context:
    context = context.replace('Messages This Round\n\n\nEnd Messages', '')

    final_prompt = system_prompt + "\n\n" + context + "\n\n" + instructions

    # Make the power names more LLM friendly
    final_prompt = (
        final_prompt.replace("AUSTRIA", "Austria")
        .replace("ENGLAND", "England")
        .replace("FRANCE", "France")
        .replace("GERMANY", "Germany")
        .replace("ITALY", "Italy")
        .replace("RUSSIA", "Russia")
        .replace("TURKEY", "Turkey")
    )
    logger.debug(f"Final order generation prompt preview for {power_name}: {final_prompt[:500]}...")

    return final_prompt
