import os
import json
import re
import logging
import ast  # For literal_eval in JSON fallback parsing
import aiohttp  # For direct HTTP requests to Responses API

from typing import List, Dict, Optional, Tuple, NamedTuple
from dotenv import load_dotenv

# Use Async versions of clients
from openai import AsyncOpenAI
from openai import AsyncOpenAI as AsyncDeepSeekOpenAI  # Alias for clarity
from anthropic import AsyncAnthropic
import asyncio
import requests
from enum import StrEnum

import google.generativeai as genai
from together import AsyncTogether
from together.error import APIError as TogetherAPIError  # For specific error handling

from config import config
from .game_history import GameHistory
from .utils import load_prompt, run_llm_and_log, log_llm_response, log_llm_response_async, generate_random_seed, get_prompt_path

# Import DiplomacyAgent for type hinting if needed, but avoid circular import if possible
from .prompt_constructor import construct_order_generation_prompt, build_context_prompt
# Moved formatter imports to avoid circular import - imported locally where needed

# set logger back to just info
logger = logging.getLogger("client")
logger.setLevel(logging.DEBUG)  # Keep debug for now during async changes
# Note: BasicConfig might conflict if already configured in lm_game. Keep client-specific for now.
# logging.basicConfig(level=logging.DEBUG) # Might be redundant if lm_game configures root

load_dotenv()


##############################################################################
# 1) Base Interface
##############################################################################
class BaseModelClient:
    """
    Base interface for any LLM client we want to plug in.
    Each must provide:
      - generate_response(prompt: str) -> str
      - get_orders(board_state, power_name, possible_orders) -> List[str]
      - get_conversation_reply(power_name, conversation_so_far, game_phase) -> str
    """

    def __init__(self, model_name: str, prompts_dir: Optional[str] = None):
        self.model_name = model_name
        self.prompts_dir = prompts_dir
        logger.info(f"[{model_name}] BaseModelClient initialized with prompts_dir: {prompts_dir}")
        # Load a default initially, can be overwritten by set_system_prompt
        self.system_prompt = load_prompt("system_prompt.txt", prompts_dir=self.prompts_dir)
        self.max_tokens = 16000  # default unless overridden

    def set_system_prompt(self, content: str):
        """Allows updating the system prompt after initialization."""
        self.system_prompt = content
        logger.info(f"[{self.model_name}] System prompt updated.")

    async def generate_response(self, prompt: str, temperature: float = 0.0, inject_random_seed: bool = True) -> str:
        """
        Returns a raw string from the LLM.
        Subclasses override this.
        """
        raise NotImplementedError("Subclasses must implement generate_response().")

    # build_context_prompt and build_prompt (now construct_order_generation_prompt)
    # have been moved to prompt_constructor.py

    async def get_orders(
        self,
        game,
        board_state,
        power_name: str,
        possible_orders: Dict[str, List[str]],
        conversation_text: str,  # This is GameHistory
        model_error_stats: dict,
        log_file_path: str,
        phase: str,
        agent_goals: Optional[List[str]] = None,
        agent_relationships: Optional[Dict[str, str]] = None,
        agent_private_diary_str: Optional[str] = None,  # Added
    ) -> List[str]:
        """
        1) Builds the prompt with conversation context if available
        2) Calls LLM
        3) Parses JSON block
        """
        # The 'conversation_text' parameter was GameHistory. Renaming for clarity.
        game_history_obj = conversation_text

        prompt = construct_order_generation_prompt(
            system_prompt=self.system_prompt,
            game=game,
            board_state=board_state,
            power_name=power_name,
            possible_orders=possible_orders,
            game_history=game_history_obj,  # Pass GameHistory object
            agent_goals=agent_goals,
            agent_relationships=agent_relationships,
            agent_private_diary_str=agent_private_diary_str,
            prompts_dir=self.prompts_dir,
        )

        raw_response = ""
        # Initialize success status. Will be updated based on outcome.
        success_status = "Failure: Initialized"
        parsed_orders_for_return = self.fallback_orders(possible_orders)  # Default to fallback

        try:
            # Call LLM using the logging wrapper
            raw_response = await run_llm_and_log(
                client=self,
                prompt=prompt,
                power_name=power_name,
                phase=phase,
                response_type="order",  # Context for run_llm_and_log's own error logging
                temperature=0,
            )
            logger.debug(f"[{self.model_name}] Raw LLM response for {power_name} orders:\n{raw_response}")

            # Conditionally format the response based on USE_UNFORMATTED_PROMPTS
            if config.USE_UNFORMATTED_PROMPTS:
                # Local import to avoid circular dependency
                from .formatter import format_with_gemini_flash, FORMAT_ORDERS

                # Format the natural language response into structured format
                formatted_response = await format_with_gemini_flash(
                    raw_response, FORMAT_ORDERS, power_name=power_name, phase=phase, log_file_path=log_file_path
                )
            else:
                # Use the raw response directly (already formatted)
                formatted_response = raw_response

            # Attempt to parse the final "orders" from the formatted response
            move_list = self._extract_moves(formatted_response, power_name)

            if not move_list:
                logger.warning(f"[{self.model_name}] Could not extract moves for {power_name}. Using fallback.")
                if model_error_stats is not None and self.model_name in model_error_stats:
                    model_error_stats[self.model_name].setdefault("order_decoding_errors", 0)
                    model_error_stats[self.model_name]["order_decoding_errors"] += 1
                success_status = "Failure: No moves extracted"
                # Fallback is already set to parsed_orders_for_return
            else:
                # Validate or fallback
                validated_moves, invalid_moves_list = self._validate_orders(move_list, possible_orders)
                logger.debug(f"[{self.model_name}] Validated moves for {power_name}: {validated_moves}")
                parsed_orders_for_return = validated_moves
                if invalid_moves_list:
                    # Truncate if too many invalid moves to keep log readable
                    max_invalid_to_log = 5
                    display_invalid_moves = invalid_moves_list[:max_invalid_to_log]
                    omitted_count = len(invalid_moves_list) - len(display_invalid_moves)

                    invalid_moves_str = ", ".join(display_invalid_moves)
                    if omitted_count > 0:
                        invalid_moves_str += f", ... ({omitted_count} more)"

                    success_status = f"Failure: Invalid LLM Moves ({len(invalid_moves_list)}): {invalid_moves_str}"
                    # If some moves were validated despite others being invalid, it's still not a full 'Success'
                    # because the LLM didn't provide a fully usable set of orders without intervention/fallbacks.
                    # The fallback_orders logic within _validate_orders might fill in missing pieces,
                    # but the key is that the LLM *proposed* invalid moves.
                    if not validated_moves:  # All LLM moves were invalid
                        logger.warning(f"[{power_name}] All LLM-proposed moves were invalid. Using fallbacks. Invalid: {invalid_moves_list}")
                    else:
                        logger.info(f"[{power_name}] Some LLM-proposed moves were invalid. Using fallbacks/validated. Invalid: {invalid_moves_list}")
                else:
                    success_status = "Success"

        except Exception as e:
            logger.error(f"[{self.model_name}] LLM error for {power_name} in get_orders: {e}", exc_info=True)
            success_status = f"Failure: Exception ({type(e).__name__})"
            # Fallback is already set to parsed_orders_for_return
        finally:
            # Log the attempt regardless of outcome
            if log_file_path:  # Only log if a path is provided
                await log_llm_response_async(
                    log_file_path=log_file_path,
                    model_name=self.model_name,
                    power_name=power_name,
                    phase=phase,
                    response_type="order_generation",  # Specific type for CSV logging
                    raw_input_prompt=prompt,  # Renamed from 'prompt' to match log_llm_response arg
                    raw_response=raw_response,
                    success=success_status,
                    # token_usage and cost can be added later if available and if log_llm_response supports them
                )
        return parsed_orders_for_return

    def _extract_moves(self, raw_response: str, power_name: str) -> Optional[List[str]]:
        """
        Attempt multiple parse strategies to find JSON array of moves.

        1. Regex for PARSABLE OUTPUT lines.
        2. If that fails, also look for fenced code blocks with { ... }.
        3. Attempt bracket-based fallback if needed.

        Returns a list of move strings or None if everything fails.
        """
        # 1) Regex for "PARSABLE OUTPUT:{...}"
        pattern = r"PARSABLE OUTPUT:\s*(\{[\s\S]*\})"
        matches = re.search(pattern, raw_response, re.DOTALL)

        if not matches:
            # Some LLMs might not put the colon or might have triple backtick fences.
            logger.debug(f"[{self.model_name}] Regex parse #1 failed for {power_name}. Trying alternative patterns.")

            # 1b) Check for inline JSON after "PARSABLE OUTPUT"
            pattern_alt = r"PARSABLE OUTPUT\s*\{(.*?)\}\s*$"
            matches = re.search(pattern_alt, raw_response, re.DOTALL)

        if not matches:
            # 1c) Check for **PARSABLE OUTPUT:** pattern (with asterisks)
            logger.debug(f"[{self.model_name}] Regex parse #2 failed for {power_name}. Trying asterisk-wrapped pattern.")
            pattern_asterisk = r"\*\*PARSABLE OUTPUT:\*\*\s*(\{[\s\S]*?\})"
            matches = re.search(pattern_asterisk, raw_response, re.DOTALL)

        if not matches:
            logger.debug(f"[{self.model_name}] Regex parse #3 failed for {power_name}. Trying triple-backtick code fences.")

        # 2) If still no match, check for triple-backtick code fences containing JSON
        if not matches:
            code_fence_pattern = r"```json\n(.*?)\n```"
            matches = re.search(code_fence_pattern, raw_response, re.DOTALL)
            if matches:
                logger.debug(f"[{self.model_name}] Found triple-backtick JSON block for {power_name}.")

        # 2b) Also try plain ``` code fences without json marker
        if not matches:
            code_fence_plain = r"```\n(.*?)\n```"
            matches = re.search(code_fence_plain, raw_response, re.DOTALL)
            if matches:
                logger.debug(f"[{self.model_name}] Found plain triple-backtick block for {power_name}.")

        # 2c) Try to find bare JSON object anywhere in the response
        if not matches:
            logger.debug(f"[{self.model_name}] No explicit markers found for {power_name}. Looking for bare JSON.")
            # Look for a JSON object that contains "orders" key
            bare_json_pattern = r'(\{[^{}]*"orders"\s*:\s*\[[^\]]*\][^{}]*\})'
            matches = re.search(bare_json_pattern, raw_response, re.DOTALL)
            if matches:
                logger.debug(f"[{self.model_name}] Found bare JSON object with 'orders' key for {power_name}.")

        # 3) Attempt to parse JSON if we found anything
        json_text = None
        if matches:
            # Add braces back around the captured group if needed
            captured = matches.group(1).strip()
            if captured.startswith(r"{{"):
                json_text = captured[1:-1]
            elif captured.startswith(r"{"):
                json_text = captured
            else:
                json_text = "{%s}" % captured

            json_text = json_text.strip()

        if not json_text:
            logger.debug(f"[{self.model_name}] No JSON text found in LLM response for {power_name}.")
            return None

        # 3a) Try JSON loading
        try:
            data = json.loads(json_text)
            return data.get("orders", None)
        except json.JSONDecodeError as e:
            logger.warning(f"[{self.model_name}] JSON decode failed for {power_name}: {e}. Trying to fix common issues.")

            # Try to fix common JSON issues
            try:
                # Remove trailing commas
                fixed_json = re.sub(r",\s*([\}\]])", r"\1", json_text)
                # Fix single quotes to double quotes
                fixed_json = fixed_json.replace("'", '"')
                # Try parsing again
                data = json.loads(fixed_json)
                logger.info(f"[{self.model_name}] Successfully parsed JSON after fixes for {power_name}")
                return data.get("orders", None)
            except json.JSONDecodeError:
                logger.warning(f"[{self.model_name}] JSON decode still failed after fixes for {power_name}. Trying to remove inline comments.")

                # Try to remove inline comments (// style)
                try:
                    # Remove // comments from each line
                    lines = json_text.split("\n")
                    cleaned_lines = []
                    for line in lines:
                        # Find // that's not inside quotes
                        comment_pos = -1
                        in_quotes = False
                        escape_next = False
                        for i, char in enumerate(line):
                            if escape_next:
                                escape_next = False
                                continue
                            if char == "\\":
                                escape_next = True
                                continue
                            if char == '"' and not escape_next:
                                in_quotes = not in_quotes
                            if not in_quotes and line[i : i + 2] == "//":
                                comment_pos = i
                                break

                        if comment_pos >= 0:
                            # Remove comment but keep any trailing comma
                            cleaned_line = line[:comment_pos].rstrip()
                        else:
                            cleaned_line = line
                        cleaned_lines.append(cleaned_line)

                    comment_free_json = "\n".join(cleaned_lines)
                    # Also remove trailing commas after comment removal
                    comment_free_json = re.sub(r",\s*([\}\]])", r"\1", comment_free_json)

                    data = json.loads(comment_free_json)
                    logger.info(f"[{self.model_name}] Successfully parsed JSON after removing inline comments for {power_name}")
                    return data.get("orders", None)
                except json.JSONDecodeError:
                    logger.warning(f"[{self.model_name}] JSON decode still failed after removing comments for {power_name}. Trying bracket fallback.")

        # 3b) Attempt bracket fallback: we look for the substring after "orders"
        #     E.g. "orders: ['A BUD H']" and parse it. This is risky but can help with minor JSON format errors.
        #     We only do this if we see something like "orders": ...
        bracket_pattern = r'["\']orders["\']\s*:\s*\[([^\]]*)\]'
        bracket_match = re.search(bracket_pattern, json_text, re.DOTALL)
        if bracket_match:
            try:
                raw_list_str = "[" + bracket_match.group(1).strip() + "]"
                moves = ast.literal_eval(raw_list_str)
                if isinstance(moves, list):
                    return moves
            except Exception as e2:
                logger.warning(f"[{self.model_name}] Bracket fallback parse also failed for {power_name}: {e2}")

        # If all attempts failed
        return None

    def _validate_orders(self, moves: List[str], possible_orders: Dict[str, List[str]]) -> Tuple[List[str], List[str]]:  # MODIFIED RETURN TYPE
        """
        Filter out invalid moves, fill missing with HOLD, else fallback.
        Returns a tuple: (validated_moves, invalid_moves_found)
        """
        logger.debug(f"[{self.model_name}] Proposed LLM moves: {moves}")
        validated = []
        invalid_moves_found = []  # ADDED: To collect invalid moves
        used_locs = set()

        if not isinstance(moves, list):
            logger.debug(f"[{self.model_name}] Moves not a list, fallback.")
            # Return fallback and empty list for invalid_moves_found as no specific LLM moves were processed
            return self.fallback_orders(possible_orders), []

        for move_str in moves:
            # Check if it's in possible orders
            if any(move_str in loc_orders for loc_orders in possible_orders.values()):
                validated.append(move_str)
                parts = move_str.split()
                if len(parts) >= 2:
                    used_locs.add(parts[1][:3])
            else:
                logger.debug(f"[{self.model_name}] Invalid move from LLM: {move_str}")
                invalid_moves_found.append(move_str)  # ADDED: Collect invalid move

        # Fill missing with hold
        for loc, orders_list in possible_orders.items():
            if loc not in used_locs and orders_list:
                hold_candidates = [o for o in orders_list if o.endswith("H")]
                validated.append(hold_candidates[0] if hold_candidates else orders_list[0])

        if not validated and not invalid_moves_found:  # Only if LLM provided no valid moves and no invalid moves (e.g. empty list from LLM)
            logger.warning(f"[{self.model_name}] No valid LLM moves provided and no invalid ones to report. Using fallback.")
            return self.fallback_orders(possible_orders), []
        elif not validated and invalid_moves_found:  # All LLM moves were invalid
            logger.warning(
                f"[{self.model_name}] All LLM moves invalid ({len(invalid_moves_found)} found), using fallback. Invalid: {invalid_moves_found}"
            )
            # We return empty list for validated, but the invalid_moves_found list is populated
            return self.fallback_orders(possible_orders), invalid_moves_found

        # If we have some validated moves, return them along with any invalid ones found
        return validated, invalid_moves_found

    def fallback_orders(self, possible_orders: Dict[str, List[str]]) -> List[str]:
        """
        Just picks HOLD if possible, else first option.
        """
        fallback = []
        for loc, orders_list in possible_orders.items():
            if orders_list:
                holds = [o for o in orders_list if o.endswith("H")]
                fallback.append(holds[0] if holds else orders_list[0])
        return fallback

    def build_planning_prompt(
        self,
        game,
        board_state,
        power_name: str,
        possible_orders: Dict[str, List[str]],
        game_history: GameHistory,
        # game_phase: str, # Not used directly by build_context_prompt
        # log_file_path: str, # Not used directly by build_context_prompt
        agent_goals: Optional[List[str]] = None,
        agent_relationships: Optional[Dict[str, str]] = None,
        agent_private_diary_str: Optional[str] = None,  # Added
    ) -> str:
        instructions = load_prompt("planning_instructions.txt", prompts_dir=self.prompts_dir)

        context = self.build_context_prompt(
            game,
            board_state,
            power_name,
            possible_orders,
            game_history,
            agent_goals=agent_goals,
            agent_relationships=agent_relationships,
            agent_private_diary=agent_private_diary_str,  # Pass diary string
            prompts_dir=self.prompts_dir,
        )

        return context + "\n\n" + instructions

    def build_conversation_prompt(
        self,
        game,
        board_state,
        power_name: str,
        possible_orders: Dict[str, List[str]],
        game_history: GameHistory,
        # game_phase: str, # Not used directly by build_context_prompt
        # log_file_path: str, # Not used directly by build_context_prompt
        agent_goals: Optional[List[str]] = None,
        agent_relationships: Optional[Dict[str, str]] = None,
        agent_private_diary_str: Optional[str] = None,  # Added
        negotiation_round: Optional[int] = None,
        max_negotiation_rounds: Optional[int] = None,
    ) -> str:
        # MINIMAL CHANGE: Just change to load unformatted version conditionally
        # Check if country-specific prompts are enabled
        if config.COUNTRY_SPECIFIC_PROMPTS:
            # Try to load country-specific version first
            country_specific_file = get_prompt_path(f"conversation_instructions_{power_name.lower()}.txt")
            instructions = load_prompt(country_specific_file, prompts_dir=self.prompts_dir)
            
            # Fall back to generic if country-specific not found
            if not instructions:
                instructions = load_prompt(get_prompt_path("conversation_instructions.txt"), prompts_dir=self.prompts_dir)
        else:
            # Load generic conversation instructions
            instructions = load_prompt(get_prompt_path("conversation_instructions.txt"), prompts_dir=self.prompts_dir)
        
        logger.debug(f"[{power_name}] Conversation instructions: {instructions}")

        # KEEP ORIGINAL: Use build_context_prompt as before
        context = build_context_prompt(
            game,
            board_state,
            power_name,
            possible_orders,
            game_history,
            agent_goals=agent_goals,
            agent_relationships=agent_relationships,
            agent_private_diary=agent_private_diary_str,  # Pass diary string
            prompts_dir=self.prompts_dir,
        )
        # Insert negotiation round below Power and Phase when available
        if negotiation_round is not None and max_negotiation_rounds is not None:
            phase_pos = context.find("Phase:")
            if phase_pos != -1:
                end_of_line = context.find("\n", phase_pos)
                end_of_line = end_of_line if end_of_line != -1 else len(context)
                round_line = f"\nNegotiation round: round {negotiation_round} out of {max_negotiation_rounds}.\n"
                context = context[:end_of_line] + round_line + context[end_of_line:]

        logger.debug(f"[{power_name}] Conversation context: {context}")

        # KEEP ORIGINAL: Get recent messages targeting this power to prioritize responses
        recent_messages_to_power = game_history.get_recent_messages_to_power(power_name, limit=3)

        # KEEP ORIGINAL: Debug logging to verify messages
        logger.info(f"[{power_name}] Found {len(recent_messages_to_power)} high priority messages to respond to")
        if recent_messages_to_power:
            for i, msg in enumerate(recent_messages_to_power):
                logger.info(f"[{power_name}] Priority message {i + 1}: From {msg['sender']} in {msg['phase']}: {msg['content'][:50]}...")

        # KEEP ORIGINAL: Add a section for unanswered messages
        unanswered_messages = "\n\nRECENT MESSAGES REQUIRING YOUR ATTENTION:\n"
        if recent_messages_to_power:
            for msg in recent_messages_to_power:
                unanswered_messages += f"\nFrom {msg['sender']} in {msg['phase']}: {msg['content']}\n"
        else:
            unanswered_messages += "\nNo urgent messages requiring direct responses.\n"

        final_prompt = context + unanswered_messages + "\n\n" + instructions
        final_prompt = (
            final_prompt.replace("AUSTRIA", "Austria")
            .replace("ENGLAND", "England")
            .replace("FRANCE", "France")
            .replace("GERMANY", "Germany")
            .replace("ITALY", "Italy")
            .replace("RUSSIA", "Russia")
            .replace("TURKEY", "Turkey")
        )
        return final_prompt

    async def get_planning_reply(  # Renamed from get_plan to avoid conflict with get_plan in agent.py
        self,
        game,
        board_state,
        power_name: str,
        possible_orders: Dict[str, List[str]],
        game_history: GameHistory,
        game_phase: str,  # Used for logging
        log_file_path: str,  # Used for logging
        agent_goals: Optional[List[str]] = None,
        agent_relationships: Optional[Dict[str, str]] = None,
        agent_private_diary_str: Optional[str] = None,  # Added
    ) -> str:
        prompt = self.build_planning_prompt(
            game,
            board_state,
            power_name,
            possible_orders,
            game_history,
            # game_phase, # Not passed to build_planning_prompt directly
            # log_file_path, # Not passed to build_planning_prompt directly
            agent_goals=agent_goals,
            agent_relationships=agent_relationships,
            agent_private_diary_str=agent_private_diary_str,  # Pass diary string
        )

        # Call LLM using the logging wrapper
        raw_response = await run_llm_and_log(
            client=self,
            prompt=prompt,
            power_name=power_name,
            phase=game_phase,  # Use game_phase for logging
            response_type="plan_reply",  # Changed from 'plan' to avoid confusion
        )
        logger.debug(f"[{self.model_name}] Raw LLM response for {power_name} planning reply:\n{raw_response}")
        return raw_response

    async def get_conversation_reply(
        self,
        game,
        board_state,
        power_name: str,
        possible_orders: Dict[str, List[str]],
        game_history: GameHistory,
        game_phase: str,
        log_file_path: str,
        active_powers: Optional[List[str]] = None,
        agent_goals: Optional[List[str]] = None,
        agent_relationships: Optional[Dict[str, str]] = None,
        agent_private_diary_str: Optional[str] = None,
        negotiation_round: Optional[int] = None,
        max_negotiation_rounds: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        """
        Generates a negotiation message, considering agent state.
        """
        logger.debug(
            "get_conversation_reply inputs: game=%s, board_state type=%s (keys=%s), power_name=%s, "
            "possible_orders keys=%s, game_history=%s, game_phase=%s, log_file_path=%s, "
            "active_powers=%s, agent_goals=%s, agent_relationships=%s, agent_private_diary_str len=%s",
            type(game).__name__,
            type(board_state).__name__,
            list(board_state.keys()) if isinstance(board_state, dict) else "n/a",
            power_name,
            list(possible_orders.keys()) if possible_orders else [],
            type(game_history).__name__,
            game_phase,
            log_file_path,
            active_powers,
            agent_goals,
            agent_relationships,
            len(agent_private_diary_str) if agent_private_diary_str else 0,
        )
        raw_input_prompt = ""  # Initialize for finally block
        raw_response = ""  # Initialize for finally block
        success_status = "Failure: Initialized"  # Default status
        messages_to_return = []  # Initialize to ensure it's defined

        try:
            raw_input_prompt = self.build_conversation_prompt(
                game,
                board_state,
                power_name,
                possible_orders,
                game_history,
                agent_goals=agent_goals,
                agent_relationships=agent_relationships,
                agent_private_diary_str=agent_private_diary_str,
                negotiation_round=negotiation_round,
                max_negotiation_rounds=max_negotiation_rounds,
            )

            logger.debug(f"[{self.model_name}] Conversation prompt for {power_name}:\n{raw_input_prompt}")

            raw_response = await run_llm_and_log(
                client=self,
                prompt=raw_input_prompt,
                power_name=power_name,
                phase=game_phase,
                response_type="negotiation",  # For run_llm_and_log's internal context
            )
            logger.debug(f"[{self.model_name}] Raw LLM response for {power_name}:\n{raw_response}")

            # Conditionally format the response based on USE_UNFORMATTED_PROMPTS
            if config.USE_UNFORMATTED_PROMPTS:
                # Local import to avoid circular dependency
                from .formatter import format_with_gemini_flash, FORMAT_CONVERSATION

                # Format the natural language response into structured JSON
                formatted_response = await format_with_gemini_flash(
                    raw_response, FORMAT_CONVERSATION, power_name=power_name, phase=game_phase, log_file_path=log_file_path
                )
            else:
                # Use the raw response directly (already formatted)
                formatted_response = raw_response

            parsed_messages = []
            json_blocks = []
            json_decode_error_occurred = False

            # For formatted response, we expect a clean JSON array
            try:
                data = json.loads(formatted_response)
                if isinstance(data, list):
                    parsed_messages = data
                    json_blocks = [json.dumps(item) for item in data if isinstance(item, dict)]
                else:
                    logger.warning(f"[{self.model_name}] Formatted response is not a list")
            except json.JSONDecodeError:
                logger.warning(f"[{self.model_name}] Failed to parse formatted response as JSON, falling back to regex")
                # Fall back to original parsing logic using formatted_response
                raw_response = formatted_response

            # Original parsing logic as fallback
            if not parsed_messages:
                # Attempt to find blocks enclosed in {{...}}
                double_brace_blocks = re.findall(r"\{\{(.*?)\}\}", raw_response, re.DOTALL)
                if double_brace_blocks:
                    # If {{...}} blocks are found, assume each is a self-contained JSON object
                    json_blocks.extend(["{" + block.strip() + "}" for block in double_brace_blocks])
                else:
                    # If no {{...}} blocks, look for ```json ... ``` markdown blocks
                    code_block_match = re.search(r"```json\n(.*?)\n```", raw_response, re.DOTALL)
                    if code_block_match:
                        potential_json_array_or_objects = code_block_match.group(1).strip()
                        # Try to parse as a list of objects or a single object
                        try:
                            data = json.loads(potential_json_array_or_objects)
                            if isinstance(data, list):
                                json_blocks = [json.dumps(item) for item in data if isinstance(item, dict)]
                            elif isinstance(data, dict):
                                json_blocks = [json.dumps(data)]
                        except json.JSONDecodeError:
                            # If parsing the whole block fails, fall back to regex for individual objects
                            json_blocks = re.findall(r"\{.*?\}", potential_json_array_or_objects, re.DOTALL)
                    else:
                        # If no markdown block, fall back to regex for any JSON object in the response
                        json_blocks = re.findall(r"\{.*?\}", raw_response, re.DOTALL)

            # Process json_blocks if we have them from fallback parsing
            if not parsed_messages and json_blocks:
                for block_index, block in enumerate(json_blocks):
                    try:
                        cleaned_block = block.strip()
                        # Attempt to fix common JSON issues like trailing commas before parsing
                        cleaned_block = re.sub(r",\s*([\}\]])", r"\1", cleaned_block)
                        parsed_message = json.loads(cleaned_block)
                        parsed_messages.append(parsed_message)
                    except json.JSONDecodeError as e:
                        logger.warning(f"[{self.model_name}] Failed to parse JSON block {block_index} for {power_name}: {e}")
                        json_decode_error_occurred = True

            if not parsed_messages:
                logger.warning(f"[{self.model_name}] No valid messages found in response for {power_name}")
                success_status = "Success: No messages found"
                # messages_to_return remains empty
            else:
                # Validate parsed messages: only accept targeted (private) messages with recipient
                validated_messages = []
                for msg in parsed_messages:
                    if not isinstance(msg, dict) or "content" not in msg:
                        logger.warning(f"[{self.model_name}] Invalid message structure for {power_name}")
                        continue
                    if msg.get("message_type") != "private":
                        logger.debug(f"[{self.model_name}] Skipping non-private message from {power_name} (targeted only).")
                        continue
                    if "recipient" not in msg or not msg.get("recipient"):
                        logger.warning(f"[{self.model_name}] Private message missing recipient for {power_name}")
                        continue
                    validated_messages.append(msg)
                parsed_messages = validated_messages

            # Set final status and return value
            if parsed_messages:
                success_status = "Success: Messages extracted"
                messages_to_return = parsed_messages
            else:
                success_status = "Success: No valid messages"
                messages_to_return = []

            logger.debug(f"[{self.model_name}] Validated conversation replies for {power_name}: {messages_to_return}")
            # return messages_to_return # Return will happen in finally block or after

        except Exception as e:
            logger.error(f"[{self.model_name}] Error in get_conversation_reply for {power_name}: {e}", exc_info=True)
            success_status = f"Failure: Exception ({type(e).__name__})"
            messages_to_return = []  # Ensure empty list on general exception
        finally:
            if log_file_path:
                await log_llm_response_async(
                    log_file_path=log_file_path,
                    model_name=self.model_name,
                    power_name=power_name,
                    phase=game_phase,
                    response_type="negotiation_message",
                    raw_input_prompt=raw_input_prompt,
                    raw_response=raw_response,
                    success=success_status,
                )
            return messages_to_return

    async def get_plan(  # This is the original get_plan, now distinct from get_planning_reply
        self,
        game,
        board_state,
        power_name: str,
        # possible_orders: Dict[str, List[str]], # Not typically needed for high-level plan
        game_history: GameHistory,
        log_file_path: str,
        agent_goals: Optional[List[str]] = None,
        agent_relationships: Optional[Dict[str, str]] = None,
        agent_private_diary_str: Optional[str] = None,  # Added
    ) -> str:
        """
        Generates a strategic plan for the given power based on the current state.
        This method is called by the agent's generate_plan method.
        """
        logger.info(f"Client generating strategic plan for {power_name}...")

        planning_instructions = load_prompt("planning_instructions.txt", prompts_dir=self.prompts_dir)
        if not planning_instructions:
            logger.error("Could not load planning_instructions.txt! Cannot generate plan.")
            return "Error: Planning instructions not found."

        # For planning, possible_orders might be less critical for the context,
        # but build_context_prompt expects it. We can pass an empty dict or calculate it.
        # For simplicity, let's pass empty if not strictly needed by context for planning.
        possible_orders_for_context = {}  # game.get_all_possible_orders() if needed by context

        context_prompt = self.build_context_prompt(
            game,
            board_state,
            power_name,
            possible_orders_for_context,
            game_history,
            agent_goals=agent_goals,
            agent_relationships=agent_relationships,
            agent_private_diary=agent_private_diary_str,  # Pass diary string
            prompts_dir=self.prompts_dir,
        )

        full_prompt = f"{context_prompt}\n\n{planning_instructions}"
        if self.system_prompt:
            full_prompt = f"{self.system_prompt}\n\n{full_prompt}"

        raw_plan_response = ""
        success_status = "Failure: Initialized"
        plan_to_return = f"Error: Plan generation failed for {power_name} (initial state)"

        try:
            # Use run_llm_and_log for the actual LLM call
            raw_plan_response = await run_llm_and_log(
                client=self,  # Pass self (the client instance)
                prompt=full_prompt,
                power_name=power_name,
                phase=game.current_short_phase,
                response_type="plan_generation",  # More specific type for run_llm_and_log context
            )
            logger.debug(f"[{self.model_name}] Raw LLM response for {power_name} plan generation:\n{raw_plan_response}")
            # No parsing needed for the plan, return the raw string
            plan_to_return = raw_plan_response.strip()
            success_status = "Success"
        except Exception as e:
            logger.error(f"Failed to generate plan for {power_name}: {e}", exc_info=True)
            success_status = f"Failure: Exception ({type(e).__name__})"
            plan_to_return = f"Error: Failed to generate plan for {power_name} due to exception: {e}"
        finally:
            if log_file_path:  # Only log if a path is provided
                await log_llm_response_async(
                    log_file_path=log_file_path,
                    model_name=self.model_name,
                    power_name=power_name,
                    phase=game.current_short_phase if game else "UnknownPhase",
                    response_type="plan_generation",  # Specific type for CSV logging
                    raw_input_prompt=full_prompt,  # Renamed from 'full_prompt' to match log_llm_response arg
                    raw_response=raw_plan_response,
                    success=success_status,
                    # token_usage and cost can be added later
                )
        return plan_to_return


##############################################################################
# 2) Concrete Implementations
##############################################################################

class OpenAIClient(BaseModelClient):
    """Async client for OpenAI-compatible chat-completion endpoints."""

    def __init__(
        self,
        model_name: str,
        prompts_dir: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        super().__init__(model_name, prompts_dir=prompts_dir)

        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"

        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY missing and no inline key provided")

        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def generate_response(
        self,
        prompt: str,
        temperature: float = 0.0,
        inject_random_seed: bool = True,
    ) -> str:
        try:
            system_prompt_content = f"{generate_random_seed()}\n\n{self.system_prompt}" if inject_random_seed else self.system_prompt
            prompt_with_cta = f"{prompt}\n\nPROVIDE YOUR RESPONSE BELOW:"

            # Determine which parameter to use based on model
            completion_params = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt_content},
                    {"role": "user", "content": prompt_with_cta},
                ],
            }
            
            # Handle model-specific parameters
            # Check if model name starts with 'nectarine' or is in the specific list
            uses_max_completion_tokens = (
                self.model_name in ["o4-mini", "o3-mini", "o3", "gpt-4.1"] or
                self.model_name.startswith("nectarine")
            )
            
            if uses_max_completion_tokens:
                completion_params["max_completion_tokens"] = self.max_tokens
                # o4-mini, o3-mini, o3 only support default temperature of 1.0
                if self.model_name in ["o4-mini", "o3-mini", "o3"]:
                    completion_params["temperature"] = 1.0
                else:
                    completion_params["temperature"] = temperature
            else:
                completion_params["max_tokens"] = self.max_tokens
                completion_params["temperature"] = temperature
            
            response = await self.client.chat.completions.create(**completion_params)

            if (
                not response
                or not response.choices
                or not response.choices[0].message
                or not response.choices[0].message.content
            ):
                raise ValueError(f"[{self.model_name}] LLM returned an empty or invalid response.")

            return response.choices[0].message.content.strip()

        except json.JSONDecodeError as json_err:
            logger.error(f"[{self.model_name}] JSON decode error: {json_err}")
            raise
        except Exception as e:
            extra = ""
            try:
                from openai import OpenAIError  # runtime import avoids circulars
                if isinstance(e, OpenAIError):
                    status = getattr(e, "status_code", None)
                    resp  = getattr(e, "response", None)
                    if status:
                        extra += f" (status {status})"
                    if resp is not None:
                        try:
                            body = resp.json() if hasattr(resp, "json") else resp
                        except Exception:
                            body = str(resp)
                        body_str = (
                            json.dumps(body) if isinstance(body, (dict, list)) else str(body)
                        )
                        if len(body_str) > 3_000:
                            body_str = body_str[:3_000] + "…[truncated]"
                        extra += f" – body: {body_str}"
            except Exception:
                # best‑effort only; never mask original error
                pass

            logger.error(f"[{self.model_name}] OpenAI client error: {e}{extra}", exc_info=True)
            raise


class ClaudeClient(BaseModelClient):
    """
    For 'claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', etc.
    """

    def __init__(self, model_name: str, prompts_dir: Optional[str] = None):
        super().__init__(model_name, prompts_dir=prompts_dir)
        self.client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    async def generate_response(self, prompt: str, temperature: float = 0.0, inject_random_seed: bool = True) -> str:
        # Updated Claude messages format
        try:
            system_prompt_content = self.system_prompt
            if inject_random_seed:
                random_seed = generate_random_seed()
                system_prompt_content = f"{random_seed}\n\n{self.system_prompt}"

            response = await self.client.messages.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                system=system_prompt_content,  # system is now a top-level parameter
                messages=[{"role": "user", "content": prompt + "\n\nPROVIDE YOUR RESPONSE BELOW:"}],
                temperature=temperature,
            )
            if not response.content or not response.content[0].text:
                raise ValueError(f"[{self.model_name}] LLM returned an empty or invalid response.")
            return response.content[0].text.strip()
        except json.JSONDecodeError as json_err:
            logger.error(f"[{self.model_name}] JSON decoding failed in generate_response: {json_err}")
            raise
        except Exception as e:
            extra = ""
            try:
                import anthropic
                if isinstance(e, anthropic.errors.APIStatusError):
                    extra += f" (status {e.status_code})"
                    body = getattr(e, "response_json", None)
                    if body:
                        body_str = json.dumps(body)
                        if len(body_str) > 3_000:
                            body_str = body_str[:3_000] + "…[truncated]"
                        extra += f" – body: {body_str}"
            except Exception:
                pass

            logger.error(f"[{self.model_name}] Claude client error: {e}{extra}", exc_info=True)
            raise


class GeminiClient(BaseModelClient):
    """
    For 'gemini-1.5-flash' or other Google Generative AI models.
    """

    def __init__(self, model_name: str, prompts_dir: Optional[str] = None):
        super().__init__(model_name, prompts_dir=prompts_dir)
        # Configure and get the model (corrected initialization)
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(model_name)
        logger.debug(f"[{self.model_name}] Initialized Gemini client (genai.GenerativeModel)")

    async def generate_response(self, prompt: str, temperature: float = 0.0, inject_random_seed: bool = True) -> str:
        system_prompt_content = self.system_prompt
        if inject_random_seed:
            random_seed = generate_random_seed()
            system_prompt_content = f"{random_seed}\n\n{self.system_prompt}"

        full_prompt = system_prompt_content + prompt + "\n\nPROVIDE YOUR RESPONSE BELOW:"

        try:
            generation_config = genai.types.GenerationConfig(temperature=temperature, max_output_tokens=self.max_tokens)
            response = await self.client.generate_content_async(
                contents=full_prompt,
                generation_config=generation_config,
            )

            if not response or not response.text:
                raise ValueError(f"[{self.model_name}] LLM returned an empty or invalid response.")
            return response.text.strip()
        except Exception as e:
            # Gemini’s sdk wraps grpc errors; include full message
            msg = str(e)
            if len(msg) > 3_000:
                msg = msg[:3_000] + "…[truncated]"
            logger.error(f"[{self.model_name}] Gemini client error: {msg}", exc_info=True)
            raise


class DeepSeekClient(BaseModelClient):
    """
    For DeepSeek R1 'deepseek-reasoner'
    """

    def __init__(self, model_name: str, prompts_dir: Optional[str] = None):
        super().__init__(model_name, prompts_dir=prompts_dir)
        self.api_key = os.environ.get("DEEPSEEK_API_KEY")
        self.client = AsyncDeepSeekOpenAI(api_key=self.api_key, base_url="https://api.deepseek.com/")

    async def generate_response(self, prompt: str, temperature: float = 0.0, inject_random_seed: bool = True) -> str:
        try:
            # Append the call to action to the user's prompt
            prompt_with_cta = prompt + "\n\nPROVIDE YOUR RESPONSE BELOW:"

            system_prompt_content = self.system_prompt
            if inject_random_seed:
                random_seed = generate_random_seed()
                system_prompt_content = f"{random_seed}\n\n{self.system_prompt}"

            # Determine which parameter to use based on model
            completion_params = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt_content},
                    {"role": "user", "content": prompt_with_cta},
                ],
                "stream": False,
                "temperature": temperature,
            }
            
            # Use max_completion_tokens for o4-mini, o3-mini models and nectarine models
            if self.model_name in ["o4-mini", "o3-mini"] or self.model_name.startswith("nectarine"):
                completion_params["max_completion_tokens"] = self.max_tokens
            else:
                completion_params["max_tokens"] = self.max_tokens
            
            response = await self.client.chat.completions.create(**completion_params)

            logger.debug(f"[{self.model_name}] Raw DeepSeek response:\n{response}")

            if not response or not response.choices or not response.choices[0].message.content:
                raise ValueError(f"[{self.model_name}] LLM returned an empty or invalid response.")

            content = response.choices[0].message.content.strip()
            return content

        except Exception as e:
            extra = ""
            try:
                from openai import OpenAIError
                if isinstance(e, OpenAIError):
                    status = getattr(e, "status_code", None)
                    if status:
                        extra += f" (status {status})"
                    resp = getattr(e, "response", None)
                    if resp is not None:
                        try:
                            body = resp.json() if hasattr(resp, "json") else resp
                        except Exception:
                            body = str(resp)
                        body_str = (
                            json.dumps(body) if isinstance(body, (dict, list)) else str(body)
                        )
                        if len(body_str) > 3_000:
                            body_str = body_str[:3_000] + "…[truncated]"
                        extra += f" – body: {body_str}"
            except Exception:
                pass

            logger.error(f"[{self.model_name}] DeepSeek client error: {e}{extra}", exc_info=True)
            raise


class OpenAIResponsesClient(BaseModelClient):
    """
    For OpenAI o3-pro model using the new Responses API endpoint.
    This client makes direct HTTP requests to the v1/responses endpoint.
    """

    def __init__(self, model_name: str, prompts_dir: Optional[str] = None, api_key: Optional[str] = None, reasoning_effort: Optional[str] = None):
        super().__init__(model_name, prompts_dir=prompts_dir)
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        self.base_url = "https://api.openai.com/v1/responses"
        self._session = None  # Lazy initialization for connection pooling
        self.reasoning_effort = reasoning_effort  # For models that support reasoning effort
        logger.info(f"[{self.model_name}] Initialized OpenAI Responses API client with reasoning_effort={reasoning_effort}")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session for connection pooling."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def generate_response(self, prompt: str, temperature: float = 0.0, inject_random_seed: bool = True) -> str:
        try:
            # The Responses API uses a different format than chat completions
            # Combine system prompt and user prompt into a single input
            system_prompt_content = self.system_prompt
            if inject_random_seed:
                random_seed = generate_random_seed()
                system_prompt_content = f"{random_seed}\n\n{self.system_prompt}"

            full_prompt = f"{system_prompt_content}\n\n{prompt}\n\nPROVIDE YOUR RESPONSE BELOW:"

            # Prepare the request payload
            payload = {
                "model": self.model_name,
                "input": full_prompt,
            }

            # The Responses API uses max_output_tokens for all models
            payload["max_output_tokens"] = self.max_tokens
            
            # Only add temperature for models that support it
            models_without_temp = ['o3', 'o4-mini', 'gpt-5-reasoning-alpha-2025-07-19', 'nectarine-alpha-2025-07-25', 'nectarine-alpha-new-reasoning-effort-2025-07-25']
            if self.model_name not in models_without_temp:
                payload["temperature"] = temperature

            # Add reasoning effort for models that support it
            reasoning_models = ['gpt-5-reasoning-alpha-2025-07-19', 'o4-mini', 'nectarine-alpha-2025-07-25', 'o4-mini-alpha-2025-07-11', 'nectarine-alpha-new-reasoning-effort-2025-07-25']
            if self.reasoning_effort and self.model_name in reasoning_models:
                payload["reasoning"] = {"effort": self.reasoning_effort}

            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}

            # Make the API call using the pooled session
            session = await self._get_session()
            async with session.post(self.base_url, json=payload, headers=headers) as response:
                response.raise_for_status()  # Will raise for non-2xx responses
                response_data = await response.json()

                # Extract the text from the nested response structure
                try:
                    outputs = response_data.get("output", [])
                    if len(outputs) < 2:
                        # Log the actual response for debugging
                        logger.error(f"[{self.model_name}] Response structure: {json.dumps(response_data, indent=2)}")
                        raise ValueError(f"[{self.model_name}] Unexpected output structure: 'output' list has < 2 items.")

                    message_output = outputs[1]
                    if message_output.get("type") != "message":
                        raise ValueError(f"[{self.model_name}] Expected 'message' type in output[1], got '{message_output.get('type')}'.")

                    content_list = message_output.get("content", [])
                    if not content_list:
                        raise ValueError(f"[{self.model_name}] Empty 'content' list in message output.")

                    text_content = ""
                    for content_item in content_list:
                        if content_item.get("type") == "output_text":
                            text_content = content_item.get("text", "")
                            break

                    if not text_content:
                        raise ValueError(f"[{self.model_name}] No 'output_text' found in content or it was empty.")

                    return text_content.strip()

                except (KeyError, IndexError, TypeError) as e:
                    # Wrap parsing error in a more informative exception
                    raise ValueError(f"[{self.model_name}] Error parsing response structure: {e}") from e

        except aiohttp.ClientError as e:
            logger.error(f"[{self.model_name}] HTTP client error in generate_response: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.model_name}] Unexpected error in generate_response: {e}")
            raise


class OpenRouterClient(BaseModelClient):
    """
    For OpenRouter models, with default being 'openrouter/quasar-alpha'
    """

    def __init__(self, model_name: str = "openrouter/quasar-alpha", prompts_dir: Optional[str] = None):
        # Allow specifying just the model identifier or the full path
        if not model_name.startswith("openrouter/") and "/" not in model_name:
            model_name = f"openrouter/{model_name}"
        if model_name.startswith("openrouter-"):
            model_name = model_name.replace("openrouter-", "")

        super().__init__(model_name, prompts_dir=prompts_dir)
        self.api_key = os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")

        self.client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=self.api_key)

        logger.debug(f"[{self.model_name}] Initialized OpenRouter client")

    async def generate_response(self, prompt: str, temperature: float = 0.0, inject_random_seed: bool = True) -> str:
        """Generate a response using OpenRouter with robust error handling."""
        try:
            # Append the call to action to the user's prompt
            prompt_with_cta = prompt + "\n\nPROVIDE YOUR RESPONSE BELOW:"

            system_prompt_content = self.system_prompt
            if inject_random_seed:
                random_seed = generate_random_seed()
                system_prompt_content = f"{random_seed}\n\n{self.system_prompt}"

            # Prepare standard OpenAI-compatible request
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "system", "content": system_prompt_content}, {"role": "user", "content": prompt_with_cta}],
                max_tokens=self.max_tokens,
                temperature=temperature,
            )

            if not response.choices or not response.choices[0].message.content:
                raise ValueError(f"[{self.model_name}] LLM returned an empty or invalid response.")

            content = response.choices[0].message.content.strip()
            return content

        except Exception as e:
            extra = ""
            try:
                from openai import OpenAIError
                if isinstance(e, OpenAIError):
                    status = getattr(e, "status_code", None)
                    if status:
                        extra += f" (status {status})"
                    resp = getattr(e, "response", None)
                    if resp is not None:
                        try:
                            body = resp.json() if hasattr(resp, "json") else resp
                        except Exception:
                            body = str(resp)
                        body_str = (
                            json.dumps(body) if isinstance(body, (dict, list)) else str(body)
                        )
                        if len(body_str) > 3_000:
                            body_str = body_str[:3_000] + "…[truncated]"
                        extra += f" – body: {body_str}"
            except Exception:
                pass

            logger.error(f"[{self.model_name}] OpenRouter client error: {e}{extra}", exc_info=True)
            raise


##############################################################################
# TogetherAI Client
##############################################################################
class TogetherAIClient(BaseModelClient):
    """
    Client for Together AI models.
    Model names should be passed without the 'together-' prefix.
    """

    def __init__(self, model_name: str, prompts_dir: Optional[str] = None):
        super().__init__(model_name, prompts_dir=prompts_dir)  # model_name here is the actual Together AI model identifier
        self.api_key = os.environ.get("TOGETHER_API_KEY")
        if not self.api_key:
            raise ValueError("TOGETHER_API_KEY environment variable is required for TogetherAIClient")

        # The model_name passed to super() is used for logging and identification.
        # The actual model name for the API call is self.model_name (from super class).
        self.client = AsyncTogether(api_key=self.api_key)
        logger.info(f"[{self.model_name}] Initialized TogetherAI client for model: {self.model_name}")

    async def generate_response(self, prompt: str) -> str:
        """
        Generates a response from the Together AI model.
        """
        logger.debug(f"[{self.model_name}] Generating response with prompt (first 100 chars): {prompt[:100]}...")

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]

        try:
            # Ensure the model name used here is the one intended for the API,
            # which is self.model_name as set by BaseModelClient.__init__
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                # Consider adding max_tokens, temperature, etc. as needed
                # max_tokens=2048, # Example
            )

            if not response.choices or not response.choices[0].message or response.choices[0].message.content is None:
                raise ValueError(f"[{self.model_name}] LLM returned an empty or invalid response.")

            content = response.choices[0].message.content
            return content.strip()
        except TogetherAPIError as e:
            body = getattr(e, "body", None) or str(e)
            if len(body) > 3_000:
                body = body[:3_000] + "…[truncated]"
            logger.error(f"[{self.model_name}] TogetherAI API error: {body}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"[{self.model_name}] Unexpected error in TogetherAIClient: {e}", exc_info=True)
            raise


##############################################################################
# RequestsOpenAIClient – sync requests, wrapped async (original + api_key)
##############################################################################


class RequestsOpenAIClient(BaseModelClient):
    """
    Synchronous `requests`-based client for any OpenAI-compatible API.
    Wrapped in `asyncio.to_thread` so call-sites remain async.
    """

    def __init__(
        self,
        model_name: str,
        prompts_dir: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        super().__init__(model_name, prompts_dir=prompts_dir)

        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY missing and no inline key provided")

        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")

        self.endpoint = f"{self.base_url}/chat/completions"

    # ---------------- internal blocking helper ---------------- #
    def _post_sync(self, payload: dict) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        r = requests.post(self.endpoint, headers=headers, json=payload, timeout=600)

        if r.status_code >= 400:
            # try to surface the real OpenAI error message
            body_excerpt = r.text.strip()
            # don’t blow the logs with megabytes of prompt echo
            if len(body_excerpt) > 3_000:
                body_excerpt = body_excerpt[:3_000] + "…[truncated]"
            raise requests.HTTPError(
                f"{r.status_code} {r.reason} – OpenAI response body:\n{body_excerpt}",
                response=r,
            )

        return r.json()


    # ---------------- public async API ---------------- #
    async def generate_response(
        self,
        prompt: str,
        temperature: float = 0.0,
        inject_random_seed: bool = True,
    ) -> str:
        system_prompt_content = f"{generate_random_seed()}\n\n{self.system_prompt}" if inject_random_seed else self.system_prompt

        if self.model_name == "qwen/qwen3-235b-a22b":
            system_prompt_content += "\n/no_think"

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt_content},
                {"role": "user", "content": f"{prompt}\n\nPROVIDE YOUR RESPONSE BELOW:"},
            ],
            "temperature": temperature,
        }
        
        # Use max_completion_tokens for o4-mini, o3-mini, o3, gpt-4.1 models and nectarine models
        if self.model_name in ["o4-mini", "o3-mini", "o3", "gpt-4.1"] or self.model_name.startswith("nectarine"):
            payload["max_completion_tokens"] = self.max_tokens
        else:
            payload["max_tokens"] = self.max_tokens

        #if self.model_name == "qwen/qwen3-235b-a22b" and self.base_url == "https://openrouter.ai/api/v1":
        #    payload["provider"] = {
        #        "order": ["Cerebras"],     # fast qwen-2-35B
        #        "allow_fallbacks": False,
        #    }

        if (self.model_name == 'o3' or self.model_name == 'o4-mini'):
            del payload["temperature"]
            if "max_tokens" in payload:
                del payload["max_tokens"]
            payload["max_completion_tokens"] = self.max_tokens

        loop = asyncio.get_running_loop()
        try:
            data = await loop.run_in_executor(None, self._post_sync, payload)
            if not data.get("choices") or not data["choices"][0].get("message") or not data["choices"][0]["message"].get("content"):
                raise ValueError(f"[{self.model_name}] LLM returned an empty or invalid response.")
            content = data["choices"][0]["message"]["content"].strip()
            if '<think>' in content and '</think>' in content:
                content = content[content.rfind('</think>') + len('</think>'):]
            return content
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"[{self.model_name}] Bad response format: {e}", exc_info=True)
            raise
        except requests.RequestException as e:
            # bubble up the richer message we attached in _post_sync
            logger.error(f"[{self.model_name}] HTTP error while calling OpenAI: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"[{self.model_name}] Unexpected error: {e}", exc_info=True)
            raise


##############################################################################
# 3) Factory to Load Model Client
##############################################################################
class ModelSpec(NamedTuple):
    prefix: Optional[str]  # 'openai', 'requests', …
    model: str  # 'gpt-4o'
    base: Optional[str]  # 'https://proxy.foo'
    key: Optional[str]  # 'sk-…' (may be None)


def _parse_model_spec(raw: str) -> ModelSpec:
    """
    Splits once on '#' (API key) and once on '@' (base URL).  A leading
    '<prefix>:' is optional.  Nothing else is interpreted.
    """
    raw = raw.strip()

    pre_hash, _, key_part = raw.partition("#")
    pre_at, _, base_part = pre_hash.partition("@")

    maybe_pref, sep, model_part = pre_at.partition(":")
    if sep:  # explicit prefix was present
        prefix, model = maybe_pref.lower(), model_part
    else:
        prefix, model = None, maybe_pref

    return ModelSpec(prefix, model, base_part or None, key_part or None)

class Prefix(StrEnum):
    OPENAI            = "openai"
    OPENAI_REQUESTS   = "openai-requests"
    OPENAI_RESPONSES  = "openai-responses"
    ANTHROPIC         = "anthropic"
    GEMINI            = "gemini"
    DEEPSEEK          = "deepseek"
    OPENROUTER        = "openrouter"
    TOGETHER          = "together"

def load_model_client(model_id: str, prompts_dir: Optional[str] = None) -> BaseModelClient:
    """
    Recognises strings like
        gpt-4o
        anthropic:claude-3.7-sonnet
        openai:llama-3-2-3b@https://localhost:8000#myapikey
        gpt-5-reasoning-alpha-2025-07-19:minimal
    and returns the appropriate client.

    • If a prefix is omitted the function falls back to the original
      heuristic mapping exactly as before.
    • If an inline API-key ('#…') is present it overrides environment vars.
    • For reasoning models, effort can be specified with :minimal, :medium, or :high
    """
    # Extract reasoning effort if present (before general parsing)
    reasoning_effort = None
    actual_model_id = model_id
    
    # Check if this is a reasoning model with effort specified
    reasoning_models = ['gpt-5-reasoning-alpha-2025-07-19', 'o4-mini', 'nectarine-alpha-2025-07-25', 'nectarine-alpha-new-reasoning-effort-2025-07-25']
    for model in reasoning_models:
        if model_id.startswith(model + ':'):
            parts = model_id.split(':', 1)
            effort_part = parts[1]
            # Check if the effort part is valid before treating it as effort
            # (it could be a prefix like "openai:")
            if effort_part.lower() in ['minimal', 'medium', 'high']:
                actual_model_id = parts[0]
                reasoning_effort = effort_part.lower()
                break
    
    spec = _parse_model_spec(actual_model_id)
    logger.info(f"[load_model_client] Loading client for model_id='{model_id}', parsed spec: prefix={spec.prefix}, model={spec.model}, reasoning_effort={reasoning_effort}")

    # Inline key overrides env; otherwise fall back as usual *per client*
    inline_key = spec.key

    # ------------------------------------------------------------------ #
    # 1. Explicit prefix path                                           #
    # ------------------------------------------------------------------ #
    if spec.prefix:
        try:
            pref = Prefix(spec.prefix.lower())
        except ValueError as exc:
            raise ValueError(
                f"[load_model_client] unknown prefix '{spec.prefix}'. "
                "Allowed prefixes: openai, openai-requests, openai-responses, "
                "anthropic, gemini, deepseek, openrouter, together."
            ) from exc

        match pref:
            case Prefix.OPENAI:
                return OpenAIClient(
                    model_name=spec.model,
                    prompts_dir=prompts_dir,
                    base_url=spec.base,
                    api_key=inline_key,
                )
            case Prefix.OPENAI_REQUESTS:
                return RequestsOpenAIClient(
                    model_name=spec.model,
                    prompts_dir=prompts_dir,
                    base_url=spec.base,
                    api_key=inline_key,
                )
            case Prefix.OPENAI_RESPONSES:
                return OpenAIResponsesClient(spec.model, prompts_dir, api_key=inline_key, reasoning_effort=reasoning_effort)
            case Prefix.ANTHROPIC:
                return ClaudeClient(spec.model, prompts_dir)
            case Prefix.GEMINI:
                return GeminiClient(spec.model, prompts_dir)
            case Prefix.DEEPSEEK:
                return DeepSeekClient(spec.model, prompts_dir)
            case Prefix.OPENROUTER:
                return OpenRouterClient(spec.model, prompts_dir)
            case Prefix.TOGETHER:
                return TogetherAIClient(spec.model, prompts_dir)

    # ------------------------------------------------------------------ #
    # 2. Heuristic fallback path (identical to the original behaviour)   #
    # ------------------------------------------------------------------ #
    lower_id = spec.model.lower()
    logger.info(f"[load_model_client] Heuristic path: checking model='{spec.model}', lower_id='{lower_id}'")

    # Check if this is a reasoning model that should use Responses API
    reasoning_models_requiring_responses = ['gpt-5-reasoning-alpha-2025-07-19', 'o4-mini', 'nectarine-alpha-2025-07-25', 'nectarine-alpha-new-reasoning-effort-2025-07-25']
    if spec.model in reasoning_models_requiring_responses:
        logger.info(f"[load_model_client] Selected OpenAIResponsesClient for reasoning model '{spec.model}'")
        return OpenAIResponsesClient(spec.model, prompts_dir, api_key=inline_key, reasoning_effort=reasoning_effort)

    if lower_id == "o3-pro":
        logger.info(f"[load_model_client] Selected OpenAIResponsesClient for '{spec.model}'")
        return OpenAIResponsesClient(spec.model, prompts_dir, api_key=inline_key)

    if spec.model.startswith("together-"):
        # e.g. "together-mixtral-8x7b"
        logger.info(f"[load_model_client] Selected TogetherAIClient for '{spec.model}'")
        return TogetherAIClient(spec.model.split("together-", 1)[1], prompts_dir)

    if "openrouter" in lower_id:
        logger.info(f"[load_model_client] Selected OpenRouterClient for '{spec.model}'")
        return OpenRouterClient(spec.model, prompts_dir)

    if "claude" in lower_id:
        logger.info(f"[load_model_client] Selected ClaudeClient for '{spec.model}'")
        return ClaudeClient(spec.model, prompts_dir)

    if "gemini" in lower_id:
        logger.info(f"[load_model_client] Selected GeminiClient for '{spec.model}'")
        return GeminiClient(spec.model, prompts_dir)

    if "deepseek" in lower_id:
        logger.info(f"[load_model_client] Selected DeepSeekClient for '{spec.model}'")
        return DeepSeekClient(spec.model, prompts_dir)

    # Default: OpenAI-compatible async client
    logger.info(f"[load_model_client] No specific match found, using default OpenAIClient for '{spec.model}'")
    return OpenAIClient(
        model_name=spec.model,
        prompts_dir=prompts_dir,
        base_url=spec.base,
        api_key=inline_key,
    )


##############################################################################
# 1) Add a method to filter visible messages (near top-level or in BaseModelClient)
##############################################################################
def get_visible_messages_for_power(conversation_messages, power_name):
    """
    Returns a chronological subset of conversation_messages that power_name can legitimately see.
    """
    visible = []
    for msg in conversation_messages:
        if msg["sender"] == power_name or msg["recipient"] == power_name:
            visible.append(msg)
    return visible  # already in chronological order if appended that way
