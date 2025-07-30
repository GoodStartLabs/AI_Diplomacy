"""
Single Bot Player

A standalone bot that connects to a Diplomacy server, controls one power,
and waits for its turn to make moves. This script is designed to be run
as a separate process for each bot in a multi-player game.
"""

import sys
import os

from bot_client.src.utils import CircuitBreaker

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import asyncio
import signal
import time
from typing import Any, Optional, Dict, List
import dotenv
from loguru import logger


from .websocket_diplomacy_client import WebSocketDiplomacyClient, connect_to_diplomacy_server


from diplomacy.utils.exceptions import GameIdException, DiplomacyException
from diplomacy.communication.notifications import GameStatusUpdate
from diplomacy.engine.message import Message

from ai_diplomacy.clients import load_model_client
from ai_diplomacy.utils import get_valid_orders, gather_possible_orders
from ai_diplomacy.game_history import GameHistory
from ai_diplomacy.agent import DiplomacyAgent
from ai_diplomacy.initialization import initialize_agent_state_ext
from .websocket_negotiations import (
    conduct_strategic_negotiation_round,
    should_participate_in_negotiations,
    get_negotiation_delay,
)
from .config import config

dotenv.load_dotenv()


class SingleBotPlayer:
    """
    A single bot player that connects to a Diplomacy server and plays as one power.

    The bot waits for game events from the server and responds appropriately:
    - When it's time to submit orders, generates and submits them
    - When messages are received, processes them and potentially responds
    - When the game phase updates, analyzes the new situation
    """

    def __init__(
        self,
        power_name: str,
        model_name: str,
        hostname: str = "localhost",
        port: int = 8432,
        game_id: Optional[str] = None,
        negotiation_rounds: int = 3,
    ):
        assert power_name is not None
        assert model_name is not None

        self.hostname = hostname
        self.port = port
        self.username = f"bot_{power_name}"
        self.password = "password"
        self.power_name = power_name
        self.model_name = model_name
        self.game_id = game_id

        # Bot state
        self.client: WebSocketDiplomacyClient
        self.agent: DiplomacyAgent
        self.game_history: GameHistory = GameHistory()
        self.running = True
        self.current_phase = None
        self.waiting_for_orders = False
        self.orders_submitted = False

        # Negotiation settings
        self.negotiation_rounds = negotiation_rounds
        self.current_negotiation_round = 0
        self.negotiation_complete = False

        # Track error stats
        self.error_stats: Dict[str, Dict[str, int]] = {self.model_name: {"conversation_errors": 0, "order_decoding_errors": 0}}

        # Track messaging patterns for strategic communication
        self.message_counts: Dict[str, int] = {}  # Messages received from each power
        self.response_counts: Dict[str, int] = {}  # Responses sent to each power
        self.priority_contacts: List[str] = []  # Powers to prioritize for communication

        # Add graceful shutdown flag
        self.shutdown_requested = False
        self.circuit_breaker = CircuitBreaker()

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down...")
        if self.shutdown_requested:
            asyncio.run(self.cleanup)
        if not self.running:
            logger.info("Already shutting down, send signal again for immediate shutdown")
            self.shutdown_requested = True
        self.running = False

    async def connect_and_initialize(self):
        """Connect to the server and initialize the bot."""
        logger.info(f"Connecting to {self.hostname}:{self.port} as {self.username}")

        # Connect to server with retry logic
        self.client = await self.circuit_breaker._retry_with_backoff(
            connect_to_diplomacy_server,
            hostname=self.hostname,
            port=self.port,
            username=self.username,
            password=self.password,
        )

        # Join or create game
        if self.game_id:
            logger.info(f"Joining existing game {self.game_id} as {self.power_name}")
            await self.client.join_game(game_id=self.game_id, power_name=self.power_name)
        else:
            logger.info(f"Creating new game as {self.power_name}")
            await self.client.create_game(
                map_name="standard",
                rules=["IGNORE_ERRORS", "POWER_CHOICE"],  # Allow messages
                power_name=self.power_name,
                n_controls=7,  # Full game
                deadline=None,
            )
            logger.info(f"Created game {self.client.game_id}")

        # Initialize AI agent
        logger.info(f"Initializing AI agent with model {self.model_name}")
        model_client = load_model_client(self.model_name)
        self.agent = DiplomacyAgent(power_name=self.power_name, client=model_client)

        # Initialize agent state
        await initialize_agent_state_ext(self.agent, self.client.game, self.game_history, config.log_file_path)

        # Setup game event callbacks
        await self._setup_event_callbacks()

        # Get initial game state
        await self.client.game.synchronize()
        self.current_phase = self.client.game.get_current_phase()
        self.game_history.add_phase(self.current_phase)

        logger.info(f"Bot initialized. Current phase: {self.current_phase}")
        logger.info(f"Game status: {self.client.game.status}")

    async def _setup_event_callbacks(self):
        """Setup callbacks for game events from the server."""

        # Game phase updates (new turn)
        self.client.game.add_on_game_phase_update(self._on_phase_update)

        # Game processing (orders executed)
        self.client.game.add_on_game_processed(self._on_game_processed)

        # Messages received
        self.client.game.add_on_game_message_received(self._on_message_received)

        # Game status changes
        self.client.game.add_on_game_status_update(self._on_status_update)

        # Power updates (other players joining/leaving)
        self.client.game.add_on_powers_controllers(self._on_powers_update)

        logger.debug("Event callbacks setup complete")

    def _on_phase_update(self, game, notification):
        """Handle game phase updates."""
        logger.info(f"Phase update received: {notification.phase_data}")

        # Schedule the async processing in the event loop
        asyncio.create_task(self._handle_phase_update_async(notification))

    async def _handle_phase_update_async(self, notification):
        """Async handler for phase updates."""
        try:
            # Update our game state with retry logic
            await self.circuit_breaker._retry_with_backoff(self.client.game.synchronize)
        except Exception as e:
            # This is a critical error. If we cannot synchronize the game, even with backoffs, we shouldn't continue.
            logger.critical(f"Failed to synchronize game state during phase update: {e}")

            raise e

        new_phase = self.client.game.get_current_phase()
        if new_phase != self.current_phase:
            logger.info(f"New phase: {new_phase} (was: {self.current_phase})")
            self.current_phase = new_phase
            self.game_history.add_phase(new_phase)
            self.orders_submitted = False
            self.current_negotiation_round = 0
            self.negotiation_complete = False

            # Log message statistics at phase transitions
            if hasattr(self, "message_counts") and self.message_counts:
                self.log_message_statistics()

            # Check if we should start negotiations for movement phases (not adjustment phases)
            if new_phase.endswith("M"):
                await self._handle_negotiation_phase()

            # Check if we need to submit orders for this new phase
            await self._check_if_orders_needed()

    def _on_game_processed(self, game, notification):
        """Handle game processing (when orders are executed)."""
        logger.info("Game processed - orders have been executed")

        # Schedule the async processing in the event loop
        asyncio.create_task(self._handle_game_processed_async())

    async def _handle_game_processed_async(self):
        """Async handler for game processing."""
        # Synchronize to get the results with retry logic
        await self.circuit_breaker._retry_with_backoff(self.client.game.synchronize)

        # Analyze the results
        await self._analyze_phase_results()

        self.orders_submitted = False
        self.waiting_for_orders = False

    def _on_message_received(self, game, notification):
        """Handle incoming diplomatic messages."""
        message = notification.message
        logger.info(f"Message received from {message.sender} to {message.recipient}: {message.message}")

        # Add message to game history
        self.game_history.add_message(
            phase_name=message.phase,
            sender=message.sender,
            recipient=message.recipient,
            message_content=message.message,
        )

        # Track message patterns
        if message.recipient == self.power_name and message.sender != self.power_name:
            self.message_counts[message.sender] = self.message_counts.get(message.sender, 0) + 1
            self._update_priority_contacts()

        # If it's a private message to us, consider responding
        if message.recipient == self.power_name and message.sender != self.power_name:
            # Schedule the async processing in the event loop
            asyncio.create_task(self._consider_message_response(message))

    def _on_status_update(self, game, notification: GameStatusUpdate):
        """Handle game status changes."""
        logger.info(f"Game status updated: {notification.status}")

        if notification.status in ["COMPLETED", "CANCELED"]:
            logger.info("Game has ended")
            self.running = False

    def _on_powers_update(self, game, notification):
        """Handle power controller updates (players joining/leaving)."""
        logger.info("Powers controllers updated")
        # Could implement logic to react to new players joining

    async def _check_if_orders_needed(self):
        """Check if we need to submit orders for the current phase."""
        if self.orders_submitted:
            return

        # Check if it's a phase where we can submit orders
        current_short_phase = self.client.game.current_short_phase

        logger.debug(f"Checking if orders needed for phase: {current_short_phase}")

        # Movement and Retreat phases
        orderable_locations = self.client.game.get_orderable_locations(self.power_name)
        if orderable_locations:
            logger.info(f"Orders needed for {current_short_phase} phase - orderable locations: {orderable_locations}")
            self.waiting_for_orders = True
            await self._submit_orders()
        else:
            logger.info(f"No orderable locations for {self.power_name} in {current_short_phase}")

    async def _submit_adjustment_orders(self, action_type, count):
        """Submit build or disband orders for adjustment phase."""
        # FIXME: This whole function is horse shit.
        return
        if action_type == "build":
            # Get buildable locations for this power
            possible_orders = gather_possible_orders(self.client.game, self.power_name)
            if not possible_orders:
                logger.warning(f"No possible build orders for {self.power_name}")
                await self.client.set_orders(self.power_name, [])
                self.orders_submitted = True
                return

            # Filter for build orders (usually start with unit type + location)
            build_orders = [order for order in possible_orders if " - " not in order and any(order.startswith(unit) for unit in ["A ", "F "])]

            logger.info(f"Available build orders for {self.power_name}: {build_orders}")

            # Select up to 'count' build orders
            selected_orders = build_orders[:count]
            logger.info(f"Submitting build orders for {self.power_name}: {selected_orders}")

            await self.client.set_orders(self.power_name, selected_orders)

        elif action_type == "disband":
            # Get current units for disbanding
            power = self.client.game.get_power(self.power_name)
            current_units = list(power.units.keys())

            # Create disband orders
            disband_orders = []
            for i, unit_location in enumerate(current_units[:count]):
                # Format: "A Berlin - DISBAND" or "F London - DISBAND"
                unit_type = power.units[unit_location][0]  # 'A' or 'F'
                disband_order = f"{unit_type} {unit_location} - DISBAND"
                disband_orders.append(disband_order)

            logger.info(f"Submitting disband orders for {self.power_name}: {disband_orders}")
            await self.client.set_orders(self.power_name, disband_orders)

        self.orders_submitted = True
        self.waiting_for_orders = False
        logger.info(f"Adjustment orders submitted successfully for {self.power_name}")

    async def _submit_orders(self):
        """Generate and submit orders for the current phase."""
        if self.orders_submitted:
            logger.debug("Orders already submitted for this phase")
            return

        current_phase = self.client.game.get_current_phase()
        logger.info(f"Generating orders for {self.power_name} in phase {current_phase}...")

        # Get current board state
        board_state = self.client.game.get_state()

        # Get possible orders
        possible_orders = gather_possible_orders(self.client.game, self.power_name)

        logger.debug(f"Possible orders for {self.power_name}: {possible_orders}")

        if not possible_orders:
            logger.info(f"No possible orders for {self.power_name}, submitting empty order set")
            await self.circuit_breaker._retry_with_backoff(self.client.set_orders, self.power_name, [])
            self.orders_submitted = True
            return

        # Generate orders using AI
        orders = await get_valid_orders(
            game=self.client.game,
            client=self.agent.client,
            board_state=board_state,
            power_name=self.power_name,
            possible_orders=possible_orders,
            game_history=self.game_history,
            model_error_stats=self.error_stats,
            agent_goals=self.agent.goals,
            agent_relationships=self.agent.relationships,
            agent_private_diary_str=self.agent.format_private_diary_for_prompt(),
            phase=self.client.game.get_current_phase(),
        )

        # Submit orders with retry logic
        if orders:
            logger.info(f"Submitting orders: {orders}")
            await self.client.set_orders(self.power_name, orders["valid"])

            # Generate order diary entry (don't retry this if it fails)
            await self.agent.generate_order_diary_entry(
                self.client.game,
                orders["valid"],
                config.log_file_path,
            )
        else:
            logger.info("No valid orders generated, submitting empty order set")
            await self.circuit_breaker._retry_with_backoff(self.client.set_orders, self.power_name, [])

        self.orders_submitted = True
        self.waiting_for_orders = False
        logger.info("Orders submitted successfully")

        # Call the no wait so we don't sit around for the turns to end.
        # TODO: We probably don't want to call this here.
        # We want to call it when negotiations end,
        self.client.game.no_wait()

    async def _analyze_phase_results(self):
        """Analyze the results of the previous phase."""
        logger.info("Analyzing phase results...")

        # Get current board state after processing
        board_state = self.client.game.get_state()

        # Generate a simple phase summary
        phase_summary = f"Phase {self.current_phase} completed."

        # Update agent state based on results
        await self.agent.analyze_phase_and_update_state(
            game=self.client.game,
            board_state=board_state,
            phase_summary=phase_summary,
            game_history=self.game_history,
            log_file_path=config.log_file_path,
        )

        logger.info("Phase analysis complete")

    async def _handle_negotiation_phase(self):
        """Handle the negotiation phase for movement turns."""
        # Check if we should participate in negotiations
        if not await should_participate_in_negotiations(self.client, self.agent):
            logger.info(f"{self.power_name} will not participate in negotiations this phase")
            self.negotiation_complete = True
            return

        logger.info(f"Starting negotiation phase for {self.power_name}")
        # TODO: This doesn't need a specific number of negotiation rounds, though it should have a top number of messages this turn so they don't blabber on forever.

        # Conduct negotiations for the specified number of rounds
        for round_num in range(1, self.negotiation_rounds + 1):
            self.current_negotiation_round = round_num

            logger.info(f"Negotiation round {round_num}/{self.negotiation_rounds} for {self.power_name}")

            # Use strategic negotiation that analyzes recent messages
            success = await conduct_strategic_negotiation_round(
                client=self.client,
                agent=self.agent,
                game_history=self.game_history,
                model_error_stats=self.error_stats,
                log_file_path=config.log_file_path,
                round_number=round_num,
                max_rounds=self.negotiation_rounds,
            )

            if not success:
                logger.info(f"No messages sent in round {round_num} for {self.power_name}")

            # Wait between rounds to allow other bots to respond
            if round_num < self.negotiation_rounds:
                delay = get_negotiation_delay(round_num, self.negotiation_rounds)
                logger.debug(f"Waiting {delay}s before next negotiation round")
                await asyncio.sleep(delay)

        self.negotiation_complete = True
        logger.info(f"Negotiation phase complete for {self.power_name}")

    async def _consider_message_response(self, message: Message):
        """Consider whether to respond to a diplomatic message."""
        # Only respond to messages directed at us specifically
        if message.recipient != self.power_name:
            return

        # Don't respond to our own messages
        if message.sender == self.power_name:
            return

        logger.info(f"Considering response to message from {message.sender}: {message.message[:50]}...")

        # Generate a contextual response using AI
        # Get current game state for context
        board_state = self.client.get_state()
        possible_orders = gather_possible_orders(self.client.game, self.power_name)

        # Create a simple conversation context
        active_powers = [p_name for p_name, p_obj in self.client.powers.items() if not p_obj.is_eliminated()]

        # Generate response using the agent's conversation capabilities
        responses = await self.agent.client.get_conversation_reply(
            game=self.client.game,
            board_state=board_state,
            power_name=self.power_name,
            possible_orders=possible_orders,
            game_history=self.game_history,
            game_phase=self.client.get_current_short_phase(),
            log_file_path=config.log_file_path,
            active_powers=active_powers,
            agent_goals=self.agent.goals,
            agent_relationships=self.agent.relationships,
            agent_private_diary_str=self.agent.format_private_diary_for_prompt(),
        )

        # Send the first response if any were generated
        if responses and len(responses) > 0:
            response_content = responses[0].get("content", "").strip()
            if response_content:
                await self.circuit_breaker._retry_with_backoff(
                    self.client.send_message,
                    sender=self.power_name,
                    recipient=message.sender,
                    message=response_content,
                    phase=self.client.get_current_short_phase(),
                )

                # Add to game history
                self.game_history.add_message(
                    phase_name=self.client.get_current_short_phase(),
                    sender=self.power_name,
                    recipient=message.sender,
                    message_content=response_content,
                )

                # Track response patterns
                self.response_counts[message.sender] = self.response_counts.get(message.sender, 0) + 1

                # Add to agent's journal
                self.agent.add_journal_entry(f"Responded to {message.sender} in {self.client.get_current_short_phase()}: {response_content[:100]}...")

                logger.info(f"Sent AI response to {message.sender}: {response_content[:50]}...")
            else:
                logger.debug(f"AI generated empty response to {message.sender}")
        else:
            logger.debug(f"AI generated no responses to {message.sender}")

    def _update_priority_contacts(self) -> None:
        """Update the list of priority contacts based on messaging patterns."""
        # Sort powers by message count (descending) and take top 3-4
        sorted_contacts = sorted(self.message_counts.items(), key=lambda x: x[1], reverse=True)

        # Keep top 4 most active contacts as priority
        self.priority_contacts = [contact[0] for contact in sorted_contacts[:4]]

        logger.debug(f"Updated priority contacts for {self.power_name}: {self.priority_contacts}")

    def get_message_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about messaging patterns."""
        active_powers = [p_name for p_name, p_obj in self.client.powers.items() if not p_obj.is_eliminated() and p_name != self.power_name]

        stats = {
            "power_name": self.power_name,
            "total_messages_received": sum(self.message_counts.values()),
            "total_responses_sent": sum(self.response_counts.values()),
            "message_counts_by_power": dict(self.message_counts),
            "response_counts_by_power": dict(self.response_counts),
            "priority_contacts": list(self.priority_contacts),
            "response_rate_by_power": {},
            "active_powers": active_powers,
            "current_phase": self.current_phase,
        }

        # Calculate response rates
        for power, received in self.message_counts.items():
            sent = self.response_counts.get(power, 0)
            stats["response_rate_by_power"][power] = sent / received if received > 0 else 0.0

        return stats

    def log_message_statistics(self) -> None:
        """Log current message statistics for analysis."""
        stats = self.get_message_statistics()

        logger.info(f"Message Statistics for {self.power_name}:")
        logger.info(f"  Total messages received: {stats['total_messages_received']}")
        logger.info(f"  Total responses sent: {stats['total_responses_sent']}")
        logger.info(f"  Priority contacts: {stats['priority_contacts']}")

        for power in stats["active_powers"]:
            received = stats["message_counts_by_power"].get(power, 0)
            sent = stats["response_counts_by_power"].get(power, 0)
            rate = stats["response_rate_by_power"].get(power, 0.0)
            logger.info(f"  {power}: {received} received, {sent} sent, {rate:.1%} response rate")

    async def run(self):
        """Main bot loop."""
        try:
            await self.connect_and_initialize()

            logger.info(f"Bot {self.username} ({self.power_name}) is now running...")

            # Main event loop
            while self.running and not self.client.game.is_game_done:
                try:
                    # Synchronize with server periodically with retry logic
                    await self.circuit_breaker._retry_with_backoff(self.client.game.synchronize)

                    # Check if we need to submit orders
                    await self._check_if_orders_needed()

                    # Sleep for a bit before next iteration
                    await asyncio.sleep(5)

                except (asyncio.CancelledError, KeyboardInterrupt):
                    logger.info("Bot operation cancelled, shutting down")
                    break
                except (TimeoutError, asyncio.TimeoutError) as e:
                    logger.warning(f"Timeout in main loop: {e}")
                    # Continue loop but with a longer sleep
                    await asyncio.sleep(10)

            if self.client.game.is_game_done:
                logger.info("Game has finished")
            else:
                logger.info("Bot shutting down")
        except GameIdException:
            logger.error(f"Game with id {self.game_id} does not exist on the server. Exiting...")
        except (asyncio.CancelledError, KeyboardInterrupt):
            logger.info("Bot cancelled or interrupted")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Clean up resources with timeout protection."""
        logger.info("Starting cleanup process...")
        cleanup_timeout = 15.0  # Maximum time to spend on cleanup

        try:
            # Use asyncio.wait_for to prevent hanging during cleanup
            await asyncio.wait_for(self._perform_cleanup(), timeout=cleanup_timeout)
            logger.info("Cleanup completed successfully")
        except asyncio.TimeoutError:
            logger.warning(f"Cleanup timed out after {cleanup_timeout} seconds")

    async def _perform_cleanup(self):
        """Perform the actual cleanup operations."""
        cleanup_tasks = []

        # Game cleanup
        if hasattr(self, "client") and self.client and hasattr(self.client, "game") and self.client.game:
            logger.debug("Cleaning up game connection...")
            # Use asyncio.create_task to make game.leave() non-blocking
            leave_task = asyncio.create_task(self._safe_game_leave())
            cleanup_tasks.append(leave_task)

        # Client cleanup
        if hasattr(self, "client") and self.client:
            logger.debug("Cleaning up client connection...")
            close_task = asyncio.create_task(self._safe_client_close())
            cleanup_tasks.append(close_task)

        # Wait for all cleanup tasks with individual timeouts
        if cleanup_tasks:
            done, pending = await asyncio.wait(
                cleanup_tasks,
                timeout=10.0,  # 10 second timeout for all cleanup tasks
                return_when=asyncio.ALL_COMPLETED,
            )

            # Cancel any pending tasks
            for task in pending:
                logger.warning(f"Cancelling pending cleanup task: {task}")
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError as e:
                    logger.warning(f"Task was cancelled, rasied {e}", exc_info=True)

    async def _safe_game_leave(self):
        """Safely leave the game with timeout."""
        try:
            # Some diplomacy client implementations have async leave, others are sync
            await self.client.game.leave()
            logger.debug("Successfully left game")
        except asyncio.TimeoutError:
            logger.warning("Game leave operation timed out")

    async def _safe_client_close(self):
        """Safely close the client with timeout."""
        try:
            await asyncio.wait_for(self.client.close(), timeout=5.0)
            logger.debug("Successfully closed client")
        except asyncio.TimeoutError:
            logger.warning("Client close operation timed out")
