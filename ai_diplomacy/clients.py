import os
import json
from json import JSONDecodeError
import re
import logging
import ast

from typing import List, Dict, Optional
from dotenv import load_dotenv

import anthropic

os.environ["GRPC_PYTHON_LOG_LEVEL"] = "10"
import google.generativeai as genai  # Import after setting log level
from openai import OpenAI as DeepSeekOpenAI
from openai import OpenAI
from anthropic import Anthropic
from google import genai

from diplomacy.engine.message import GLOBAL

from .game_history import GameHistory

# set logger back to just info
logger = logging.getLogger("client")
logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG)

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

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.system_prompt = load_prompt("system_prompt.txt")

    def generate_response(self, prompt: str) -> str:
        """
        Returns a raw string from the LLM.
        Subclasses override this.
        """
        raise NotImplementedError("Subclasses must implement generate_response().")

    def build_context_prompt(
        self,
        game,
        board_state,
        power_name: str,
        possible_orders: Dict[str, List[str]],
        game_history: GameHistory,
        include_plans: bool = True
    ) -> str:
        context = load_prompt("context_prompt.txt")

        # Get our units and centers
        units_info = board_state["units"].get(power_name, [])
        units_info_set = set(units_info)
        centers_info = board_state["centers"].get(power_name, [])

        # Get the current phase
        year_phase = board_state["phase"]  # e.g. 'S1901M'

        # Get enemy units and centers and label them for each power
        enemy_units = {}
        enemy_centers = {}
        for power, info in board_state["units"].items():
            if power != power_name:
                enemy_units[power] = info
                enemy_centers[power] = board_state["centers"].get(power, [])

        # Get possible orders
        possible_orders_str = ""
        for loc, orders in possible_orders.items():
            possible_orders_str += f"  {loc}: {orders}\n"

        # Convoy paths
        all_convoy_paths_possible = game.convoy_paths_possible
        convoy_paths_possible = {}
        for start_loc, fleets_req, end_loc in all_convoy_paths_possible:
            for fleet in fleets_req:
                if fleet in units_info_set:
                    convoy_paths_possible.append((start_loc, fleets_req, end_loc))

        conversation_text = game_history.get_game_history(power_name, include_plans=include_plans)
        if not conversation_text:
            conversation_text = "\n(No game history yet)\n"

        # Load in current context values
        context = context.format(
            power_name=power_name,
            current_phase=year_phase,
            game_map_loc_name=game.map.loc_name,
            game_map_loc_type=game.map.loc_type,
            map_as_adjacency_list=game.map.loc_abut,
            possible_coasts=game.map.loc_coasts,
            game_map_scs=game.map.scs,
            game_history=conversation_text,
            enemy_units=enemy_units,
            enemy_centers=enemy_centers,
            units_info=units_info,
            centers_info=centers_info,
            possible_orders=possible_orders_str,
            convoy_paths_possible=convoy_paths_possible,
        )

        return context

    def build_prompt(
        self,
        game,
        board_state,
        power_name: str,
        possible_orders: Dict[str, List[str]],
        game_history: GameHistory,
    ) -> str:
        """
        Unified prompt approach: incorporate conversation and 'PARSABLE OUTPUT' requirements.
        """
        # Load prompts
        few_shot_example = load_prompt("few_shot_example.txt")
        instructions = load_prompt("order_instructions.txt")

        # Build the context prompt
        context = self.build_context_prompt(
            game,
            board_state,
            power_name,
            possible_orders,
            game_history,
        )

        return context + "\n\n" + instructions

    def get_orders(
        self,
        game,
        board_state,
        power_name: str,
        possible_orders: Dict[str, List[str]],
        conversation_text: str,
        model_error_stats=None,  # New optional param
    ) -> List[str]:
        """
        1) Builds the prompt with conversation context if available
        2) Calls LLM
        3) Parses JSON block
        """
        prompt = self.build_prompt(
            game,
            board_state,
            power_name,
            possible_orders,
            conversation_text,
        )

        raw_response = ""

        try:
            raw_response = self.generate_response(prompt)
            logger.info(
                f"[{self.model_name}] Raw LLM response for {power_name}:\n{raw_response}"
            )

            # Attempt to parse the final "orders" from the LLM
            move_list = self._extract_moves(raw_response, power_name)

            if not move_list:
                logger.warning(
                    f"[{self.model_name}] Could not extract moves for {power_name}. Using fallback."
                )
                if model_error_stats is not None:
                    model_error_stats[self.model_name]["order_decoding_errors"] += 1
                return self.fallback_orders(possible_orders)
            # Validate or fallback
            validated_moves = self._validate_orders(move_list, possible_orders)
            return validated_moves

        except Exception as e:
            logger.error(f"[{self.model_name}] LLM error for {power_name}: {e}")
            return self.fallback_orders(possible_orders)

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
            logger.debug(
                f"[{self.model_name}] Regex parse #1 failed for {power_name}. Trying alternative patterns."
            )

            # 1b) Check for inline JSON after "PARSABLE OUTPUT"
            pattern_alt = r"PARSABLE OUTPUT\s*\{(.*?)\}\s*$"
            matches = re.search(pattern_alt, raw_response, re.DOTALL)

        if not matches:
            logger.debug(
                f"[{self.model_name}] Regex parse #2 failed for {power_name}. Trying triple-backtick code fences."
            )

        # 2) If still no match, check for triple-backtick code fences containing JSON
        if not matches:
            code_fence_pattern = r"```json\s*(\{.*?\})\s*```"
            matches = re.search(code_fence_pattern, raw_response, re.DOTALL)
            if matches:
                logger.debug(
                    f"[{self.model_name}] Found triple-backtick JSON block for {power_name}."
                )

        # 3) Attempt to parse JSON if we found anything
        json_text = None
        if matches:
            # Add braces back around the captured group
            if matches.group(1).strip().startswith(r"{{"):
                json_text = matches.group(1).strip()[1:-1]
            elif matches.group(1).strip().startswith(r"{"):
                json_text = matches.group(1).strip()
            else:
                json_text = "{%s}" % matches.group(1).strip

            json_text = json_text.strip()

        if not json_text:
            logger.debug(
                f"[{self.model_name}] No JSON text found in LLM response for {power_name}."
            )
            return None

        # 3a) Try JSON loading
        try:
            data = json.loads(json_text)
            return data.get("orders", None)
        except json.JSONDecodeError as e:
            logger.warning(
                f"[{self.model_name}] JSON decode failed for {power_name}: {e}. Trying bracket fallback."
            )

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
                logger.warning(
                    f"[{self.model_name}] Bracket fallback parse also failed for {power_name}: {e2}"
                )

        # If all attempts failed
        return None

    def _validate_orders(
        self, moves: List[str], possible_orders: Dict[str, List[str]]
    ) -> List[str]:
        """
        Filter out invalid moves, fill missing with HOLD, else fallback.
        """
        logger.debug(f"[{self.model_name}] Proposed LLM moves: {moves}")
        validated = []
        used_locs = set()

        if not isinstance(moves, list):
            logger.debug(f"[{self.model_name}] Moves not a list, fallback.")
            return self.fallback_orders(possible_orders)

        for move in moves:
            move_str = move.strip()
            # Check if it's in possible orders
            if any(move_str in loc_orders for loc_orders in possible_orders.values()):
                validated.append(move_str)
                parts = move_str.split()
                if len(parts) >= 2:
                    used_locs.add(parts[1][:3])
            else:
                logger.debug(f"[{self.model_name}] Invalid move from LLM: {move_str}")

        # Fill missing with hold
        for loc, orders_list in possible_orders.items():
            if loc not in used_locs and orders_list:
                hold_candidates = [o for o in orders_list if o.endswith("H")]
                validated.append(
                    hold_candidates[0] if hold_candidates else orders_list[0]
                )

        if not validated:
            logger.warning(f"[{self.model_name}] All moves invalid, fallback.")
            return self.fallback_orders(possible_orders)

        logger.debug(f"[{self.model_name}] Validated moves: {validated}")
        return validated

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
        game_phase: str,
    ) -> str:
        
        instructions = load_prompt("planning_instructions.txt")

        context = self.build_context_prompt(
            game,
            board_state,
            power_name,
            possible_orders,
            game_history,
            include_plans=False
        )

        return context + "\n\n" + instructions

    def build_conversation_prompt(
        self,
        game,
        board_state,
        power_name: str,
        possible_orders: Dict[str, List[str]],
        game_history: GameHistory,
        game_phase: str,
    ) -> str:
        instructions = load_prompt("conversation_instructions.txt")

        context = self.build_context_prompt(
            game,
            board_state,
            power_name,
            possible_orders,
            game_history,
        )

        return context + "\n\n" + instructions

    def get_planning_reply(
        self,
        game,
        board_state,
        power_name: str,
        possible_orders: Dict[str, List[str]],
        game_history: GameHistory,
        game_phase: str,
        active_powers: Optional[List[str]] = None,
    ) -> str:
        
        prompt = self.build_planning_prompt(
            game,
            board_state,
            power_name,
            possible_orders,
            game_history,
            game_phase,
        )

        raw_response = self.generate_response(prompt)
        return raw_response
    
    def get_conversation_reply(
        self,
        game,
        board_state,
        power_name: str,
        possible_orders: Dict[str, List[str]],
        game_history: GameHistory,
        game_phase: str,
        active_powers: Optional[List[str]] = None,
    ) -> str:
        
        prompt = self.build_conversation_prompt(
            game,
            board_state,
            power_name,
            possible_orders,
            game_history,
            game_phase,
        )

        raw_response = self.generate_response(prompt)

        messages = []
        if raw_response:
            try:
                # Find the JSON block between double curly braces
                json_matches = re.findall(r"\{\{(.*?)\}\}", raw_response, re.DOTALL)

                if not json_matches:
                    # try normal
                    logger.debug(
                        f"[{self.model_name}] No JSON block found in LLM response for {power_name}. Trying double braces."
                    )
                    json_matches = re.findall(
                        r"PARSABLE OUTPUT:\s*\{(.*?)\}", raw_response, re.DOTALL
                    )

                if not json_matches:
                    # try backtick fences
                    logger.debug(
                        f"[{self.model_name}] No JSON block found in LLM response for {power_name}. Trying backtick fences."
                    )
                    json_matches = re.findall(
                        r"```json\n(.*?)\n```", raw_response, re.DOTALL
                    )

                for match in json_matches:
                    try:
                        if match.strip().startswith(r"{"):
                            message_data = json.loads(match.strip())
                        else:
                            message_data = json.loads(f"{{{match}}}")

                        # Extract message details
                        message_type = message_data.get("message_type", "global")
                        content = message_data.get("content", "").strip()
                        recipient = message_data.get("recipient", GLOBAL)

                        # Validate recipient if private message
                        if message_type == "private" and recipient not in active_powers:
                            logger.warning(
                                f"Invalid recipient {recipient} for private message, defaulting to GLOBAL"
                            )
                            recipient = GLOBAL

                        # For private messages, ensure recipient is specified
                        if message_type == "private" and recipient == GLOBAL:
                            logger.warning(
                                "Private message without recipient specified, defaulting to GLOBAL"
                            )

                        # Log for debugging
                        logger.info(
                            f"Power {power_name} sends {message_type} message to {recipient}"
                        )

                        # Keep local record for building future conversation context
                        message = {
                            "sender": power_name,
                            "recipient": recipient,
                            "content": content,
                        }

                        messages.append(message)

                    except (json.JSONDecodeError, AttributeError) as e:
                        message = None

            except AttributeError:
                logger.error("Error parsing raw response")

        # Deduplicate messages
        messages = list(set([json.dumps(m) for m in messages]))
        messages = [json.loads(m) for m in messages]

        return messages


##############################################################################
# 2) Concrete Implementations
##############################################################################


class OpenAIClient(BaseModelClient):
    """
    For 'o3-mini', 'gpt-4o', or other OpenAI model calls.
    """

    def __init__(self, model_name: str):
        super().__init__(model_name)
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def generate_response(self, prompt: str) -> str:
        # Updated to new API format
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
            )
            if not response or not hasattr(response, "choices") or not response.choices:
                logger.warning(
                    f"[{self.model_name}] Empty or invalid result in generate_response. Returning empty."
                )
                return ""
            return response.choices[0].message.content.strip()
        except json.JSONDecodeError as json_err:
            logger.error(
                f"[{self.model_name}] JSON decoding failed in generate_response: {json_err}"
            )
            return ""
        except Exception as e:
            logger.error(
                f"[{self.model_name}] Unexpected error in generate_response: {e}"
            )
            return ""


class ClaudeClient(BaseModelClient):
    """
    For 'claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', etc.
    """

    def __init__(self, model_name: str):
        super().__init__(model_name)
        self.client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    def generate_response(self, prompt: str) -> str:
        # Updated Claude messages format
        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=2000,
                system=self.system_prompt,  # system is now a top-level parameter
                messages=[{"role": "user", "content": prompt}],
            )
            if not response.content:
                logger.warning(
                    f"[{self.model_name}] Empty content in Claude generate_response. Returning empty."
                )
                return ""
            return response.content[0].text.strip() if response.content else ""
        except json.JSONDecodeError as json_err:
            logger.error(
                f"[{self.model_name}] JSON decoding failed in generate_response: {json_err}"
            )
            return ""
        except Exception as e:
            logger.error(
                f"[{self.model_name}] Unexpected error in generate_response: {e}"
            )
            return ""


class GeminiClient(BaseModelClient):
    """
    For 'gemini-1.5-flash' or other Google Generative AI models.
    """

    def __init__(self, model_name: str):
        super().__init__(model_name)
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    def generate_response(self, prompt: str) -> str:
        full_prompt = self.system_prompt + prompt

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
            )
            if not response or not response.text:
                logger.warning(
                    f"[{self.model_name}] Empty Gemini generate_response. Returning empty."
                )
                return ""
            return response.text.strip()
        except Exception as e:
            logger.error(f"[{self.model_name}] Error in Gemini generate_response: {e}")
            return ""


class DeepSeekClient(BaseModelClient):
    """
    For DeepSeek R1 'deepseek-reasoner'
    """

    def __init__(self, model_name: str):
        super().__init__(model_name)
        self.api_key = os.environ.get("DEEPSEEK_API_KEY")
        self.client = DeepSeekOpenAI(
            api_key=self.api_key, base_url="https://api.deepseek.com/"
        )

    def generate_response(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                stream=False,
            )
            logger.debug(f"[{self.model_name}] Raw DeepSeek response:\n{response}")

            if not response or not response.choices:
                logger.warning(
                    f"[{self.model_name}] No valid response in generate_response."
                )
                return ""

            content = response.choices[0].message.content.strip()
            if not content:
                logger.warning(f"[{self.model_name}] DeepSeek returned empty content.")
                return ""

            try:
                json_response = json.loads(content)
                required_fields = ["message_type", "content"]
                if json_response["message_type"] == "private":
                    required_fields.append("recipient")
                if not all(field in json_response for field in required_fields):
                    logger.error(
                        f"[{self.model_name}] Missing required fields in response: {content}"
                    )
                    return ""
                return content
            except JSONDecodeError:
                logger.error(
                    f"[{self.model_name}] Response is not valid JSON: {content}"
                )
                content = content.replace("'", '"')
                try:
                    json.loads(content)
                    return content
                except JSONDecodeError:
                    return ""

        except Exception as e:
            logger.error(
                f"[{self.model_name}] Unexpected error in generate_response: {e}"
            )
            return ""


##############################################################################
# 3) Factory to Load Model Client
##############################################################################


def load_model_client(model_id: str) -> BaseModelClient:
    """
    Returns the appropriate LLM client for a given model_id string.
    Example usage:
       client = load_model_client("claude-3-5-sonnet-20241022")
    """
    # Basic pattern matching or direct mapping
    lower_id = model_id.lower()
    if "claude" in lower_id:
        return ClaudeClient(model_id)
    elif "gemini" in lower_id:
        return GeminiClient(model_id)
    elif "deepseek" in lower_id:
        return DeepSeekClient(model_id)
    else:
        # Default to OpenAI
        return OpenAIClient(model_id)


##############################################################################
# 4) Example Usage in a Diplomacy "main" or Similar
##############################################################################


def example_game_loop(game):
    """
    Pseudocode: Integrate with the Diplomacy loop.
    """
    # Suppose we gather all active powers
    active_powers = [
        (p_name, p_obj)
        for p_name, p_obj in game.powers.items()
        if not p_obj.is_eliminated()
    ]
    power_model_mapping = assign_models_to_powers()

    for power_name, power_obj in active_powers:
        model_id = power_model_mapping.get(power_name, "o3-mini")
        client = load_model_client(model_id)

        # Get possible orders from the game
        possible_orders = game.get_all_possible_orders()
        board_state = game.get_state()

        # Get orders from the client
        orders = client.get_orders(board_state, power_name, possible_orders)
        game.set_orders(power_name, orders)

    # Then process, etc.
    game.process()


class LMServiceVersus:
    """
    Optional wrapper class if you want extra control.
    For example, you could store or reuse clients, etc.
    """

    def __init__(self):
        self.power_model_map = assign_models_to_powers()

    def get_orders_for_power(self, game, power_name):
        model_id = self.power_model_map.get(power_name, "o3-mini")
        client = load_model_client(model_id)
        possible_orders = gather_possible_orders(game, power_name)
        board_state = game.get_state()
        return client.get_orders(board_state, power_name, possible_orders)


##############################################################################
# 1) Add a method to filter visible messages (near top-level or in BaseModelClient)
##############################################################################
def get_visible_messages_for_power(conversation_messages, power_name):
    """
    Returns a chronological subset of conversation_messages that power_name can legitimately see.
    """
    visible = []
    for msg in conversation_messages:
        # GLOBAL might be 'ALL' or 'GLOBAL' depending on your usage
        if (
            msg["recipient"] == "ALL"
            or msg["recipient"] == "GLOBAL"
            or msg["sender"] == power_name
            or msg["recipient"] == power_name
        ):
            visible.append(msg)
    return visible  # already in chronological order if appended that way


def load_prompt(filename: str) -> str:
    """Helper to load prompt text from file"""
    with open(f"./ai_diplomacy/prompts/{filename}", "r") as f:
        return f.read().strip()
