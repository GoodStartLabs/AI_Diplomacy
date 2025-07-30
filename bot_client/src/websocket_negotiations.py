"""
WebSocket-specific negotiation logic for single bot players.

This module provides negotiation capabilities for individual bots connected
via WebSocket, adapted from the multi-agent negotiation system in the main
ai_diplomacy package.
"""

from typing import Dict, Optional, List
from loguru import logger

from diplomacy.engine.message import GLOBAL

from ai_diplomacy.utils import gather_possible_orders

from ai_diplomacy.agent import DiplomacyAgent
from ai_diplomacy.game_history import GameHistory
from .websocket_diplomacy_client import WebSocketDiplomacyClient


async def conduct_single_bot_negotiation(
    client: "WebSocketDiplomacyClient",
    agent: "DiplomacyAgent",
    game_history: "GameHistory",
    model_error_stats: Dict[str, Dict[str, int]],
    log_file_path: str,
    max_rounds: int = 3,
    round_number: int = 1,
    prioritize_targets: Optional[List[str]] = None,
) -> bool:
    """
    Conduct negotiation for a single bot during one negotiation round.

    This function handles message generation and sending for one bot during
    a negotiation phase. Unlike the multi-agent version, this focuses on
    a single power and sends messages via WebSocket.

    Args:
        client: WebSocket diplomacy client
        agent: The bot's AI agent
        game_history: Game history tracker
        model_error_stats: Error statistics tracking
        log_file_path: Path for logging
        max_rounds: Maximum number of negotiation rounds
        round_number: Current round number (1-indexed)
        prioritize_targets: Optional list of powers to prioritize for messaging

    Returns:
        True if messages were sent successfully, False otherwise
    """
    power_name = agent.power_name
    logger.info(f"Starting negotiation round {round_number}/{max_rounds} for {power_name}")

    # Check if this power is eliminated
    if client.get_power(power_name).is_eliminated():
        logger.info(f"{power_name} is eliminated, skipping negotiation")
        return False

    # Check if this power has any orderable locations
    possible_orders = gather_possible_orders(client.game, power_name)
    if not possible_orders:
        logger.info(f"No orderable locations for {power_name}, skipping negotiation")
        return False

    # Get active powers for context
    active_powers = [p_name for p_name, p_obj in client.powers.items() if not p_obj.is_eliminated()]

    # Prioritize message targets if specified
    message_targets = prioritize_targets if prioritize_targets else active_powers
    message_targets = [p for p in message_targets if p in active_powers and p != power_name]

    # Generate conversation messages using the AI agent
    board_state = client.get_state()

    messages = await agent.client.get_conversation_reply(
        game=client.game,
        board_state=board_state,
        power_name=power_name,
        possible_orders=possible_orders,
        game_history=game_history,
        game_phase=client.get_current_short_phase(),
        log_file_path=log_file_path,
        active_powers=active_powers,
        agent_goals=agent.goals,
        agent_relationships=agent.relationships,
        agent_private_diary_str=agent.format_private_diary_for_prompt(),
    )

    if not messages:
        logger.debug(f"No messages generated for {power_name} in round {round_number}")
        return False

    # Process and send each message
    messages_sent = 0
    for message in messages:
        success = await _send_negotiation_message(client, agent, game_history, message, power_name)
        if success:
            messages_sent += 1

    logger.info(f"Sent {messages_sent}/{len(messages)} messages for {power_name}")
    return messages_sent > 0


async def _send_negotiation_message(
    client: WebSocketDiplomacyClient,
    agent: DiplomacyAgent,
    game_history: GameHistory,
    message: Dict,
    power_name: str,
) -> bool:
    """
    Send a single negotiation message via WebSocket.

    Args:
        client: WebSocket diplomacy client
        agent: The bot's AI agent
        game_history: Game history tracker
        message: Message dictionary with content and metadata
        power_name: Name of the sending power

    Returns:
        True if message was sent successfully, False otherwise
    """
    # Validate message structure
    if not isinstance(message, dict) or "content" not in message:
        logger.warning(f"Invalid message format from {power_name}: {message}")
        return False

    content = message.get("content", "").strip()
    if not content:
        logger.debug(f"Empty message content from {power_name}, skipping")
        return False

    # Determine recipient
    recipient = GLOBAL  # Default to global
    if message.get("message_type") == "private":
        recipient = message.get("recipient", GLOBAL)
        # Validate recipient is a valid power
        if recipient not in client.powers and recipient != GLOBAL:
            logger.warning(f"Invalid recipient '{recipient}' from {power_name}, sending globally")
            recipient = GLOBAL

    # Send the message via WebSocket
    await client.send_message(
        sender=power_name,
        recipient=recipient,
        message=content,
        phase=client.get_current_short_phase(),
    )

    # Add to game history
    game_history.add_message(
        phase_name=client.get_current_short_phase(),
        sender=power_name,
        recipient=recipient,
        message_content=content,
    )

    # Add to agent's journal
    journal_recipient = f"to {recipient}" if recipient != GLOBAL else "globally"
    agent.add_journal_entry(f"Sent message {journal_recipient} in {client.get_current_short_phase()}: {content[:100]}...")

    logger.info(f"[{power_name} -> {recipient}] {content[:100]}...")
    return True


async def should_participate_in_negotiations(
    client: "WebSocketDiplomacyClient",
    agent: "DiplomacyAgent",
) -> bool:
    """
    Determine if this bot should participate in negotiations.

    Args:
        client: WebSocket diplomacy client
        agent: The bot's AI agent

    Returns:
        True if the bot should participate in negotiations
    """
    power_name = agent.power_name

    # Don't negotiate if eliminated
    if client.get_power(power_name).is_eliminated():
        return False

    # Don't negotiate if no orderable locations
    possible_orders = gather_possible_orders(client.game, power_name)
    if not possible_orders:
        return False

    # Only negotiate during movement phases
    current_phase = client.get_current_short_phase()
    if not current_phase.endswith("M"):
        return False

    return True


def get_negotiation_delay(round_number: int, total_rounds: int) -> float:
    """
    Calculate delay between negotiation rounds to allow message processing.

    Args:
        round_number: Current round number (1-indexed)
        total_rounds: Total number of rounds

    Returns:
        Delay in seconds
    """
    # Longer delay in early rounds to allow more strategic messaging
    base_delay = 10.0  # Base delay between rounds

    if round_number == 1:
        return base_delay * 1.5  # Extra time for first round
    elif round_number == total_rounds:
        return base_delay * 0.5  # Less time for final round
    else:
        return base_delay


async def analyze_recent_messages_for_targeting(
    client: "WebSocketDiplomacyClient",
    power_name: str,
    max_messages: int = 20,
) -> List[str]:
    """
    Analyze recent messages to identify which powers should be prioritized for negotiations.

    Args:
        client: WebSocket diplomacy client
        power_name: Name of the analyzing power
        max_messages: Maximum number of recent messages to analyze

    Returns:
        List of power names in order of priority for messaging
    """
    # Get recent messages from current phase
    recent_messages = await client.get_recent_messages(limit=max_messages)

    # Track who has been active and who has messaged us
    message_activity = {}
    direct_messages_to_us = {}

    for message in recent_messages:
        sender = message.sender
        recipient = message.recipient

        # Track general activity
        if sender != power_name:
            message_activity[sender] = message_activity.get(sender, 0) + 1

        # Track direct messages to us
        if recipient == power_name and sender != power_name:
            direct_messages_to_us[sender] = direct_messages_to_us.get(sender, 0) + 1

    # Get all active powers
    active_powers = [p_name for p_name, p_obj in client.powers.items() if not p_obj.is_eliminated() and p_name != power_name]

    # Prioritize based on: 1) Powers that messaged us directly, 2) Most active powers
    priority_list = []

    # First, add powers that sent us direct messages (sorted by count)
    direct_senders = sorted(direct_messages_to_us.items(), key=lambda x: x[1], reverse=True)
    for sender, _ in direct_senders:
        if sender in active_powers:
            priority_list.append(sender)

    # Then add other active powers (sorted by activity)
    remaining_powers = [p for p in active_powers if p not in priority_list]
    activity_sorted = sorted(remaining_powers, key=lambda p: message_activity.get(p, 0), reverse=True)
    priority_list.extend(activity_sorted)

    logger.debug(f"Message targeting priority for {power_name}: {priority_list}")
    return priority_list


async def conduct_strategic_negotiation_round(
    client: "WebSocketDiplomacyClient",
    agent: "DiplomacyAgent",
    game_history: "GameHistory",
    model_error_stats: Dict[str, Dict[str, int]],
    log_file_path: str,
    round_number: int,
    max_rounds: int = 3,
) -> bool:
    """
    Conduct a single negotiation round with strategic message targeting.

    This function analyzes recent message activity to determine which powers
    to prioritize for messaging in this round.

    Args:
        client: WebSocket diplomacy client
        agent: The bot's AI agent
        game_history: Game history tracker
        model_error_stats: Error statistics tracking
        log_file_path: Path for logging
        round_number: Current round number (1-indexed)
        max_rounds: Maximum number of negotiation rounds

    Returns:
        True if messages were sent successfully, False otherwise
    """
    power_name = agent.power_name

    # Analyze recent messages to prioritize targets
    priority_targets = await analyze_recent_messages_for_targeting(client, power_name)

    # Limit to top 3-4 targets in later rounds to focus conversations
    if round_number > 1:
        priority_targets = priority_targets[: min(4, len(priority_targets))]

    logger.info(f"Round {round_number} targets for {power_name}: {priority_targets}")

    # Conduct negotiation with prioritized targets
    return await conduct_single_bot_negotiation(
        client=client,
        agent=agent,
        game_history=game_history,
        model_error_stats=model_error_stats,
        log_file_path=log_file_path,
        max_rounds=max_rounds,
        round_number=round_number,
        prioritize_targets=priority_targets,
    )
