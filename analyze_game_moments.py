#!/usr/bin/env python3
"""
Analyze Key Game Moments: Betrayals, Collaborations, and Playing Both Sides

This script analyzes Diplomacy game data to identify the most interesting strategic moments.
Enhanced with:
- More stringent rating criteria
- Integration of power diary entries for better context
- Analysis of well-executed strategies and strategic mistakes
"""

import json
import asyncio
import argparse
import logging
import csv
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import os
from dotenv import load_dotenv

# Import the client from ai_diplomacy module
from ai_diplomacy.clients import load_model_client

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class GameMoment:
    """Represents a key moment in the game"""
    phase: str
    category: str  # BETRAYAL, COLLABORATION, PLAYING_BOTH_SIDES, BRILLIANT_STRATEGY, STRATEGIC_BLUNDER
    powers_involved: List[str]
    promise_agreement: str
    actual_action: str
    impact: str
    interest_score: float
    raw_messages: List[Dict]
    raw_orders: Dict
    diary_context: Dict[str, str]  # New field for diary entries

@dataclass
class Lie:
    """Represents a detected lie in diplomatic communications"""
    phase: str
    liar: str
    recipient: str
    promise: str
    diary_intent: str
    actual_action: str
    intentional: bool
    explanation: str

class GameAnalyzer:
    """Analyzes Diplomacy game data for key strategic moments"""
    
    def __init__(self, results_folder: str, model_name: str = "openrouter-google/gemini-2.5-flash-preview"):
        self.results_folder = Path(results_folder)
        self.game_data_path = self.results_folder / "lmvsgame.json"
        self.overview_path = self.results_folder / "overview.jsonl"
        self.csv_path = self.results_folder / "llm_responses.csv"
        self.model_name = model_name
        self.client = None
        self.game_data = None
        self.power_to_model = None
        self.moments = []
        self.diary_entries = {}  # phase -> power -> diary content
        self.invalid_moves_by_model = {} # Initialize attribute
        self.lies = []  # Track detected lies
        self.lies_by_model = {}  # model -> {intentional: count, unintentional: count}
        
    async def initialize(self):
        """Initialize the analyzer with game data and model client"""
        # Load game data
        with open(self.game_data_path, 'r') as f:
            self.game_data = json.load(f)
        
        # Load power-to-model mapping from overview.jsonl
        with open(self.overview_path, 'r') as f:
            lines = f.readlines()
            # Second line contains the power-to-model mapping
            if len(lines) >= 2:
                self.power_to_model = json.loads(lines[1])
                logger.info(f"Loaded power-to-model mapping: {self.power_to_model}")
            else:
                logger.warning("Could not find power-to-model mapping in overview.jsonl")
                self.power_to_model = {}
        
        # Load diary entries from CSV
        self.diary_entries = self.parse_llm_responses_csv()
        logger.info(f"Loaded diary entries for {len(self.diary_entries)} phases")
        
        # Load invalid moves data from CSV
        self.invalid_moves_by_model = self.parse_invalid_moves_from_csv()
        logger.info(f"Loaded invalid moves for {len(self.invalid_moves_by_model)} models")
        
        # Initialize model client
        self.client = load_model_client(self.model_name)
        logger.info(f"Initialized with model: {self.model_name}")
    
    def parse_llm_responses_csv(self) -> Dict[str, Dict[str, str]]:
        """Parse the CSV file to extract diary entries by phase and power"""
        diary_entries = {}
        
        try:
            import pandas as pd
            # Use pandas for more robust CSV parsing
            df = pd.read_csv(self.csv_path)
            
            # Filter for negotiation diary entries
            diary_df = df[df['response_type'] == 'negotiation_diary']
            
            for _, row in diary_df.iterrows():
                phase = row['phase']
                power = row['power']
                raw_response = str(row['raw_response']).strip()
                
                if phase not in diary_entries:
                    diary_entries[phase] = {}
                
                try:
                    # Try to parse as JSON first
                    response = json.loads(raw_response)
                    diary_content = f"Negotiation Summary: {response.get('negotiation_summary', 'N/A')}\n"
                    diary_content += f"Intent: {response.get('intent', 'N/A')}\n"
                    relationships = response.get('updated_relationships', {})
                    if isinstance(relationships, dict):
                        diary_content += f"Relationships: {relationships}"
                    else:
                        diary_content += f"Relationships: {relationships}"
                    diary_entries[phase][power] = diary_content
                except (json.JSONDecodeError, TypeError):
                    # If JSON parsing fails, use a simplified version or skip
                    if raw_response and raw_response.lower() not in ['null', 'nan', 'none']:
                        diary_entries[phase][power] = f"Raw diary: {raw_response}"
                    
            logger.info(f"Successfully parsed {len(diary_entries)} phases with diary entries")
            return diary_entries
            
        except ImportError:
            # Fallback to standard CSV if pandas not available
            logger.info("Pandas not available, using standard CSV parsing")
            import csv
            
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        if row.get('response_type') == 'negotiation_diary':
                            phase = row.get('phase', '')
                            power = row.get('power', '')
                            
                            if phase and power:
                                if phase not in diary_entries:
                                    diary_entries[phase] = {}
                                
                                raw_response = row.get('raw_response', '').strip()
                                
                                try:
                                    # Try to parse as JSON
                                    response = json.loads(raw_response)
                                    diary_content = f"Negotiation Summary: {response.get('negotiation_summary', 'N/A')}\n"
                                    diary_content += f"Intent: {response.get('intent', 'N/A')}\n"
                                    diary_content += f"Relationships: {response.get('updated_relationships', 'N/A')}"
                                    diary_entries[phase][power] = diary_content
                                except (json.JSONDecodeError, TypeError):
                                    if raw_response and raw_response != "null":
                                        diary_entries[phase][power] = f"Raw diary: {raw_response}"
                    except Exception as e:
                        continue  # Skip problematic rows
                        
            return diary_entries
            
        except Exception as e:
            logger.error(f"Error parsing CSV file: {e}")
            return {}
    
    def parse_invalid_moves_from_csv(self) -> Dict[str, int]:
        """Parse the CSV file to count invalid moves by model"""
        invalid_moves_by_model = {}
        
        try:
            import pandas as pd
            # Use pandas for more robust CSV parsing
            df = pd.read_csv(self.csv_path)
            
            # Look for failures in the success column
            failure_df = df[df['success'].str.contains('Failure: Invalid LLM Moves', na=False)]
            
            for _, row in failure_df.iterrows():
                model = row['model']
                success_text = str(row['success'])
                
                # Extract the number from "Failure: Invalid LLM Moves (N):"
                import re
                match = re.search(r'Invalid LLM Moves \((\d+)\)', success_text)
                if match:
                    invalid_count = int(match.group(1))
                    if model not in invalid_moves_by_model:
                        invalid_moves_by_model[model] = 0
                    invalid_moves_by_model[model] += invalid_count
            
            logger.info(f"Successfully parsed invalid moves for {len(invalid_moves_by_model)} models")
            return invalid_moves_by_model
            
        except ImportError:
            # Fallback to standard CSV if pandas not available
            logger.info("Pandas not available, using standard CSV parsing for invalid moves")
            import csv
            import re
            
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        success_text = row.get('success', '')
                        if 'Failure: Invalid LLM Moves' in success_text:
                            model = row.get('model', '')
                            match = re.search(r'Invalid LLM Moves \((\d+)\)', success_text)
                            if match and model:
                                invalid_count = int(match.group(1))
                                if model not in invalid_moves_by_model:
                                    invalid_moves_by_model[model] = 0
                                invalid_moves_by_model[model] += invalid_count
                    except Exception as e:
                        continue  # Skip problematic rows
                        
            return invalid_moves_by_model
            
        except Exception as e:
            logger.error(f"Error parsing invalid moves from CSV file: {e}")
            return {}
    
    def extract_turn_data(self, phase_data: Dict) -> Dict:
        """Extract relevant data from a single turn/phase"""
        phase_name = phase_data.get("name", "")
        
        # Get diary entries for this phase
        phase_diaries = self.diary_entries.get(phase_name, {})
        
        return {
            "phase": phase_name,
            "messages": phase_data.get("messages", []),
            "orders": phase_data.get("orders", {}),
            "summary": phase_data.get("summary", ""),
            "statistical_summary": phase_data.get("statistical_summary", {}),
            "diaries": phase_diaries
        }
    
    def create_analysis_prompt(self, turn_data: Dict) -> str:
        """Create the analysis prompt for a single turn"""
        # Format messages for analysis
        formatted_messages = []
        for msg in turn_data.get("messages", []):
            sender = msg.get('sender', 'Unknown')
            sender_model = self.power_to_model.get(sender, '')
            sender_str = f"{sender} ({sender_model})" if sender_model else sender
            
            recipient = msg.get('recipient', 'Unknown')
            recipient_model = self.power_to_model.get(recipient, '')
            recipient_str = f"{recipient} ({recipient_model})" if recipient_model else recipient
            
            formatted_messages.append(
                f"{sender_str} to {recipient_str}: {msg.get('message', '')}"
            )
        
        # Format orders for analysis
        formatted_orders = []
        for power, power_orders in turn_data.get("orders", {}).items():
            power_model = self.power_to_model.get(power, '')
            power_str = f"{power} ({power_model})" if power_model else power
            formatted_orders.append(f"{power_str}: {power_orders}")
        
        # Format diary entries
        formatted_diaries = []
        for power, diary in turn_data.get("diaries", {}).items():
            power_model = self.power_to_model.get(power, '')
            power_str = f"{power} ({power_model})" if power_model else power
            formatted_diaries.append(f"{power_str} DIARY:\n{diary}")
        
        prompt = f"""You are analyzing diplomatic negotiations and subsequent military orders from a Diplomacy game. Your task is to identify key strategic moments in the following categories:

1. BETRAYAL: When a power explicitly promises one action but takes a contradictory action
2. COLLABORATION: When powers successfully coordinate as agreed
3. PLAYING_BOTH_SIDES: When a power makes conflicting promises to different parties
4. BRILLIANT_STRATEGY: Exceptionally well-executed strategic maneuvers that gain significant advantage
5. STRATEGIC_BLUNDER: Major strategic mistakes that significantly weaken a power's position

IMPORTANT SCORING GUIDELINES:
- Scores 1-3: Minor or routine diplomatic events
- Scores 4-6: Significant but expected diplomatic maneuvers
- Scores 7-8: Notable strategic moments with clear impact
- Scores 9-10: EXCEPTIONAL moments that are truly dramatic or game-changing

Reserve high scores (8+) for:
- Major betrayals that fundamentally shift alliances
- Successful coordinated attacks on major powers
- Clever deceptions that fool multiple powers
- Brilliant strategic maneuvers that dramatically improve position
- Catastrophic strategic errors with lasting consequences
- Actions that dramatically alter the game's balance

For this turn ({turn_data.get('phase', '')}), analyze:

PRIVATE DIARY ENTRIES (Powers' internal thoughts):
{chr(10).join(formatted_diaries) if formatted_diaries else 'No diary entries available'}

MESSAGES:
{chr(10).join(formatted_messages) if formatted_messages else 'No messages this turn'}

ORDERS:
{chr(10).join(formatted_orders) if formatted_orders else 'No orders this turn'}

TURN SUMMARY:
{turn_data.get('summary', 'No summary available')}

Identify ALL instances that fit the five categories. For each instance provide:
{{
    "category": "BETRAYAL" or "COLLABORATION" or "PLAYING_BOTH_SIDES" or "BRILLIANT_STRATEGY" or "STRATEGIC_BLUNDER",
    "powers_involved": ["POWER1", "POWER2", ...],
    "promise_agreement": "What was promised/agreed/intended (or strategy attempted)",
    "actual_action": "What actually happened",
    "impact": "Strategic impact on the game",
    "interest_score": 6.5  // 1-10 scale, be STRICT with high scores
}}

Use the diary entries to verify:
- Whether actions align with stated intentions
- Hidden motivations behind diplomatic moves
- Contradictions between public promises and private plans
- Strategic planning and its execution

Return your response as a JSON array of detected moments. If no relevant moments are found, return an empty array [].

Focus on:
- Comparing diary intentions vs actual orders
- Explicit promises vs actual orders
- Coordinated attacks or defenses
- DMZ violations
- Support promises kept or broken
- Conflicting negotiations with different powers
- Clever strategic positioning
- Missed strategic opportunities
- Tactical errors that cost supply centers
"""
        return prompt
    
    async def analyze_turn(self, phase_data: Dict) -> List[Dict]:
        """Analyze a single turn for key moments"""
        turn_data = self.extract_turn_data(phase_data)
        
        # Skip if no meaningful data
        if not turn_data["messages"] and not turn_data["orders"]:
            return []
        
        prompt = self.create_analysis_prompt(turn_data)
        
        try:
            response = await self.client.generate_response(prompt)
            
            # Parse JSON response
            # Handle potential code blocks or direct JSON
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            detected_moments = json.loads(response)
            
            # Enrich with raw data
            moments = []
            for moment in detected_moments:
                game_moment = GameMoment(
                    phase=turn_data["phase"],
                    category=moment.get("category", ""),
                    powers_involved=moment.get("powers_involved", []),
                    promise_agreement=moment.get("promise_agreement", ""),
                    actual_action=moment.get("actual_action", ""),
                    impact=moment.get("impact", ""),
                    interest_score=float(moment.get("interest_score", 5)),
                    raw_messages=turn_data["messages"],
                    raw_orders=turn_data["orders"],
                    diary_context=turn_data["diaries"]
                )
                moments.append(game_moment)
                logger.info(f"Detected {game_moment.category} in {game_moment.phase} "
                          f"(score: {game_moment.interest_score})")
            
            return moments
            
        except Exception as e:
            logger.error(f"Error analyzing turn {turn_data.get('phase', '')}: {e}")
            return []
    
    def detect_lies_in_phase(self, phase_data: Dict) -> List[Lie]:
        """Detect lies by comparing messages, diary entries, and actual orders"""
        phase_name = phase_data.get("name", "")
        messages = phase_data.get("messages", [])
        orders = phase_data.get("orders", {})
        diaries = self.diary_entries.get(phase_name, {})
        
        detected_lies = []
        
        # Group messages by sender
        messages_by_sender = {}
        for msg in messages:
            sender = msg.get('sender', '')
            if sender not in messages_by_sender:
                messages_by_sender[sender] = []
            messages_by_sender[sender].append(msg)
        
        # Analyze each power's messages against their diary and orders
        for sender, sent_messages in messages_by_sender.items():
            sender_diary = diaries.get(sender, '')
            sender_orders = orders.get(sender, [])
            
            for msg in sent_messages:
                recipient = msg.get('recipient', '')
                message_text = msg.get('message', '')
                
                # Extract promises from message using keywords
                promises = self.extract_promises_from_message(message_text)
                
                for promise in promises:
                    # Check if promise was kept
                    lie_detected = self.check_promise_against_orders(
                        promise, sender_orders, sender_diary, 
                        sender, recipient, phase_name
                    )
                    if lie_detected:
                        detected_lies.append(lie_detected)
        
        return detected_lies
    
    def extract_promises_from_message(self, message: str) -> List[Dict]:
        """Extract specific promises from a message"""
        promises = []
        message_lower = message.lower()
        
        # Common promise patterns - more specific to Diplomacy
        promise_patterns = [
            # Support promises
            (r'(?:i )?will support (?:your )?(\w+)(?:/\w+)? (?:to|into|-) (\w+)', 'support'),
            (r'(?:my )?(\w+) (?:will )?s(?:upport)?s? (?:your )?(\w+)(?:/\w+)?(?:\s+)?(?:to|into|-)(?:\s+)?(\w+)', 'support'),
            (r'a (\w+) s a (\w+)(?:\s+)?(?:-|to)(?:\s+)?(\w+)', 'support'),
            (r'f (\w+) s (?:a |f )?(\w+)(?:\s+)?(?:-|to)(?:\s+)?(\w+)', 'support'),
            # Movement promises
            (r'(?:i )?will (?:move|order) (?:my )?(\w+) to (\w+)', 'move'),
            (r'a (\w+)(?:\s+)?(?:->|-)(?:\s+)?(\w+)', 'move'),
            (r'f (\w+)(?:\s+)?(?:->|-)(?:\s+)?(\w+)', 'move'),
            (r'(\w+) (?:moves?|going) to (\w+)', 'move'),
            # Hold promises
            (r'(?:will )?hold (?:in )?(\w+)', 'hold'),
            (r'(\w+) (?:will )?h(?:old)?s?', 'hold'),
            (r'a (\w+) h', 'hold'),
            (r'f (\w+) h', 'hold'),
            # No attack promises  
            (r'(?:will |won\'t |will not )attack (\w+)', 'no_attack'),
            (r'no (?:moves?|attacks?) (?:on|against|to) (\w+)', 'no_attack'),
            (r'stay(?:ing)? out of (\w+)', 'no_attack'),
            # DMZ promises
            (r'dmz (?:in |on |for )?(\w+)', 'dmz'),
            (r'(\w+) (?:will be|stays?|remains?) dmz', 'dmz'),
            (r'demilitari[sz]ed? (?:zone )?(?:in |on )?(\w+)', 'dmz'),
            # Specific coordination
            (r'(?:agree|agreed) (?:to |on )?(.+)', 'agreement'),
            (r'(?:promise|commit) (?:to |that )?(.+)', 'promise'),
        ]
        
        import re
        for pattern, promise_type in promise_patterns:
            matches = re.finditer(pattern, message_lower, re.IGNORECASE)
            for match in matches:
                promise_dict = {
                    'type': promise_type,
                    'details': match.groups(),
                    'full_match': match.group(0),
                    'start': match.start(),
                    'end': match.end()
                }
                
                # Extract context around the promise
                context_start = max(0, match.start() - 50)
                context_end = min(len(message), match.end() + 50)
                promise_dict['context'] = message[context_start:context_end]
                
                promises.append(promise_dict)
        
        return promises
    
    def check_promise_against_orders(self, promise: Dict, actual_orders: List[str], 
                                   diary: str, sender: str, recipient: str, 
                                   phase: str) -> Optional[Lie]:
        """Check if a promise was kept by comparing against actual orders"""
        promise_type = promise['type']
        details = promise['details']
        
        # Normalize orders for comparison
        orders_str = ' '.join(actual_orders).lower()
        orders_lower = [order.lower() for order in actual_orders]
        
        lie_detected = False
        actual_action = ""
        
        # More sophisticated checking based on promise type
        if promise_type == 'support':
            # Check if support was given
            if len(details) >= 3:
                unit_loc = details[0]  # Location of supporting unit
                supported_loc = details[1]  # Location being supported from
                target_loc = details[2]  # Target location
                
                # Check various support formats
                support_patterns = [
                    f"{unit_loc} s {supported_loc} - {target_loc}",
                    f"{unit_loc} s {supported_loc}-{target_loc}",
                    f"{unit_loc} support {supported_loc} - {target_loc}",
                    f"s {supported_loc} - {target_loc}"  # Sometimes location is implicit
                ]
                
                found_support = False
                for pattern in support_patterns:
                    if pattern in orders_str:
                        found_support = True
                        break
                
                if not found_support:
                    lie_detected = True
                    actual_action = f"No support from {unit_loc} for {supported_loc}-{target_loc} found in orders: {', '.join(actual_orders)}"
                    
        elif promise_type == 'move':
            if len(details) >= 2:
                unit = details[0]
                destination = details[1]
                
                # Check various move formats
                move_patterns = [
                    f"{unit} - {destination}",
                    f"{unit}-{destination}",
                    f"a {unit} - {destination}",
                    f"f {unit} - {destination}"
                ]
                
                found_move = False
                for pattern in move_patterns:
                    if pattern in orders_str:
                        found_move = True
                        break
                        
                if not found_move:
                    # Check what the unit actually did
                    unit_action = "Unknown"
                    for order in orders_lower:
                        if unit in order:
                            unit_action = order
                            break
                    
                    lie_detected = True
                    actual_action = f"Unit at {unit} did not move to {destination}. Actual order: {unit_action}"
                    
        elif promise_type == 'hold':
            if len(details) >= 1:
                unit = details[0]
                
                hold_patterns = [
                    f"{unit} h",
                    f"a {unit} h",
                    f"f {unit} h",
                    f"{unit} hold"
                ]
                
                found_hold = False
                for pattern in hold_patterns:
                    if pattern in orders_str:
                        found_hold = True
                        break
                        
                if not found_hold:
                    # Check what the unit actually did
                    unit_action = "Unknown"
                    for order in orders_lower:
                        if unit in order:
                            unit_action = order
                            break
                            
                    lie_detected = True
                    actual_action = f"Unit at {unit} did not hold. Actual order: {unit_action}"
                    
        elif promise_type == 'no_attack':
            if len(details) >= 1:
                target = details[0]
                
                # Check if any unit attacked the target
                attack_patterns = [
                    f"- {target}",
                    f"-{target}",
                    f"to {target}",
                    f"into {target}"
                ]
                
                for pattern in attack_patterns:
                    if pattern in orders_str:
                        # Find which unit attacked
                        attacking_unit = "Unknown"
                        for order in orders_lower:
                            if pattern in order:
                                attacking_unit = order
                                break
                                
                        lie_detected = True
                        actual_action = f"Attacked {target} despite promise not to. Order: {attacking_unit}"
                        break
        
        if lie_detected:
            # Determine if intentional based on diary
            intentional = self.check_if_lie_intentional(promise, diary, actual_action)
            
            return Lie(
                phase=phase,
                liar=sender,
                recipient=recipient,
                promise=f"{promise['full_match']} (context: {promise.get('context', '')})",
                diary_intent=self.extract_relevant_diary_excerpt(diary, promise),
                actual_action=actual_action,
                intentional=intentional,
                explanation="Intentional deception" if intentional else "Possible misunderstanding or changed circumstances"
            )
        
        return None
    
    def check_if_lie_intentional(self, promise: Dict, diary: str, actual_action: str) -> bool:
        """Determine if a lie was intentional based on diary content"""
        if not diary:
            return False
            
        diary_lower = diary.lower()
        
        # Indicators of intentional deception
        deception_indicators = [
            'mislead', 'deceive', 'trick', 'false', 'pretend',
            'while actually', 'but will', 'instead will',
            'make them think', 'let them believe', 'deliberately',
            'stab', 'betray', 'double-cross', 'feign',
            'was deliberately misled', 'lied to', 'false promise'
        ]
        
        # Check for explicit deception language
        for indicator in deception_indicators:
            if indicator in diary_lower:
                return True
        
        # Check if diary explicitly contradicts the promise
        promise_text = promise['full_match']
        promise_context = promise.get('context', '').lower()
        
        # Look for specific contradictions based on promise type
        if promise['type'] == 'support':
            if len(promise['details']) >= 2:
                target = promise['details'][1]
                # Check if diary mentions NOT supporting or attacking instead
                if (f"not support {target}" in diary_lower or 
                    f"attack {target}" in diary_lower or
                    f"will not help" in diary_lower):
                    return True
                    
        elif promise['type'] == 'no_attack':
            target = promise['details'][0] if promise['details'] else ''
            if target and (f"attack {target}" in diary_lower or 
                          f"move to {target}" in diary_lower or
                          f"take {target}" in diary_lower):
                return True
                
        elif promise['type'] == 'move' or promise['type'] == 'hold':
            # Check if diary mentions different plans
            if 'different plan' in diary_lower or 'change of plans' in diary_lower:
                # But not if it mentions unexpected circumstances
                if 'forced to' not in diary_lower and 'had to' not in diary_lower:
                    return True
        
        # Check for planning contradictory actions
        if 'negotiation_summary' in diary_lower:
            # Extract negotiation summary section
            summary_start = diary_lower.find('negotiation_summary')
            summary_end = diary_lower.find('intent:', summary_start) if summary_start != -1 else len(diary_lower)
            if summary_start != -1:
                summary_section = diary_lower[summary_start:summary_end]
                
                # Check if the summary mentions agreements that contradict the promise
                if promise['type'] == 'support' and 'agreed' in promise_context:
                    # Check if diary mentions different agreement
                    if 'agreed' in summary_section and promise_text not in summary_section:
                        return True
        
        # Additional check: if diary mentions the recipient being deceived
        recipient_mentioned = False
        if 'details' in promise and len(promise['details']) > 0:
            for detail in promise['details']:
                if detail and detail.lower() in diary_lower:
                    recipient_mentioned = True
                    break
                    
        if recipient_mentioned and any(word in diary_lower for word in ['trick', 'fool', 'deceive', 'mislead']):
            return True
        
        return False
    
    def extract_relevant_diary_excerpt(self, diary: str, promise: Dict) -> str:
        """Extract the most relevant part of diary related to the promise"""
        if not diary:
            return "No diary entry"
            
        # Try to find relevant sentences
        sentences = diary.split('.')
        relevant = []
        
        promise_keywords = promise['full_match'].split()
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in promise_keywords):
                relevant.append(sentence.strip())
        
        if relevant:
            return '. '.join(relevant[:2])  # Return up to 2 relevant sentences
        else:
            # Return first 100 chars if no specific match
            return diary[:100] + "..." if len(diary) > 100 else diary
    
    async def analyze_game(self, max_phases: Optional[int] = None, max_concurrent: int = 5):
        """Analyze the entire game for key moments with concurrent processing
        
        Args:
            max_phases: Maximum number of phases to analyze (None = all)
            max_concurrent: Maximum number of concurrent phase analyses
        """
        phases = self.game_data.get("phases", [])
        
        if max_phases is not None:
            phases = phases[:max_phases]
            logger.info(f"Analyzing first {len(phases)} phases (out of {len(self.game_data.get('phases', []))} total)...")
        else:
            logger.info(f"Analyzing {len(phases)} phases...")
        
        # Process phases in batches to avoid overwhelming the API
        all_moments = []
        
        for i in range(0, len(phases), max_concurrent):
            batch = phases[i:i + max_concurrent]
            batch_start = i + 1
            batch_end = min(i + max_concurrent, len(phases))
            
            logger.info(f"Processing batch {batch_start}-{batch_end} of {len(phases)} phases...")
            
            # Create tasks for concurrent processing
            tasks = []
            for j, phase_data in enumerate(batch):
                phase_name = phase_data.get("name", f"Phase {i+j}")
                logger.info(f"Starting analysis of phase {phase_name}")
                task = self.analyze_turn(phase_data)
                tasks.append(task)
            
            # Wait for all tasks in this batch to complete
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results and handle any exceptions
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    phase_name = batch[j].get("name", f"Phase {i+j}")
                    logger.error(f"Error analyzing phase {phase_name}: {result}")
                else:
                    all_moments.extend(result)
            
            # Small delay between batches to be respectful to the API
            if i + max_concurrent < len(phases):
                logger.info(f"Batch complete. Waiting 2 seconds before next batch...")
                await asyncio.sleep(2)
        
        self.moments = all_moments
        
        # Analyze lies separately
        logger.info("Analyzing diplomatic lies...")
        for phase_data in phases:
            phase_lies = self.detect_lies_in_phase(phase_data)
            self.lies.extend(phase_lies)
        
        # Count lies by model
        for lie in self.lies:
            liar_model = self.power_to_model.get(lie.liar, 'Unknown')
            if liar_model not in self.lies_by_model:
                self.lies_by_model[liar_model] = {'intentional': 0, 'unintentional': 0}
            
            if lie.intentional:
                self.lies_by_model[liar_model]['intentional'] += 1
            else:
                self.lies_by_model[liar_model]['unintentional'] += 1
        
        # Sort moments by interest score
        self.moments.sort(key=lambda m: m.interest_score, reverse=True)
        
        logger.info(f"Analysis complete. Found {len(self.moments)} key moments and {len(self.lies)} lies.")
    
    def format_power_with_model(self, power: str) -> str:
        """Format power name with model in parentheses"""
        model = self.power_to_model.get(power, '')
        return f"{power} ({model})" if model else power
    
    def phase_sort_key(self, phase_name):
        """Create a sortable key for diplomacy phases like 'S1901M', 'F1901M', etc."""
        # Extract season, year, and type
        if not phase_name or len(phase_name) < 6:
            return (0, 0, "")
            
        try:
            season = phase_name[0]  # S, F, W
            year = int(phase_name[1:5]) if phase_name[1:5].isdigit() else 0  # 1901, 1902, etc.
            phase_type = phase_name[5:]  # M, A, R
            
            # Order: Spring (S) < Fall (F) < Winter (W)
            season_order = {"S": 1, "F": 2, "W": 3}.get(season, 0)
            
            return (year, season_order, phase_type)
        except Exception:
            return (0, 0, "")
    
    async def generate_narrative(self) -> str:
        """Generate a narrative story of the game using phase summaries and top moments"""
        # Collect all phase summaries
        phase_summaries = []
        phases_with_summaries = []
        
        for phase in self.game_data.get("phases", []):
            if phase.get("summary"):
                phase_name = phase.get("name", "")
                summary = phase.get("summary", "")
                phases_with_summaries.append((phase_name, summary))
        
        # Sort phases chronologically
        phases_with_summaries.sort(key=lambda p: self.phase_sort_key(p[0]))
        
        # Create summary strings
        for phase_name, summary in phases_with_summaries:
            phase_summaries.append(f"{phase_name}: {summary}")
        
        # Create the narrative prompt
        narrative_prompt = f"""You are a master war historian writing a dramatic chronicle of a Diplomacy game. Transform the comprehensive game record below into a single, gripping narrative of betrayal, alliance, and conquest.

THE COMPETING POWERS (always refer to them as "Power (Model)"):
{chr(10).join([f"- {power} ({model})" for power, model in sorted(self.power_to_model.items())])}

COMPLETE GAME RECORD (synthesize all of this into your narrative):
{chr(10).join(phase_summaries)}

IMPORTANT POWER DIARIES (internal thoughts of each power):
"""
        # Sort diary phases chronologically
        diary_phases = list(self.diary_entries.keys())
        diary_phases.sort(key=self.phase_sort_key)
        
        # Include power diaries for context (early phases)
        for phase in diary_phases[:3]:  # First few phases for early intentions
            narrative_prompt += f"Phase {phase}:\n"
            for power, diary in sorted(self.diary_entries[phase].items()):
                power_with_model = self.format_power_with_model(power)
                diary_excerpt = diary  # Display full diary content
                narrative_prompt += f"- {power_with_model}: {diary_excerpt}\n"
            narrative_prompt += "\n"
            
        # Also include some late-game diaries
        if len(diary_phases) > 3:
            for phase in diary_phases[-2:]:  # Last two phases for endgame context
                narrative_prompt += f"Phase {phase}:\n"
                for power, diary in sorted(self.diary_entries[phase].items()):
                    power_with_model = self.format_power_with_model(power)
                    diary_excerpt = diary  # Display full diary content
                    narrative_prompt += f"- {power_with_model}: {diary_excerpt}\n"
                narrative_prompt += "\n"
            
        narrative_prompt += """
KEY DRAMATIC MOMENTS (reference these highlights appropriately):
"""
        # Extract top moments from each category for narrative context
        key_moments = []
        for category in ["BETRAYAL", "COLLABORATION", "PLAYING_BOTH_SIDES", "BRILLIANT_STRATEGY", "STRATEGIC_BLUNDER"]:
            category_moments = [m for m in self.moments if m.category == category]
            category_moments.sort(key=lambda m: m.interest_score, reverse=True)
            key_moments.extend(category_moments[:5])  # Top 5 from each category
        
        # Sort by phase chronologically
        key_moments.sort(key=lambda m: self.phase_sort_key(m.phase))
        
        # Format dramatic moments with power names and models (simpler format)
        for moment in key_moments:
            powers_with_models = [f"{p} ({self.power_to_model.get(p, 'Unknown')})" for p in moment.powers_involved]
            narrative_prompt += f"{moment.phase} - {moment.category} (Score: {moment.interest_score}/10): {', '.join(powers_with_models)}\n"

        narrative_prompt += """
CRITICAL INSTRUCTIONS:
- Write EXACTLY 1-2 paragraphs that tell the COMPLETE story of the ENTIRE game
- This is NOT a summary of each phase - it's ONE flowing narrative of the whole game
- Always refer to powers as "PowerName (ModelName)" - e.g., "Germany (o3)", "France (o4-mini)"
- Start with how the game began and the initial alliances
- Cover the major turning points and dramatic moments
- End with how the game concluded and who won
- Use dramatic, evocative language but be concise
- Focus on the overall arc of the game, not individual phase details

Create a single, cohesive narrative that captures the essence of the entire game from start to finish. Think of it as the opening passage of a history book chapter about this conflict.
"""

        try:
            response = await self.client.generate_response(narrative_prompt)
            return response
        except Exception as e:
            logger.error(f"Error generating narrative: {e}")
            return "Unable to generate narrative due to an error."
    
    async def generate_report(self, output_path: Optional[str] = None):
        """Generate a markdown report of key moments"""
        # Generate unique filename with datetime if no path specified
        if output_path is None:
            # Create in the game_moments directory
            game_moments_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "game_moments")
            os.makedirs(game_moments_dir, exist_ok=True)
            
            # Use results folder name in the file name
            results_name = os.path.basename(os.path.normpath(str(self.results_folder)))
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(game_moments_dir, f"{results_name}_report_{timestamp}.md")
        
        # Generate the narrative first
        narrative = await self.generate_narrative()
        
        report_lines = [
            "# Diplomacy Game Analysis: Key Moments",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Game: {self.game_data_path}",
            "",
            "## Game Narrative",
            "",
            narrative,
            "",
            "---",
            "",
            "## Summary",
            f"- Total moments analyzed: {len(self.moments)}",
            f"- Betrayals: {len([m for m in self.moments if m.category == 'BETRAYAL'])}",
            f"- Collaborations: {len([m for m in self.moments if m.category == 'COLLABORATION'])}",
            f"- Playing Both Sides: {len([m for m in self.moments if m.category == 'PLAYING_BOTH_SIDES'])}",
            f"- Brilliant Strategies: {len([m for m in self.moments if m.category == 'BRILLIANT_STRATEGY'])}",
            f"- Strategic Blunders: {len([m for m in self.moments if m.category == 'STRATEGIC_BLUNDER'])}",
            "",
            "## Score Distribution",
            f"- Scores 9-10: {len([m for m in self.moments if m.interest_score >= 9])}",
            f"- Scores 7-8: {len([m for m in self.moments if 7 <= m.interest_score < 9])}",
            f"- Scores 4-6: {len([m for m in self.moments if 4 <= m.interest_score < 7])}",
            f"- Scores 1-3: {len([m for m in self.moments if m.interest_score < 4])}",
            "",
            "## Power Models",
            ""
        ]
        
        # Add power-model mapping
        for power, model in sorted(self.power_to_model.items()):
            report_lines.append(f"- **{power}**: {model}")
        
        # Add invalid moves analysis section RIGHT AFTER Power Models
        if self.invalid_moves_by_model:
            report_lines.extend([
                "",
                "## Invalid Moves by Model",
                ""
            ])
            
            sorted_invalid = sorted(self.invalid_moves_by_model.items(), 
                                  key=lambda x: x[1], reverse=True)
            for model, count in sorted_invalid:
                report_lines.append(f"- **{model}**: {count} invalid moves")
        
        # Add lies analysis section 
        report_lines.extend([
            "",
            "## Lies Analysis",
            "",
            "### Lies by Model",
            ""
        ])
        
        # Sort models by total lies
        sorted_models = sorted(self.lies_by_model.items(), 
                             key=lambda x: x[1]['intentional'] + x[1]['unintentional'], 
                             reverse=True)
        
        for model, counts in sorted_models:
            total = counts['intentional'] + counts['unintentional']
            if total > 0:  # Only show models with lies
                report_lines.append(f"- **{model}**: {total} total lies ({counts['intentional']} intentional, {counts['unintentional']} unintentional)")
        
        # Add top lies examples
        if self.lies:  # Only add if there are lies
            report_lines.extend([
                "",
                "### Notable Lies",
                ""
            ])
            
            # Show top 5 intentional lies
            intentional_lies = [lie for lie in self.lies if lie.intentional]
            for i, lie in enumerate(intentional_lies[:5], 1):
                liar_str = self.format_power_with_model(lie.liar)
                recipient_str = self.format_power_with_model(lie.recipient)
                report_lines.extend([
                    f"#### {i}. {lie.phase} - Intentional Deception",
                    f"**{liar_str}** to **{recipient_str}**",
                    "",
                    f"**Promise:** \"{lie.promise}\"",
                    "",
                    f"**Diary Intent:** {lie.diary_intent}",
                    "",
                    f"**Actual Action:** {lie.actual_action}",
                    ""
                ])
        
        # Add category breakdowns with detailed information
        report_lines.extend([
            "",
            "## Key Strategic Moments by Category",
            ""
        ])
        
        # BETRAYALS SECTION
        report_lines.extend([
            "### Betrayals",
            "_When powers explicitly promised one action but took a contradictory action_",
            ""
        ])
        
        betrayals = [m for m in self.moments if m.category == "BETRAYAL"]
        betrayals.sort(key=lambda m: m.interest_score, reverse=True)
        
        for i, moment in enumerate(betrayals[:5], 1):
            powers_str = ', '.join([self.format_power_with_model(p) for p in moment.powers_involved])
            report_lines.extend([
                f"#### {i}. {moment.phase} (Score: {moment.interest_score}/10)",
                f"**Powers Involved:** {powers_str}",
                "",
                f"**Promise:** {moment.promise_agreement if moment.promise_agreement else 'N/A'}",
                "",
                f"**Actual Action:** {moment.actual_action if moment.actual_action else 'N/A'}",
                "",
                f"**Impact:** {moment.impact if moment.impact else 'N/A'}",
                "",
                "**Diary Context:**",
                ""
            ])
            
            # Add relevant diary entries
            for power in moment.powers_involved:
                if power in moment.diary_context:
                    power_with_model = self.format_power_with_model(power)
                    report_lines.append(f"_{power_with_model} Diary:_ {moment.diary_context[power]}")
                    report_lines.append("")
                    
            report_lines.append("")
        
        # COLLABORATIONS SECTION
        report_lines.extend([
            "### Collaborations",
            "_When powers successfully coordinated as agreed_",
            ""
        ])
        
        collaborations = [m for m in self.moments if m.category == "COLLABORATION"]
        collaborations.sort(key=lambda m: m.interest_score, reverse=True)
        
        for i, moment in enumerate(collaborations[:5], 1):
            powers_str = ', '.join([self.format_power_with_model(p) for p in moment.powers_involved])
            report_lines.extend([
                f"#### {i}. {moment.phase} (Score: {moment.interest_score}/10)",
                f"**Powers Involved:** {powers_str}",
                "",
                f"**Agreement:** {moment.promise_agreement if moment.promise_agreement else 'N/A'}",
                "",
                f"**Action Taken:** {moment.actual_action if moment.actual_action else 'N/A'}",
                "",
                f"**Impact:** {moment.impact if moment.impact else 'N/A'}",
                "",
                "**Diary Context:**",
                ""
            ])
            
            # Add relevant diary entries
            for power in moment.powers_involved:
                if power in moment.diary_context:
                    power_with_model = self.format_power_with_model(power)
                    report_lines.append(f"_{power_with_model} Diary:_ {moment.diary_context[power]}")
                    report_lines.append("")
                    
            report_lines.append("")
        
        # PLAYING BOTH SIDES SECTION
        report_lines.extend([
            "### Playing Both Sides",
            "_When a power made conflicting promises to different parties_",
            ""
        ])
        
        playing_both = [m for m in self.moments if m.category == "PLAYING_BOTH_SIDES"]
        playing_both.sort(key=lambda m: m.interest_score, reverse=True)
        
        for i, moment in enumerate(playing_both[:5], 1):
            powers_str = ', '.join([self.format_power_with_model(p) for p in moment.powers_involved])
            report_lines.extend([
                f"#### {i}. {moment.phase} (Score: {moment.interest_score}/10)",
                f"**Powers Involved:** {powers_str}",
                "",
                f"**Conflicting Promises:** {moment.promise_agreement if moment.promise_agreement else 'N/A'}",
                "",
                f"**Actual Action:** {moment.actual_action if moment.actual_action else 'N/A'}",
                "",
                f"**Impact:** {moment.impact if moment.impact else 'N/A'}",
                "",
                "**Diary Context:**",
                ""
            ])
            
            # Add relevant diary entries
            for power in moment.powers_involved:
                if power in moment.diary_context:
                    power_with_model = self.format_power_with_model(power)
                    report_lines.append(f"_{power_with_model} Diary:_ {moment.diary_context[power]}")
                    report_lines.append("")
                    
            report_lines.append("")
        
        # BRILLIANT STRATEGIES SECTION
        report_lines.extend([
            "### Brilliant Strategies",
            "_Exceptionally well-executed strategic maneuvers that gained significant advantage_",
            ""
        ])
        
        brilliant = [m for m in self.moments if m.category == "BRILLIANT_STRATEGY"]
        brilliant.sort(key=lambda m: m.interest_score, reverse=True)
        
        for i, moment in enumerate(brilliant[:5], 1):
            powers_str = ', '.join([self.format_power_with_model(p) for p in moment.powers_involved])
            report_lines.extend([
                f"#### {i}. {moment.phase} (Score: {moment.interest_score}/10)",
                f"**Powers Involved:** {powers_str}",
                "",
                f"**Strategy:** {moment.promise_agreement if moment.promise_agreement else 'N/A'}",
                "",
                f"**Execution:** {moment.actual_action if moment.actual_action else 'N/A'}",
                "",
                f"**Impact:** {moment.impact if moment.impact else 'N/A'}",
                "",
                "**Diary Context:**",
                ""
            ])
            
            # Add relevant diary entries
            for power in moment.powers_involved:
                if power in moment.diary_context:
                    power_with_model = self.format_power_with_model(power)
                    report_lines.append(f"_{power_with_model} Diary:_ {moment.diary_context[power]}")
                    report_lines.append("")
                    
            report_lines.append("")
        
        # STRATEGIC BLUNDERS SECTION
        report_lines.extend([
            "### Strategic Blunders",
            "_Major strategic mistakes that significantly weakened a power's position_",
            ""
        ])
        
        blunders = [m for m in self.moments if m.category == "STRATEGIC_BLUNDER"]
        blunders.sort(key=lambda m: m.interest_score, reverse=True)
        
        for i, moment in enumerate(blunders[:5], 1):
            powers_str = ', '.join([self.format_power_with_model(p) for p in moment.powers_involved])
            report_lines.extend([
                f"#### {i}. {moment.phase} (Score: {moment.interest_score}/10)",
                f"**Powers Involved:** {powers_str}",
                "",
                f"**Mistaken Strategy:** {moment.promise_agreement if moment.promise_agreement else 'N/A'}",
                "",
                f"**What Happened:** {moment.actual_action if moment.actual_action else 'N/A'}",
                "",
                f"**Impact:** {moment.impact if moment.impact else 'N/A'}",
                "",
                "**Diary Context:**",
                ""
            ])
            
            # Add relevant diary entries
            for power in moment.powers_involved:
                if power in moment.diary_context:
                    power_with_model = self.format_power_with_model(power)
                    report_lines.append(f"_{power_with_model} Diary:_ {moment.diary_context[power]}")
                    report_lines.append("")
                    
            report_lines.append("")
        
        # Write report
        with open(output_path, 'w') as f:
            f.write('\n'.join(report_lines))
        
        logger.info(f"Report generated: {output_path}")
        return output_path
    
    def save_json_results(self, output_path: Optional[str] = None):
        """Save all moments as JSON for further analysis"""
        # Generate unique filename with datetime if no path specified
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if output_path is None:
            # Create in the game_moments directory
            game_moments_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "game_moments")
            os.makedirs(game_moments_dir, exist_ok=True)
            
            # Use results folder name in the file name
            results_name = os.path.basename(os.path.normpath(str(self.results_folder)))
            output_path = os.path.join(game_moments_dir, f"{results_name}_data_{timestamp}.json")
        
        # Prepare the moments data
        moments_data = []
        for moment in self.moments:
            moment_dict = asdict(moment)
            # Remove raw data for cleaner JSON
            moment_dict.pop('raw_messages', None)
            moment_dict.pop('raw_orders', None)
            # Keep diary context but limit size
            if 'diary_context' in moment_dict:
                for power, diary in moment_dict['diary_context'].items():
                    moment_dict['diary_context'][power] = diary  # Include full diary content
            moments_data.append(moment_dict)
        
        # Create the final data structure with metadata
        full_data = {
            "metadata": {
                "timestamp": timestamp,
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source_folder": str(self.results_folder),
                "analysis_model": self.model_name,
                "total_moments": len(self.moments),
                "moment_categories": {
                    "betrayals": len([m for m in self.moments if m.category == "BETRAYAL"]),
                    "collaborations": len([m for m in self.moments if m.category == "COLLABORATION"]),
                    "playing_both_sides": len([m for m in self.moments if m.category == "PLAYING_BOTH_SIDES"]),
                    "brilliant_strategies": len([m for m in self.moments if m.category == "BRILLIANT_STRATEGY"]),
                    "strategic_blunders": len([m for m in self.moments if m.category == "STRATEGIC_BLUNDER"])
                },
                "score_distribution": {
                    "scores_9_10": len([m for m in self.moments if m.interest_score >= 9]),
                    "scores_7_8": len([m for m in self.moments if 7 <= m.interest_score < 9]),
                    "scores_4_6": len([m for m in self.moments if 4 <= m.interest_score < 7]),
                    "scores_1_3": len([m for m in self.moments if m.interest_score < 4])
                }
            },
            "power_models": self.power_to_model,
            "invalid_moves_by_model": self.invalid_moves_by_model,
            "lies_by_model": self.lies_by_model,
            "moments": moments_data,
            "lies": [asdict(lie) for lie in self.lies]
        }
        
        # Write to file
        with open(output_path, 'w') as f:
            json.dump(full_data, f, indent=2)
        
        logger.info(f"JSON results saved: {output_path}")
        return output_path

async def main():
    parser = argparse.ArgumentParser(description="Analyze Diplomacy game for key strategic moments")
    parser.add_argument("results_folder", help="Path to the results folder containing lmvsgame.json and overview.jsonl")
    parser.add_argument("--model", default="openrouter-google/gemini-2.5-flash-preview",
                        help="Model to use for analysis")
    parser.add_argument("--report", default=None,
                        help="Output path for markdown report (auto-generates timestamped name if not specified)")
    parser.add_argument("--json", default=None,
                        help="Output path for JSON results (auto-generates timestamped name if not specified)")
    parser.add_argument("--max-phases", type=int, default=None,
                        help="Maximum number of phases to analyze (useful for testing)")
    parser.add_argument("--max-concurrent", type=int, default=5,
                        help="Maximum number of concurrent phase analyses (default: 5)")
    
    args = parser.parse_args()
    
    # Ensure the game_moments directory exists
    game_moments_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "game_moments")
    os.makedirs(game_moments_dir, exist_ok=True)
    
    # Extract game name from the results folder
    results_folder_name = os.path.basename(os.path.normpath(args.results_folder))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create default report and JSON paths in the game_moments directory
    if args.report is None:
        args.report = os.path.join(game_moments_dir, f"{results_folder_name}_report_{timestamp}.md")
    
    if args.json is None:
        args.json = os.path.join(game_moments_dir, f"{results_folder_name}_data_{timestamp}.json")
    
    analyzer = GameAnalyzer(args.results_folder, args.model)
    
    try:
        await analyzer.initialize()
        await analyzer.analyze_game(max_phases=args.max_phases, max_concurrent=args.max_concurrent)
        report_path = await analyzer.generate_report(args.report)
        json_path = analyzer.save_json_results(args.json)
        
        # Print summary
        print(f"\nAnalysis Complete!")
        print(f"Found {len(analyzer.moments)} key moments")
        print(f"Report saved to: {report_path}")
        print(f"JSON data saved to: {json_path}")
        
        # Show score distribution
        print("\nScore Distribution:")
        print(f"  Scores 9-10: {len([m for m in analyzer.moments if m.interest_score >= 9])}")
        print(f"  Scores 7-8: {len([m for m in analyzer.moments if 7 <= m.interest_score < 9])}")
        print(f"  Scores 4-6: {len([m for m in analyzer.moments if 4 <= m.interest_score < 7])}")
        print(f"  Scores 1-3: {len([m for m in analyzer.moments if m.interest_score < 4])}")
        
        # Show top 3 moments
        print("\nTop 3 Most Interesting Moments:")
        for i, moment in enumerate(analyzer.moments[:3], 1):
            powers_str = ', '.join([analyzer.format_power_with_model(p) for p in moment.powers_involved])
            print(f"{i}. {moment.category} in {moment.phase} (Score: {moment.interest_score})")
            print(f"   Powers: {powers_str}")
            print(f"   Impact: {moment.impact[:100]}...")
            print()
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())