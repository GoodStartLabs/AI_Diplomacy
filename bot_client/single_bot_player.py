"""
Single Bot Player

A standalone bot that connects to a Diplomacy server, controls one power,
and waits for its turn to make moves. This script is designed to be run
as a separate process for each bot in a multi-player game.
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import argparse
import asyncio
import signal
from typing import Optional, Dict
import dotenv
from loguru import logger


from websocket_diplomacy_client import (
    WebSocketDiplomacyClient,
    connect_to_diplomacy_server,
)

from diplomacy.utils.exceptions import DiplomacyException, GameIdException

# Suppress warnings
# os.environ["GRPC_PYTHON_LOG_LEVEL"] = "40"
# os.environ["GRPC_VERBOSITY"] = "ERROR"
# os.environ["ABSL_MIN_LOG_LEVEL"] = "2"
# os.environ["GRPC_POLL_STRATEGY"] = "poll"


from diplomacy.engine.message import Message

from ai_diplomacy.clients import load_model_client
from ai_diplomacy.utils import get_valid_orders, gather_possible_orders
from ai_diplomacy.game_history import GameHistory
from ai_diplomacy.agent import DiplomacyAgent
from ai_diplomacy.initialization import initialize_agent_state_ext
from config import Configuration

dotenv.load_dotenv()

config = Configuration()

if config.DEBUG:
    import tracemalloc

    tracemalloc.start()


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
        username: str,
        password: str,
        power_name: str,
        model_name: str,
        hostname: str = "localhost",
        port: int = 8432,
        game_id: Optional[str] = None,
    ):
        assert username is not None
        assert password is not None
        assert power_name is not None
        assert model_name is not None

        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.power_name = power_name
        self.model_name = model_name
        self.game_id = game_id

        # Bot state
        self.client: WebSocketDiplomacyClient
        self.agent: DiplomacyAgent
        self.game_history = GameHistory()
        self.running = True
        self.current_phase = None
        self.waiting_for_orders = False
        self.orders_submitted = False

        # Track error stats
        self.error_stats: Dict[str, Dict[str, int]] = {
            self.model_name: {"conversation_errors": 0, "order_decoding_errors": 0}
        }

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    async def connect_and_initialize(self):
        """Connect to the server and initialize the bot."""
        logger.info(f"Connecting to {self.hostname}:{self.port} as {self.username}")

        # Connect to server
        self.client = await connect_to_diplomacy_server(
            hostname=self.hostname,
            port=self.port,
            username=self.username,
            password=self.password,
        )

        # Join or create game
        if self.game_id:
            logger.info(f"Joining existing game {self.game_id} as {self.power_name}")
            game = await self.client.join_game(
                game_id=self.game_id, power_name=self.power_name
            )
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
        await initialize_agent_state_ext(
            self.agent, self.client.game, self.game_history, config.log_file_path
        )

        # Setup game event callbacks
        await self._setup_event_callbacks()

        # Get initial game state
        await self.client.game.synchronize()
        self.current_phase = self.client.game.get_current_phase()
        self.game_history.add_phase(self.current_phase)

        logger.info(f"Bot initialized. Current phase: {self.current_phase}")
        logger.info(f"Game status: {self.client.game.status}")

        # Check if we need to submit orders immediately
        await self._check_if_orders_needed()

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
        # Update our game state
        await self.client.game.synchronize()

        new_phase = self.client.game.get_current_phase()
        if new_phase != self.current_phase:
            logger.info(f"New phase: {new_phase} (was: {self.current_phase})")
            self.current_phase = new_phase
            self.game_history.add_phase(new_phase)
            self.orders_submitted = False

            # Check if we need to submit orders for this new phase
            await self._check_if_orders_needed()

    def _on_game_processed(self, game, notification):
        """Handle game processing (when orders are executed)."""
        logger.info("Game processed - orders have been executed")

        # Schedule the async processing in the event loop
        asyncio.create_task(self._handle_game_processed_async())

    async def _handle_game_processed_async(self):
        """Async handler for game processing."""
        # Synchronize to get the results
        await self.client.game.synchronize()

        # Analyze the results
        await self._analyze_phase_results()

        self.orders_submitted = False
        self.waiting_for_orders = False

    def _on_message_received(self, game, notification):
        """Handle incoming diplomatic messages."""
        message = notification.message
        logger.info(
            f"Message received from {message.sender} to {message.recipient}: {message.message}"
        )

        # Add message to game history
        self.game_history.add_message(
            phase_name=message.phase,
            sender=message.sender,
            recipient=message.recipient,
            message_content=message.message,
        )

        # If it's a private message to us, consider responding
        if message.recipient == self.power_name and message.sender != self.power_name:
            # Schedule the async processing in the event loop
            asyncio.create_task(self._consider_message_response(message))

    def _on_status_update(self, game, notification):
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

        # We submit orders in Movement and Retreat phases
        if current_short_phase.endswith("M") or current_short_phase.endswith("R"):
            # Check if we have units that can receive orders
            orderable_locations = self.client.game.get_orderable_locations(
                self.power_name
            )
            if orderable_locations:
                logger.info(f"Orders needed for phase {current_short_phase}")
                self.waiting_for_orders = True
                await self._submit_orders()
            else:
                logger.info(
                    f"No orderable locations for {self.power_name} in {current_short_phase}"
                )

    async def _submit_orders(self):
        """Generate and submit orders for the current phase."""
        if self.orders_submitted:
            logger.debug("Orders already submitted for this phase")
            return

        try:
            logger.info("Generating orders...")

            # Get current board state
            board_state = self.client.game.get_state()

            # Get possible orders
            possible_orders = gather_possible_orders(self.client.game, self.power_name)

            if not possible_orders:
                logger.info("No possible orders, submitting empty order set")
                await self.client.set_orders(self.power_name, [])
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

            # Submit orders
            if orders:
                logger.info(f"Submitting orders: {orders}")
                await self.client.set_orders(self.power_name, orders)

                # Generate order diary entry
                await self.agent.generate_order_diary_entry(
                    self.client.game,
                    orders,
                    config.log_file_path,
                )
            else:
                logger.info("No valid orders generated, submitting empty order set")
                await self.client.set_orders(self.power_name, [])

            self.orders_submitted = True
            self.waiting_for_orders = False
            logger.info("Orders submitted successfully")
            # Call the no wait so we don't sit around for the turns to end.
            self.client.game.no_wait()

        except DiplomacyException as e:
            logger.error(f"Error submitting orders: {e}", exc_info=True)
            # FIXME: I don't think we want to do this. Likely want to retry again multiple times.
            #
            # Submit empty orders as fallback
            try:
                await self.client.set_orders(self.power_name, [])
                self.orders_submitted = True
            except Exception as fallback_error:
                logger.error(f"Failed to submit fallback orders: {fallback_error}")

    async def _analyze_phase_results(self):
        """Analyze the results of the previous phase."""
        try:
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

        except Exception as e:
            logger.error(f"Error analyzing phase results: {e}", exc_info=True)

    async def _consider_message_response(self, message: Message):
        """Consider whether to respond to a diplomatic message."""
        try:
            # Simple logic: if someone greets us, greet back
            if any(
                word in message.message.lower() for word in ["hello", "hi", "greetings"]
            ):
                response = f"Hello {message.sender}! Good to hear from you."
                await self.client.game.send_game_message(
                    sender=self.power_name, recipient=message.sender, message=response
                )
                logger.info(f"Sent response to {message.sender}: {response}")

        except Exception as e:
            logger.error(f"Error responding to message: {e}")

    async def run(self):
        """Main bot loop."""
        try:
            await self.connect_and_initialize()

            logger.info(f"Bot {self.username} ({self.power_name}) is now running...")

            # Main event loop
            while self.running and not self.client.game.is_game_done:
                # Synchronize with server periodically
                await self.client.game.synchronize()

                # Check if we need to submit orders
                await self._check_if_orders_needed()

                # Sleep for a bit before next iteration
                await asyncio.sleep(5)

            if self.client.game.is_game_done:
                logger.info("Game has finished")
            else:
                logger.info("Bot shutting down")
        except GameIdException:
            logger.error(
                f"Game with id {self.game_id} does not exist on the server. Exiting..."
            )
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Clean up resources."""
        try:
            if self.client.game:
                # We need to leave a game here, otherwise the connection stays for some reason and we can never rejoin
                self.client.game.leave()
            if self.client:
                await self.client.close()
            logger.info("Cleanup complete")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Single bot player for Diplomacy")

    parser.add_argument("--hostname", default="localhost", help="Server hostname")
    parser.add_argument("--port", type=int, default=8432, help="Server port")
    parser.add_argument("--username", help="Bot username")
    parser.add_argument("--password", default="password", help="Bot password")
    parser.add_argument("--power", default="FRANCE", help="Power to control")
    parser.add_argument("--model", default="gpt-3.5-turbo", help="AI model to use")
    parser.add_argument(
        "--game-id", help="Game ID to join (creates new if not specified)"
    )
    parser.add_argument("--log-level", default="INFO", help="Logging level")

    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_arguments()
    if not args.username:
        args.username = f"bot_{args.power}"

    bot = SingleBotPlayer(
        hostname=args.hostname,
        port=args.port,
        username=args.username,
        password=args.password,
        power_name=args.power,
        model_name=args.model,
        game_id=args.game_id,
    )

    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
