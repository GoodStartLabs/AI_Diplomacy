"""
Pytest configuration and fixtures for WebSocket testing.

This module provides shared fixtures and utilities for testing our
WebSocket client implementations against a fake server.
"""

# Add parent directory to path for ai_diplomacy imports (runtime only)
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from typing import AsyncGenerator, Dict, Generator
import pytest
import pytest_asyncio

# Add the bot_client directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from .test_fake_websocket_server import FakeServerManager, FakeWebSocketServer
from typed_websocket_client import TypedWebSocketDiplomacyClient


@pytest_asyncio.fixture(scope="function", autouse=True)
async def fake_server() -> AsyncGenerator[FakeWebSocketServer, None]:
    """
    Fixture that provides a running fake WebSocket server for testing.

    The server is automatically started before the test and stopped after.
    Uses port 8433 to avoid conflicts with real servers on 8432.
    """
    async with FakeServerManager("localhost", 8433) as server:
        yield server


@pytest.fixture
def credentials() -> Generator[Dict[str, str], None]:
    yield {"username": "test_user", "password": "test_password"}


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[TypedWebSocketDiplomacyClient, None]:
    """
    Fixture that provides a TypedWebSocketDiplomacyClient instance.

    The client is configured to connect to the fake server on port 8433.
    """
    client = TypedWebSocketDiplomacyClient("localhost", 8433, use_ssl=False)
    yield client

    # Cleanup: close the client connection
    try:
        await client.close()
    except:
        pass  # Ignore cleanup errors


@pytest.fixture
async def authenticated_client(fake_server, client):
    """
    Fixture that provides an authenticated TypedWebSocketDiplomacyClient.

    This client is already connected and authenticated, ready for testing
    game operations.
    """
    await client.connect()
    token = await client.authenticate("test_user", "test_password")
    assert token is not None
    assert client.token == token
    yield client


@pytest.fixture
async def client_with_game(authenticated_client):
    """
    Fixture that provides an authenticated client with a created game.

    The client is in a game as FRANCE, ready for order submission and
    game interaction testing.
    """
    game_data = await authenticated_client.create_game(
        power_name="FRANCE",
        n_controls=1,  # For testing
    )
    assert game_data is not None
    assert authenticated_client.game_id is not None
    yield authenticated_client


# Test utilities
class TestHelpers:
    """Helper methods for testing WebSocket interactions."""

    @staticmethod
    def assert_valid_token(token: str):
        """Assert that a token looks valid."""
        assert isinstance(token, str)
        assert len(token) > 10
        assert "fake_token_" in token

    @staticmethod
    def assert_valid_game_data(game_data: dict):
        """Assert that game data has expected structure."""
        assert isinstance(game_data, dict)
        assert "game_id" in game_data
        assert "phase" in game_data
        assert "powers" in game_data
        assert "map_name" in game_data

    @staticmethod
    def assert_valid_games_list(games: list):
        """Assert that games list has expected structure."""
        assert isinstance(games, list)
        for game in games:
            assert "game_id" in game
            assert "status" in game
            assert "phase" in game


@pytest.fixture
def helpers():
    """Fixture that provides test helper methods."""
    return TestHelpers
