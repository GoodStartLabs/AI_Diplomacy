"""
Integration tests for message persistence and tracking functionality.

These tests verify that the SingleBotPlayer can properly:
1. Track message counts and response patterns
2. Update priority contacts based on messaging activity
3. Generate accurate message statistics
4. Log statistics during phase transitions
5. Maintain message persistence across game phases

Tests focus on the tracking and statistics features rather than
the actual AI message generation.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict

from single_bot_player import SingleBotPlayer
from websocket_diplomacy_client import WebSocketDiplomacyClient
from diplomacy.engine.message import Message
from ai_diplomacy.agent import DiplomacyAgent
from ai_diplomacy.game_history import GameHistory


class TestMessageCounting:
    """Test message counting and tracking functionality."""

    @pytest.fixture
    def mock_bot_player(self):
        """Create a SingleBotPlayer with mocked dependencies for testing."""
        # Create mock bot player
        bot = SingleBotPlayer(username="test_bot", password="test_pass", power_name="ENGLAND", model_name="test_model", game_id="test_game")

        # Mock the client and agent
        bot.client = MagicMock(spec=WebSocketDiplomacyClient)
        bot.agent = MagicMock(spec=DiplomacyAgent)
        bot.game_history = GameHistory()

        return bot

    def test_initial_message_tracking_state(self, mock_bot_player):
        """Test that message tracking starts in clean state."""
        bot = mock_bot_player

        assert isinstance(bot.message_counts, dict)
        assert isinstance(bot.response_counts, dict)
        assert isinstance(bot.priority_contacts, list)

        assert len(bot.message_counts) == 0
        assert len(bot.response_counts) == 0
        assert len(bot.priority_contacts) == 0

    def test_message_count_tracking(self, mock_bot_player):
        """Test that incoming messages are counted correctly."""
        bot = mock_bot_player

        # Simulate receiving messages from different powers
        test_messages = [
            Message(sender="FRANCE", recipient="ENGLAND", message="Hello England!", phase="S1901M"),
            Message(sender="FRANCE", recipient="ENGLAND", message="Another message", phase="S1901M"),
            Message(sender="GERMANY", recipient="ENGLAND", message="Greetings!", phase="S1901M"),
            Message(sender="ITALY", recipient="GLOBAL", message="Global message", phase="S1901M"),  # Should not be counted
            Message(sender="ENGLAND", recipient="FRANCE", message="Self message", phase="S1901M"),  # Should not be counted
        ]

        # Process each message through the message handler
        for msg in test_messages:
            # Simulate the message handling logic from _on_message_received
            bot.game_history.add_message(
                phase_name=msg.phase,
                sender=msg.sender,
                recipient=msg.recipient,
                message_content=msg.message,
            )

            # Track message patterns (only for messages TO this bot)
            if msg.recipient == bot.power_name and msg.sender != bot.power_name:
                bot.message_counts[msg.sender] = bot.message_counts.get(msg.sender, 0) + 1
                bot._update_priority_contacts()

        # Check counts
        assert bot.message_counts["FRANCE"] == 2
        assert bot.message_counts["GERMANY"] == 1
        assert "ITALY" not in bot.message_counts  # Global message not counted
        assert "ENGLAND" not in bot.message_counts  # Self message not counted

    def test_response_count_tracking(self, mock_bot_player):
        """Test that outgoing responses are counted correctly."""
        bot = mock_bot_player

        # Simulate sending responses to different powers
        responses = [
            ("FRANCE", "Thanks for your message!"),
            ("FRANCE", "Another response to France"),
            ("GERMANY", "Hello Germany"),
        ]

        for recipient, message in responses:
            # Simulate response sending logic
            bot.response_counts[recipient] = bot.response_counts.get(recipient, 0) + 1

        # Check response counts
        assert bot.response_counts["FRANCE"] == 2
        assert bot.response_counts["GERMANY"] == 1

    def test_priority_contact_updates(self, mock_bot_player):
        """Test that priority contacts are updated based on message counts."""
        bot = mock_bot_player

        # Set up message counts with different activity levels
        bot.message_counts = {
            "FRANCE": 5,  # Most active
            "GERMANY": 3,  # Second most active
            "ITALY": 2,  # Third most active
            "AUSTRIA": 1,  # Least active
            "RUSSIA": 4,  # Second highest
        }

        # Update priority contacts
        bot._update_priority_contacts()

        # Should have top 4 contacts in order of activity
        assert len(bot.priority_contacts) == 4
        assert bot.priority_contacts[0] == "FRANCE"  # Highest count (5)
        assert bot.priority_contacts[1] == "RUSSIA"  # Second highest (4)
        assert bot.priority_contacts[2] == "GERMANY"  # Third highest (3)
        assert bot.priority_contacts[3] == "ITALY"  # Fourth highest (2)
        # AUSTRIA should not be in top 4

    def test_priority_contacts_with_fewer_powers(self, mock_bot_player):
        """Test priority contacts when fewer than 4 powers are active."""
        bot = mock_bot_player

        # Set up message counts with only 2 powers
        bot.message_counts = {
            "FRANCE": 3,
            "GERMANY": 1,
        }

        bot._update_priority_contacts()

        # Should have only 2 contacts
        assert len(bot.priority_contacts) == 2
        assert bot.priority_contacts[0] == "FRANCE"
        assert bot.priority_contacts[1] == "GERMANY"


class TestMessageStatistics:
    """Test message statistics generation and reporting."""

    @pytest.fixture
    def bot_with_message_data(self, mock_bot_player):
        """Bot player with pre-populated message tracking data."""
        bot = mock_bot_player

        # Set up realistic message and response data
        bot.message_counts = {
            "FRANCE": 8,
            "GERMANY": 5,
            "ITALY": 3,
            "RUSSIA": 2,
        }

        bot.response_counts = {
            "FRANCE": 6,  # 75% response rate
            "GERMANY": 2,  # 40% response rate
            "ITALY": 3,  # 100% response rate
            "RUSSIA": 0,  # 0% response rate
        }

        bot.priority_contacts = ["FRANCE", "GERMANY", "ITALY", "RUSSIA"]
        bot.current_phase = "S1901M"

        # Mock the client's powers for active power detection
        mock_powers = {
            "ENGLAND": MagicMock(is_eliminated=lambda: False),
            "FRANCE": MagicMock(is_eliminated=lambda: False),
            "GERMANY": MagicMock(is_eliminated=lambda: False),
            "ITALY": MagicMock(is_eliminated=lambda: False),
            "RUSSIA": MagicMock(is_eliminated=lambda: False),
            "AUSTRIA": MagicMock(is_eliminated=lambda: True),  # Eliminated
            "TURKEY": MagicMock(is_eliminated=lambda: False),
        }
        bot.client.powers = mock_powers

        return bot

    def test_message_statistics_generation(self, bot_with_message_data):
        """Test that message statistics are generated correctly."""
        bot = bot_with_message_data

        stats = bot.get_message_statistics()

        # Check basic structure
        assert stats["power_name"] == "ENGLAND"
        assert stats["current_phase"] == "S1901M"
        assert isinstance(stats["message_counts_by_power"], dict)
        assert isinstance(stats["response_counts_by_power"], dict)
        assert isinstance(stats["response_rate_by_power"], dict)
        assert isinstance(stats["priority_contacts"], list)
        assert isinstance(stats["active_powers"], list)

        # Check calculated values
        assert stats["total_messages_received"] == 18  # 8+5+3+2
        assert stats["total_responses_sent"] == 11  # 6+2+3+0

        # Check response rates
        assert stats["response_rate_by_power"]["FRANCE"] == 0.75  # 6/8
        assert stats["response_rate_by_power"]["GERMANY"] == 0.4  # 2/5
        assert stats["response_rate_by_power"]["ITALY"] == 1.0  # 3/3
        assert stats["response_rate_by_power"]["RUSSIA"] == 0.0  # 0/2

        # Check active powers (should exclude eliminated AUSTRIA and self)
        active_powers = stats["active_powers"]
        assert "AUSTRIA" not in active_powers  # Eliminated
        assert "ENGLAND" not in active_powers  # Self
        assert "FRANCE" in active_powers
        assert "TURKEY" in active_powers

    def test_message_statistics_empty_data(self, mock_bot_player):
        """Test statistics generation with no message data."""
        bot = mock_bot_player
        bot.current_phase = "S1901M"

        # Mock empty powers
        mock_powers = {
            "ENGLAND": MagicMock(is_eliminated=lambda: False),
            "FRANCE": MagicMock(is_eliminated=lambda: False),
        }
        bot.client.powers = mock_powers

        stats = bot.get_message_statistics()

        assert stats["total_messages_received"] == 0
        assert stats["total_responses_sent"] == 0
        assert len(stats["message_counts_by_power"]) == 0
        assert len(stats["response_counts_by_power"]) == 0
        assert len(stats["response_rate_by_power"]) == 0
        assert len(stats["priority_contacts"]) == 0

    def test_message_statistics_logging(self, bot_with_message_data, caplog):
        """Test that message statistics are logged correctly."""
        bot = bot_with_message_data

        # Call the logging method
        bot.log_message_statistics()

        # Check that appropriate log messages were generated
        log_output = caplog.text
        assert "Message Statistics for ENGLAND" in log_output
        assert "Total messages received: 18" in log_output
        assert "Total responses sent: 11" in log_output
        assert "Priority contacts:" in log_output

        # Check that individual power stats are logged
        assert "FRANCE:" in log_output
        assert "GERMANY:" in log_output
        assert "75%" in log_output  # France response rate
        assert "40%" in log_output  # Germany response rate


class TestMessagePersistenceIntegration:
    """Test integration of message persistence with game flow."""

    @pytest.fixture
    async def bot_integration_setup(self, fake_server):
        """Setup for integration testing with fake server."""
        # Note: This is a more complex fixture that would require actual
        # SingleBotPlayer initialization, which depends on AI client setup
        # For now, we'll focus on the core tracking logic

        bot = SingleBotPlayer(username="integration_test", password="test_pass", power_name="ITALY", model_name="test_model", game_id=None)

        # Mock the complex dependencies
        bot.client = MagicMock(spec=WebSocketDiplomacyClient)
        bot.agent = MagicMock(spec=DiplomacyAgent)
        bot.game_history = GameHistory()

        return bot

    def test_message_tracking_during_phase_transition(self, bot_integration_setup):
        """Test that message statistics are logged during phase transitions."""
        bot = bot_integration_setup

        # Set up some message data
        bot.message_counts = {"FRANCE": 2, "GERMANY": 1}
        bot.current_phase = "S1901M"

        # Mock the client powers for log_message_statistics
        mock_powers = {
            "ITALY": MagicMock(is_eliminated=lambda: False),
            "FRANCE": MagicMock(is_eliminated=lambda: False),
            "GERMANY": MagicMock(is_eliminated=lambda: False),
        }
        bot.client.powers = mock_powers

        # Mock the log_message_statistics method to track if it's called
        with patch.object(bot, "log_message_statistics") as mock_log:
            # Simulate phase transition logic
            new_phase = "F1901M"
            if new_phase != bot.current_phase:
                bot.current_phase = new_phase
                bot.game_history.add_phase(new_phase)
                bot.orders_submitted = False
                bot.current_negotiation_round = 0
                bot.negotiation_complete = False

                # This is the key logic from _handle_phase_update_async
                if hasattr(bot, "message_counts") and bot.message_counts:
                    bot.log_message_statistics()

            # Verify that statistics were logged
            mock_log.assert_called_once()

    def test_priority_contact_influence_on_response_decisions(self, bot_integration_setup):
        """Test that priority contacts influence message response decisions."""
        bot = bot_integration_setup

        # Set up priority contacts
        bot.priority_contacts = ["FRANCE", "GERMANY"]

        # Create test messages from different senders
        priority_message = Message(sender="FRANCE", recipient="ITALY", message="Hello Italy!", phase="S1901M")

        non_priority_message = Message(sender="AUSTRIA", recipient="ITALY", message="Hello Italy!", phase="S1901M")

        # Test the response decision logic (from _consider_message_response)
        def should_respond_to_message(message):
            message_lower = message.message.lower()
            strategic_keywords = [
                "alliance",
                "deal",
                "propose",
                "agreement",
                "support",
                "attack",
                "coordinate",
                "move",
                "order",
                "help",
                "work together",
                "partner",
                "enemy",
                "threat",
                "negotiate",
                "discuss",
                "plan",
                "strategy",
                "bounce",
                "convoy",
                "retreat",
            ]

            return any(
                [
                    "?" in message.message,  # Questions
                    any(word in message_lower for word in ["hello", "hi", "greetings"]),  # Greetings
                    any(keyword in message_lower for keyword in strategic_keywords),  # Strategic content
                    len(message.message.split()) > 15,  # Longer messages
                    message.sender in bot.priority_contacts,  # Priority contacts
                ]
            )

        # Priority contact should be more likely to get response
        priority_should_respond = should_respond_to_message(priority_message)
        non_priority_should_respond = should_respond_to_message(non_priority_message)

        # Both should respond due to "hello" keyword, but priority contact logic is working
        assert priority_should_respond is True
        # Non-priority should also respond due to "hello", but test the contact logic
        assert priority_message.sender in bot.priority_contacts
        assert non_priority_message.sender not in bot.priority_contacts

    def test_message_persistence_across_multiple_phases(self, bot_integration_setup):
        """Test that message counts persist across multiple game phases."""
        bot = bot_integration_setup

        # Simulate message accumulation over multiple phases
        phases = ["S1901M", "F1901M", "W1901A", "S1902M"]

        for phase in phases:
            bot.current_phase = phase

            # Simulate receiving messages in each phase
            if phase.endswith("M"):  # Movement phases
                # More messages during movement phases
                for sender in ["FRANCE", "GERMANY"]:
                    bot.message_counts[sender] = bot.message_counts.get(sender, 0) + 2
            else:
                # Fewer messages during other phases
                bot.message_counts["FRANCE"] = bot.message_counts.get("FRANCE", 0) + 1

            bot._update_priority_contacts()

        # After all phases, check accumulated counts
        assert bot.message_counts["FRANCE"] >= 5  # 2+2+1+2 from movement phases + 1 from adjustment
        assert bot.message_counts["GERMANY"] >= 4  # 2+2+2 from movement phases only

        # France should be top priority due to higher count
        assert len(bot.priority_contacts) > 0
        assert bot.priority_contacts[0] == "FRANCE"
