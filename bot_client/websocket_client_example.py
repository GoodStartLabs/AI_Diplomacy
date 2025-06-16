"""
Simple example demonstrating how to use the WebSocketDiplomacyClient.

This script shows basic operations like connecting, creating/joining games,
and interacting with a Diplomacy server via WebSocket.
"""

import asyncio
import logging
from websocket_diplomacy_client import connect_to_diplomacy_server

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def basic_client_example():
    """
    Basic example showing how to connect and interact with a Diplomacy server.
    """
    try:
        # Connect to the server
        logger.info("Connecting to Diplomacy server...")
        client = await connect_to_diplomacy_server(
            hostname="localhost",
            port=8432,
            username="test_player",
            password="test_password"
        )
        logger.info("Connected successfully!")

        # List available games
        logger.info("Listing available games...")
        games = await client.list_games()
        logger.info(f"Found {len(games)} games:")
        for game in games:
            logger.info(f"  Game {game.get('game_id', 'unknown')}: {game.get('status', 'unknown')} "
                       f"({game.get('n_players', 0)}/{game.get('n_controls', 0)} players)")

        # Get available maps
        logger.info("Getting available maps...")
        maps = await client.get_available_maps()
        logger.info(f"Available maps: {list(maps.keys())}")

        # Create a new game
        logger.info("Creating a new game...")
        game = await client.create_game(
            map_name="standard",
            rules=["NO_PRESS", "IGNORE_ERRORS", "POWER_CHOICE"],
            power_name="FRANCE",  # Control France
            n_controls=1,  # Only need 1 player to start (for testing)
            deadline=None  # No time pressure
        )
        logger.info(f"Created game {client.game_id} as {client.power_name}")

        # Get current game state
        logger.info("Getting current game state...")
        state = client.get_state()
        logger.info(f"Current phase: {client.get_current_phase()}")
        logger.info(f"France has {len(client.get_units('FRANCE'))} units")

        # Get possible orders
        logger.info("Getting possible orders for France...")
        possible_orders = client.get_all_possible_orders()
        france_orders = possible_orders.get('FRANCE', [])
        logger.info(f"France can make {len(france_orders)} possible orders")
        if france_orders:
            logger.info(f"First few orders: {france_orders[:5]}")

        # Submit some orders (example: hold all units)
        logger.info("Submitting hold orders for all French units...")
        units = client.get_units('FRANCE')
        hold_orders = []
        for unit in units:
            # Format: "A PAR H" means Army in Paris holds
            hold_orders.append(f"{unit} H")
        
        if hold_orders:
            await client.set_orders('FRANCE', hold_orders)
            logger.info(f"Submitted orders: {hold_orders}")

        # Try to process the game (might fail if we don't have admin rights)
        logger.info("Attempting to process the game...")
        try:
            await client.process_game()
            logger.info("Game processed successfully")
            
            # Synchronize to get updated state
            await client.synchronize()
            logger.info(f"After processing - Current phase: {client.get_current_phase()}")
            
        except Exception as e:
            logger.warning(f"Could not process game (normal if not admin): {e}")

        # Leave the game
        logger.info("Leaving the game...")
        await client.game.leave()
        logger.info("Left the game successfully")

    except Exception as e:
        logger.error(f"Error in example: {e}", exc_info=True)
    finally:
        # Clean up
        if 'client' in locals():
            await client.close()
        logger.info("Example completed")


async def join_existing_game_example(game_id: str):
    """
    Example showing how to join an existing game.
    
    Args:
        game_id: ID of the game to join
    """
    try:
        logger.info(f"Joining existing game {game_id}...")
        client = await connect_to_diplomacy_server(
            hostname="localhost",
            port=8432,
            username="test_player_2",
            password="test_password"
        )

        # Join as an observer first
        game = await client.join_game(game_id=game_id, power_name=None)
        logger.info(f"Joined game {game_id} as observer")

        # Get game state
        state = client.get_state()
        logger.info(f"Game phase: {client.get_current_phase()}")
        logger.info(f"Game status: {game.status}")

        # List powers and their status
        for power_name, power in client.powers.items():
            logger.info(f"{power_name}: {len(power.centers)} centers, "
                       f"{len(power.units)} units, eliminated: {power.is_eliminated()}")

    except Exception as e:
        logger.error(f"Error joining game: {e}", exc_info=True)
    finally:
        if 'client' in locals():
            await client.close()


async def message_sending_example():
    """
    Example showing how to send diplomatic messages.
    """
    try:
        client = await connect_to_diplomacy_server()
        
        # Create a game with PRESS allowed
        game = await client.create_game(
            rules=["IGNORE_ERRORS", "POWER_CHOICE"],  # Remove NO_PRESS to allow messages
            power_name="FRANCE",
            n_controls=1
        )
        
        # Send a public message
        await client.send_message(
            sender="FRANCE",
            recipient="GLOBAL",
            message="Greetings from France! Let's have a fair game."
        )
        logger.info("Sent public message")
        
        # Send a private message (would need another power to be present)
        try:
            await client.send_message(
                sender="FRANCE",
                recipient="ENGLAND",
                message="Hello England, shall we discuss an alliance?"
            )
            logger.info("Sent private message to England")
        except Exception as e:
            logger.info(f"Could not send private message: {e}")

    except Exception as e:
        logger.error(f"Error in messaging example: {e}", exc_info=True)
    finally:
        if 'client' in locals():
            await client.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Join existing game if game ID provided as argument
        game_id = sys.argv[1]
        asyncio.run(join_existing_game_example(game_id))
    else:
        # Run basic example
        asyncio.run(basic_client_example())