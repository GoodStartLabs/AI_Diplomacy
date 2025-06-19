"""
Multi-Bot Launcher

A launcher script that starts multiple bot players for a full Diplomacy game.
This script can create a game and launch bots for all powers, or join bots
to an existing game.
"""

import argparse
import asyncio
from loguru import logger
import subprocess
import sys
import time
from typing import List, Dict, Optional

# Add parent directory to path for ai_diplomacy imports (runtime only)
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from websocket_diplomacy_client import connect_to_diplomacy_server
from diplomacy.engine.game import Game


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
        self.game_id: Optional[str] = None

        # Default power to model mapping
        self.default_models = {
            "AUSTRIA": "gpt-3.5-turbo",
            "ENGLAND": "gpt-4",
            "FRANCE": "claude-3-haiku",
            "GERMANY": "gpt-3.5-turbo",
            "ITALY": "gemini-pro",
            "RUSSIA": "gpt-4",
            "TURKEY": "claude-3-sonnet",
        }

    async def create_game(self, creator_power: str = "FRANCE") -> str:
        """
        Create a new game and return the game ID.

        Args:
            creator_power: Which power should create the game

        Returns:
            Game ID of the created game
        """
        logger.info("Creating new game...")

        # Connect as the game creator
        creator_username = f"{self.base_username}_{creator_power.lower()}"
        client = await connect_to_diplomacy_server(
            hostname=self.hostname,
            port=self.port,
            username=creator_username,
            password=self.password,
        )

        # Create the game
        self.game = await client.create_game(
            map_name="standard",
            rules=["IGNORE_ERRORS", "POWER_CHOICE"],  # Allow messages and power choice
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

    def launch_bot(
        self, power: str, model: str, game_id: str, log_level: str = "INFO"
    ) -> subprocess.Popen:
        """
        Launch a single bot process.

        Args:
            power: Power name (e.g., "FRANCE")
            model: AI model to use
            game_id: Game ID to join
            log_level: Logging level

        Returns:
            subprocess.Popen object for the bot process
        """
        username = f"{self.base_username}_{power.lower()}"

        cmd = [
            sys.executable,
            "single_bot_player.py",
            "--hostname",
            self.hostname,
            "--port",
            str(self.port),
            "--username",
            username,
            "--password",
            self.password,
            "--power",
            power,
            "--model",
            model,
            "--game-id",
            game_id,
            "--log-level",
            log_level,
        ]

        logger.info(f"Launching bot for {power} with model {model}")
        logger.debug(f"Command: {' '.join(cmd)}")

        # Launch bot in a new process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,  # Line buffered
        )

        return process

    async def launch_all_bots(
        self,
        game_id: str,
        models: Optional[Dict[str, str]] = None,
        powers: Optional[List[str]] = None,
        log_level: str = "INFO",
        stagger_delay: float = 2.0,
    ):
        """
        Launch bots for all specified powers.

        Args:
            game_id: Game ID to join
            models: Mapping of power to model name (uses defaults if None)
            powers: List of powers to launch bots for (all 7 if None)
            log_level: Logging level for bots
            stagger_delay: Delay between launching bots (seconds)
        """
        if models is None:
            models = self.default_models.copy()

        if powers is None:
            powers = list(self.default_models.keys())

        logger.info(f"Launching bots for {len(powers)} powers...")

        for i, power in enumerate(powers):
            model = models.get(power, "gpt-3.5-turbo")

            try:
                process = self.launch_bot(power, model, game_id, log_level)
                self.bot_processes.append(process)

                logger.info(
                    f"Launched bot {i + 1}/{len(powers)}: {power} (PID: {process.pid})"
                )

                # Stagger the launches to avoid overwhelming the server
                if i < len(powers) - 1:  # Don't delay after the last bot
                    await asyncio.sleep(stagger_delay)

            except Exception as e:
                logger.error(f"Failed to launch bot for {power}: {e}")

        logger.info(f"All {len(self.bot_processes)} bots launched successfully")

    def monitor_bots(self, check_interval: float = 10.0):
        """
        Monitor bot processes and log their output.

        Args:
            check_interval: How often to check bot status (seconds)
        """
        logger.info("Monitoring bot processes...")

        try:
            while self.bot_processes:
                active_processes = []

                for _, process in enumerate(self.bot_processes):
                    if process.poll() is None:  # Still running
                        active_processes.append(process)

                        # Read and log any output (non-blocking)
                        try:
                            while True:
                                line = process.stdout.readline()
                                if not line:
                                    break
                                print(f"Bot-{process.pid}: {line.strip()}")
                        except:
                            pass  # No output available
                    else:
                        # Process has ended
                        return_code = process.returncode
                        logger.info(
                            f"Bot process {process.pid} ended with code {return_code}"
                        )

                        # Read any remaining output
                        try:
                            remaining_output = process.stdout.read()
                            if remaining_output:
                                print(
                                    f"Bot-{process.pid} final output: {remaining_output}"
                                )
                        except:
                            pass

                self.bot_processes = active_processes

                if self.bot_processes:
                    logger.debug(f"{len(self.bot_processes)} bots still running")
                    time.sleep(check_interval)
                else:
                    logger.info("All bots have finished")
                    break

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping bots...")
            self.stop_all_bots()

    def stop_all_bots(self):
        """Stop all bot processes."""
        logger.info("Stopping all bot processes...")

        for process in self.bot_processes:
            if process.poll() is None:  # Still running
                logger.info(f"Terminating bot process {process.pid}")
                process.terminate()

                # Wait a bit for graceful shutdown
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Force killing bot process {process.pid}")
                    process.kill()

        self.bot_processes.clear()
        logger.info("All bots stopped")

    async def run_full_game(
        self,
        models: Optional[Dict[str, str]] = None,
        log_level: str = "INFO",
        creator_power: str = "FRANCE",
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
            await self.launch_all_bots(game_id, models, log_level=log_level)

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
            await self.launch_all_bots(game_id, models, powers, log_level)

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
    parser.add_argument(
        "--game-id", help="Game ID to join (creates new if not specified)"
    )
    parser.add_argument(
        "--powers", nargs="+", help="Powers to launch bots for (default: all)"
    )
    parser.add_argument(
        "--models", help="Comma-separated list of models in power order"
    )
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    parser.add_argument(
        "--creator-power", default="FRANCE", help="Power that creates the game"
    )

    return parser.parse_args()


async def main():
    """Main entry point."""
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
            logger.error(
                f"Number of models ({len(model_list)}) must match number of powers ({len(powers)})"
            )
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
            )
        else:
            # Create new game and launch all bots
            await launcher.run_full_game(
                models=models,
                log_level=args.log_level,
                creator_power=args.creator_power,
            )

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error in launcher: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
