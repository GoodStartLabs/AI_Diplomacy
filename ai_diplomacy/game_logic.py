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
from .utils import atomic_write_json, atomic_write_json_async, assign_models_to_powers

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


def deserialize_agent(agent_data: dict, prompts_dir: Optional[str] = None, *, override_model_id: Optional[str] = None, override_max_tokens: Optional[int] = None) -> DiplomacyAgent:
    """
    Recreates an agent object from a dictionary.

    If *override_model_id* is provided (e.g. because the CLI argument
    ``--models`` was used when resuming a game), that model is loaded
    instead of the one stored in the save file.
    
    If *override_max_tokens* is provided (e.g. because the CLI argument
    ``--max_tokens`` was used when resuming a game), that value is used
    instead of the one stored in the save file.
    """
    model_id = override_model_id or agent_data["model_id"]
    client = load_model_client(model_id, prompts_dir=prompts_dir)

    # Use override if provided, otherwise use saved value, otherwise default to 16000
    client.max_tokens = override_max_tokens or agent_data.get("max_tokens", 16000)

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



async def save_game_state(
    game: "Game",
    agents: Dict[str, "DiplomacyAgent"],
    game_history: "GameHistory",
    output_path: str,
    run_config,
    completed_phase_name: str,
):
    """
    Serialise the entire game to JSON, preserving per-phase custom metadata and
    adding `state_phase_summaries` for every completed phase.
    """
    logger.info(f"Saving game state to {output_path}…")

    # 1.  If a previous save exists, cache its extra per-phase keys -------------
    previous_phase_extras: Dict[str, Dict[str, Any]] = {}
    if os.path.isfile(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as fh:
                previous_save = json.load(fh)
            for phase in previous_save.get("phases", []):
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

    # 2.  Base structure from diplomacy-python ---------------------------------
    saved_game = to_saved_game_format(game)

    # 3.  Re-insert extras, order_results, phase_summaries, state_agents --------
    current_state_agents = {
        p_name: serialize_agent(p_agent)
        for p_name, p_agent in agents.items()
        if not game.powers[p_name].is_eliminated()
    }

    for phase_block in saved_game.get("phases", []):
        phase_name = phase_block["name"]

        # 3a.  Merge cached extras
        if phase_name in previous_phase_extras:
            phase_block.update(previous_phase_extras[phase_name])

        # 3b.  Inject data only for the newly completed phase
        if phase_name == completed_phase_name:
            # Config made JSON-safe
            cfg = vars(run_config).copy()
            if isinstance(cfg.get("prompts_dir"), os.PathLike):
                cfg["prompts_dir"] = str(cfg["prompts_dir"])
            if "prompts_dir_map" in cfg and isinstance(cfg["prompts_dir_map"], dict):
                cfg["prompts_dir_map"] = {p: str(v) for p, v in cfg["prompts_dir_map"].items()}

            phase_block["config"] = cfg
            phase_block["state_agents"] = current_state_agents
            phase_block["order_results"] = game_history.get_orders_history_for_phase(game, completed_phase_name)

            # NEW: save per-power phase summaries
            hist = game_history._get_phase(phase_name)
            if hist and hist.phase_summaries:
                phase_block["state_phase_summaries"] = hist.phase_summaries

    # 4.  Top-level metadata ----------------------------------------------------
    saved_game["phase_summaries"] = getattr(game, "phase_summaries", {})
    saved_game["final_agent_states"] = {
        p_name: {"relationships": a.relationships, "goals": a.goals} for p_name, a in agents.items()
    }

    await atomic_write_json_async(saved_game, output_path)
    logger.info("Game state saved successfully.")


def load_game_state(
    run_dir: str,
    game_file_name: str,
    run_config,
    resume_from_phase: Optional[str] = None,
) -> Tuple["Game", Dict[str, "DiplomacyAgent"], "GameHistory", Optional[Any]]:
    """
    Load and fully re-hydrate the game, agents and GameHistory – including
    `orders_by_power`, `results_by_power`, `submitted_orders_by_power`,
    and per-power `phase_summaries`.
    """
    from collections import defaultdict  # local to avoid new global import

    game_file_path = os.path.join(run_dir, game_file_name)
    if not os.path.exists(game_file_path):
        raise FileNotFoundError(f"Cannot resume. Save file not found at: {game_file_path}")

    logger.info(f"Loading game state from: {game_file_path}")
    with open(game_file_path, "r") as f:
        saved_game_data = json.load(f)

    # --- Trim history if --resume_from_phase was requested --------------------
    if resume_from_phase:
        try:
            resume_idx = next(i for i, ph in enumerate(saved_game_data["phases"]) if ph["name"] == resume_from_phase)
            saved_game_data["phases"] = saved_game_data["phases"][: resume_idx + 1]
            for k in ("orders", "results", "messages"):
                saved_game_data["phases"][-1].pop(k, None)
            logger.info("Game history truncated for resume.")
        except StopIteration:
            if resume_from_phase == "S1901M":
                saved_game_data["phases"] = []
                logger.info("Resuming from start – clean history.")
            else:
                raise ValueError(f"Resume phase '{resume_from_phase}' not found in the save file.")

    # --- Reconstruct Game object ---------------------------------------------
    if saved_game_data.get("phases"):
        saved_game_data["phases"][-1].update({"orders": {}, "results": {}, "messages": []})
    game = from_saved_game_format(saved_game_data)
    game.phase_summaries = saved_game_data.get("phase_summaries", {})

    # --- Rebuild agents -------------------------------------------------------
    agents: Dict[str, "DiplomacyAgent"] = {}
    power_model_map: Dict[str, str] = {}
    powers_order = sorted(list(ALL_POWERS))
    
    # Parse token limits from run_config
    default_max_tokens = run_config.max_tokens if run_config and hasattr(run_config, 'max_tokens') else 16000
    model_max_tokens = {p: default_max_tokens for p in powers_order}
    
    if run_config and hasattr(run_config, 'max_tokens_per_model') and run_config.max_tokens_per_model:
        per_model_values = [s.strip() for s in run_config.max_tokens_per_model.split(",")]
        if len(per_model_values) == 7:
            for power, token_val_str in zip(powers_order, per_model_values):
                model_max_tokens[power] = int(token_val_str)
        else:
            logger.warning("Expected 7 values for --max_tokens_per_model, using default.")
    
    if run_config and getattr(run_config, "models", None):
        provided = [m.strip() for m in run_config.models.split(",")]
        if len(provided) == len(powers_order):
            power_model_map = dict(zip(powers_order, provided))
        elif len(provided) == 1:
            power_model_map = dict(zip(powers_order, provided * len(powers_order)))
        else:
            raise ValueError(f"Invalid --models argument: expected 1 or {len(powers_order)} items, got {len(provided)}.")

    if saved_game_data.get("phases"):
        last_phase_data = saved_game_data["phases"][-2] if len(saved_game_data["phases"]) > 1 else {}
        if "state_agents" not in last_phase_data:
            raise ValueError("Cannot resume: 'state_agents' key missing in last completed phase.")

        for power_name, agent_data in last_phase_data["state_agents"].items():
            override_id = power_model_map.get(power_name)
            prompts_dir_from_config = (
                run_config.prompts_dir_map.get(power_name)
                if getattr(run_config, "prompts_dir_map", None)
                else run_config.prompts_dir
            )
            agents[power_name] = deserialize_agent(
                agent_data,
                prompts_dir=prompts_dir_from_config,
                override_model_id=override_id,
                override_max_tokens=model_max_tokens.get(power_name),
            )

    # --- Rebuild GameHistory --------------------------------------------------
    game_history = GameHistory()
    for phase_data in saved_game_data["phases"][:-1]:
        phase_name = phase_data["name"]
        game_history.add_phase(phase_name)
        ph_obj = game_history._get_phase(phase_name)

        # Messages
        for msg in phase_data.get("messages", []):
            game_history.add_message(phase_name, msg["sender"], msg["recipient"], msg["message"])

        # Plans
        for p_name, plan in phase_data.get("state_history_plans", {}).items():
            game_history.add_plan(phase_name, p_name, plan)

        # --- NEW restorations --------------------------------------------------
        # Accepted orders
        ph_obj.orders_by_power = defaultdict(list, phase_data.get("orders", {}))

        # Results (wrap scalar -> list[list[str]])
        ph_obj.results_by_power = defaultdict(list)
        for pwr, res_list in phase_data.get("results", {}).items():
            if res_list and isinstance(res_list[0], list):
                ph_obj.results_by_power[pwr] = res_list
            else:
                ph_obj.results_by_power[pwr] = [[r] for r in res_list]

        # Phase summaries
        ph_obj.phase_summaries = phase_data.get("state_phase_summaries", {})

        # Submitted orders reconstructed from order_results
        submitted = defaultdict(list)
        for pwr, type_map in phase_data.get("order_results", {}).items():
            for lst in type_map.values():
                for entry in lst:
                    if isinstance(entry, dict):
                        order_str = entry.get("order")
                    else:
                        order_str = entry
                    if order_str:
                        submitted[pwr].append(order_str)
        ph_obj.submitted_orders_by_power = submitted

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
                logger.info(f"[{power_name}] Using prompts_dir from map: {prompts_dir_for_power}")
            else:
                prompts_dir_for_power = args.prompts_dir
                logger.info(f"[{power_name}] Using prompts_dir from args: {prompts_dir_for_power}")

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

