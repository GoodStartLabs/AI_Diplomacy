"""
Integration tests for multi-bot messaging scenarios.

These tests verify realistic inter-power communication scenarios with
multiple bots interacting simultaneously. Tests focus on:
1. Multi-bot conversation flows
2. Negotiation coordination between multiple powers
3. Message response patterns in realistic scenarios
4. Phase transition coordination across multiple bots

Tests use the fake server but simulate realistic multi-power interactions
without mocking the core message transport logic.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List

from websocket_diplomacy_client import WebSocketDiplomacyClient
from single_bot_player import SingleBotPlayer
from ai_diplomacy.agent import DiplomacyAgent
from ai_diplomacy.game_history import GameHistory


class TestTwoBotConversation:
    """Test conversation flow between two bots."""

    @pytest.fixture
    async def two_bot_setup(self, fake_server):
        """Setup two bots in the same game for conversation testing."""
        # Create two WebSocket clients
        client_france = WebSocketDiplomacyClient("localhost", 8433, use_ssl=False)
        client_england = WebSocketDiplomacyClient("localhost", 8433, use_ssl=False)

        try:
            # Connect both clients
            await client_france.connect_and_authenticate("france_bot", "password")
            await client_england.connect_and_authenticate("england_bot", "password")

            # Create game with France
            await client_france.create_game(
                map_name="standard",
                rules=["IGNORE_ERRORS", "POWER_CHOICE"],
                power_name="FRANCE",
                n_controls=2,
            )

            # England joins the game
            await client_england.join_game(game_id=client_france.game_id, power_name="ENGLAND")

            # Synchronize both clients
            await client_france.synchronize()
            await client_england.synchronize()

            yield {"france_client": client_france, "england_client": client_england, "game_id": client_france.game_id}

        finally:
            try:
                await client_france.close()
                await client_england.close()
            except:
                pass

    async def test_basic_two_bot_exchange(self, two_bot_setup):
        """Test basic message exchange between two bots."""
        france_client = two_bot_setup["france_client"]
        england_client = two_bot_setup["england_client"]

        # France initiates conversation
        await france_client.send_message(sender="FRANCE", recipient="ENGLAND", message="Hello England! Shall we discuss our border?")

        await asyncio.sleep(0.1)
        await england_client.synchronize()

        # Check England received the message
        england_messages = await england_client.get_recent_messages(limit=5)
        france_message = None
        for msg in england_messages:
            if msg.sender == "FRANCE" and msg.recipient == "ENGLAND":
                france_message = msg
                break

        assert france_message is not None
        assert "border" in france_message.message

        # England responds
        await england_client.send_message(sender="ENGLAND", recipient="FRANCE", message="Indeed, France. I propose we coordinate our fleets.")

        await asyncio.sleep(0.1)
        await france_client.synchronize()

        # Check France received the response
        france_messages = await france_client.get_recent_messages(limit=5)
        england_response = None
        for msg in france_messages:
            if msg.sender == "ENGLAND" and msg.recipient == "FRANCE":
                england_response = msg
                break

        assert england_response is not None
        assert "coordinate" in england_response.message

    async def test_conversation_thread_tracking(self, two_bot_setup):
        """Test that conversation threads can be tracked across multiple exchanges."""
        france_client = two_bot_setup["france_client"]
        england_client = two_bot_setup["england_client"]

        # Simulate a conversation thread
        conversation = [
            ("FRANCE", "ENGLAND", "England, are you interested in an alliance?"),
            ("ENGLAND", "FRANCE", "Yes France, what do you propose?"),
            ("FRANCE", "ENGLAND", "Let's coordinate attacks on Germany."),
            ("ENGLAND", "FRANCE", "Agreed. I'll move my fleet to support you."),
        ]

        for sender, recipient, message in conversation:
            if sender == "FRANCE":
                await france_client.send_message(sender, recipient, message)
            else:
                await england_client.send_message(sender, recipient, message)

            await asyncio.sleep(0.05)  # Small delay between messages

        # Synchronize both clients
        await france_client.synchronize()
        await england_client.synchronize()

        # Get conversation history from both perspectives
        france_messages = await france_client.get_recent_messages(limit=10)
        england_messages = await england_client.get_recent_messages(limit=10)

        # Filter for conversation between France and England
        def filter_conversation(messages):
            return [msg for msg in messages if (msg.sender in ["FRANCE", "ENGLAND"] and msg.recipient in ["FRANCE", "ENGLAND"])]

        france_conv = filter_conversation(france_messages)
        england_conv = filter_conversation(england_messages)

        # Both should see the same conversation
        assert len(france_conv) >= 4
        assert len(england_conv) >= 4

        # Check that key terms from the conversation appear
        all_messages_text = " ".join([msg.message for msg in france_conv])
        assert "alliance" in all_messages_text
        assert "Germany" in all_messages_text
        assert "support" in all_messages_text


class TestThreeBotNegotiation:
    """Test more complex negotiations with three bots."""

    @pytest.fixture
    async def three_bot_setup(self, fake_server):
        """Setup three bots for complex negotiation testing."""
        clients = {}
        powers = ["FRANCE", "ENGLAND", "GERMANY"]

        try:
            # Create and connect three clients
            for power in powers:
                client = WebSocketDiplomacyClient("localhost", 8433, use_ssl=False)
                await client.connect_and_authenticate(f"{power.lower()}_bot", "password")
                clients[power] = client

            # Create game with France
            await clients["FRANCE"].create_game(
                map_name="standard",
                rules=["IGNORE_ERRORS", "POWER_CHOICE"],
                power_name="FRANCE",
                n_controls=3,
            )

            game_id = clients["FRANCE"].game_id

            # Other powers join
            await clients["ENGLAND"].join_game(game_id=game_id, power_name="ENGLAND")
            await clients["GERMANY"].join_game(game_id=game_id, power_name="GERMANY")

            # Synchronize all clients
            for client in clients.values():
                await client.synchronize()

            yield {"clients": clients, "game_id": game_id}

        finally:
            for client in clients.values():
                try:
                    await client.close()
                except:
                    pass

    async def test_three_way_alliance_negotiation(self, three_bot_setup):
        """Test alliance negotiation between three powers."""
        clients = three_bot_setup["clients"]

        # Simulate alliance negotiation sequence
        negotiations = [
            ("FRANCE", "ENGLAND", "England, shall we form an alliance against Germany?"),
            ("ENGLAND", "FRANCE", "I'm interested. What are your terms?"),
            ("FRANCE", "GERMANY", "Germany, France and England are discussing cooperation."),
            ("GERMANY", "FRANCE", "I see. Perhaps we should talk as well."),
            ("GERMANY", "ENGLAND", "England, what is France offering you?"),
            ("ENGLAND", "GERMANY", "Germany, I think we should all work together."),
        ]

        # Send all negotiation messages
        for sender, recipient, message in negotiations:
            await clients[sender].send_message(sender, recipient, message)
            await asyncio.sleep(0.1)  # Allow message processing

        # Synchronize all clients
        for client in clients.values():
            await client.synchronize()

        # Analyze message patterns from each perspective
        for power, client in clients.items():
            messages = await client.get_recent_messages(limit=20)

            # Count messages involving this power
            involving_power = [msg for msg in messages if msg.sender == power or msg.recipient == power]

            # Each power should be involved in multiple messages
            assert len(involving_power) >= 2, f"{power} should be involved in multiple messages"

        # Check that all three powers have communicated
        all_messages = await clients["FRANCE"].get_recent_messages(limit=20)

        senders = set(msg.sender for msg in all_messages)
        recipients = set(msg.recipient for msg in all_messages)

        # All three powers should appear as senders
        assert "FRANCE" in senders
        assert "ENGLAND" in senders
        assert "GERMANY" in senders

    async def test_broadcast_with_private_follow_ups(self, three_bot_setup):
        """Test broadcast message followed by private conversations."""
        clients = three_bot_setup["clients"]

        # France sends a global announcement
        await clients["FRANCE"].send_broadcast_message(sender="FRANCE", message="All powers: I propose we establish clear spheres of influence.")

        await asyncio.sleep(0.2)

        # Follow up with private messages to each power
        private_messages = [
            ("FRANCE", "ENGLAND", "England, I suggest you focus on the seas."),
            ("FRANCE", "GERMANY", "Germany, the eastern approach might suit you."),
        ]

        for sender, recipient, message in private_messages:
            await clients[sender].send_message(sender, recipient, message)
            await asyncio.sleep(0.1)

        # Synchronize all clients
        for client in clients.values():
            await client.synchronize()

        # Check that England and Germany received their specific messages
        england_messages = await clients["ENGLAND"].get_recent_messages(limit=10)
        germany_messages = await clients["GERMANY"].get_recent_messages(limit=10)

        # England should see both broadcast (to all) and private message
        england_private = [msg for msg in england_messages if msg.sender == "FRANCE" and msg.recipient == "ENGLAND"]
        england_broadcast = [msg for msg in england_messages if msg.sender == "FRANCE" and "spheres of influence" in msg.message]

        assert len(england_private) >= 1, "England should receive private message"
        assert any("seas" in msg.message for msg in england_private), "England should get seas message"

        # Germany should see broadcast and their private message
        germany_private = [msg for msg in germany_messages if msg.sender == "FRANCE" and msg.recipient == "GERMANY"]

        assert len(germany_private) >= 1, "Germany should receive private message"
        assert any("eastern" in msg.message for msg in germany_private), "Germany should get eastern message"


class TestBotPlayerMessageIntegration:
    """Test SingleBotPlayer message handling in multi-bot scenarios."""

    @pytest.fixture
    def mock_bot_players(self):
        """Create multiple mock SingleBotPlayer instances."""
        bots = {}
        powers = ["FRANCE", "ENGLAND", "GERMANY"]

        for power in powers:
            bot = SingleBotPlayer(
                username=f"{power.lower()}_bot", password="test_pass", power_name=power, model_name="test_model", game_id="test_game"
            )

            # Mock dependencies
            bot.client = MagicMock(spec=WebSocketDiplomacyClient)
            bot.agent = MagicMock(spec=DiplomacyAgent)
            bot.game_history = GameHistory()

            # Set up power name correctly
            bot.agent.power_name = power

            bots[power] = bot

        return bots

    def test_multi_bot_priority_contact_evolution(self, mock_bot_players):
        """Test how priority contacts evolve in multi-bot scenarios."""
        bots = mock_bot_players

        # Simulate asymmetric communication patterns
        # France talks to everyone, England focuses on France, Germany is quiet

        # France receives messages from multiple powers
        france_bot = bots["FRANCE"]
        france_bot.message_counts = {
            "ENGLAND": 5,  # England is very active with France
            "GERMANY": 2,  # Germany occasionally talks to France
            "ITALY": 1,  # Italy sends one message
        }
        france_bot._update_priority_contacts()

        # England receives mostly from France
        england_bot = bots["ENGLAND"]
        england_bot.message_counts = {
            "FRANCE": 8,  # France talks to England a lot
            "GERMANY": 1,  # Germany sends one message
        }
        england_bot._update_priority_contacts()

        # Germany receives few messages
        germany_bot = bots["GERMANY"]
        germany_bot.message_counts = {
            "FRANCE": 3,  # Some communication with France
            "ENGLAND": 1,  # Minimal with England
        }
        germany_bot._update_priority_contacts()

        # Check that priority contacts reflect communication patterns
        assert france_bot.priority_contacts[0] == "ENGLAND"  # Most active with France
        assert england_bot.priority_contacts[0] == "FRANCE"  # France is England's main contact
        assert germany_bot.priority_contacts[0] == "FRANCE"  # France is Germany's main contact

        # Check list lengths
        assert len(france_bot.priority_contacts) == 3  # Three powers contacted France
        assert len(england_bot.priority_contacts) == 2  # Two powers contacted England
        assert len(germany_bot.priority_contacts) == 2  # Two powers contacted Germany

    def test_response_pattern_analysis(self, mock_bot_players):
        """Test analysis of response patterns across multiple bots."""
        bots = mock_bot_players

        # Set up different response patterns for each bot
        # France: Responsive to everyone
        france_bot = bots["FRANCE"]
        france_bot.message_counts = {"ENGLAND": 4, "GERMANY": 3}
        france_bot.response_counts = {"ENGLAND": 4, "GERMANY": 3}  # 100% response rate

        # England: Selective responder
        england_bot = bots["ENGLAND"]
        england_bot.message_counts = {"FRANCE": 6, "GERMANY": 2}
        england_bot.response_counts = {"FRANCE": 6, "GERMANY": 0}  # Only responds to France

        # Germany: Poor responder
        germany_bot = bots["GERMANY"]
        germany_bot.message_counts = {"FRANCE": 5, "ENGLAND": 3}
        germany_bot.response_counts = {"FRANCE": 2, "ENGLAND": 1}  # Low response rates

        # Mock client powers for statistics
        for power, bot in bots.items():
            mock_powers = {p: MagicMock(is_eliminated=lambda: False) for p in ["FRANCE", "ENGLAND", "GERMANY", "ITALY"]}
            bot.client.powers = mock_powers

        # Generate statistics for each bot
        stats = {}
        for power, bot in bots.items():
            stats[power] = bot.get_message_statistics()

        # Analyze response patterns
        france_stats = stats["FRANCE"]
        england_stats = stats["ENGLAND"]
        germany_stats = stats["GERMANY"]

        # France should have high overall response rate
        france_avg_response = sum(france_stats["response_rate_by_power"].values()) / len(france_stats["response_rate_by_power"])
        assert france_avg_response == 1.0  # Perfect responder

        # England should have selective response pattern
        assert england_stats["response_rate_by_power"]["FRANCE"] == 1.0  # Always responds to France
        assert england_stats["response_rate_by_power"]["GERMANY"] == 0.0  # Never responds to Germany

        # Germany should have low overall response rate
        germany_avg_response = sum(germany_stats["response_rate_by_power"].values()) / len(germany_stats["response_rate_by_power"])
        assert germany_avg_response < 0.5  # Poor overall response rate

    def test_message_history_consistency_across_bots(self, mock_bot_players):
        """Test that message history tracking is consistent across different bots."""
        bots = mock_bot_players

        # Simulate the same set of messages being processed by different bots
        # (as they would see them in a real game)

        from diplomacy.engine.message import Message

        shared_messages = [
            Message(sender="FRANCE", recipient="ENGLAND", message="Alliance proposal", phase="S1901M"),
            Message(sender="ENGLAND", recipient="FRANCE", message="I accept", phase="S1901M"),
            Message(sender="GERMANY", recipient="FRANCE", message="What about me?", phase="S1901M"),
            Message(sender="FRANCE", recipient="GERMANY", message="You're welcome too", phase="S1901M"),
        ]

        # Each bot processes messages relevant to them
        for message in shared_messages:
            for power, bot in bots.items():
                # Add message to game history (all bots see all messages)
                bot.game_history.add_message(
                    phase_name=message.phase,
                    sender=message.sender,
                    recipient=message.recipient,
                    message_content=message.message,
                )

                # Track messages directed at this bot
                if message.recipient == power and message.sender != power:
                    bot.message_counts[message.sender] = bot.message_counts.get(message.sender, 0) + 1
                    bot._update_priority_contacts()

        # Verify that each bot has tracked messages correctly
        # France should have received 2 messages (from England and Germany)
        assert bots["FRANCE"].message_counts["ENGLAND"] == 1
        assert bots["FRANCE"].message_counts["GERMANY"] == 1

        # England should have received 1 message (from France)
        assert bots["ENGLAND"].message_counts["FRANCE"] == 1

        # Germany should have received 1 message (from France)
        assert bots["GERMANY"].message_counts["FRANCE"] == 1

        # Check that game history is consistent (all bots see all 4 messages)
        for power, bot in bots.items():
            all_messages = bot.game_history.get_messages_for_phase("S1901M")
            assert len(all_messages) == 4, f"{power} should see all 4 messages in game history"
