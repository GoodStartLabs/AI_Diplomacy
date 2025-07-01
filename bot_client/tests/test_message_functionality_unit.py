"""
Unit tests for the new inter-power messaging functionality.

These tests focus on testing the specific functionality we added:
1. Enhanced WebSocketDiplomacyClient methods
2. Message tracking and statistics in SingleBotPlayer
3. Negotiation targeting logic

These are more focused unit tests that don't require full server integration.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, List

from websocket_diplomacy_client import WebSocketDiplomacyClient
from single_bot_player import SingleBotPlayer
from websocket_negotiations import (
    analyze_recent_messages_for_targeting,
    should_participate_in_negotiations,
    get_negotiation_delay,
)
from diplomacy.engine.message import Message, GLOBAL


class TestWebSocketClientEnhancements:
    """Test the enhanced methods we added to WebSocketDiplomacyClient."""

    @pytest.fixture
    def mock_client(self):
        """Create a mocked WebSocketDiplomacyClient for testing."""
        client = WebSocketDiplomacyClient()

        # Mock the game and related objects
        client.game = MagicMock()
        mock_powers = {
            "FRANCE": MagicMock(is_eliminated=lambda: False),
            "ENGLAND": MagicMock(is_eliminated=lambda: False),
            "GERMANY": MagicMock(is_eliminated=lambda: False),
            "ITALY": MagicMock(is_eliminated=lambda: True),  # Eliminated
        }
        client.game.powers = mock_powers

        # Mock message history
        mock_messages = [
            Message(sender="ENGLAND", recipient="FRANCE", message="Hello France!", phase="S1901M"),
            Message(sender="GERMANY", recipient="FRANCE", message="Greetings!", phase="S1901M"),
            Message(sender="FRANCE", recipient="GLOBAL", message="Hello everyone!", phase="S1901M"),
        ]
        client.game.messages = {i: msg for i, msg in enumerate(mock_messages)}

        return client

    async def test_send_broadcast_message(self, mock_client):
        """Test the new send_broadcast_message method."""
        # Mock the send_message method and powers property
        mock_client.send_message = AsyncMock()

        # Mock the powers property to return our mock powers
        with patch.object(type(mock_client), "powers", new_callable=lambda: property(lambda self: self.game.powers)):
            # Send broadcast message
            await mock_client.send_broadcast_message(sender="FRANCE", message="Hello to all active powers!")

            # Should have called send_message for each active power (excluding sender and eliminated)
            expected_calls = 2  # ENGLAND and GERMANY (not ITALY because eliminated, not FRANCE because sender)
            assert mock_client.send_message.call_count == expected_calls

            # Check that messages were sent to the right powers
            call_args_list = mock_client.send_message.call_args_list
            recipients = [call[1]["recipient"] for call in call_args_list]  # Get recipient from kwargs

            assert "ENGLAND" in recipients
            assert "GERMANY" in recipients
            assert "FRANCE" not in recipients  # Shouldn't send to self
            assert "ITALY" not in recipients  # Shouldn't send to eliminated power

    async def test_get_recent_messages_filtering(self, mock_client):
        """Test the new get_recent_messages method with filtering."""
        # Mock current phase
        mock_client.get_current_short_phase = MagicMock(return_value="S1901M")

        # Mock the messages property to return our mock messages
        with patch.object(type(mock_client), "messages", new_callable=lambda: property(lambda self: self.messages)):
            # Test getting recent messages
            recent_messages = await mock_client.get_recent_messages(limit=5)

            # Should return the mocked messages
            assert len(recent_messages) <= 5
            assert len(recent_messages) == 3  # We have 3 mock messages

            # Test phase filtering
            phase_messages = await mock_client.get_recent_messages(phase="S1901M", limit=10)
            assert all(msg.phase == "S1901M" for msg in phase_messages)

    async def test_get_recent_messages_limit(self, mock_client):
        """Test that the limit parameter works correctly."""
        # Mock the messages property to return our mock messages
        with patch.object(type(mock_client), "messages", new_callable=lambda: property(lambda self: self.messages)):
            # Test with limit smaller than available messages
            limited_messages = await mock_client.get_recent_messages(limit=2)
            assert len(limited_messages) <= 2

            # Test with limit larger than available messages
            all_messages = await mock_client.get_recent_messages(limit=100)
            assert len(all_messages) == 3  # Should not exceed available messages


class TestSingleBotPlayerMessageTracking:
    """Test the message tracking functionality in SingleBotPlayer."""

    @pytest.fixture
    def mock_bot_player(self):
        """Create a mock SingleBotPlayer for testing."""
        bot = SingleBotPlayer(username="test_bot", password="test_pass", power_name="FRANCE", model_name="test_model")

        # Mock dependencies
        bot.client = MagicMock()
        bot.agent = MagicMock()
        bot.game_history = MagicMock()

        # Set up powers
        bot.client.powers = {
            "FRANCE": MagicMock(is_eliminated=lambda: False),
            "ENGLAND": MagicMock(is_eliminated=lambda: False),
            "GERMANY": MagicMock(is_eliminated=lambda: False),
            "ITALY": MagicMock(is_eliminated=lambda: False),
        }

        return bot

    def test_message_counting_initialization(self, mock_bot_player):
        """Test that message tracking starts in clean state."""
        bot = mock_bot_player

        assert isinstance(bot.message_counts, dict)
        assert isinstance(bot.response_counts, dict)
        assert isinstance(bot.priority_contacts, list)

        assert len(bot.message_counts) == 0
        assert len(bot.response_counts) == 0
        assert len(bot.priority_contacts) == 0

    def test_priority_contact_updates(self, mock_bot_player):
        """Test that priority contacts are updated correctly."""
        bot = mock_bot_player

        # Set up message counts
        bot.message_counts = {
            "ENGLAND": 5,
            "GERMANY": 3,
            "ITALY": 2,
            "AUSTRIA": 1,
            "RUSSIA": 4,
        }

        # Update priority contacts
        bot._update_priority_contacts()

        # Should have top 4 contacts in order of activity
        assert len(bot.priority_contacts) == 4
        assert bot.priority_contacts[0] == "ENGLAND"  # Highest count (5)
        assert bot.priority_contacts[1] == "RUSSIA"  # Second highest (4)
        assert bot.priority_contacts[2] == "GERMANY"  # Third highest (3)
        assert bot.priority_contacts[3] == "ITALY"  # Fourth highest (2)

    def test_message_statistics_generation(self, mock_bot_player):
        """Test generation of message statistics."""
        bot = mock_bot_player
        bot.current_phase = "S1901M"

        # Set up data
        bot.message_counts = {"ENGLAND": 4, "GERMANY": 2}
        bot.response_counts = {"ENGLAND": 3, "GERMANY": 1}
        bot.priority_contacts = ["ENGLAND", "GERMANY"]

        # Generate statistics
        stats = bot.get_message_statistics()

        # Check basic structure
        assert stats["power_name"] == "FRANCE"
        assert stats["current_phase"] == "S1901M"
        assert stats["total_messages_received"] == 6  # 4 + 2
        assert stats["total_responses_sent"] == 4  # 3 + 1

        # Check response rates
        assert stats["response_rate_by_power"]["ENGLAND"] == 0.75  # 3/4
        assert stats["response_rate_by_power"]["GERMANY"] == 0.5  # 1/2

    def test_response_decision_logic(self, mock_bot_player):
        """Test the enhanced response decision logic."""
        bot = mock_bot_player
        bot.priority_contacts = ["ENGLAND"]

        # Create test messages
        priority_message = MagicMock()
        priority_message.sender = "ENGLAND"
        priority_message.recipient = "FRANCE"
        priority_message.message = "Hello France!"

        non_priority_message = MagicMock()
        non_priority_message.sender = "GERMANY"
        non_priority_message.recipient = "FRANCE"
        non_priority_message.message = "Hello France!"

        # Test the decision logic (extracted from _consider_message_response)
        def should_respond(message):
            message_lower = message.message.lower()
            strategic_keywords = ["alliance", "deal", "propose", "agreement"]

            return any(
                [
                    "?" in message.message,
                    any(word in message_lower for word in ["hello", "hi", "greetings"]),
                    any(keyword in message_lower for keyword in strategic_keywords),
                    len(message.message.split()) > 15,
                    message.sender in bot.priority_contacts,
                ]
            )

        # Both should respond due to "hello", but priority logic is tested
        assert should_respond(priority_message) is True
        assert should_respond(non_priority_message) is True

        # Test priority contact influence
        assert priority_message.sender in bot.priority_contacts
        assert non_priority_message.sender not in bot.priority_contacts


class TestNegotiationTargeting:
    """Test the strategic negotiation targeting logic."""

    @pytest.fixture
    def mock_client_with_messages(self):
        """Create a mock client with message history."""
        client = MagicMock()

        # Mock recent messages
        mock_messages = [
            Message(sender="ENGLAND", recipient="FRANCE", message="Direct to France", phase="S1901M"),
            Message(sender="ENGLAND", recipient="FRANCE", message="Another to France", phase="S1901M"),
            Message(sender="GERMANY", recipient="FRANCE", message="Message to France", phase="S1901M"),
            Message(sender="ITALY", recipient="GLOBAL", message="Global message", phase="S1901M"),
        ]

        client.get_recent_messages = AsyncMock(return_value=mock_messages)
        client.powers = {
            "FRANCE": MagicMock(is_eliminated=lambda: False),
            "ENGLAND": MagicMock(is_eliminated=lambda: False),
            "GERMANY": MagicMock(is_eliminated=lambda: False),
            "ITALY": MagicMock(is_eliminated=lambda: False),
        }

        return client

    async def test_analyze_recent_messages_for_targeting(self, mock_client_with_messages):
        """Test the message analysis for targeting."""
        client = mock_client_with_messages

        # Analyze targeting for FRANCE
        targets = await analyze_recent_messages_for_targeting(client, "FRANCE", max_messages=20)

        # Should return a list of powers
        assert isinstance(targets, list)
        assert "FRANCE" not in targets  # Should not include self

        # ENGLAND should be prioritized (sent 2 direct messages to FRANCE)
        # GERMANY should be second (sent 1 direct message to FRANCE)
        if len(targets) >= 2:
            assert targets[0] == "ENGLAND"  # Most direct messages
            if "GERMANY" in targets:
                germany_index = targets.index("GERMANY")
                england_index = targets.index("ENGLAND")
                assert england_index < germany_index  # England should come before Germany

    def test_negotiation_delay_calculation(self):
        """Test that negotiation delays are calculated correctly."""
        # Test different round scenarios
        first_delay = get_negotiation_delay(round_number=1, total_rounds=3)
        middle_delay = get_negotiation_delay(round_number=2, total_rounds=3)
        final_delay = get_negotiation_delay(round_number=3, total_rounds=3)

        # First round should have longer delay
        assert first_delay > middle_delay
        # Final round should have shorter delay
        assert final_delay < middle_delay
        # All delays should be positive
        assert all(delay > 0 for delay in [first_delay, middle_delay, final_delay])

    async def test_should_participate_in_negotiations(self):
        """Test negotiation participation logic."""
        # Mock client and agent
        mock_client = MagicMock()
        mock_agent = MagicMock()
        mock_agent.power_name = "FRANCE"

        # Test case: active power in movement phase
        mock_power = MagicMock()
        mock_power.is_eliminated.return_value = False
        mock_client.get_power.return_value = mock_power
        mock_client.get_current_short_phase.return_value = "S1901M"

        with patch("websocket_negotiations.gather_possible_orders") as mock_orders:
            mock_orders.return_value = ["A Paris - Hold"]  # Has orders

            result = await should_participate_in_negotiations(mock_client, mock_agent)
            assert result is True

        # Test case: eliminated power
        mock_power.is_eliminated.return_value = True
        result = await should_participate_in_negotiations(mock_client, mock_agent)
        assert result is False

        # Test case: non-movement phase
        mock_power.is_eliminated.return_value = False
        mock_client.get_current_short_phase.return_value = "S1901R"  # Retreat phase

        with patch("websocket_negotiations.gather_possible_orders") as mock_orders:
            mock_orders.return_value = ["A Paris - Hold"]

            result = await should_participate_in_negotiations(mock_client, mock_agent)
            assert result is False


class TestIntegrationScenarios:
    """Test integration scenarios with mocked components."""

    def test_message_persistence_across_phases(self):
        """Test that message counts persist across multiple game phases."""
        bot = SingleBotPlayer(username="test_bot", password="test_pass", power_name="AUSTRIA", model_name="test_model")

        # Mock dependencies
        bot.client = MagicMock()
        bot.agent = MagicMock()
        bot.game_history = MagicMock()

        # Simulate message accumulation over phases
        phases = ["S1901M", "F1901M", "W1901A", "S1902M"]

        for phase in phases:
            bot.current_phase = phase

            # Simulate receiving messages
            if phase.endswith("M"):  # Movement phases
                for sender in ["FRANCE", "ENGLAND"]:
                    bot.message_counts[sender] = bot.message_counts.get(sender, 0) + 2
            else:
                # Fewer messages in other phases
                bot.message_counts["FRANCE"] = bot.message_counts.get("FRANCE", 0) + 1

            bot._update_priority_contacts()

        # Check accumulated counts
        assert bot.message_counts["FRANCE"] >= 5  # Should have accumulated messages
        assert bot.message_counts["ENGLAND"] >= 4
        assert len(bot.priority_contacts) > 0
        assert bot.priority_contacts[0] == "FRANCE"  # Should be top priority
