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
import select
import os
from typing import List, Dict, Optional

# Add parent directory to path for ai_diplomacy imports (runtime only)
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
        self.process_to_power: Dict[subprocess.Popen, str] = {}
        self.game_id: Optional[str] = None

        # Default power to model mapping
        self.default_models = {
            "AUSTRIA": "gemini-2.5-flash-lite-preview-06-17",
            "ENGLAND": "gemini-2.5-flash-lite-preview-06-17",
            "FRANCE": "gemini-2.5-flash-lite-preview-06-17",
            "GERMANY": "gemini-2.5-flash-lite-preview-06-17",
            "ITALY": "gemini-2.5-flash-lite-preview-06-17",
            "RUSSIA": "gemini-2.5-flash-lite-preview-06-17",
            "TURKEY": "gemini-2.5-flash-lite-preview-06-17",
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
        self,
        power: str,
        model: str,
        game_id: str,
        log_level: str = "INFO",
        negotiation_rounds: int = 3,
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
            "--negotiation-rounds",
            str(negotiation_rounds),
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
        stagger_delay: float = 0.5,
        negotiation_rounds: int = 3,
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
                process = self.launch_bot(power, model, game_id, log_level, negotiation_rounds)
                self.bot_processes.append(process)
                self.process_to_power[process] = power

                logger.info(f"Launched bot {i + 1}/{len(powers)}: {power} (PID: {process.pid})")

                # Stagger the launches to avoid overwhelming the server
                if i < len(powers) - 1:  # Don't delay after the last bot
                    await asyncio.sleep(stagger_delay)

            except Exception as e:
                logger.error(f"Failed to launch bot for {power}: {e}")

        logger.info(f"All {len(self.bot_processes)} bots launched successfully")

    def monitor_bots(self, check_interval: float = 1.0):
        """
        Monitor bot processes and log their output.

        Args:
            check_interval: How often to check bot status (seconds)
        """
        logger.info("Monitoring bot processes...")

        try:
            while self.bot_processes:
                active_processes = []

                # Collect all stdout file descriptors from active processes
                stdout_fds = []
                fd_to_process = {}

                for process in self.bot_processes:
                    if process.poll() is None:  # Still running
                        active_processes.append(process)
                        stdout_fd = process.stdout.fileno()
                        stdout_fds.append(stdout_fd)
                        fd_to_process[stdout_fd] = process
                    else:
                        # Process has ended
                        return_code = process.returncode
                        power = self.process_to_power.get(process, "UNKNOWN")
                        logger.info(f"{power} bot process {process.pid} ended with code {return_code}")

                        # Read any remaining output
                        remaining_output = process.stdout.read()
                        if remaining_output:
                            print(f"{power}_{process.pid} final output: {remaining_output}")

                        # Clean up the power mapping
                        self.process_to_power.pop(process, None)

                self.bot_processes = active_processes

                if not self.bot_processes:
                    logger.info("All bots have finished")
                    break

                # Use select to check which processes have output ready (Unix only)
                if stdout_fds and hasattr(select, "select"):
                    try:
                        ready_fds, _, _ = select.select(stdout_fds, [], [], 0.1)  # 100ms timeout

                        for fd in ready_fds:
                            process = fd_to_process[fd]
                            power = self.process_to_power.get(process, "UNKNOWN")

                            # Read available lines (but limit to prevent monopolizing)
                            lines_read = 0
                            max_lines_per_process = 10

                            while lines_read < max_lines_per_process:
                                try:
                                    line = process.stdout.readline()
                                    if not line:
                                        break
                                    print(f"{power}_{process.pid}: {line.strip()}")
                                    lines_read += 1
                                except:
                                    break

                    except (OSError, ValueError):
                        # Fallback if select fails
                        self._fallback_read_output(active_processes)
                else:
                    # Windows fallback or if select is not available
                    self._fallback_read_output(active_processes)

                logger.debug(f"{len(self.bot_processes)} bots still running")
                time.sleep(check_interval)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping bots...")
            self.stop_all_bots()

    def _fallback_read_output(self, active_processes):
        """Fallback method for reading output when select is not available."""
        for process in active_processes:
            power = self.process_to_power.get(process, "UNKNOWN")

            # Read limited lines per process to prevent monopolizing
            lines_read = 0
            max_lines_per_process = 3  # More conservative for fallback

            while lines_read < max_lines_per_process:
                try:
                    line = process.stdout.readline()
                    if not line:
                        break
                    print(f"{power}_{process.pid}: {line.strip()}")
                    lines_read += 1
                except:
                    break

    def stop_all_bots(self):
        """Stop all bot processes."""
        logger.info("Stopping all bot processes...")

        for process in self.bot_processes:
            if process.poll() is None:  # Still running
                power = self.process_to_power.get(process, "UNKNOWN")
                logger.info(f"Terminating {power} bot process {process.pid}")
                process.terminate()

                # Wait a bit for graceful shutdown
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Force killing {power} bot process {process.pid}")
                    process.kill()

        self.bot_processes.clear()
        self.process_to_power.clear()
        logger.info("All bots stopped")

    async def run_full_game(
        self,
        models: Optional[Dict[str, str]] = None,
        log_level: str = "INFO",
        creator_power: str = "FRANCE",
        negotiation_rounds: int = 3,
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
            )
        else:
            # Create new game and launch all bots
            await launcher.run_full_game(
                models=models,
                log_level=args.log_level,
                creator_power=args.creator_power,
                negotiation_rounds=args.negotiation_rounds,
            )

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error in launcher: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
