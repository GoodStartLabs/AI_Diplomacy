# ai_diplomacy/game_logic.py
import logging
import os
import json
import asyncio
from typing import Dict, Tuple, Optional, Any
from argparse import Namespace
from pathlib import Path
import re

from diplomacy import Game
from diplomacy.utils.export import to_saved_game_format, from_saved_game_format

from .agent import DiplomacyAgent, ALL_POWERS
from .clients import load_model_client
from .game_history import GameHistory
from .initialization import initialize_agent_state_ext
from .utils import atomic_write_json, assign_models_to_powers

logger = logging.getLogger(__name__)

# --- Serialization / Deserialization ---


def serialize_agent(agent: DiplomacyAgent) -> dict:
    """Converts an agent object to a JSON-serializable dictionary."""
    return {
        "power_name": agent.power_name,
        "model_id": agent.client.model_name,
        "max_tokens": agent.client.max_tokens,
        "goals": agent.goals,
        "relationships": agent.relationships,
        "full_private_diary": agent.full_private_diary,
        "private_diary": agent.private_diary,
    }


def deserialize_agent(agent_data: dict, prompts_dir: Optional[str] = None, *, override_model_id: Optional[str] = None) -> DiplomacyAgent:
    """
    Recreates an agent object from a dictionary.

    If *override_model_id* is provided (e.g. because the CLI argument
    ``--models`` was used when resuming a game), that model is loaded
    instead of the one stored in the save file.
    """
    model_id = override_model_id or agent_data["model_id"]
    client = load_model_client(model_id, prompts_dir=prompts_dir)

    # Keep the original or fallback token limit exactly as before.
    client.max_tokens = agent_data.get("max_tokens", 16000)

    agent = DiplomacyAgent(
        power_name=agent_data["power_name"],
        client=client,
        initial_goals=agent_data.get("goals", []),
        initial_relationships=agent_data.get("relationships", None),
        prompts_dir=prompts_dir,
    )

    # Restore diary state
    agent.full_private_diary = agent_data.get("full_private_diary", [])
    agent.private_diary = agent_data.get("private_diary", [])

    return agent


# --- State Management ---

_PHASE_RE = re.compile(r"^[SW](\d{4})[MRA]$")

def _phase_year(phase_name: str) -> Optional[int]:
    """
    Return the four-digit year encoded in standard phase strings
    like 'S1901M'.  For anything non-standard (e.g. 'COMPLETE')
    return None so callers can decide how to handle it.
    """
    m = _PHASE_RE.match(phase_name)
    return int(m.group(1)) if m else None



def save_game_state(
    game: Game, agents: Dict[str, DiplomacyAgent], game_history: GameHistory, output_path: str, run_config: Namespace, completed_phase_name: str
):
    """
    Serialise the entire game to JSON, preserving per-phase custom metadata
    (e.g. 'state_agents') that may have been written by earlier save passes.
    """
    logger.info(f"Saving game state to {output_path}…")

    # ------------------------------------------------------------------ #
    # 1.  If the file already exists, cache the per-phase custom blocks. #
    # ------------------------------------------------------------------ #
    previous_phase_extras: Dict[str, Dict[str, Any]] = {}
    if os.path.isfile(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as fh:
                previous_save = json.load(fh)
            for phase in previous_save.get("phases", []):
                # Keep a copy of *all* non-standard keys so that future
                # additions survive automatically.
                extras = {
                    k: v
                    for k, v in phase.items()
                    if k
                    not in {
                        "name",
                        "orders",
                        "results",
                        "messages",
                        "state",
                        "config",
                    }
                }
                if extras:
                    previous_phase_extras[phase["name"]] = extras
        except Exception as exc:
            logger.warning("Could not load previous save to retain metadata: %s", exc, exc_info=True)

    # -------------------------------------------------------------- #
    # 2.  Build the fresh base structure from the diplomacy library. #
    # -------------------------------------------------------------- #
    saved_game = to_saved_game_format(game)

    # -------------------------------------------------------------- #
    # 3.  Walk every phase and merge the metadata back in.           #
    # -------------------------------------------------------------- #
    # Capture the *current* snapshot of every live agent exactly once.
    current_state_agents = {p_name: serialize_agent(p_agent) for p_name, p_agent in agents.items() if not game.powers[p_name].is_eliminated()}

    for phase_block in saved_game.get("phases", []):
        year_val = _phase_year(phase_block["name"])
        if year_val is not None and year_val > run_config.max_year:
            break

        phase_name = phase_block["name"]        

        # 3a.  Re-attach anything we cached from a previous save.
        if phase_name in previous_phase_extras:
            phase_block.update(previous_phase_extras[phase_name])

        # 3b.  For *this* phase we also inject the fresh agent snapshot
        #      and the plans written during the turn.
        if phase_name == completed_phase_name:
            # ---- make run_config serialisable ---------------------------------
            cfg = vars(run_config).copy()
            if "prompts_dir_map" in cfg and isinstance(cfg["prompts_dir_map"], dict):
                cfg["prompts_dir_map"] = {p: str(path) for p, path in cfg["prompts_dir_map"].items()}
            if isinstance(cfg.get("prompts_dir"), Path):
                cfg["prompts_dir"] = str(cfg["prompts_dir"])
            # -------------------------------------------------------------------
            phase_block["config"] = cfg
            phase_block["state_agents"] = current_state_agents
            phase_block["order_results"] = game_history.get_orders_history_for_phase(
                game, completed_phase_name
            )

    # -------------------------------------------------------------- #
    # 4.  Attach top-level metadata and write atomically.            #
    # -------------------------------------------------------------- #
    saved_game["phase_summaries"] = getattr(game, "phase_summaries", {})
    saved_game["final_agent_states"] = {p_name: {"relationships": a.relationships, "goals": a.goals} for p_name, a in agents.items()}    

    # Filter out phases > max_year
    # saved_game["phases"] = [
    #    ph for ph in saved_game["phases"]
    #    if int(ph["name"][1:5]) <= run_config.max_year        # <= 1902, for example
    # ]
    atomic_write_json(saved_game, output_path)

    logger.info("Game state saved successfully.")


def load_game_state(
    run_dir: str,
    game_file_name: str,
    run_config: Namespace,
    resume_from_phase: Optional[str] = None,
) -> Tuple[Game, Dict[str, DiplomacyAgent], GameHistory, Optional[Namespace]]:
    """Loads and reconstructs the game state from a saved game file."""
    game_file_path = os.path.join(run_dir, game_file_name)
    if not os.path.exists(game_file_path):
        raise FileNotFoundError(f"Cannot resume. Save file not found at: {game_file_path}")

    logger.info(f"Loading game state from: {game_file_path}")
    with open(game_file_path, "r") as f:
        saved_game_data = json.load(f)

    # If resuming, find the specified phase and truncate the data after it
    if resume_from_phase:
        logger.info(f"Resuming from phase '{resume_from_phase}'. Truncating subsequent data.")
        try:
            # Find the index of the phase *before* the one we want to resume from.
            # We will start the simulation *at* the resume_from_phase.
            resume_idx = next(i for i, phase in enumerate(saved_game_data["phases"]) if phase["name"] == resume_from_phase)
            # Truncate the list to exclude everything after the resume phase
            # Note: the state saved for a given phase represents the state at the beginning of that phase.
            saved_game_data["phases"] = saved_game_data["phases"][: resume_idx + 1]

            # Wipe any data that must be regenerated.
            for key in ("orders", "results", "messages"):
                saved_game_data["phases"][-1].pop(key, None)
            logger.info(f"Game history truncated to {len(saved_game_data['phases'])} phases. The next phase to run will be {resume_from_phase}.")
        except StopIteration:
            # If the phase is not found, maybe it's the first phase (S1901M)
            if resume_from_phase == "S1901M":
                saved_game_data["phases"] = []
                logger.info("Resuming from S1901M. Starting with a clean history.")
            else:
                raise ValueError(f"Resume phase '{resume_from_phase}' not found in the save file.")

    # Reconstruct the Game object
    last_phase = saved_game_data["phases"][-1]

    # Wipe the data that must be regenerated **but preserve the keys**
    last_phase["orders"] = {}
    last_phase["results"] = {}
    last_phase["messages"] = []

    game = from_saved_game_format(saved_game_data)

    game.phase_summaries = saved_game_data.get("phase_summaries", {})

    # Reconstruct agents and game history from the *last* valid phase in the data
    if not saved_game_data["phases"]:
        # This happens if we are resuming from the very beginning (S1901M)
        logger.info("No previous phases found. Initializing fresh agents and history.")
        agents = {}  # Will be created by the main loop
        game_history = GameHistory()
    else:
        # We save the game state up to & including the current (uncompleted) phase.
        # So we need to grab the agent state from the previous (completed) phase.
        if len(saved_game_data["phases"]) <= 1:
            last_phase_data = {}
        else:
            last_phase_data = saved_game_data["phases"][-2]

        # --------------------  Rebuild agents  -------------------- #
        agents = {}

        # Build a power→model map from the CLI argument --models, if present.
        power_model_map: Dict[str, str] = {}
        if run_config and getattr(run_config, "models", None):
            provided = [m.strip() for m in run_config.models.split(",")]
            powers_order = sorted(list(ALL_POWERS))
            if len(provided) == len(powers_order):
                power_model_map = dict(zip(powers_order, provided))
            elif len(provided) == 1:
                power_model_map = dict(zip(powers_order, provided * len(powers_order)))
            else:
                raise ValueError(f"Invalid --models argument: expected 1 or {len(powers_order)} items, got {len(provided)}.")

        if "state_agents" in last_phase_data:
            logger.info("Rebuilding agents from saved state...")
            
            for power_name, agent_data in last_phase_data["state_agents"].items():
                override_id = power_model_map.get(power_name)
                prompts_dir_from_config = (
                    run_config.prompts_dir_map.get(power_name)
                    if getattr(run_config, "prompts_dir_map", None)
                    else run_config.prompts_dir  # fallback to old single path
                )
                agents[power_name] = deserialize_agent(
                    agent_data,
                    prompts_dir=prompts_dir_from_config,
                    override_model_id=override_id,
                )
            logger.info(f"Rebuilt {len(agents)} agents.")
        else:
            raise ValueError("Cannot resume: 'state_agents' key not found in the last phase of the save file.")

        # Rebuild GameHistory
        game_history = GameHistory()
        logger.info("Rebuilding game history...")
        for phase_data in saved_game_data["phases"][:-1]:
            phase_name = phase_data["name"]
            game_history.add_phase(phase_name)
            # Add messages
            for msg in phase_data.get("messages", []):
                game_history.add_message(phase_name, msg["sender"], msg["recipient"], msg["message"])
            # Add plans
            if "state_history_plans" in phase_data:
                for p_name, plan in phase_data["state_history_plans"].items():
                    game_history.add_plan(phase_name, p_name, plan)
        logger.info("Game history rebuilt.")

    return game, agents, game_history, run_config


# ai_diplomacy/game_logic.py
async def initialize_new_game(
    args: Namespace,
    game: Game,
    game_history: GameHistory,
    llm_log_file_path: str,
) -> Dict[str, DiplomacyAgent]:
    """Initializes agents for a new game (supports per-power prompt directories)."""

    powers_order = sorted(list(ALL_POWERS))

    # Parse token limits
    default_max_tokens = args.max_tokens
    model_max_tokens = {p: default_max_tokens for p in powers_order}

    if args.max_tokens_per_model:
        per_model_values = [s.strip() for s in args.max_tokens_per_model.split(",")]
        if len(per_model_values) == 7:
            for power, token_val_str in zip(powers_order, per_model_values):
                model_max_tokens[power] = int(token_val_str)
        else:
            logger.warning("Expected 7 values for --max_tokens_per_model, using default.")

    # Handle power-model mapping
    if args.models:
        provided_models = [name.strip() for name in args.models.split(",")]
        if len(provided_models) == len(powers_order):
            game.power_model_map = dict(zip(powers_order, provided_models))
        elif len(provided_models) == 1:
            game.power_model_map = dict(zip(powers_order, provided_models * 7))
        else:
            logger.error(
                f"Expected {len(powers_order)} models for --models but got {len(provided_models)}."
            )
            raise Exception(
                "Invalid number of models. Models list must be either exactly 1 or 7 models, comma delimited."
            )
    else:
        game.power_model_map = assign_models_to_powers()

    agents: Dict[str, DiplomacyAgent] = {}
    initialization_tasks = []
    logger.info("Initializing Diplomacy Agents for each power...")

    for power_name, model_id in game.power_model_map.items():
        if not game.powers[power_name].is_eliminated():
            # Determine the prompts directory for this power
            if hasattr(args, "prompts_dir_map") and args.prompts_dir_map:
                prompts_dir_for_power = args.prompts_dir_map.get(power_name, args.prompts_dir)
            else:
                prompts_dir_for_power = args.prompts_dir

            try:
                client = load_model_client(model_id, prompts_dir=prompts_dir_for_power)
                client.max_tokens = model_max_tokens[power_name]
                agent = DiplomacyAgent(
                    power_name=power_name,
                    client=client,
                    prompts_dir=prompts_dir_for_power,
                )
                agents[power_name] = agent
                logger.info(f"Preparing initialization task for {power_name} with model {model_id}")
                initialization_tasks.append(
                    initialize_agent_state_ext(
                        agent,
                        game,
                        game_history,
                        llm_log_file_path,
                        prompts_dir=prompts_dir_for_power,
                    )
                )
            except Exception as e:
                logger.error(
                    f"Failed to create agent or client for {power_name} with model {model_id}: {e}",
                    exc_info=True,
                )

    logger.info(f"Running {len(initialization_tasks)} agent initializations concurrently...")
    initialization_results = await asyncio.gather(*initialization_tasks, return_exceptions=True)

    initialized_powers = list(agents.keys())
    for i, result in enumerate(initialization_results):
        if i < len(initialized_powers):
            power_name = initialized_powers[i]
            if isinstance(result, Exception):
                logger.error(f"Failed to initialize agent state for {power_name}: {result}", exc_info=result)
            else:
                logger.info(f"Successfully initialized agent state for {power_name}.")

    return agents

