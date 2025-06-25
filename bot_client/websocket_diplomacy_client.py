"""
WebSocket Diplomacy Client

A simplified client wrapper for connecting to a Diplomacy server via WebSocket
and playing games remotely, designed as a drop-in replacement for direct Game() usage.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import Dict, List, Optional, Any
from loguru import logger

from diplomacy.client.connection import connect
from diplomacy.client.network_game import NetworkGame
from diplomacy.engine.message import Message
from diplomacy.utils.exceptions import DiplomacyException


class WebSocketDiplomacyClient:
    """
    A WebSocket-based client for playing Diplomacy games on a remote server.

    This client provides a simplified interface similar to the local Game class
    but communicates with a remote server via WebSocket connections.
    """

    def __init__(self, hostname: str = "localhost", port: int = 8432, use_ssl: bool = False):
        """
        Initialize the WebSocket client.

        Args:
            hostname: Server hostname (default: localhost)
            port: Server port (default: 8432)
            use_ssl: Whether to use SSL/TLS (default: False)
        """
        self.hostname = hostname
        self.port = port
        self.use_ssl = use_ssl

        self.game: NetworkGame
        self.connection = None
        self.channel = None
        self.username = None
        self.token = None

        # Game state tracking
        self._game_id = None
        self._power_name = None
        self._game_role = None

    async def connect_and_authenticate(self, username: str, password: str) -> None:
        """
        Connect to the server and authenticate.

        Args:
            username: Username for authentication
            password: Password for authentication
        """
        logger.info(f"Connecting to {self.hostname}:{self.port}")
        self.connection = await connect(self.hostname, self.port)

        logger.info(f"Authenticating as {username}")
        self.channel = await self.connection.authenticate(username, password)
        self.username = username
        self.token = self.channel.token

        logger.info("Successfully connected and authenticated")

    async def create_game(
        self,
        map_name: str = "standard",
        rules: Optional[List[str]] = None,
        game_id: Optional[str] = None,
        power_name: Optional[str] = None,
        n_controls: int = 7,
        deadline: Optional[int] = None,
        registration_password: Optional[str] = None,
    ) -> NetworkGame:
        """
        Create a new game on the server.

        Args:
            map_name: Name of the map to use (default: "standard")
            rules: List of game rules (default: ["NO_PRESS", "IGNORE_ERRORS", "POWER_CHOICE"])
            game_id: Optional specific game ID
            power_name: Power to control (None for omniscient observer)
            n_controls: Number of controls required to start the game
            deadline: Game deadline in seconds
            registration_password: Password to protect the game

        Returns:
            NetworkGame object representing the created game
        """
        if not self.channel:
            raise DiplomacyException("Must connect and authenticate first")

        if rules is None:
            rules = ["NO_PRESS", "IGNORE_ERRORS", "POWER_CHOICE"]

        logger.info(f"Creating game with map '{map_name}', rules: {rules}")

        self.game = await self.channel.create_game(
            map_name=map_name,
            rules=rules,
            game_id=game_id,
            power_name=power_name,
            n_controls=n_controls,
            deadline=deadline,
            registration_password=registration_password,
        )

        self._game_id = self.game.game_id
        self._power_name = power_name
        self._game_role = power_name if power_name else "OMNISCIENT"

        logger.info(f"Created game {self._game_id} as {self._game_role}")
        return self.game

    async def join_game(
        self,
        game_id: str,
        power_name: Optional[str] = None,
        registration_password: Optional[str] = None,
    ) -> NetworkGame:
        """
        Join an existing game.

        Args:
            game_id: ID of the game to join
            power_name: Power to control (None for observer)
            registration_password: Password if the game is protected

        Returns:
            NetworkGame object representing the joined game
        """
        if not self.channel:
            raise DiplomacyException("Must connect and authenticate first")

        logger.info(f"Joining game {game_id} as {power_name or 'observer'}")

        self.game = await self.channel.join_game(
            game_id=game_id,
            power_name=power_name,
            registration_password=registration_password,
        )

        self._game_id = game_id
        self._power_name = power_name
        self._game_role = power_name if power_name else "OBSERVER"

        logger.info(f"Joined game {game_id} as {self._game_role}")
        return self.game

    async def list_games(
        self,
        game_id_filter: Optional[str] = None,
        map_name: Optional[str] = None,
        status: Optional[str] = None,
        include_protected: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        List available games on the server.

        Args:
            game_id_filter: Filter by game ID substring
            map_name: Filter by map name
            status: Filter by game status
            include_protected: Include password-protected games

        Returns:
            List of game information dictionaries
        """
        if not self.channel:
            raise DiplomacyException("Must connect and authenticate first")

        games = await self.channel.list_games(
            game_id=game_id_filter,
            map_name=map_name,
            status=status,
            include_protected=include_protected,
        )

        return games

    async def get_available_maps(self) -> Dict[str, Any]:
        """
        Get available maps from the server.

        Returns:
            Dictionary of available maps and their properties
        """
        if not self.channel:
            raise DiplomacyException("Must connect and authenticate first")

        return await self.channel.get_available_maps()

    async def set_orders(self, power_name: str, orders: List[str], wait: Optional[bool] = None) -> None:
        """
        Set orders for a power.

        Args:
            power_name: Name of the power
            orders: List of order strings
            wait: Whether to wait for other players
        """
        if not self.game:
            raise DiplomacyException("Must join a game first")

        logger.debug(f"Setting orders for {power_name}: {orders}")
        await self.game.set_orders(orders=orders, wait=wait)

    async def clear_orders(self, power_name: str) -> None:
        """
        Clear orders for a power.

        Args:
            power_name: Name of the power
        """
        if not self.game:
            raise DiplomacyException("Must join a game first")

        logger.debug(f"Clearing orders for {power_name}")
        await self.game.clear_orders()

    async def set_wait_flag(self, power_name: str, wait: bool) -> None:
        """
        Set the wait flag for a power.

        Args:
            power_name: Name of the power
            wait: Whether to wait for other players
        """
        if not self.game:
            raise DiplomacyException("Must join a game first")

        logger.debug(f"Setting wait flag for {power_name}: {wait}")
        if wait:
            await self.game.wait()
        else:
            await self.game.no_wait()

    async def send_message(self, sender: str, recipient: str, message: str, phase: Optional[str] = None) -> None:
        """
        Send a diplomatic message.

        Args:
            sender: Sending power name
            recipient: Receiving power name (or GLOBAL for public messages)
            message: Message content
            phase: Game phase (uses current phase if None)
        """
        if not self.game:
            raise DiplomacyException("Must join a game first")

        if phase is None:
            phase = self.game.current_short_phase

        msg = Message(sender=sender, recipient=recipient, message=message, phase=phase)

        logger.debug(f"Sending message from {sender} to {recipient}: {message}")
        await self.game.send_game_message(message=msg)

    async def send_broadcast_message(self, sender: str, message: str, phase: Optional[str] = None) -> None:
        """
        Send a broadcast message to all active powers.

        Args:
            sender: Sending power name
            message: Message content
            phase: Game phase (uses current phase if None)
        """
        if not self.game:
            raise DiplomacyException("Must join a game first")

        if phase is None:
            phase = self.game.current_short_phase

        # Send to all active powers
        active_powers = [power_name for power_name, power in self.powers.items() if not power.is_eliminated() and power_name != sender]

        for recipient in active_powers:
            await self.send_message(sender, recipient, message, phase)

        logger.debug(f"Broadcast message from {sender} to {len(active_powers)} powers: {message}")

    async def get_recent_messages(self, phase: Optional[str] = None, limit: int = 50) -> List[Message]:
        """
        Get recent messages from the game.

        Args:
            phase: Filter by specific phase (None for current phase)
            limit: Maximum number of messages to return

        Returns:
            List of recent messages
        """
        if not self.game:
            raise DiplomacyException("Must join a game first")

        if phase is None:
            phase = self.game.current_short_phase

        # Get messages from the game and filter by phase
        all_messages = list(self.messages.values())

        # Filter by phase if specified
        filtered_messages = [msg for msg in all_messages if msg.phase == phase]

        # Sort by time (most recent first) and limit
        filtered_messages.sort(key=lambda m: m.time_sent or 0, reverse=True)

        return filtered_messages[:limit]

    async def process_game(self) -> None:
        """
        Force the game to process immediately (admin/moderator only).
        """
        if not self.game:
            raise DiplomacyException("Must join a game first")

        logger.info("Processing game")
        await self.game.process()

    async def synchronize(self) -> None:
        """
        Synchronize the local game state with the server.
        """
        if not self.game:
            raise DiplomacyException("Must join a game first")

        logger.debug("Synchronizing game state")
        await self.game.synchronize()

    async def get_phase_history(self, from_phase: Optional[str] = None, to_phase: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get phase history for the game.

        Args:
            from_phase: Starting phase (None for beginning)
            to_phase: Ending phase (None for current)

        Returns:
            List of phase data dictionaries
        """
        if not self.game:
            raise DiplomacyException("Must join a game first")

        return await self.game.get_phase_history(from_phase=from_phase, to_phase=to_phase)

    async def vote(self, power_name: str, vote: str) -> None:
        """
        Submit a vote (e.g., for draw).

        Args:
            power_name: Name of the power voting
            vote: Vote value (e.g., "yes", "no")
        """
        if not self.game:
            raise DiplomacyException("Must join a game first")

        logger.debug(f"Voting {vote} for {power_name}")
        await self.game.vote(vote=vote)

    def get_current_phase(self) -> str:
        """Get the current game phase."""
        if not self.game:
            raise DiplomacyException("Must join a game first")
        return self.game.get_current_phase()

    def get_current_short_phase(self) -> str:
        """Get the current short phase name."""
        if not self.game:
            raise DiplomacyException("Must join a game first")
        return self.game.current_short_phase

    def get_state(self) -> Dict[str, Any]:
        """Get the current game state."""
        if not self.game:
            raise DiplomacyException("Must join a game first")
        return self.game.get_state()

    def get_power(self, power_name: str) -> Any:
        """Get power object by name."""
        if not self.game:
            raise DiplomacyException("Must join a game first")
        return self.game.get_power(power_name)

    def get_orderable_locations(self, power_name: str) -> List[str]:
        """Get orderable locations for a power."""
        if not self.game:
            raise DiplomacyException("Must join a game first")
        return self.game.get_orderable_locations(power_name)

    def get_all_possible_orders(self) -> Dict[str, List[str]]:
        """Get all possible orders for all powers."""
        if not self.game:
            raise DiplomacyException("Must join a game first")
        return self.game.get_all_possible_orders()

    def get_units(self, power_name: str) -> List[str]:
        """Get units for a power."""
        if not self.game:
            raise DiplomacyException("Must join a game first")
        return self.game.get_units(power_name)

    @property
    def is_game_done(self) -> bool:
        """Check if the game is done."""
        if not self.game:
            return False
        return self.game.is_game_done

    @property
    def powers(self) -> Dict[str, Any]:
        """Get all powers in the game."""
        if not self.game:
            raise DiplomacyException("Must join a game first")
        return self.game.powers

    @property
    def order_history(self) -> Dict[str, Dict[str, List[str]]]:
        """Get order history."""
        if not self.game:
            raise DiplomacyException("Must join a game first")
        return self.game.order_history

    @property
    def result_history(self) -> Dict[str, Dict[str, List[str]]]:
        """Get result history."""
        if not self.game:
            raise DiplomacyException("Must join a game first")
        return self.game.result_history

    @property
    def messages(self) -> Dict[int, Message]:
        """Get game messages."""
        if not self.game:
            raise DiplomacyException("Must join a game first")
        return self.game.messages

    @property
    def game_id(self) -> Optional[str]:
        """Get the current game ID."""
        return self._game_id

    @property
    def power_name(self) -> Optional[str]:
        """Get the controlled power name."""
        return self._power_name

    @property
    def game_role(self) -> Optional[str]:
        """Get the current game role."""
        return self._game_role

    async def close(self) -> None:
        """Close the connection to the server."""
        if self.connection:
            try:
                # The connection doesn't have a direct close method in the API,
                # but we can disconnect by setting the connection to None
                self.connection = None
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")

        logger.info("Connection closed")


# Convenience function for quick setup
async def connect_to_diplomacy_server(
    username: str,
    password: str,
    hostname: str = "localhost",
    port: int = 8432,
    use_ssl: bool = False,
) -> WebSocketDiplomacyClient:
    """
    Convenience function to quickly connect to a Diplomacy server.

    Args:
        hostname: Server hostname
        port: Server port
        username: Username for authentication
        password: Password for authentication
        use_ssl: Whether to use SSL/TLS

    Returns:
        Connected and authenticated WebSocketDiplomacyClient
    """
    client = WebSocketDiplomacyClient(hostname, port, use_ssl)
    await client.connect_and_authenticate(username, password)
    return client
