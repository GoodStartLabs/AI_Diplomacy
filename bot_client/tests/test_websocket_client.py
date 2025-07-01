"""
Tests for WebSocket client functionality using the fake server.

These tests verify that our typed WebSocket client can properly:
1. Connect to a WebSocket server
2. Send and receive typed messages according to the protocol
3. Handle authentication, game creation, and game operations
4. Validate message format and content
"""

from typing import Dict
import pytest
import uuid

from models import (
    SignInRequest,
    CreateGameRequest,
    SetOrdersRequest,
    serialize_message,
    parse_message,
)
from websocket_diplomacy_client import WebSocketDiplomacyClient


class TestAuthentication:
    """Test authentication flow and message handling."""

    @pytest.mark.websocket
    async def test_successful_authentication(self, client: WebSocketDiplomacyClient, helpers):
        """Test successful authentication with valid credentials."""
        await client.connect_and_authenticate("test_user", "test_password")
        helpers.assert_valid_token(client.token)

    @pytest.mark.websocket
    async def test_failed_authentication(self, client):
        """Test authentication failure with invalid credentials."""
        await client.connect()

        with pytest.raises(ValueError, match="Authentication failed"):
            await client.authenticate("invalid_user", "wrong_password")

        assert client.token is None

    @pytest.mark.websocket
    async def test_authentication_message_format(self, credentials: Dict[str, str], client: WebSocketDiplomacyClient):
        """Test that authentication messages are properly formatted."""
        await client.connect_and_authenticate(**credentials)

        # Create a sign-in request manually to test message format
        request = SignInRequest(request_id=str(uuid.uuid4()), username="test_user", password="test_password")

        # Verify the request serializes correctly
        message_data = serialize_message(request)
        assert message_data["name"] == "sign_in"
        assert message_data["username"] == "test_user"
        assert message_data["password"] == "test_password"
        assert "request_id" in message_data

        # Test that we can parse it back
        parsed = parse_message(message_data)
        assert isinstance(parsed, SignInRequest)
        assert parsed.username == "test_user"


class TestGameOperations:
    """Test game creation, joining, and basic operations."""

    @pytest.mark.websocket
    async def test_create_game(self, authenticated_client, helpers):
        """Test creating a new game."""
        game_data = await authenticated_client.create_game(power_name="FRANCE", n_controls=1)

        helpers.assert_valid_game_data(game_data)
        assert authenticated_client.game_id is not None
        assert authenticated_client.game_role == "FRANCE"

    @pytest.mark.websocket
    async def test_list_games(self, authenticated_client, helpers):
        """Test listing available games."""
        # First create a game so there's something to list
        await authenticated_client.create_game(power_name="ENGLAND", n_controls=1)

        games = await authenticated_client.list_games()

        helpers.assert_valid_games_list(games)
        assert len(games) >= 1

        # Check that our created game is in the list
        game_ids = [game["game_id"] for game in games]
        assert authenticated_client.game_id in game_ids

    @pytest.mark.websocket
    async def test_join_existing_game(self, client: WebSocketDiplomacyClient, helpers):
        """Test joining an existing game."""
        # Connect and authenticate a first client
        await client.connect()
        await client.authenticate("test_user", "test_password")

        # Create a game
        game_data = await client.create_game(power_name="FRANCE", n_controls=1)
        game_id = game_data["game_id"]

        # Create a second client to join the game
        client2 = client.__class__("localhost", 8433, use_ssl=False)
        try:
            await client2.connect()
            await client2.authenticate("ai_player", "password")

            # Join the existing game as a different power
            joined_game_data = await client2.join_game(game_id, power_name="ENGLAND")

            helpers.assert_valid_game_data(joined_game_data)
            assert joined_game_data["game_id"] == game_id
            assert client2.game_role == "ENGLAND"

        finally:
            await client2.close()

    @pytest.mark.websocket
    async def test_join_nonexistent_game(self, authenticated_client):
        """Test joining a game that doesn't exist."""
        with pytest.raises(ValueError, match="Game .* not found"):
            await authenticated_client.join_game("NONEXISTENT_GAME", power_name="FRANCE")


class TestGamePlay:
    """Test actual gameplay operations like setting orders and processing."""

    @pytest.mark.websocket
    async def test_set_orders(self, client_with_game):
        """Test submitting orders for a power."""
        orders = ["A PAR H", "F BRE H", "A MAR H"]

        # Should not raise an exception
        await client_with_game.set_orders("FRANCE", orders)

    @pytest.mark.websocket
    async def test_set_empty_orders(self, client_with_game):
        """Test submitting empty orders."""
        await client_with_game.set_orders("FRANCE", [])

    @pytest.mark.websocket
    async def test_process_game(self, client_with_game):
        """Test processing the game phase."""
        # Should not raise an exception (fake server allows processing)
        await client_with_game.process_game()

    @pytest.mark.websocket
    async def test_get_possible_orders(self, client_with_game):
        """Test getting possible orders for the current phase."""
        possible_orders = await client_with_game.get_all_possible_orders()

        assert isinstance(possible_orders, dict)
        # Fake server returns some mock orders
        assert len(possible_orders) > 0

        # Check format: location -> list of orders
        for location, orders in possible_orders.items():
            assert isinstance(location, str)
            assert isinstance(orders, list)
            for order in orders:
                assert isinstance(order, str)


class TestMessageValidation:
    """Test message format validation and error handling."""

    @pytest.mark.websocket
    async def test_create_game_message_format(self, authenticated_client):
        """Test that create game messages have correct format."""
        request = CreateGameRequest(
            request_id=str(uuid.uuid4()),
            token=authenticated_client.token,
            map_name="standard",
            rules=["NO_PRESS", "IGNORE_ERRORS"],
            power_name="AUSTRIA",
            n_controls=7,
        )

        message_data = serialize_message(request)

        # Verify all required fields are present
        assert message_data["name"] == "create_game"
        assert message_data["token"] == authenticated_client.token
        assert message_data["map_name"] == "standard"
        assert message_data["rules"] == ["NO_PRESS", "IGNORE_ERRORS"]
        assert message_data["power_name"] == "AUSTRIA"
        assert message_data["n_controls"] == 7
        assert "request_id" in message_data

    @pytest.mark.websocket
    async def test_set_orders_message_format(self, client_with_game):
        """Test that set orders messages have correct format."""
        request = SetOrdersRequest(
            request_id=str(uuid.uuid4()),
            token=client_with_game.token,
            game_id=client_with_game.game_id,
            game_role="FRANCE",
            orders=["A PAR H", "F BRE - ENG"],
        )

        message_data = serialize_message(request)

        # Verify all required fields are present
        assert message_data["name"] == "set_orders"
        assert message_data["token"] == client_with_game.token
        assert message_data["game_id"] == client_with_game.game_id
        assert message_data["game_role"] == "FRANCE"
        assert message_data["orders"] == ["A PAR H", "F BRE - ENG"]
        assert "request_id" in message_data

    @pytest.mark.websocket
    async def test_error_response_handling(self, client):
        """Test that error responses are properly handled."""
        await client.connect()

        # Try to authenticate with wrong credentials
        with pytest.raises(ValueError) as exc_info:
            await client.authenticate("bad_user", "bad_pass")

        assert "Authentication failed" in str(exc_info.value)

    @pytest.mark.websocket
    async def test_unauthenticated_requests_fail(self, client):
        """Test that requests without authentication fail appropriately."""
        await client.connect()
        # Don't authenticate

        with pytest.raises(ValueError, match="Must authenticate first"):
            await client.create_game()

    @pytest.mark.websocket
    async def test_message_round_trip(self, authenticated_client):
        """Test that messages can be serialized and parsed correctly."""
        # Test various message types
        messages = [
            SignInRequest(request_id=str(uuid.uuid4()), username="test", password="pass"),
            CreateGameRequest(
                request_id=str(uuid.uuid4()),
                token="test_token",
                map_name="standard",
                power_name="FRANCE",
            ),
            SetOrdersRequest(
                request_id=str(uuid.uuid4()),
                token="test_token",
                game_id="TEST_GAME",
                game_role="FRANCE",
                orders=["A PAR H"],
            ),
        ]

        for original_msg in messages:
            # Serialize to dict
            serialized = serialize_message(original_msg)

            # Parse back to object
            parsed_msg = parse_message(serialized)

            # Should be the same type and have same data
            assert type(parsed_msg) == type(original_msg)
            assert parsed_msg.name == original_msg.name
            assert parsed_msg.request_id == original_msg.request_id


class TestConcurrentOperations:
    """Test concurrent WebSocket operations."""

    @pytest.mark.websocket
    @pytest.mark.slow
    async def test_multiple_concurrent_clients(self, fake_server):
        """Test multiple clients connecting simultaneously."""
        clients = []

        try:
            # Create multiple clients
            for i in range(3):
                client = WebSocketDiplomacyClient("localhost", 8433, use_ssl=False)
                await client.connect()
                await client.authenticate("test_user", "test_password")
                clients.append(client)

            # All should be connected
            for client in clients:
                assert client.token is not None

            # Each can create games independently
            for i, client in enumerate(clients):
                game_data = await client.create_game(power_name="FRANCE" if i == 0 else None, n_controls=1)
                assert game_data["game_id"] is not None

        finally:
            # Cleanup
            for client in clients:
                try:
                    await client.close()
                except:
                    pass

    @pytest.mark.websocket
    async def test_rapid_message_sending(self, client_with_game):
        """Test sending multiple messages rapidly."""
        # Send multiple order updates rapidly
        for i in range(5):
            orders = [f"A PAR H  # Iteration {i}"]
            await client_with_game.set_orders("FRANCE", orders)

        # All should succeed without errors
