from dotenv import load_dotenv
from loguru import logger
import asyncio
from typing import Dict, TYPE_CHECKING

from diplomacy.engine.message import Message, GLOBAL

from .agent import DiplomacyAgent
from .clients import load_model_client
from .utils import gather_possible_orders, load_prompt

if TYPE_CHECKING:
    from .game_history import GameHistory
    from diplomacy import Game


load_dotenv()


async def conduct_negotiations(
    game: "Game",
    agents: Dict[str, DiplomacyAgent],
    game_history: "GameHistory",
    model_error_stats: Dict[str, Dict[str, int]],
    log_file_path: str,
    max_rounds: int = 3,
):
    """
    Conducts a round-robin conversation among all non-eliminated powers.
    Each power can send up to 'max_rounds' messages, choosing between private
    and global messages each turn. Uses asyncio for concurrent message generation.
    """
    logger.info("Starting negotiation phase.")

    active_powers = [
        p_name for p_name, p_obj in game.powers.items() if not p_obj.is_eliminated()
    ]
    eliminated_powers = [
        p_name for p_name, p_obj in game.powers.items() if p_obj.is_eliminated()
    ]

    logger.info(f"Active powers for negotiations: {active_powers}")
    if eliminated_powers:
        logger.info(f"Eliminated powers (skipped): {eliminated_powers}")
    else:
        logger.info("No eliminated powers yet.")

    # We do up to 'max_rounds' single-message turns for each power
    for round_index in range(max_rounds):
        logger.info(f"Negotiation Round {round_index + 1}/{max_rounds}")

        # Prepare tasks for asyncio.gather
        tasks = []
        power_names_for_tasks = []

        for power_name in active_powers:
            if power_name not in agents:
                logger.warning(
                    f"Agent for {power_name} not found in negotiations. Skipping."
                )
                continue
            agent = agents[power_name]
            client = agent.client

            possible_orders = gather_possible_orders(game, power_name)
            if not possible_orders:
                logger.info(
                    f"No orderable locations for {power_name}; skipping message generation."
                )
                continue
            board_state = game.get_state()

            # Append the coroutine to the tasks list
            tasks.append(
                client.get_conversation_reply(
                    game,
                    board_state,
                    power_name,
                    possible_orders,
                    game_history,
                    game.current_short_phase,
                    log_file_path=log_file_path,
                    active_powers=active_powers,
                    agent_goals=agent.goals,
                    agent_relationships=agent.relationships,
                    agent_private_diary_str=agent.format_private_diary_for_prompt(),
                )
            )
            power_names_for_tasks.append(power_name)
            logger.debug(f"Prepared get_conversation_reply task for {power_name}.")

        # Run tasks concurrently if any were created
        if tasks:
            logger.debug(f"Running {len(tasks)} conversation tasks concurrently...")
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            logger.debug("No conversation tasks to run for this round.")
            results = []

        # Process results
        for i, result in enumerate(results):
            power_name = power_names_for_tasks[i]
            agent = agents[power_name]  # Get agent again for journaling
            model_name = agent.client.model_name  # Get model name for stats

            if isinstance(result, Exception):
                logger.error(
                    f"Error getting conversation reply for {power_name}: {result}",
                    exc_info=result,
                )
                # Use model_name for stats key if possible
                if model_name in model_error_stats:
                    model_error_stats[model_name]["conversation_errors"] += 1
                else:  # Fallback to power_name if model name not tracked (shouldn't happen)
                    model_error_stats.setdefault(power_name, {}).setdefault(
                        "conversation_errors", 0
                    )
                    model_error_stats[power_name]["conversation_errors"] += 1
                messages = []  # Treat as no messages on error
            elif (
                result is None
            ):  # Handle case where client might return None on internal error
                logger.warning(f"Received None instead of messages for {power_name}.")
                messages = []
                if model_name in model_error_stats:
                    model_error_stats[model_name]["conversation_errors"] += 1
                else:
                    model_error_stats.setdefault(power_name, {}).setdefault(
                        "conversation_errors", 0
                    )
                    model_error_stats[power_name]["conversation_errors"] += 1
            else:
                messages = result  # result is the list of message dicts
                logger.debug(f"Received {len(messages)} message(s) from {power_name}.")

            # Process the received messages (same logic as before)
            if messages:
                for message in messages:
                    # Validate message structure
                    if not isinstance(message, dict) or "content" not in message:
                        logger.warning(
                            f"Invalid message format received from {power_name}: {message}. Skipping."
                        )
                        continue

                    # Create an official message in the Diplomacy engine
                    # Determine recipient based on message type
                    if message.get("message_type") == "private":
                        recipient = message.get(
                            "recipient", GLOBAL
                        )  # Default to GLOBAL if recipient missing somehow
                        if recipient not in game.powers and recipient != GLOBAL:
                            logger.warning(
                                f"Invalid recipient '{recipient}' in message from {power_name}. Sending globally."
                            )
                            recipient = GLOBAL  # Fallback to GLOBAL if recipient power is invalid
                    else:  # Assume global if not private or type is missing
                        recipient = GLOBAL

                    diplo_message = Message(
                        phase=game.current_short_phase,
                        sender=power_name,
                        recipient=recipient,  # Use determined recipient
                        message=message.get("content", ""),  # Use .get for safety
                        time_sent=None,  # Let the engine assign time
                    )
                    game.add_message(diplo_message)
                    # Also add to our custom history
                    game_history.add_message(
                        game.current_short_phase,
                        power_name,
                        recipient,  # Use determined recipient here too
                        message.get("content", ""),  # Use .get for safety
                    )
                    journal_recipient = (
                        f"to {recipient}" if recipient != GLOBAL else "globally"
                    )
                    agent.add_journal_entry(
                        f"Sent message {journal_recipient} in {game.current_short_phase}: {message.get('content', '')[:100]}..."
                    )
                    logger.info(
                        f"[{power_name} -> {recipient}] {message.get('content', '')[:100]}..."
                    )
            else:
                logger.debug(
                    f"No valid messages returned or error occurred for {power_name}."
                )
                # Error stats handled above based on result type

    logger.info("Negotiation phase complete.")
    return game_history
