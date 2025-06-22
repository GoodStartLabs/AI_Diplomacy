"""
Fake WebSocket Server for Testing

This module provides a mock Diplomacy WebSocket server that implements the protocol
from WEBSOCKET.md for testing purposes. It responds to typed messages with appropriate
responses, allowing us to test our client implementation.
"""

import asyncio
import json
import uuid
import websockets
from typing import Dict, Any, Optional, Set
from loguru import logger

from models import (
    # Request types
    SignInRequest,
    CreateGameRequest,
    JoinGameRequest,
    ListGamesRequest,
    SetOrdersRequest,
    ProcessGameRequest,
    GetAllPossibleOrdersRequest,
    # Response types
    DataTokenResponse,
    DataGameResponse,
    DataGamesResponse,
    DataPossibleOrdersResponse,
    OkResponse,
    ErrorResponse,
    # Notifications
    parse_message,
    serialize_message,
)


class FakeWebSocketServer:
    """
    A fake WebSocket server that implements the Diplomacy protocol for testing.
    
    This server maintains minimal state and responds to requests with valid
    responses according to the WEBSOCKET.md protocol specification.
    """
    
    def __init__(self, host: str = "localhost", port: int = 8433):
        self.host = host
        self.port = port
        self.server = None
        self.connected_clients: Set[websockets.WebSocketServerProtocol] = set()
        
        # Mock server state
        self.users = {
            "test_user": "test_password",
            "ai_player": "password",
            "player1": "password"
        }
        self.tokens: Dict[str, str] = {}  # token -> username
        self.games: Dict[str, Dict[str, Any]] = {}
        self.game_counter = 1
        
    async def start(self):
        """Start the fake WebSocket server."""
        logger.info(f"Starting fake WebSocket server on {self.host}:{self.port}")
        self.server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port
        )
        logger.info("Fake WebSocket server started")
        
    async def stop(self):
        """Stop the fake WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("Fake WebSocket server stopped")
            
    async def handle_client(self, websocket):
        """Handle a new WebSocket client connection."""
        self.connected_clients.add(websocket)
        logger.info(f"Client connected from {websocket.remote_address}")
        
        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected")
        except Exception as e:
            logger.error(f"Error handling client: {e}")
        finally:
            self.connected_clients.discard(websocket)
            
    async def handle_message(self, websocket, message_text: str):
        """Handle an incoming message from a client."""
        try:
            # Parse the raw message
            data = json.loads(message_text)
            request = parse_message(data)
            
            # Generate response based on request type
            response = await self.generate_response(request)
            
            # Send response back to client
            if response:
                response_data = serialize_message(response)
                await websocket.send(json.dumps(response_data))
                logger.debug(f"Sent response: {response.name}")
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            logger.debug(f"Raw message: {message_text}")
            
            # Send error response if we can extract request_id
            try:
                data = json.loads(message_text)
                request_id = data.get("request_id", str(uuid.uuid4()))
                error_response = ErrorResponse(
                    request_id=request_id,
                    error_type="PARSING_ERROR",
                    message=str(e)
                )
                error_data = serialize_message(error_response)
                await websocket.send(json.dumps(error_data))
            except:
                logger.error("Could not send error response")
                
    async def generate_response(self, request) -> Optional[Any]:
        """Generate appropriate response for a request."""
        logger.info(f"Processing request: {request.name}")
        
        # Authentication requests
        if isinstance(request, SignInRequest):
            return await self.handle_sign_in(request)
            
        # Channel-level requests (require token)
        elif isinstance(request, CreateGameRequest):
            return await self.handle_create_game(request)
        elif isinstance(request, JoinGameRequest):
            return await self.handle_join_game(request)
        elif isinstance(request, ListGamesRequest):
            return await self.handle_list_games(request)
            
        # Game-level requests (require token + game context)
        elif isinstance(request, SetOrdersRequest):
            return await self.handle_set_orders(request)
        elif isinstance(request, ProcessGameRequest):
            return await self.handle_process_game(request)
        elif isinstance(request, GetAllPossibleOrdersRequest):
            return await self.handle_get_possible_orders(request)
            
        else:
            logger.warning(f"Unhandled request type: {type(request)}")
            return ErrorResponse(
                request_id=request.request_id,
                error_type="UNSUPPORTED_REQUEST",
                message=f"Request type {request.name} not supported by fake server"
            )
            
    async def handle_sign_in(self, request: SignInRequest) -> Any:
        """Handle authentication request."""
        username = request.username
        password = request.password
        
        if username in self.users and self.users[username] == password:
            # Generate auth token
            token = f"fake_token_{uuid.uuid4().hex[:16]}"
            self.tokens[token] = username
            
            return DataTokenResponse(
                request_id=request.request_id,
                data=token
            )
        else:
            return ErrorResponse(
                request_id=request.request_id,
                error_type="AUTHENTICATION_ERROR",
                message="Invalid username or password"
            )
            
    async def handle_create_game(self, request: CreateGameRequest) -> Any:
        """Handle game creation request."""
        if not self.validate_token(request.token):
            return self.create_auth_error(request.request_id)
            
        # Create a new game
        game_id = f"GAME_{self.game_counter:04d}"
        self.game_counter += 1
        
        game_data = {
            "game_id": game_id,
            "map_name": request.map_name,
            "rules": request.rules,
            "phase": "S1901M",
            "status": "FORMING",
            "n_controls": request.n_controls,
            "powers": {
                "AUSTRIA": {"units": [], "centers": ["VIE", "BUD", "TRI"], "is_eliminated": False},
                "ENGLAND": {"units": [], "centers": ["EDI", "LVP", "LON"], "is_eliminated": False},
                "FRANCE": {"units": [], "centers": ["PAR", "BRE", "MAR"], "is_eliminated": False},
                "GERMANY": {"units": [], "centers": ["BER", "MUN", "KIE"], "is_eliminated": False},
                "ITALY": {"units": [], "centers": ["ROM", "NAP", "VEN"], "is_eliminated": False},
                "RUSSIA": {"units": [], "centers": ["MOS", "SEV", "STP", "WAR"], "is_eliminated": False},
                "TURKEY": {"units": [], "centers": ["ANK", "CON", "SMY"], "is_eliminated": False},
            },
            "controlled_powers": {}
        }
        
        # If a specific power was requested, assign it
        if request.power_name:
            game_data["controlled_powers"][request.power_name] = self.tokens[request.token]
            
        self.games[game_id] = game_data
        
        return DataGameResponse(
            request_id=request.request_id,
            data=game_data
        )
        
    async def handle_join_game(self, request: JoinGameRequest) -> Any:
        """Handle game join request."""
        if not self.validate_token(request.token):
            return self.create_auth_error(request.request_id)
            
        game_id = request.game_id
        if game_id not in self.games:
            return ErrorResponse(
                request_id=request.request_id,
                error_type="GAME_NOT_FOUND",
                message=f"Game {game_id} not found"
            )
            
        game_data = self.games[game_id].copy()
        
        # If a specific power was requested, assign it
        if request.power_name:
            game_data["controlled_powers"][request.power_name] = self.tokens[request.token]
            self.games[game_id] = game_data
            
        return DataGameResponse(
            request_id=request.request_id,
            data=game_data
        )
        
    async def handle_list_games(self, request: ListGamesRequest) -> Any:
        """Handle list games request."""
        if not self.validate_token(request.token):
            return self.create_auth_error(request.request_id)
            
        # Return simplified game info
        games_list = []
        for game_id, game_data in self.games.items():
            games_list.append({
                "game_id": game_id,
                "map_name": game_data["map_name"],
                "status": game_data["status"],
                "phase": game_data["phase"],
                "n_controls": game_data["n_controls"]
            })
            
        return DataGamesResponse(
            request_id=request.request_id,
            data=games_list
        )
        
    async def handle_set_orders(self, request: SetOrdersRequest) -> Any:
        """Handle set orders request."""
        if not self.validate_token(request.token):
            return self.create_auth_error(request.request_id)
            
        game_id = request.game_id
        if game_id not in self.games:
            return ErrorResponse(
                request_id=request.request_id,
                error_type="GAME_NOT_FOUND",
                message=f"Game {game_id} not found"
            )
            
        # In a real server, we'd validate the orders and store them
        # For testing, we just acknowledge receipt
        logger.info(f"Orders received for {request.game_role}: {request.orders}")
        
        return OkResponse(request_id=request.request_id)
        
    async def handle_process_game(self, request: ProcessGameRequest) -> Any:
        """Handle process game request."""
        if not self.validate_token(request.token):
            return self.create_auth_error(request.request_id)
            
        game_id = request.game_id
        if game_id not in self.games:
            return ErrorResponse(
                request_id=request.request_id,
                error_type="GAME_NOT_FOUND",
                message=f"Game {game_id} not found"
            )
            
        # Simulate game processing
        game_data = self.games[game_id]
        current_phase = game_data["phase"]
        
        # Simple phase progression
        if current_phase == "S1901M":
            game_data["phase"] = "F1901M"
        elif current_phase == "F1901M":
            game_data["phase"] = "W1901A"
        else:
            # For testing, cycle back to start
            game_data["phase"] = "S1902M"
            
        self.games[game_id] = game_data
        
        # Send notification to all clients (in real implementation)
        # For testing, we'll just return OK
        return OkResponse(request_id=request.request_id)
        
    async def handle_get_possible_orders(self, request: GetAllPossibleOrdersRequest) -> Any:
        """Handle get possible orders request."""
        if not self.validate_token(request.token):
            return self.create_auth_error(request.request_id)
            
        # Return mock possible orders
        possible_orders = {
            "PAR": ["A PAR H", "A PAR - BUR", "A PAR - PIC", "A PAR - GAS"],
            "BRE": ["F BRE H", "F BRE - MAO", "F BRE - ENG", "F BRE - PIC"],
            "MAR": ["A MAR H", "A MAR - GAS", "A MAR - SPA", "A MAR - PIE"],
        }
        
        return DataPossibleOrdersResponse(
            request_id=request.request_id,
            data=possible_orders
        )
        
    def validate_token(self, token: str) -> bool:
        """Validate an authentication token."""
        return token in self.tokens
        
    def create_auth_error(self, request_id: str) -> ErrorResponse:
        """Create a standard authentication error response."""
        return ErrorResponse(
            request_id=request_id,
            error_type="AUTHENTICATION_ERROR",
            message="Invalid or missing authentication token"
        )


class FakeServerManager:
    """Context manager for the fake WebSocket server."""
    
    def __init__(self, host: str = "localhost", port: int = 8433):
        self.server = FakeWebSocketServer(host, port)
        
    async def __aenter__(self):
        await self.server.start()
        # Give the server a moment to start
        await asyncio.sleep(0.1)
        return self.server
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.server.stop()


# Utility function for tests
async def run_fake_server(host: str = "localhost", port: int = 8433):
    """Run the fake server (for manual testing)."""
    async with FakeServerManager(host, port) as server:
        logger.info(f"Fake server running on {host}:{port}")
        logger.info("Press Ctrl+C to stop")
        try:
            # Keep running until interrupted
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")


if __name__ == "__main__":
    # Run the fake server for manual testing
    asyncio.run(run_fake_server())