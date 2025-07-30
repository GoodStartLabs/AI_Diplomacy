from src import SingleBotPlayer
import asyncio
import argparse
from loguru import logger
from src.config import config
from src.utils import create_game


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Single bot player for Diplomacy")

    parser.add_argument("--hostname", default="localhost", help="Server hostname")
    parser.add_argument("--port", type=int, default=8432, help="Server port")
    parser.add_argument("--power", default="FRANCE", help="Power to control")
    parser.add_argument("--model", default="gemini-2.5-flash-lite-preview-06-17", help="AI model to use")
    parser.add_argument("--game-id", help="Game ID to join (creates new if not specified)")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    parser.add_argument("--fill-game", action="store_true", default=False, help="Launch one bot, or fill the game with bots. Default is one bot")
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
    """Main entry point with comprehensive error handling."""
    bots = {}
    args = parse_arguments()
    bot_tasks = set()
    shutdown_event = asyncio.Event()

    if not args.game_id:
        # No game id, lets create a new game.
        args.game_id = await create_game()

    if args.fill_game:
        logger.info(f"Filling game {args.game_id} with bots")
        for power_str, model_str in config.DEFAULT_POWER_MODELS_MAP.items():
            bots[power_str] = SingleBotPlayer(
                hostname=args.hostname,
                port=args.port,
                power_name=power_str,
                model_name=model_str,
                game_id=args.game_id,
                negotiation_rounds=args.negotiation_rounds,
            )

        # Set shutdown event on all bots
        for bot in bots.values():
            bot.shutdown_event = shutdown_event
            
        for power, bot in bots.items():
            task = asyncio.create_task(bot.run())
            bot_tasks.add(task)
            logger.info(f"Bot_{bot.power_name} started")
            
        try:
            await asyncio.gather(*bot_tasks)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down all bots...")
            shutdown_event.set()
            
            # Cancel all tasks
            for task in bot_tasks:
                if not task.done():
                    task.cancel()
                    
            # Wait for tasks to complete with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(*bot_tasks, return_exceptions=True),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                logger.warning("Some tasks did not complete within timeout")
        finally:
            # Cleanup all bots
            for bot in bots.values():
                await bot.cleanup()

    else:
        bot = SingleBotPlayer(
            hostname=args.hostname,
            port=args.port,
            power_name=args.power,
            model_name=args.model,
            game_id=args.game_id,
            negotiation_rounds=args.negotiation_rounds,
        )
        bot.shutdown_event = shutdown_event

        try:
            await bot.run()
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
            shutdown_event.set()
        finally:
            if bot:
                # Ensure cleanup happens even if there was an error
                await bot.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program interrupted")
