"""
Integration tests for inter-power messaging functionality.

These tests verify that the enhanced WebSocket client can properly:
1. Send messages between powers
2. Retrieve and filter messages
3. Handle broadcast messaging
4. Track message patterns for strategic communication

The tests use the fake server infrastructure but test real message flow
without mocking the transport layer.
"""

import asyncio
import pytest
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock

from websocket_diplomacy_client import WebSocketDiplomacyClient, connect_to_diplomacy_server
from diplomacy.engine.message import Message, GLOBAL


class TestBasicMessaging:
    """Test core messaging functionality between powers."""

    @pytest.fixture
    async def two_clients(self, fake_server):
        """Fixture providing two authenticated clients in the same game."""
        # Create two clients
        client_france = WebSocketDiplomacyClient("localhost", 8433, use_ssl=False)
        client_germany = WebSocketDiplomacyClient("localhost", 8433, use_ssl=False)

        try:
            # Connect and authenticate both clients
            await client_france.connect_and_authenticate("test_user", "test_password")
            await client_germany.connect_and_authenticate("ai_player", "password")

            # Create a game with first client as FRANCE
            await client_france.create_game(
                map_name="standard",
                rules=["IGNORE_ERRORS", "POWER_CHOICE"],
                power_name="FRANCE",
                n_controls=2,  # Only need 2 powers for testing
            )

            # Second client joins as GERMANY
            await client_germany.join_game(game_id=client_france.game_id, power_name="GERMANY")

            # Synchronize both clients
            await client_france.synchronize()
            await client_germany.synchronize()

            yield {"france": client_france, "germany": client_germany}

        finally:
            # Cleanup
            try:
                await client_france.close()
                await client_germany.close()
            except:
                pass

    async def test_direct_message_sending(self, two_clients):
        """Test sending a direct message between two powers."""
        france_client = two_clients["france"]
        germany_client = two_clients["germany"]

        # Send message from FRANCE to GERMANY
        test_message = "Hello Germany, shall we form an alliance?"
        await france_client.send_message(sender="FRANCE", recipient="GERMANY", message=test_message)

        # Allow message to propagate
        await asyncio.sleep(0.1)

        # Synchronize both clients to get latest messages
        await france_client.synchronize()
        await germany_client.synchronize()

        # Check that Germany received the message
        germany_messages = await germany_client.get_recent_messages(limit=10)

        # Find our message
        sent_message = None
        for msg in germany_messages:
            if msg.sender == "FRANCE" and msg.recipient == "GERMANY":
                sent_message = msg
                break

        assert sent_message is not None, "Message was not received by Germany"
        assert sent_message.message == test_message
        assert sent_message.sender == "FRANCE"
        assert sent_message.recipient == "GERMANY"

    async def test_global_message_broadcasting(self, two_clients):
        """Test broadcasting a global message."""
        france_client = two_clients["france"]
        germany_client = two_clients["germany"]

        # Send global message from FRANCE
        test_message = "Greetings to all powers! Let's have a good game."
        await france_client.send_message(sender="FRANCE", recipient=GLOBAL, message=test_message)

        # Allow message to propagate
        await asyncio.sleep(0.1)

        # Synchronize both clients
        await france_client.synchronize()
        await germany_client.synchronize()

        # Check that both clients can see the global message
        france_messages = await france_client.get_recent_messages(limit=10)
        germany_messages = await germany_client.get_recent_messages(limit=10)

        # Find the global message in both clients
        def find_global_message(messages):
            for msg in messages:
                if msg.sender == "FRANCE" and msg.recipient == GLOBAL:
                    return msg
            return None

        france_msg = find_global_message(france_messages)
        germany_msg = find_global_message(germany_messages)

        assert france_msg is not None, "France should see its own global message"
        assert germany_msg is not None, "Germany should see France's global message"
        assert france_msg.message == test_message
        assert germany_msg.message == test_message

    async def test_broadcast_to_all_active_powers(self, two_clients):
        """Test the enhanced broadcast functionality."""
        france_client = two_clients["france"]
        germany_client = two_clients["germany"]

        # Send broadcast message to all active powers
        test_message = "This is a broadcast to all active powers."
        await france_client.send_broadcast_message(sender="FRANCE", message=test_message)

        # Allow messages to propagate
        await asyncio.sleep(0.1)

        # Synchronize clients
        await france_client.synchronize()
        await germany_client.synchronize()

        # Check that Germany received the direct message from broadcast
        germany_messages = await germany_client.get_recent_messages(limit=10)

        broadcast_message = None
        for msg in germany_messages:
            if msg.sender == "FRANCE" and msg.recipient == "GERMANY" and msg.message == test_message:
                broadcast_message = msg
                break

        assert broadcast_message is not None, "Germany should receive broadcast message"
        assert broadcast_message.message == test_message

    async def test_message_filtering_by_phase(self, two_clients):
        """Test message retrieval filtered by game phase."""
        france_client = two_clients["france"]

        # Get current phase
        current_phase = france_client.get_current_short_phase()

        # Send a message
        test_message = "Phase-specific message"
        await france_client.send_message(sender="FRANCE", recipient="GERMANY", message=test_message)

        # Allow message to propagate
        await asyncio.sleep(0.1)
        await france_client.synchronize()

        # Get messages for current phase
        phase_messages = await france_client.get_recent_messages(phase=current_phase, limit=10)

        # Find our message
        found_message = None
        for msg in phase_messages:
            if msg.message == test_message:
                found_message = msg
                break

        assert found_message is not None, "Message should be found in current phase"
        assert found_message.phase == current_phase


class TestMessageHistory:
    """Test message history and retrieval functionality."""

    @pytest.fixture
    async def client_with_messages(self, fake_server):
        """Fixture providing a client with some test messages."""
        client = WebSocketDiplomacyClient("localhost", 8433, use_ssl=False)

        try:
            await client.connect_and_authenticate("test_user", "test_password")
            await client.create_game(
                map_name="standard",
                rules=["IGNORE_ERRORS", "POWER_CHOICE"],
                power_name="FRANCE",
                n_controls=1,
            )
            await client.synchronize()

            # Send several test messages
            test_messages = [
                ("Hello world!", GLOBAL),
                ("Private message to England", "ENGLAND"),
                ("Another global message", GLOBAL),
                ("Direct to Germany", "GERMANY"),
            ]

            for message, recipient in test_messages:
                await client.send_message(sender="FRANCE", recipient=recipient, message=message)
                await asyncio.sleep(0.05)  # Small delay between messages

            await client.synchronize()
            yield client

        finally:
            try:
                await client.close()
            except:
                pass

    async def test_get_recent_messages_limit(self, client_with_messages):
        """Test that message limit parameter works correctly."""
        client = client_with_messages

        # Get recent messages with different limits
        messages_3 = await client.get_recent_messages(limit=3)
        messages_2 = await client.get_recent_messages(limit=2)
        messages_1 = await client.get_recent_messages(limit=1)

        assert len(messages_3) <= 3
        assert len(messages_2) <= 2
        assert len(messages_1) <= 1

        # Messages should be in reverse chronological order (most recent first)
        if len(messages_3) > 1:
            # Check that timestamps are in descending order
            for i in range(len(messages_3) - 1):
                msg1_time = messages_3[i].time_sent or 0
                msg2_time = messages_3[i + 1].time_sent or 0
                assert msg1_time >= msg2_time, "Messages should be in reverse chronological order"

    async def test_message_retrieval_by_sender(self, client_with_messages):
        """Test filtering messages by sender."""
        client = client_with_messages

        # Get all recent messages
        all_messages = await client.get_recent_messages(limit=20)

        # Filter messages from FRANCE
        france_messages = [msg for msg in all_messages if msg.sender == "FRANCE"]

        # We should have the 4 messages we sent as FRANCE
        assert len(france_messages) >= 4, f"Expected at least 4 FRANCE messages, got {len(france_messages)}"

        # All messages should be from FRANCE
        for msg in france_messages:
            assert msg.sender == "FRANCE"

    async def test_empty_message_history(self, fake_server):
        """Test behavior when no messages exist."""
        client = WebSocketDiplomacyClient("localhost", 8433, use_ssl=False)

        try:
            await client.connect_and_authenticate("ai_player", "password")
            await client.create_game(
                map_name="standard",
                rules=["IGNORE_ERRORS"],
                power_name="AUSTRIA",
                n_controls=1,
            )
            await client.synchronize()

            # Get messages when none exist
            messages = await client.get_recent_messages(limit=10)

            # Should return empty list, not None or error
            assert isinstance(messages, list)
            assert len(messages) == 0

        finally:
            try:
                await client.close()
            except:
                pass


class TestMessageErrorHandling:
    """Test error handling in messaging functionality."""

    @pytest.fixture
    async def client(self, fake_server):
        """Basic authenticated client for error testing."""
        client = WebSocketDiplomacyClient("localhost", 8433, use_ssl=False)

        try:
            await client.connect_and_authenticate("player1", "password")
            await client.create_game(
                map_name="standard",
                rules=["IGNORE_ERRORS"],
                power_name="ITALY",
                n_controls=1,
            )
            await client.synchronize()
            yield client

        finally:
            try:
                await client.close()
            except:
                pass

    async def test_send_message_to_invalid_recipient(self, client):
        """Test sending message to non-existent power."""
        # This should not raise an exception - the server/game should handle invalid recipients
        try:
            await client.send_message(sender="ITALY", recipient="INVALID_POWER", message="This should not crash")
            # If we get here, the call succeeded (which is fine)
        except Exception as e:
            # If an exception is raised, it should be a specific diplomacy exception, not a crash
            assert "INVALID_POWER" in str(e) or "recipient" in str(e).lower()

    async def test_send_empty_message(self, client):
        """Test sending empty message."""
        # Empty messages should be handled gracefully
        await client.send_message(sender="ITALY", recipient="FRANCE", message="")
        # If we get here without exception, the empty message was handled properly

    async def test_get_messages_before_game_setup(self, fake_server):
        """Test getting messages when no game is joined."""
        client = WebSocketDiplomacyClient("localhost", 8433, use_ssl=False)

        try:
            await client.connect_and_authenticate("test_user", "test_password")

            # Try to get messages without joining a game
            with pytest.raises(Exception):  # Should raise some form of exception
                await client.get_recent_messages()

        finally:
            try:
                await client.close()
            except:
                pass
