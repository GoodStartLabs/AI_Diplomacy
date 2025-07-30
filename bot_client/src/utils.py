import argparse
import asyncio
from loguru import logger
import subprocess
import time
import sys
import os
from typing import List, Dict, Optional

# Add parent directory to path for ai_diplomacy imports (runtime only)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from .websocket_diplomacy_client import connect_to_diplomacy_server
from diplomacy.engine.game import Game
from .config import config


class CircuitBreaker:
    def __init__(
        self,
        connection_timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        self.connection_timeout = connection_timeout
        self.retry_delay = retry_delay
        self.max_retries = max_retries
        self.last_successful_operation = time.time()
        self.connection_failures = 0
        self.open = False
        self.last_failure = 0
        self.timeout = 60.0  # 1 minute before trying again

    def _is_open(self) -> bool:
        """Check if circuit breaker is open (preventing operations due to failures)."""
        if not self.open:
            return False

        # Check if timeout has passed and we should try again
        if time.time() - self.last_failure > self.timeout:
            logger.info("Circuit breaker timeout expired, allowing operations")
            self.open = False
            return False

        return True

    def _record_operation_success(self):
        """Record a successful operation."""
        self.last_successful_operation = time.time()
        self.connection_failures = 0
        if self.open:
            logger.info("Operation successful, closing circuit breaker")
            self.open = False

    def _record_operation_failure(self):
        """Record a failed operation and potentially open circuit breaker."""
        self.connection_failures += 1
        logger.warning(f"Operation failed, failure count: {self.connection_failures}")

        if self.connection_failures >= 5:  # Open circuit after 5 consecutive failures
            logger.error("Opening circuit breaker due to repeated failures")
            self.open = True
            self.last_failure = time.time()

    async def _retry_with_backoff(self, operation, *args, **kwargs):
        """Execute an operation with exponential backoff retry logic."""
        if self._is_open():
            raise Exception("Circuit breaker is open, operation not allowed")

        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                result = await asyncio.wait_for(operation(*args, **kwargs), timeout=self.connection_timeout)
                self._record_operation_success()
                return result

            except (TimeoutError, asyncio.TimeoutError) as e:
                last_exception = e
                logger.warning(f"Operation timeout on attempt {attempt + 1}/{self.max_retries + 1}: {e}")

            except ConnectionError as e:
                last_exception = e
                logger.warning(f"Connection error on attempt {attempt + 1}/{self.max_retries + 1}: {e}")

            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error on attempt {attempt + 1}/{self.max_retries + 1}: {e}")

            # Don't delay after the last attempt
            if attempt < self.max_retries:
                delay = self.retry_delay * (2**attempt)  # Exponential backoff
                logger.info(f"Retrying in {delay:.1f} seconds...")
                await asyncio.sleep(delay)

        # All retries failed
        self._record_operation_failure()
        logger.error(f"Operation failed after {self.max_retries + 1} attempts")
        raise last_exception or Exception("Operation failed with unknown error")


async def create_game(hostname="localhost", port=8432, password="password", creator_power: str = "FRANCE") -> str:
    """
    Create a new game and return the game ID.

    Args:
        creator_power: Which power should create the game

    Returns:
        Game ID of the created game
    """
    logger.info("Creating new game...")

    # Connect as the game creator
    creator_username = f"bot_{creator_power}"
    client = await connect_to_diplomacy_server(
        hostname=hostname,
        port=port,
        username=creator_username,
        password=password,
    )

    # Create the game
    # TODO: Make more of the rules come from the config file
    _ = await client.create_game(
        map_name="standard",
        rules=config.DEFAULT_GAME_RULES,
        power_name=creator_power,
        n_controls=7,  # Full 7-player game
        deadline=None,  # No time pressure
    )

    game_id = client.game_id
    logger.info(f"Created game {game_id}")

    # Leave the game so the bot can join properly
    await client.game.leave()
    await client.close()
    assert game_id is not None, "game_id cannot be None, failed to create new game."
    return game_id


class MultiBotLauncher:
    """
    Launcher for multiple bot players.

    Can either:
    1. Create a new game and launch bots for all powers
    2. Launch bots to join an existing game
    """

    def __init__(
        self,
        hostname: str = "localhost",
        port: int = 8432,
        base_username: str = "bot",
        password: str = "password",
    ):
        self.game: Game
        self.hostname = hostname
        self.port = port
        self.base_username = base_username
        self.password = password
        self.bot_processes: List[subprocess.Popen] = []
        self.process_to_power: Dict[subprocess.Popen, str] = {}
        self.game_id: Optional[str] = None

    async def run_full_game(
        self,
        models: Optional[Dict[str, str]] = None,
        log_level: str = "INFO",
        creator_power: str = "FRANCE",
        negotiation_rounds: int = 3,
        connection_timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        """
        Create a game and launch all bots for a complete game.

        Args:
            models: Power to model mapping
            log_level: Logging level for bots
            creator_power: Which power should create the game
        """
        try:
            # Create the game
            game_id = await self.create_game(creator_power)
            self.game_id = game_id

            # Wait a moment for the server to be ready
            await asyncio.sleep(2)

            # Launch all bots
            await self.launch_all_bots(
                game_id,
                models,
                log_level=log_level,
                negotiation_rounds=negotiation_rounds,
                connection_timeout=connection_timeout,
                max_retries=max_retries,
                retry_delay=retry_delay,
            )

            # Monitor the bots
            self.monitor_bots()

        except Exception as e:
            logger.error(f"Error running full game: {e}", exc_info=True)
        finally:
            self.stop_all_bots()

    async def join_existing_game(
        self,
        game_id: str,
        powers: List[str],
        models: Optional[Dict[str, str]] = None,
        log_level: str = "INFO",
        negotiation_rounds: int = 3,
        connection_timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        """
        Launch bots to join an existing game.

        Args:
            game_id: Game ID to join
            powers: List of powers to launch bots for
            models: Power to model mapping
            log_level: Logging level for bots
        """
        try:
            self.game_id = game_id

            # Launch bots for specified powers
            await self.launch_all_bots(
                game_id,
                models,
                powers,
                log_level,
                negotiation_rounds=negotiation_rounds,
                connection_timeout=connection_timeout,
                max_retries=max_retries,
                retry_delay=retry_delay,
            )

            # Monitor the bots
            self.monitor_bots()

        except Exception as e:
            logger.error(f"Error joining existing game: {e}", exc_info=True)
        finally:
            self.stop_all_bots()


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Launch multiple bot players")

    parser.add_argument("--hostname", default="localhost", help="Server hostname")
    parser.add_argument("--port", type=int, default=8432, help="Server port")
    parser.add_argument("--username-base", default="bot", help="Base username for bots")
    parser.add_argument("--password", default="password", help="Password for all bots")
    parser.add_argument("--game-id", help="Game ID to join (creates new if not specified)")
    parser.add_argument("--powers", nargs="+", help="Powers to launch bots for (default: all)")
    parser.add_argument("--models", help="Comma-separated list of models in power order")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    parser.add_argument("--creator-power", default="FRANCE", help="Power that creates the game")
    parser.add_argument(
        "--negotiation-rounds",
        type=int,
        default=3,
        help="Number of negotiation rounds per movement phase (default: 3)",
    )
    parser.add_argument(
        "--connection-timeout",
        type=float,
        default=30.0,
        help="Timeout for network operations in seconds (default: 30.0)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum number of retries for failed operations (default: 3)",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=2.0,
        help="Base delay between retries in seconds (default: 2.0)",
    )

    return parser.parse_args()


async def main():
    """Main entry point."""

    # FIXME: Arg parse appears to not like game ids with hypens in the name. e.g.
    # uv run python multi_bot_launcher.py --game-id "-1D0i-fobmvprIh1" results in an error
    args = parse_arguments()

    launcher = MultiBotLauncher(
        hostname=args.hostname,
        port=args.port,
        base_username=args.username_base,
        password=args.password,
    )

    # Parse models if provided
    models = None
    if args.models:
        model_list = [m.strip() for m in args.models.split(",")]
        powers = args.powers or list(launcher.default_models.keys())
        if len(model_list) != len(powers):
            logger.error(f"Number of models ({len(model_list)}) must match number of powers ({len(powers)})")
            return
        models = dict(zip(powers, model_list))

    try:
        if args.game_id:
            # Join existing game
            powers = args.powers or list(launcher.default_models.keys())
            await launcher.join_existing_game(
                game_id=args.game_id,
                powers=powers,
                models=models,
                log_level=args.log_level,
                negotiation_rounds=args.negotiation_rounds,
                connection_timeout=args.connection_timeout,
                max_retries=args.max_retries,
                retry_delay=args.retry_delay,
            )
        else:
            # Create new game and launch all bots
            await launcher.run_full_game(
                models=models,
                log_level=args.log_level,
                creator_power=args.creator_power,
                negotiation_rounds=args.negotiation_rounds,
                connection_timeout=args.connection_timeout,
                max_retries=args.max_retries,
                retry_delay=args.retry_delay,
            )

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error in launcher: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
