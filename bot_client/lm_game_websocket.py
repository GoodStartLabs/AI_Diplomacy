"""
WebSocket-based version of lm_game.py

This demonstrates how to use the WebSocketDiplomacyClient as a drop-in replacement
for the direct Game() import in lm_game.py, allowing the AI agents to play against
a remote Diplomacy server via WebSocket connections.
"""

import argparse
import logging
import time
import dotenv
import os
import json
import asyncio
from collections import defaultdict
import concurrent.futures

# Suppress Gemini/PaLM gRPC warnings
os.environ["GRPC_PYTHON_LOG_LEVEL"] = "40"
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["ABSL_MIN_LOG_LEVEL"] = "2"
os.environ["GRPC_POLL_STRATEGY"] = "poll"

# Import our WebSocket client instead of direct Game import
from websocket_diplomacy_client import WebSocketDiplomacyClient, connect_to_diplomacy_server
from diplomacy.engine.message import GLOBAL, Message
from diplomacy.utils.export import to_saved_game_format

from ai_diplomacy.clients import load_model_client
from ai_diplomacy.utils import (
    get_valid_orders,
    gather_possible_orders,
    assign_models_to_powers,
)
from ai_diplomacy.negotiations import conduct_negotiations
from ai_diplomacy.planning import planning_phase
from ai_diplomacy.game_history import GameHistory
from ai_diplomacy.agent import DiplomacyAgent
import ai_diplomacy.narrative
from ai_diplomacy.initialization import initialize_agent_state_ext

dotenv.load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
# Silence noisy dependencies
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("root").setLevel(logging.WARNING)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Run a Diplomacy game simulation with WebSocket server connection."
    )
    parser.add_argument(
        "--hostname",
        type=str,
        default="localhost",
        help="Diplomacy server hostname (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8432,
        help="Diplomacy server port (default: 8432)",
    )
    parser.add_argument(
        "--username",
        type=str,
        default="ai_player",
        help="Username for server authentication (default: ai_player)",
    )
    parser.add_argument(
        "--password",
        type=str,
        default="password",
        help="Password for server authentication (default: password)",
    )
    parser.add_argument(
        "--game_id",
        type=str,
        default=None,
        help="Existing game ID to join (if not provided, creates new game)",
    )
    parser.add_argument(
        "--max_year",
        type=int,
        default=1901,
        help="Maximum year to simulate. The game will stop once this year is reached.",
    )
    parser.add_argument(
        "--num_negotiation_rounds",
        type=int,
        default=0,
        help="Number of negotiation rounds per phase.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="Output filename for the final JSON result. If not provided, a timestamped name will be generated.",
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
        "--create_multi_power_game",
        action="store_true",
        help="Create a game and join multiple powers (for testing with bots)",
    )
    return parser.parse_args()


async def join_powers_for_testing(client: WebSocketDiplomacyClient, power_model_map: dict):
    """
    Join multiple powers in the same game for testing purposes.
    This simulates having multiple AI players in one game.
    """
    power_names = list(power_model_map.keys())
    
    # Join additional powers beyond the first one
    for power_name in power_names[1:]:
        try:
            logger.info(f"Attempting to join power {power_name}")
            await client.channel.join_game(
                game_id=client.game_id,
                power_name=power_name
            )
            logger.info(f"Successfully joined {power_name}")
        except Exception as e:
            logger.warning(f"Could not join {power_name}: {e}")


async def create_or_join_game(client: WebSocketDiplomacyClient, args, power_model_map: dict):
    """
    Create a new game or join an existing one based on arguments.
    """
    if args.game_id:
        # Join existing game
        logger.info(f"Joining existing game {args.game_id}")
        
        # List available games first to see what's available
        try:
            games = await client.list_games()
            logger.info(f"Available games: {[g.get('game_id', 'unknown') for g in games]}")
        except Exception as e:
            logger.warning(f"Could not list games: {e}")
        
        # For testing, we'll join as the first power in our model map
        first_power = list(power_model_map.keys())[0]
        game = await client.join_game(
            game_id=args.game_id,
            power_name=first_power
        )
        
        if args.create_multi_power_game:
            await join_powers_for_testing(client, power_model_map)
            
    else:
        # Create new game
        logger.info("Creating new game")
        
        # Get the first power to control
        first_power = list(power_model_map.keys())[0] if not args.create_multi_power_game else None
        
        game = await client.create_game(
            map_name="standard",
            rules=["NO_PRESS", "IGNORE_ERRORS", "POWER_CHOICE"],
            power_name=first_power,
            n_controls=7 if not args.create_multi_power_game else 1,  # Lower requirement for testing
            deadline=None  # No time pressure for AI testing
        )
        
        if args.create_multi_power_game:
            await join_powers_for_testing(client, power_model_map)
    
    return game


async def simulate_game_processing(client: WebSocketDiplomacyClient):
    """
    Simulate game processing for testing purposes.
    In a real server environment, this would happen automatically.
    """
    try:
        await client.process_game()
        logger.info("Game processed successfully")
    except Exception as e:
        logger.warning(f"Could not process game (may not have admin rights): {e}")


async def main():
    args = parse_arguments()
    max_year = args.max_year

    logger.info("Starting WebSocket-based Diplomacy game with multiple LLMs")
    start_whole = time.time()

    model_error_stats = defaultdict(
        lambda: {"conversation_errors": 0, "order_decoding_errors": 0}
    )

    # Determine the result folder based on a timestamp
    timestamp_str = time.strftime("%Y%m%d_%H%M%S")
    result_folder = f"./results/websocket_{timestamp_str}"
    os.makedirs(result_folder, exist_ok=True)

    # Setup general file logging
    general_log_file_path = os.path.join(result_folder, "general_game.log")
    file_handler = logging.FileHandler(general_log_file_path, mode='a')
    file_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - [%(funcName)s:%(lineno)d] - %(message)s", 
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(file_handler)
    
    logging.info(f"General game logs will be appended to: {general_log_file_path}")

    # File paths
    manifesto_path = f"{result_folder}/game_manifesto.txt"
    game_file_path = args.output if args.output else f"{result_folder}/lmvsgame_websocket.json"
    overview_file_path = f"{result_folder}/overview.jsonl"
    llm_log_file_path = f"{result_folder}/llm_responses.csv"

    # Handle power model mapping
    if args.models:
        powers_order = ["AUSTRIA", "ENGLAND", "FRANCE", "GERMANY", "ITALY", "RUSSIA", "TURKEY"]
        provided_models = [name.strip() for name in args.models.split(",")]
        if len(provided_models) != len(powers_order):
            logger.error(
                f"Expected {len(powers_order)} models for --models but got {len(provided_models)}. Exiting."
            )
            return
        power_model_map = dict(zip(powers_order, provided_models))
    else:
        power_model_map = assign_models_to_powers()

    try:
        # Connect to the Diplomacy server
        logger.info(f"Connecting to Diplomacy server at {args.hostname}:{args.port}")
        client = await connect_to_diplomacy_server(
            hostname=args.hostname,
            port=args.port,
            username=args.username,
            password=args.password
        )
        
        # Create or join game
        game = await create_or_join_game(client, args, power_model_map)
        logger.info(f"Game ID: {client.game_id}, Role: {client.game_role}")
        
        # Initialize game history
        game_history = GameHistory()
        
        # Add phase_summaries attribute if not present
        if not hasattr(client.game, "phase_summaries"):
            client.game.phase_summaries = {}

        # Initialize agents for powers we control
        agents = {}
        initialization_tasks = []
        logger.info("Initializing Diplomacy Agents for controlled powers...")
        
        # Determine which powers we're controlling
        controlled_powers = []
        if client.power_name:
            controlled_powers = [client.power_name]
        elif args.create_multi_power_game:
            # We're controlling multiple powers in test mode
            controlled_powers = list(power_model_map.keys())
        
        for power_name in controlled_powers:
            model_id = power_model_map.get(power_name)
            if model_id and not client.get_power(power_name).is_eliminated():
                try:
                    client_obj = load_model_client(model_id)
                    agent = DiplomacyAgent(power_name=power_name, client=client_obj)
                    agents[power_name] = agent
                    logger.info(f"Preparing initialization task for {power_name} with model {model_id}")
                    initialization_tasks.append(
                        initialize_agent_state_ext(agent, client.game, game_history, llm_log_file_path)
                    )
                except Exception as e:
                    logger.error(f"Failed to create agent for {power_name} with model {model_id}: {e}", exc_info=True)
            else:
                logger.info(f"Skipping agent initialization for {power_name} (no model or eliminated)")

        # Run initializations concurrently
        if initialization_tasks:
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

        # Main game loop
        all_phase_relationships = {}
        all_phase_relationships_history = {}

        while not client.is_game_done:
            phase_start = time.time()
            current_phase = client.get_current_phase()
            
            # Synchronize with server to get latest state
            await client.synchronize()

            # Ensure the current phase is registered in the history
            game_history.add_phase(current_phase)
            current_short_phase = client.get_current_short_phase()
            
            logger.info(f"PHASE: {current_phase} (time so far: {phase_start - start_whole:.2f}s)")

            # Prevent unbounded simulation based on year
            year_str = current_phase[1:5]
            year_int = int(year_str)
            if year_int > max_year:
                logger.info(f"Reached year {year_int}, stopping the test game early.")
                break

            # Negotiations for movement phases
            if client.get_current_short_phase().endswith("M"):
                if args.num_negotiation_rounds > 0:
                    logger.info(f"Running {args.num_negotiation_rounds} rounds of negotiations...")
                    game_history = await conduct_negotiations(
                        client.game,  # Pass the NetworkGame object
                        agents,
                        game_history,
                        model_error_stats,
                        max_rounds=args.num_negotiation_rounds,
                        log_file_path=llm_log_file_path,
                    )
                else:
                    logger.info("Skipping negotiation phase as num_negotiation_rounds=0")

                # Planning phase (if enabled)
                if args.planning_phase:
                    logger.info("Executing strategic planning phase...")
                    await planning_phase(
                        client.game,
                        agents,
                        game_history,
                        model_error_stats,
                        log_file_path=llm_log_file_path,
                    )

                # Generate negotiation diary entries
                logger.info(f"Generating negotiation diary entries for phase {current_short_phase}...")
                active_powers_for_neg_diary = [p for p in agents.keys() if not client.get_power(p).is_eliminated()]
                
                neg_diary_tasks = []
                for power_name, agent in agents.items():
                    if not client.get_power(power_name).is_eliminated():
                        neg_diary_tasks.append(
                            agent.generate_negotiation_diary_entry(
                                client.game,
                                game_history,
                                llm_log_file_path
                            )
                        )
                if neg_diary_tasks:
                    await asyncio.gather(*neg_diary_tasks, return_exceptions=True)

            # AI Decision Making: Get orders for each controlled power
            logger.info("Getting orders from agents...")
            active_powers_for_orders = [p for p in agents.keys() if not client.get_power(p).is_eliminated()]
            
            order_tasks = []
            order_power_names = []
            board_state = client.get_state()

            for power_name, agent in agents.items():
                if client.get_power(power_name).is_eliminated():
                    logger.debug(f"Skipping order generation for eliminated power {power_name}.")
                    continue

                # Diagnostic logging
                logger.info(f"--- Diagnostic Log for {power_name} in phase {current_phase} ---")
                try:
                    orderable_locs = client.get_orderable_locations(power_name)
                    logger.info(f"[{power_name}][{current_phase}] Orderable locations: {orderable_locs}")
                    actual_units = client.get_units(power_name)
                    logger.info(f"[{power_name}][{current_phase}] Actual units: {actual_units}")
                except Exception as e_diag:
                    logger.error(f"[{power_name}][{current_phase}] Error during diagnostic logging: {e_diag}")

                # Calculate possible orders
                possible_orders = gather_possible_orders(client.game, power_name)
                if not possible_orders:
                    logger.debug(f"No orderable locations for {power_name}; submitting empty orders.")
                    await client.set_orders(power_name, [])
                    continue

                order_power_names.append(power_name)
                diary_preview = agent.format_private_diary_for_prompt()
                
                order_tasks.append(
                    get_valid_orders(
                        client.game,
                        agent.client,
                        board_state,
                        power_name,
                        possible_orders,
                        game_history,
                        model_error_stats,
                        agent_goals=agent.goals,
                        agent_relationships=agent.relationships,
                        agent_private_diary_str=diary_preview,
                        log_file_path=llm_log_file_path,
                        phase=current_phase,
                    )
                )

            # Run order generation concurrently
            if order_tasks:
                logger.debug(f"Running {len(order_tasks)} order generation tasks concurrently...")
                order_results = await asyncio.gather(*order_tasks, return_exceptions=True)
            else:
                order_results = []

            # Process order results and submit them
            for i, result in enumerate(order_results):
                p_name = order_power_names[i]
                agent = agents[p_name]

                if isinstance(result, Exception):
                    logger.error(f"Error during get_valid_orders for {p_name}: {result}", exc_info=result)
                    await client.set_orders(p_name, [])
                elif result is None:
                    logger.warning(f"get_valid_orders returned None for {p_name}. Setting empty orders.")
                    await client.set_orders(p_name, [])
                else:
                    orders = result
                    logger.debug(f"Validated orders for {p_name}: {orders}")
                    if orders:
                        await client.set_orders(p_name, orders)
                        logger.debug(f"Set orders for {p_name} in {current_short_phase}: {orders}")
                        
                        # Generate order diary entry
                        try:
                            await agent.generate_order_diary_entry(
                                client.game,
                                orders,
                                llm_log_file_path
                            )
                        except Exception as e_diary:
                            logger.error(f"Error generating order diary for {p_name}: {e_diary}", exc_info=True)
                    else:
                        await client.set_orders(p_name, [])

            # Process the game phase (if we have admin rights)
            logger.info(f"Processing orders for {current_phase}...")
            await simulate_game_processing(client)
            
            # Wait a moment for the server to process
            await asyncio.sleep(1)
            
            # Synchronize again to get results
            await client.synchronize()

            # Log the results
            logger.info(f"Results for {current_phase}:")
            for power_name, power in client.powers.items():
                logger.info(f"{power_name}: {power.centers}")

            # Add orders to game history
            current_order_history = client.order_history.get(current_short_phase, {})
            for power_name, orders in current_order_history.items():
                game_history.add_orders(current_short_phase, power_name, orders)

            # Collect relationships for this phase
            current_relationships_for_phase = {}
            for power_name, agent in agents.items():
                if power_name in client.powers and not client.get_power(power_name).is_eliminated():
                    current_relationships_for_phase[power_name] = agent.relationships
            all_phase_relationships[current_short_phase] = current_relationships_for_phase

            # Generate phase result diary entries
            logger.info(f"Generating phase result diary entries for completed phase {current_phase}...")
            phase_summary = getattr(client.game, 'phase_summaries', {}).get(current_phase, "(Summary not generated)")
            all_orders_this_phase = current_order_history
            
            phase_result_diary_tasks = []
            for power_name, agent in agents.items():
                if not client.get_power(power_name).is_eliminated():
                    phase_result_diary_tasks.append(
                        agent.generate_phase_result_diary_entry(
                            client.game,
                            game_history,
                            phase_summary,
                            all_orders_this_phase,
                            llm_log_file_path
                        )
                    )
            
            if phase_result_diary_tasks:
                await asyncio.gather(*phase_result_diary_tasks, return_exceptions=True)

            # State update analysis
            logger.info(f"Starting state update analysis for completed phase {current_phase}...")
            current_board_state = client.get_state()
            
            active_agent_powers = [(p, power) for p, power in client.powers.items() 
                                 if p in agents and not power.is_eliminated()]
            
            if active_agent_powers:
                state_update_tasks = []
                for power_name, _ in active_agent_powers:
                    agent = agents[power_name]
                    state_update_tasks.append(
                        agent.analyze_phase_and_update_state(
                            client.game,
                            current_board_state,
                            phase_summary,
                            game_history,
                            llm_log_file_path,
                        )
                    )
                
                if state_update_tasks:
                    await asyncio.gather(*state_update_tasks, return_exceptions=True)

            logger.info(f"Phase {current_phase} took {time.time() - phase_start:.2f}s")

            # Check year limit again
            if year_int > max_year:
                break

        # Game is done
        total_time = time.time() - start_whole
        logger.info(f"Game ended after {total_time:.2f}s. Saving results...")

        # Save game results
        output_path = game_file_path
        if os.path.exists(output_path):
            timestamp = int(time.time())
            base, ext = os.path.splitext(output_path)
            output_path = f"{base}_{timestamp}{ext}"

        # Create a simplified saved game format
        # Note: The NetworkGame may not have all the same export capabilities as a local Game
        saved_game = {
            'game_id': client.game_id,
            'map_name': 'standard',
            'rules': ['NO_PRESS', 'IGNORE_ERRORS', 'POWER_CHOICE'],
            'phases': [],
            'powers': {},
            'messages': {},
            'phase_summaries': getattr(client.game, 'phase_summaries', {}),
            'final_agent_states': {}
        }

        # Add final agent states
        for power_name, agent in agents.items():
            saved_game['final_agent_states'][power_name] = {
                "relationships": agent.relationships,
                "goals": agent.goals,
            }

        # Add power information
        for power_name, power in client.powers.items():
            saved_game['powers'][power_name] = {
                'centers': list(power.centers),
                'units': list(power.units),
                'is_eliminated': power.is_eliminated()
            }

        logger.info(f"Saving game to {output_path}...")
        with open(output_path, "w") as f:
            json.dump(saved_game, f, indent=4)

        # Save overview
        with open(overview_file_path, "w") as overview_file:
            overview_file.write(json.dumps(model_error_stats) + "\n")
            overview_file.write(json.dumps(power_model_map) + "\n")
            overview_file.write(json.dumps(vars(args)) + "\n")

        logger.info(f"Saved game data and error stats in: {result_folder}")

    except Exception as e:
        logger.error(f"Error during game execution: {e}", exc_info=True)
    finally:
        # Clean up connection
        if 'client' in locals():
            await client.close()
        logger.info("Done.")


if __name__ == "__main__":
    asyncio.run(main())