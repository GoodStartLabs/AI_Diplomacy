import argparse
import logging
import random
import time
import dotenv
import os
import json
import asyncio
from collections import defaultdict
from argparse import Namespace
from typing import Dict, List, Tuple
import shutil
import sys

# Suppress Gemini/PaLM gRPC warnings
os.environ["GRPC_PYTHON_LOG_LEVEL"] = "40"  # ERROR level only
os.environ["GRPC_VERBOSITY"] = "ERROR"  # Additional gRPC verbosity control
os.environ["ABSL_MIN_LOG_LEVEL"] = "2"  # Suppress abseil warnings
# Disable gRPC forking warnings
os.environ["GRPC_POLL_STRATEGY"] = "poll"  # Use 'poll' for macOS compatibility

from diplomacy import Game

from ai_diplomacy.utils import get_valid_orders, gather_possible_orders, parse_prompts_dir_arg
from ai_diplomacy.negotiations import conduct_negotiations
from ai_diplomacy.planning import planning_phase
from ai_diplomacy.game_history import GameHistory
from ai_diplomacy.agent import DiplomacyAgent
from ai_diplomacy.game_logic import (
    save_game_state,
    load_game_state,
    initialize_new_game,
    serialize_agent,
    deserialize_agent,
)
from ai_diplomacy.diary_logic import run_diary_consolidation
from config import config

dotenv.load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
# Silence noisy dependencies
logging.getLogger("httpx").setLevel(logging.WARNING)
# logging.getLogger("root").setLevel(logging.WARNING) # Assuming root handles AFC


def _str2bool(v: str) -> bool:
    v = str(v).lower()
    if v in {"1", "true", "t", "yes", "y"}:
        return True
    if v in {"0", "false", "f", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError(f"Boolean value expected, got '{v}'")

def _detect_victory(game: Game, threshold: int = 18) -> bool:
    """True iff any power already owns ≥ `threshold` supply centres."""
    return any(len(p.centers) >= threshold for p in game.powers.values())

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Run a Diplomacy game simulation with configurable parameters."
    )
    parser.add_argument(
        "--run_dir",
        type=str,
        default="",
        help="Directory for results. If it exists, the game resumes. If not, it's created. Defaults to a new timestamped directory.",
    )
    parser.add_argument(
        "--output",            # alias for back compatibility
        dest="run_dir",        # write to the same variable as --run_dir
        type=str,
        help=argparse.SUPPRESS # hides it from `--help`
    )
    parser.add_argument(
        "--critical_state_analysis_dir",
        type=str,
        default="",
        help="Resumes from the game state in --run_dir, but saves new results to a separate dir, leaving the original run_dir intact.",
    )
    parser.add_argument(
        "--resume_from_phase",
        type=str,
        default="",
        help="Phase to resume from (e.g., 'S1902M'). Requires --run_dir. IMPORTANT: This option clears any existing phase results ahead of & including the specified resume phase.",
    )
    parser.add_argument(
        "--end_at_phase",
        type=str,
        default="",
        help="Phase to end the simulation after (e.g., 'F1905M').",
    )
    parser.add_argument(
        "--max_year",
        type=int,
        help="Maximum year to simulate. The game will stop once this year is reached.",
    )
    parser.add_argument(
        "--num_negotiation_rounds",
        type=int,
        default=0,
        help="Number of negotiation rounds per phase.",
    )
    parser.add_argument(
        "--models",
        type=str,
        default="",
        help=(
            "Comma-separated list of model names to assign to powers in order. "
            "The order is: AUSTRIA, ENGLAND, FRANCE, GERMANY, ITALY, RUSSIA, TURKEY."
        ),
    )
    parser.add_argument(
        "--planning_phase", 
        action="store_true",
        help="Enable the planning phase for each power to set strategic directives.",
    )
    parser.add_argument(
        "--max_tokens",
        type=int,
        default=16000,
        help="Maximum number of new tokens to generate per LLM call (default: 16000)."
    )
    parser.add_argument(
        "--seed_base",
        type=int,
        default=42,
        help="RNG seed placeholder for compatibility with experiment_runner. Currently unused."
    )
    parser.add_argument(
        "--max_tokens_per_model",
        type=str,
        default="",
        help="Comma-separated list of 7 token limits (in order: AUSTRIA, ENGLAND, FRANCE, GERMANY, ITALY, RUSSIA, TURKEY). Overrides --max_tokens."
    )
    parser.add_argument(
        "--prompts_dir",
        type=str,
        default=None,
        help="Path to the directory containing prompt files. Defaults to the packaged prompts directory."
    )
    parser.add_argument(
        "--simple_prompts",
        type=_str2bool,
        nargs="?",
        const=True,
        default=True,
        help=(
            "When true (1 / true / yes) the engine switches to simpler prompts which low-midrange models handle better."
        ),
    )
    parser.add_argument(
        "--generate_phase_summaries",
        type=_str2bool,
        nargs="?",
        const=True,
        default=False,
        help=(
            "When true (1 / true / yes / default) generates narrative phase summaries. "
            "Set to false (0 / false / no) to skip phase summary generation."
        ),
    )
    parser.add_argument(
        "--use_unformatted_prompts",
        type=_str2bool,
        nargs="?",
        const=True,
        default=False,
        help=(
            "When true (1 / true / yes / default) uses two-step approach: unformatted prompts + Gemini Flash formatting. "
            "Set to false (0 / false / no) to use original single-step formatted prompts."
        ),
    )
    parser.add_argument(
        "--country_specific_prompts",
        type=_str2bool,
        nargs="?",
        const=True,
        default=False,
        help=(
            "When true (1 / true / yes) enables country-specific order and conversation prompts. "
            "Each power will use their own custom prompts if available (e.g., order_instructions_movement_phase_france.txt). "
            "Falls back to generic prompts if country-specific not found."
        ),
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode: log every LLM input and output to the console.",
    )

    return parser.parse_args()


async def main():
    args = parse_arguments()
    start_whole = time.time()

    # Apply debug flag so all LLM I/O logging can use it, and show existing logger.debug() calls
    config.DEBUG = getattr(args, "debug", False)
    if config.DEBUG:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Debug mode enabled: logger.debug() messages and every LLM input/output will be shown.")

    logger.info(f"args.simple_prompts = {args.simple_prompts} (type: {type(args.simple_prompts)}), args.prompts_dir = {args.prompts_dir}")
    logger.info(f"config.SIMPLE_PROMPTS before update = {config.SIMPLE_PROMPTS}")
    
    # IMPORTANT: Check if user explicitly provided a prompts_dir
    user_provided_prompts_dir = args.prompts_dir is not None
    
    if args.simple_prompts:
        config.SIMPLE_PROMPTS = True
        if args.prompts_dir is None:
            pkg_root = os.path.join(os.path.dirname(__file__), "ai_diplomacy")
            args.prompts_dir = os.path.join(pkg_root, "prompts_simple")
            logger.info(f"Set prompts_dir to {args.prompts_dir} because simple_prompts=True and prompts_dir was None")
        else:
            # User provided their own prompts_dir, but simple_prompts is True
            # This is likely a conflict - warn the user
            logger.warning(f"Both --simple_prompts=True and --prompts_dir={args.prompts_dir} were specified. Using user-provided prompts_dir.")
    else:
        logger.info(f"simple_prompts is False, using prompts_dir: {args.prompts_dir}")

    # Prompt-dir validation & mapping
    try:
        logger.info(f"About to parse prompts_dir: {args.prompts_dir}")
        args.prompts_dir_map = parse_prompts_dir_arg(args.prompts_dir)
        logger.info(f"prompts_dir_map after parsing: {args.prompts_dir_map}")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    # Handle phase summaries flag - import narrative module only if enabled
    if args.generate_phase_summaries:
        import ai_diplomacy.narrative
        logger.info("Phase summary generation enabled")
    else:
        logger.info("Phase summary generation disabled")

    # Handle unformatted prompts flag
    if args.use_unformatted_prompts:
        config.USE_UNFORMATTED_PROMPTS = True
        logger.info("Using two-step approach: unformatted prompts + Gemini Flash formatting")
    else:
        config.USE_UNFORMATTED_PROMPTS = False
        logger.info("Using original single-step formatted prompts")
    
    # Handle country-specific prompts flag
    if args.country_specific_prompts:
        config.COUNTRY_SPECIFIC_PROMPTS = True
        logger.info("Country-specific prompts enabled - powers will use their custom prompts when available")
    else:
        config.COUNTRY_SPECIFIC_PROMPTS = False
        logger.info("Using generic prompts for all powers")

    if args.max_year == None:
        if args.end_at_phase:
            # infer the max year
            args.max_year = int(args.end_at_phase[1:5])
        else:
            raise Exception("--max_year is required.")

    # --- Determine Run Directory and Mode (New vs. Resume) ---
    run_dir = args.run_dir
    is_resuming = False
    if run_dir and os.path.exists(run_dir) and not args.critical_state_analysis_dir:
        is_resuming = True
    
    if args.critical_state_analysis_dir:
        if not run_dir:
            raise ValueError("--run_dir must be given when using --critical_state_analysis_dir")

        original_run_dir = run_dir                      # where the live game lives
        run_dir = args.critical_state_analysis_dir      # where new artefacts will be written
        os.makedirs(run_dir, exist_ok=True)

        # copy the most-recent game snapshot so we can resume from it
        src = os.path.join(original_run_dir, "lmvsgame.json")
        dst = os.path.join(run_dir,        "lmvsgame.json")
        if not os.path.exists(src):
            raise FileNotFoundError(f"No saved game found at {src}")
        if not os.path.exists(dst):
            shutil.copy2(src, dst)

        is_resuming = True                              # we *are* continuing a game
        logger.info(
            "Critical state analysis: resuming from %s, writing new results to %s",
            original_run_dir, run_dir,
        )

    
    if not run_dir:
        # Default behavior: create a new timestamped directory
        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        run_dir = f"./results/{timestamp_str}"
    
    os.makedirs(run_dir, exist_ok=True)
    logger.info(f"Using result directory: {run_dir}")

    # --- 2. Setup Logging and File Paths ---
    general_log_file_path = os.path.join(run_dir, "general_game.log")
    file_handler = logging.FileHandler(general_log_file_path, mode='a')
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - [%(funcName)s:%(lineno)d] - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)
    logging.getLogger().addHandler(file_handler)
    logger.info(f"General game logs will be appended to: {general_log_file_path}")

    game_file_name = "lmvsgame.json"
    game_file_path = os.path.join(run_dir, game_file_name)
    llm_log_file_path = os.path.join(run_dir, "llm_responses.csv")
    model_error_stats = defaultdict(lambda: {"conversation_errors": 0, "order_decoding_errors": 0})

    # --- 3. Initialize or Load Game State ---
    game: Game
    agents: Dict[str, DiplomacyAgent]
    game_history: GameHistory
    run_config: Namespace = args # Default to current args

    if is_resuming:
        try:
            # When resuming, we always use the provided params (they will override the params used in the saved state)
            game, agents, game_history, _ = load_game_state(run_dir, game_file_name, run_config, args.resume_from_phase)

            logger.info(f"Successfully resumed game from phase: {game.get_current_phase()}.")
        except (FileNotFoundError, ValueError) as e:
            logger.error(f"Could not resume game: {e}. Starting a new game instead.")
            is_resuming = False # Fallback to new game
    
    if not is_resuming:
        game = Game()
        game_history = GameHistory()
        if not hasattr(game, "phase_summaries"):
            game.phase_summaries = {}
        agents = await initialize_new_game(run_config, game, game_history, llm_log_file_path)

    if _detect_victory(game):
        game.is_game_done = True          # short-circuit the main loop
        logger.info(
            "Game already complete on load – a power has ≥18 centres "
            f"(current phase {game.get_current_phase()})."
        )

    # --- 4. Main Game Loop ---
    while not game.is_game_done:
        phase_start = time.time()
        current_phase = game.get_current_phase()
        current_short_phase = game.current_short_phase

        # --- 4a. Termination Checks ---
        year_int = int(current_phase[1:5])
        if year_int > run_config.max_year:
            logger.info(f"Reached max year {run_config.max_year}, stopping simulation.")
            break
        if run_config.end_at_phase and current_phase == run_config.end_at_phase:
            logger.info(f"Reached end phase {run_config.end_at_phase}, stopping simulation.")
            break

        logger.info(f"PHASE: {current_phase} (time so far: {time.time() - start_whole:.2f}s)")
        game_history.add_phase(current_phase)

        # --- 4b. Pre-Order Generation Steps (Movement Phases Only) ---
        if current_short_phase.endswith("M"):
            if run_config.num_negotiation_rounds > 0:
                game_history = await conduct_negotiations(
                    game, agents, game_history, model_error_stats,
                    max_rounds=run_config.num_negotiation_rounds, log_file_path=llm_log_file_path,
                )
            if run_config.planning_phase:
                await planning_phase(
                    game, agents, game_history, model_error_stats, log_file_path=llm_log_file_path,
                )
            
            neg_diary_tasks = [
                agent.generate_negotiation_diary_entry(game, game_history, llm_log_file_path)
                for agent in agents.values() if not game.powers[agent.power_name].is_eliminated()
            ]
            if neg_diary_tasks:
                await asyncio.gather(*neg_diary_tasks, return_exceptions=True)

        # --- 4c. Parallel Order Generation and Diary Consolidation ---
        # Start diary consolidation in parallel with order generation
        consolidation_future = None
        if current_short_phase.startswith("S") and current_short_phase.endswith("M"):
            consolidation_tasks = [
                run_diary_consolidation(agent, game, llm_log_file_path,
                                        prompts_dir=agent.prompts_dir)
                for agent in agents.values()
                if not game.powers[agent.power_name].is_eliminated()
            ]
            if consolidation_tasks:
                # Start consolidation tasks but don't await yet
                consolidation_future = asyncio.gather(*consolidation_tasks, return_exceptions=True)

        # Order Generation (proceeds with current diary state)
        logger.info("Getting orders from agents...")
        board_state = game.get_state()
        order_tasks = []
        for power_name, agent in agents.items():
            if not game.powers[power_name].is_eliminated():
                possible_orders = gather_possible_orders(game, power_name)
                if not possible_orders:
                    game.set_orders(power_name, [])
                    continue
                
                order_tasks.append(
                    get_valid_orders(
                        game, agent.client, board_state, power_name, possible_orders,
                        game_history, model_error_stats,
                        agent_goals=agent.goals, agent_relationships=agent.relationships,
                        agent_private_diary_str=agent.get_latest_phase_diary_entries(), # only include latest phase in orders prompt
                        log_file_path=llm_log_file_path, phase=current_phase,
                    )
                )
        
        order_results = await asyncio.gather(*order_tasks, return_exceptions=True)
        
        # Ensure consolidation completes before proceeding to diary entries
        if consolidation_future:
            await consolidation_future
        
        active_powers = [p for p, a in agents.items() if not game.powers[p].is_eliminated()]
        order_power_names = [p for p in active_powers if gather_possible_orders(game, p)]
        submitted_orders_this_phase = defaultdict(list)

        for i, result in enumerate(order_results):
            p_name = order_power_names[i]

            if isinstance(result, Exception):
                logger.error("Error getting orders for %s: %s", p_name, result, exc_info=result)
                valid, invalid = [], []
            else:
                valid   = result.get("valid", [])
                invalid = result.get("invalid", [])

            # what the engine will actually execute
            game.set_orders(p_name, valid)

            # what we record for prompt/history purposes
            submitted_orders_this_phase[p_name] = valid + invalid

            # diary entry only for the orders we tried to submit
            if False: # disabled for now
                if valid or invalid:
                    await agents[p_name].generate_order_diary_entry(
                        game, valid + invalid, llm_log_file_path
                    )
                
        # --- 4d. Process Phase ---
        completed_phase = current_phase
        game.process()
        logger.info(f"Results for {current_phase}:")
        for power_name, power in game.powers.items():
            logger.info(f"{power_name}: {power.centers}")

        # --- 4e. Post-Processing and State Updates ---
        phase_history_from_game = game.get_phase_history()
        if phase_history_from_game:
            last_phase_from_game = phase_history_from_game[-1]
            if last_phase_from_game.name == completed_phase:
                phase_obj_in_my_history = game_history._get_phase(completed_phase)
                if phase_obj_in_my_history:
                    # Store the orders the agents generated
                    phase_obj_in_my_history.submitted_orders_by_power = submitted_orders_this_phase
                    # Store the orders the engine actually accepted
                    phase_obj_in_my_history.orders_by_power = last_phase_from_game.orders
                    
                    # Store the results for the accepted orders
                    converted_results = defaultdict(list)
                    if last_phase_from_game.results:
                        for pwr, res_list in last_phase_from_game.results.items():
                            converted_results[pwr] = [[res] for res in res_list]
                    phase_obj_in_my_history.results_by_power = converted_results
                    logger.debug(f"Populated submitted/accepted order and result history for phase {completed_phase}.")

        phase_summary = game.phase_summaries.get(current_phase, "(Summary not generated)")
        all_orders_this_phase = game.order_history.get(current_short_phase, {})
        
        # Phase Result Diary Entries
        if current_short_phase.endswith("M"):
            phase_result_diary_tasks = [
                agent.generate_phase_result_diary_entry(game, game_history, phase_summary, all_orders_this_phase, llm_log_file_path, current_short_phase)
                for agent in agents.values() if not game.powers[agent.power_name].is_eliminated()
            ]
            if phase_result_diary_tasks:
                await asyncio.gather(*phase_result_diary_tasks, return_exceptions=True)

        

        # Agent State Updates
        if current_short_phase.endswith("M") and run_config.num_negotiation_rounds == 0: # r'ships are updated in negotiation round. otherwise in no press, updated in a separate step.
            current_board_state = game.get_state()
            state_update_tasks = [
                agent.analyze_phase_and_update_state(game, current_board_state, phase_summary, game_history, llm_log_file_path)
                for agent in agents.values() if not game.powers[agent.power_name].is_eliminated()
            ]
            if state_update_tasks:
                await asyncio.gather(*state_update_tasks, return_exceptions=True)

        # --- 4f. Save State At End of Phase ---
        await save_game_state(game, agents, game_history, game_file_path, run_config, completed_phase)
        logger.info(f"Phase {current_phase} took {time.time() - phase_start:.2f}s")

    # --- 5. Game End ---
    total_time = time.time() - start_whole
    logger.info(f"Game ended after {total_time:.2f}s. Final state saved in {run_dir}")

    # Save final overview stats
    overview_file_path = os.path.join(run_dir, "overview.jsonl")
    with open(overview_file_path, "w") as overview_file:
        # ---- make Namespace JSON-safe ----------------------------------
        cfg = vars(run_config).copy()
        if "prompts_dir_map" in cfg and isinstance(cfg["prompts_dir_map"], dict):
            cfg["prompts_dir_map"] = {p: str(path) for p, path in cfg["prompts_dir_map"].items()}
        # ----------------------------------------------------------------
        overview_file.write(json.dumps(model_error_stats) + "\n")
        overview_file.write(json.dumps(getattr(game, 'power_model_map', {})) + "\n")
        overview_file.write(json.dumps(cfg) + "\n")

    logger.info("Done.")


if __name__ == "__main__":
    asyncio.run(main())