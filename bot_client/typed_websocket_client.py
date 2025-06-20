"""
Typed WebSocket Diplomacy Client

This demonstrates how to create a fully typed WebSocket client using the pydantic models
from models.py, providing type safety and protocol compliance.

This is a demonstration/reference implementation showing how to properly use the
typed messages with raw WebSocket connections.
"""

import asyncio
import json
import uuid
import websockets
from typing import Dict, Any, Optional, Union, List
from loguru import logger

from models import (
    # Request messages
    SignInRequest,
    CreateGameRequest,
    JoinGameRequest,
    ListGamesRequest,
    SetOrdersRequest,
    ProcessGameRequest,
    GetAllPossibleOrdersRequest,
    # Response messages
    DataTokenResponse,
    DataGameResponse,
    DataGamesResponse,
    OkResponse,
    ErrorResponse,
    # Utility functions
    parse_message,
    serialize_message,
    WebSocketMessage,
    ResponseMessage,
    NotificationMessage,
)


class TypedWebSocketDiplomacyClient:
    """
    A fully typed WebSocket client that uses pydantic models for all communications.
    
    This demonstrates the proper way to implement the WebSocket protocol
    as documented in WEBSOCKET.md using type-safe message models.
    """
    
    def __init__(self, hostname: str = "localhost", port: int = 8432, use_ssl: bool = False):
        """Initialize the typed WebSocket client."""
        self.hostname = hostname
        self.port = port
        self.use_ssl = use_ssl
        self.websocket = None
        self.token: Optional[str] = None
        self.game_id: Optional[str] = None
        self.game_role: Optional[str] = None
        self._pending_requests: Dict[str, asyncio.Future] = {}
        
    async def connect(self) -> None:
        """Establish WebSocket connection to the server."""
        protocol = "wss" if self.use_ssl else "ws"
        uri = f"{protocol}://{self.hostname}:{self.port}/"
        
        logger.info(f"Connecting to {uri}")
        self.websocket = await websockets.connect(uri)
        logger.info("WebSocket connection established")
        
        # Start message handler
        asyncio.create_task(self._message_handler())
        
    async def _message_handler(self):
        """Handle incoming WebSocket messages."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    parsed_msg = parse_message(data)
                    await self._handle_message(parsed_msg)
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    logger.debug(f"Raw message: {message}")
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Message handler error: {e}")
            
    async def _handle_message(self, message: WebSocketMessage):
        """Process an incoming parsed message."""
        if hasattr(message, 'request_id') and message.request_id in self._pending_requests:
            # This is a response to a request we sent
            future = self._pending_requests.pop(message.request_id)
            future.set_result(message)
        else:
            # This is a notification - handle it
            await self._handle_notification(message)
            
    async def _handle_notification(self, message: WebSocketMessage):
        """Handle server notifications."""
        logger.info(f"Received notification: {message.name}")
        # In a real implementation, you'd dispatch to appropriate handlers
        # based on the notification type
        
    async def _send_request(self, request: WebSocketMessage) -> ResponseMessage:
        """Send a request and wait for the response."""
        if not self.websocket:
            raise ConnectionError("Not connected to server")
            
        # Create a future to wait for the response
        future = asyncio.Future()
        self._pending_requests[request.request_id] = future
        
        # Send the request
        message_data = serialize_message(request)
        await self.websocket.send(json.dumps(message_data))
        logger.debug(f"Sent request: {request.name}")
        
        # Wait for response (with timeout)
        try:
            response = await asyncio.wait_for(future, timeout=30.0)
            return response
        except asyncio.TimeoutError:
            # Clean up the pending request
            self._pending_requests.pop(request.request_id, None)
            raise TimeoutError(f"Request {request.name} timed out")
            
    async def authenticate(self, username: str, password: str) -> str:
        """Authenticate with the server and return the auth token."""
        request = SignInRequest(
            request_id=str(uuid.uuid4()),
            username=username,
            password=password
        )
        
        response = await self._send_request(request)
        
        if isinstance(response, ErrorResponse):
            raise ValueError(f"Authentication failed: {response.message}")
        elif isinstance(response, DataTokenResponse):
            self.token = response.data
            logger.info("Successfully authenticated")
            return self.token
        else:
            raise ValueError(f"Unexpected response type: {type(response)}")
            
    async def create_game(
        self,
        map_name: str = "standard",
        rules: List[str] = None,
        power_name: Optional[str] = None,
        n_controls: int = 7,
        deadline: Optional[int] = None,
        registration_password: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new game on the server."""
        if not self.token:
            raise ValueError("Must authenticate first")
            
        if rules is None:
            rules = ["NO_PRESS", "IGNORE_ERRORS", "POWER_CHOICE"]
            
        request = CreateGameRequest(
            request_id=str(uuid.uuid4()),
            token=self.token,
            map_name=map_name,
            rules=rules,
            power_name=power_name,
            n_controls=n_controls,
            deadline=deadline,
            registration_password=registration_password
        )
        
        response = await self._send_request(request)
        
        if isinstance(response, ErrorResponse):
            raise ValueError(f"Game creation failed: {response.message}")
        elif isinstance(response, DataGameResponse):
            game_data = response.data
            self.game_id = game_data.get('game_id')
            self.game_role = power_name or "OMNISCIENT"
            logger.info(f"Created game {self.game_id} as {self.game_role}")
            return game_data
        else:
            raise ValueError(f"Unexpected response type: {type(response)}")
            
    async def join_game(
        self,
        game_id: str,
        power_name: Optional[str] = None,
        registration_password: Optional[str] = None
    ) -> Dict[str, Any]:
        """Join an existing game."""
        if not self.token:
            raise ValueError("Must authenticate first")
            
        request = JoinGameRequest(
            request_id=str(uuid.uuid4()),
            token=self.token,
            game_id=game_id,
            power_name=power_name,
            registration_password=registration_password
        )
        
        response = await self._send_request(request)
        
        if isinstance(response, ErrorResponse):
            raise ValueError(f"Game join failed: {response.message}")
        elif isinstance(response, DataGameResponse):
            game_data = response.data
            self.game_id = game_id
            self.game_role = power_name or "OBSERVER"
            logger.info(f"Joined game {game_id} as {self.game_role}")
            return game_data
        else:
            raise ValueError(f"Unexpected response type: {type(response)}")
            
    async def list_games(
        self,
        game_id_filter: Optional[str] = None,
        map_name: Optional[str] = None,
        status: Optional[str] = None,
        include_protected: bool = False
    ) -> List[Dict[str, Any]]:
        """List available games on the server."""
        if not self.token:
            raise ValueError("Must authenticate first")
            
        request = ListGamesRequest(
            request_id=str(uuid.uuid4()),
            token=self.token,
            game_id_filter=game_id_filter,
            map_name=map_name,
            status=status,
            include_protected=include_protected
        )
        
        response = await self._send_request(request)
        
        if isinstance(response, ErrorResponse):
            raise ValueError(f"List games failed: {response.message}")
        elif isinstance(response, DataGamesResponse):
            return response.data
        else:
            raise ValueError(f"Unexpected response type: {type(response)}")
            
    async def set_orders(
        self,
        power_name: str,
        orders: List[str],
        phase: Optional[str] = None
    ) -> None:
        """Submit orders for a power."""
        if not self.token or not self.game_id:
            raise ValueError("Must authenticate and join game first")
            
        request = SetOrdersRequest(
            request_id=str(uuid.uuid4()),
            token=self.token,
            game_id=self.game_id,
            game_role=power_name,
            phase=phase,
            orders=orders
        )
        
        response = await self._send_request(request)
        
        if isinstance(response, ErrorResponse):
            raise ValueError(f"Set orders failed: {response.message}")
        elif isinstance(response, OkResponse):
            logger.info(f"Orders set for {power_name}: {orders}")
        else:
            raise ValueError(f"Unexpected response type: {type(response)}")
            
    async def process_game(self, phase: Optional[str] = None) -> None:
        """Process the game (admin only)."""
        if not self.token or not self.game_id:
            raise ValueError("Must authenticate and join game first")
            
        request = ProcessGameRequest(
            request_id=str(uuid.uuid4()),
            token=self.token,
            game_id=self.game_id,
            game_role=self.game_role or "MASTER",
            phase=phase
        )
        
        response = await self._send_request(request)
        
        if isinstance(response, ErrorResponse):
            raise ValueError(f"Process game failed: {response.message}")
        elif isinstance(response, OkResponse):
            logger.info("Game processed successfully")
        else:
            raise ValueError(f"Unexpected response type: {type(response)}")
            
    async def get_all_possible_orders(self, phase: Optional[str] = None) -> Dict[str, List[str]]:
        """Get all possible orders for the current phase."""
        if not self.token or not self.game_id:
            raise ValueError("Must authenticate and join game first")
            
        request = GetAllPossibleOrdersRequest(
            request_id=str(uuid.uuid4()),
            token=self.token,
            game_id=self.game_id,
            game_role=self.game_role or "OBSERVER",
            phase=phase
        )
        
        response = await self._send_request(request)
        
        if isinstance(response, ErrorResponse):
            raise ValueError(f"Get possible orders failed: {response.message}")
        elif hasattr(response, 'data'):
            return response.data
        else:
            raise ValueError(f"Unexpected response type: {type(response)}")
            
    async def close(self):
        """Close the WebSocket connection."""
        if self.websocket:
            await self.websocket.close()
            logger.info("WebSocket connection closed")


# Example usage function
async def example_usage():
    """Demonstrate how to use the typed WebSocket client."""
    client = TypedWebSocketDiplomacyClient()
    
    try:
        # Connect to server
        await client.connect()
        
        # Authenticate
        token = await client.authenticate("player1", "password")
        print(f"Authenticated with token: {token[:10]}...")
        
        # List available games
        games = await client.list_games()
        print(f"Found {len(games)} games")
        
        # Create a new game
        game_data = await client.create_game(
            power_name="FRANCE",
            n_controls=1  # For testing
        )
        print(f"Created game: {game_data.get('game_id')}")
        
        # Submit some orders
        await client.set_orders("FRANCE", ["A PAR H", "F BRE H", "A MAR H"])
        print("Orders submitted")
        
        # Get possible orders
        possible_orders = await client.get_all_possible_orders()
        print(f"Possible orders: {len(possible_orders)} locations")
        
        # Process game (if admin)
        try:
            await client.process_game()
            print("Game processed")
        except ValueError as e:
            print(f"Could not process game: {e}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    # Run the example
    asyncio.run(example_usage())