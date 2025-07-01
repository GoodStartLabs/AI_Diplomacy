"""
Integration tests for negotiation round functionality.

These tests verify that the negotiation system can properly:
1. Conduct strategic negotiation rounds with message targeting
2. Analyze recent messages for targeting decisions
3. Handle negotiation timing and coordination
4. Determine negotiation participation appropriately

Tests use mocked AI responses for predictable behavior while testing
the real negotiation coordination logic.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List

from websocket_diplomacy_client import WebSocketDiplomacyClient
from websocket_negotiations import (
    conduct_strategic_negotiation_round,
    analyze_recent_messages_for_targeting,
    should_participate_in_negotiations,
    get_negotiation_delay,
)
from ai_diplomacy.agent import DiplomacyAgent
from ai_diplomacy.game_history import GameHistory


class TestMessageTargeting:
    """Test strategic message targeting analysis."""

    @pytest.fixture
    async def client_with_messages(self, fake_server):
        """Client with pre-populated message history for targeting tests."""
        client = WebSocketDiplomacyClient("localhost", 8433, use_ssl=False)

        try:
            await client.connect_and_authenticate("targeting_user", "password")
            await client.create_game(
                map_name="standard",
                rules=["IGNORE_ERRORS", "POWER_CHOICE"],
                power_name="FRANCE",
                n_controls=7,  # Full game for realistic targeting
            )
            await client.synchronize()

            # Simulate message history with different activity levels
            # Note: In a real scenario, these would come from other players
            # For testing, we'll add them to the game's message history directly

            yield client

        finally:
            try:
                await client.close()
            except:
                pass

    async def test_analyze_recent_messages_empty_history(self, client_with_messages):
        """Test targeting analysis with no message history."""
        client = client_with_messages

        # Get targeting priority with empty message history
        targets = await analyze_recent_messages_for_targeting(client=client, power_name="FRANCE", max_messages=20)

        # Should return all active powers (excluding FRANCE itself)
        assert isinstance(targets, list)
        # Should not include FRANCE itself
        assert "FRANCE" not in targets
        # Should include other major powers
        expected_powers = {"ENGLAND", "GERMANY", "ITALY", "AUSTRIA", "RUSSIA", "TURKEY"}
        assert len(set(targets) & expected_powers) > 0

    async def test_analyze_recent_messages_with_activity(self, client_with_messages):
        """Test targeting analysis with simulated message activity."""
        client = client_with_messages

        # Simulate some message activity by sending messages
        # This tests the actual message retrieval and analysis logic

        # Send messages to create activity patterns
        await client.send_message("ENGLAND", "FRANCE", "Hello France!")
        await client.send_message("ENGLAND", "FRANCE", "Another message from England")
        await client.send_message("GERMANY", "FRANCE", "Message from Germany")
        await client.send_message("ITALY", "GLOBAL", "Global message from Italy")

        await asyncio.sleep(0.1)
        await client.synchronize()

        # Now analyze targeting
        targets = await analyze_recent_messages_for_targeting(client=client, power_name="FRANCE", max_messages=20)

        # ENGLAND should be prioritized (sent 2 direct messages to FRANCE)
        # GERMANY should be second (sent 1 direct message to FRANCE)
        # Others should follow
        assert isinstance(targets, list)
        assert "FRANCE" not in targets

        # England should be first in priority (most direct messages to FRANCE)
        if "ENGLAND" in targets:
            england_index = targets.index("ENGLAND")
            if "GERMANY" in targets:
                germany_index = targets.index("GERMANY")
                assert england_index < germany_index, "England should be prioritized over Germany"

    async def test_analyze_messages_error_handling(self, client_with_messages):
        """Test error handling in message analysis."""
        client = client_with_messages

        # Test with invalid power name
        targets = await analyze_recent_messages_for_targeting(client=client, power_name="INVALID_POWER", max_messages=20)

        # Should still return a valid list (fallback behavior)
        assert isinstance(targets, list)


class TestNegotiationTiming:
    """Test negotiation delay and timing logic."""

    def test_negotiation_delay_calculation(self):
        """Test that negotiation delays are calculated correctly."""

        # Test first round gets extra time
        first_round_delay = get_negotiation_delay(round_number=1, total_rounds=3)
        base_delay = get_negotiation_delay(round_number=2, total_rounds=3)
        final_round_delay = get_negotiation_delay(round_number=3, total_rounds=3)

        assert first_round_delay > base_delay, "First round should have longer delay"
        assert final_round_delay < base_delay, "Final round should have shorter delay"

        # All delays should be positive
        assert first_round_delay > 0
        assert base_delay > 0
        assert final_round_delay > 0

    def test_negotiation_delay_edge_cases(self):
        """Test delay calculation with edge cases."""

        # Single round
        single_delay = get_negotiation_delay(round_number=1, total_rounds=1)
        assert single_delay > 0

        # Many rounds
        many_rounds_delay = get_negotiation_delay(round_number=5, total_rounds=10)
        assert many_rounds_delay > 0


class TestNegotiationParticipation:
    """Test logic for determining negotiation participation."""

    @pytest.fixture
    async def client_and_mocked_agent(self, fake_server):
        """Client with mocked agent for participation testing."""
        client = WebSocketDiplomacyClient("localhost", 8433, use_ssl=False)

        try:
            await client.connect_and_authenticate("participation_user", "password")
            await client.create_game(
                map_name="standard",
                rules=["IGNORE_ERRORS"],
                power_name="RUSSIA",
                n_controls=1,
            )
            await client.synchronize()

            # Create mock agent
            mock_agent = MagicMock(spec=DiplomacyAgent)
            mock_agent.power_name = "RUSSIA"

            yield {"client": client, "agent": mock_agent}

        finally:
            try:
                await client.close()
            except:
                pass

    async def test_should_participate_eliminated_power(self, client_and_mocked_agent):
        """Test that eliminated powers don't participate in negotiations."""
        client = client_and_mocked_agent["client"]
        agent = client_and_mocked_agent["agent"]

        # Mock the power as eliminated
        with patch.object(client, "get_power") as mock_get_power:
            mock_power = MagicMock()
            mock_power.is_eliminated.return_value = True
            mock_get_power.return_value = mock_power

            should_participate = await should_participate_in_negotiations(client, agent)
            assert should_participate is False

    async def test_should_participate_no_orders(self, client_and_mocked_agent):
        """Test that powers with no orderable locations don't negotiate."""
        client = client_and_mocked_agent["client"]
        agent = client_and_mocked_agent["agent"]

        # Mock the power as not eliminated but with no orderable locations
        with patch.object(client, "get_power") as mock_get_power, patch("websocket_negotiations.gather_possible_orders") as mock_orders:
            mock_power = MagicMock()
            mock_power.is_eliminated.return_value = False
            mock_get_power.return_value = mock_power
            mock_orders.return_value = []  # No possible orders

            should_participate = await should_participate_in_negotiations(client, agent)
            assert should_participate is False

    async def test_should_participate_non_movement_phase(self, client_and_mocked_agent):
        """Test that powers don't negotiate in non-movement phases."""
        client = client_and_mocked_agent["client"]
        agent = client_and_mocked_agent["agent"]

        # Mock retreat phase
        with (
            patch.object(client, "get_power") as mock_get_power,
            patch.object(client, "get_current_short_phase") as mock_phase,
            patch("websocket_negotiations.gather_possible_orders") as mock_orders,
        ):
            mock_power = MagicMock()
            mock_power.is_eliminated.return_value = False
            mock_get_power.return_value = mock_power
            mock_orders.return_value = ["A Moscow - Hold"]  # Has orders
            mock_phase.return_value = "S1901R"  # Retreat phase

            should_participate = await should_participate_in_negotiations(client, agent)
            assert should_participate is False

    async def test_should_participate_movement_phase_with_orders(self, client_and_mocked_agent):
        """Test that active powers with orders participate in movement phases."""
        client = client_and_mocked_agent["client"]
        agent = client_and_mocked_agent["agent"]

        # Mock movement phase with orderable locations
        with (
            patch.object(client, "get_power") as mock_get_power,
            patch.object(client, "get_current_short_phase") as mock_phase,
            patch("websocket_negotiations.gather_possible_orders") as mock_orders,
        ):
            mock_power = MagicMock()
            mock_power.is_eliminated.return_value = False
            mock_get_power.return_value = mock_power
            mock_orders.return_value = ["A Moscow - Hold", "F Sevastopol - Black Sea"]
            mock_phase.return_value = "S1901M"  # Movement phase

            should_participate = await should_participate_in_negotiations(client, agent)
            assert should_participate is True


class TestStrategicNegotiationRound:
    """Test the complete strategic negotiation round functionality."""

    @pytest.fixture
    async def negotiation_setup(self, fake_server):
        """Setup for testing complete negotiation rounds."""
        client = WebSocketDiplomacyClient("localhost", 8433, use_ssl=False)

        try:
            await client.connect_and_authenticate("negotiation_user", "password")
            await client.create_game(
                map_name="standard",
                rules=["IGNORE_ERRORS", "POWER_CHOICE"],
                power_name="TURKEY",
                n_controls=1,
            )
            await client.synchronize()

            # Create mock agent with necessary attributes
            mock_agent = MagicMock(spec=DiplomacyAgent)
            mock_agent.power_name = "TURKEY"
            mock_agent.goals = "Expand into the Mediterranean"
            mock_agent.relationships = {}
            mock_agent.format_private_diary_for_prompt.return_value = "Test diary entry"

            # Mock AI client for message generation
            mock_ai_client = AsyncMock()
            mock_agent.client = mock_ai_client

            # Create game history
            game_history = GameHistory()

            # Mock error stats
            error_stats = {"test_model": {"conversation_errors": 0, "order_decoding_errors": 0}}

            yield {"client": client, "agent": mock_agent, "game_history": game_history, "error_stats": error_stats}

        finally:
            try:
                await client.close()
            except:
                pass

    async def test_successful_negotiation_round(self, negotiation_setup):
        """Test a successful negotiation round with message generation."""
        setup = negotiation_setup
        client = setup["client"]
        agent = setup["agent"]
        game_history = setup["game_history"]
        error_stats = setup["error_stats"]

        # Mock AI response for message generation
        mock_messages = [
            {"content": "Greetings! Turkey seeks peaceful relations.", "message_type": "global"},
            {"content": "Russia, shall we coordinate our efforts?", "message_type": "private", "recipient": "RUSSIA"},
        ]
        agent.client.get_conversation_reply.return_value = mock_messages

        # Mock power and orders
        with (
            patch.object(client, "get_power") as mock_get_power,
            patch("websocket_negotiations.gather_possible_orders") as mock_orders,
            patch.object(client, "send_message") as mock_send,
        ):
            mock_power = MagicMock()
            mock_power.is_eliminated.return_value = False
            mock_get_power.return_value = mock_power
            mock_orders.return_value = ["A Constantinople - Hold"]

            # Run negotiation round
            success = await conduct_strategic_negotiation_round(
                client=client,
                agent=agent,
                game_history=game_history,
                model_error_stats=error_stats,
                log_file_path="/tmp/test_log.txt",
                round_number=1,
                max_rounds=3,
            )

            assert success is True
            # Should have called send_message for each generated message
            assert mock_send.call_count == len(mock_messages)

    async def test_negotiation_round_no_messages(self, negotiation_setup):
        """Test negotiation round when AI generates no messages."""
        setup = negotiation_setup
        client = setup["client"]
        agent = setup["agent"]
        game_history = setup["game_history"]
        error_stats = setup["error_stats"]

        # Mock AI response with no messages
        agent.client.get_conversation_reply.return_value = []

        # Mock power and orders
        with patch.object(client, "get_power") as mock_get_power, patch("websocket_negotiations.gather_possible_orders") as mock_orders:
            mock_power = MagicMock()
            mock_power.is_eliminated.return_value = False
            mock_get_power.return_value = mock_power
            mock_orders.return_value = ["A Constantinople - Hold"]

            # Run negotiation round
            success = await conduct_strategic_negotiation_round(
                client=client,
                agent=agent,
                game_history=game_history,
                model_error_stats=error_stats,
                log_file_path="/tmp/test_log.txt",
                round_number=1,
                max_rounds=3,
            )

            assert success is False

    async def test_negotiation_round_ai_error(self, negotiation_setup):
        """Test negotiation round when AI client raises an exception."""
        setup = negotiation_setup
        client = setup["client"]
        agent = setup["agent"]
        game_history = setup["game_history"]
        error_stats = setup["error_stats"]

        # Mock AI client to raise exception
        agent.client.get_conversation_reply.side_effect = Exception("AI service unavailable")
        agent.client.model_name = "test_model"

        # Mock power and orders
        with patch.object(client, "get_power") as mock_get_power, patch("websocket_negotiations.gather_possible_orders") as mock_orders:
            mock_power = MagicMock()
            mock_power.is_eliminated.return_value = False
            mock_get_power.return_value = mock_power
            mock_orders.return_value = ["A Constantinople - Hold"]

            # Run negotiation round
            success = await conduct_strategic_negotiation_round(
                client=client,
                agent=agent,
                game_history=game_history,
                model_error_stats=error_stats,
                log_file_path="/tmp/test_log.txt",
                round_number=1,
                max_rounds=3,
            )

            assert success is False
            # Error should be tracked in statistics
            assert error_stats["test_model"]["conversation_errors"] == 1

    async def test_negotiation_round_with_targeting(self, negotiation_setup):
        """Test that negotiation round uses strategic targeting."""
        setup = negotiation_setup
        client = setup["client"]
        agent = setup["agent"]
        game_history = setup["game_history"]
        error_stats = setup["error_stats"]

        # Mock message targeting analysis
        with patch("websocket_negotiations.analyze_recent_messages_for_targeting") as mock_targeting:
            mock_targeting.return_value = ["RUSSIA", "AUSTRIA", "ITALY"]

            # Mock AI response
            mock_messages = [{"content": "Test message", "message_type": "global"}]
            agent.client.get_conversation_reply.return_value = mock_messages

            # Mock power and orders
            with patch.object(client, "get_power") as mock_get_power, patch("websocket_negotiations.gather_possible_orders") as mock_orders:
                mock_power = MagicMock()
                mock_power.is_eliminated.return_value = False
                mock_get_power.return_value = mock_power
                mock_orders.return_value = ["A Constantinople - Hold"]

                # Run negotiation round 2 (should use targeting)
                await conduct_strategic_negotiation_round(
                    client=client,
                    agent=agent,
                    game_history=game_history,
                    model_error_stats=error_stats,
                    log_file_path="/tmp/test_log.txt",
                    round_number=2,  # Round > 1 should use targeting
                    max_rounds=3,
                )

                # Should have called the targeting analysis
                mock_targeting.assert_called_once_with(client, "TURKEY")
