# ai_diplomacy/initialization.py
import json
from loguru import logger

# Forward declaration for type hinting, actual imports in function if complex
from diplomacy import Game
from .game_history import GameHistory
from .agent import DiplomacyAgent

from .agent import ALL_POWERS, ALLOWED_RELATIONSHIPS
from .utils import run_llm_and_log, log_llm_response
from .prompt_constructor import build_context_prompt


async def initialize_agent_state_ext(
    agent: DiplomacyAgent, game: Game, game_history: GameHistory, log_file_path: str
):
    """Uses the LLM to set initial goals and relationships for the agent."""
    power_name = agent.power_name
    logger.info(
        f"[{power_name}] Initializing agent state using LLM (external function)..."
    )
    current_phase = game.get_current_phase() if game else "UnknownPhase"

    full_prompt = (
        ""  # Ensure full_prompt is defined in the outer scope for finally block
    )
    response = ""  # Ensure response is defined for finally block
    success_status = "Failure: Initialized"  # Default status

    try:
        # Use a simplified prompt for initial state generation
        allowed_labels_str = ", ".join(ALLOWED_RELATIONSHIPS)
        initial_prompt = (
            f"You are the agent for {power_name} in a game of Diplomacy at the very start (Spring 1901). "
            f"Analyze the initial board position and suggest 2-3 strategic high-level goals for the early game. "
            f"Consider your power's strengths, weaknesses, and neighbors. "
            f"Also, provide an initial assessment of relationships with other powers. "
            f"IMPORTANT: For each relationship, you MUST use exactly one of the following labels: {allowed_labels_str}. "
            f"Format your response as a JSON object with two keys: 'initial_goals' (a list of strings) and 'initial_relationships' (a dictionary mapping power names to one of the allowed relationship strings)."
        )

        board_state = game.get_state() if game else {}
        possible_orders = game.get_all_possible_orders() if game else {}

        logger.debug(
            f"[{power_name}] Preparing context for initial state. Board state type: {type(board_state)}, possible_orders type: {type(possible_orders)}, game_history type: {type(game_history)}"
        )
        # Ensure agent.client and its methods can handle None for game/board_state/etc. if that's a possibility
        # For initialization, game should always be present.

        formatted_diary = agent.format_private_diary_for_prompt()

        context = build_context_prompt(
            game=game,
            board_state=board_state,
            power_name=power_name,
            possible_orders=possible_orders,
            game_history=game_history,
            agent_goals=None,
            agent_relationships=None,
            agent_private_diary=formatted_diary,
        )
        full_prompt = initial_prompt + "\n\n" + context

        response = await run_llm_and_log(
            client=agent.client,
            prompt=full_prompt,
            log_file_path=log_file_path,
            power_name=power_name,
            phase=current_phase,
            response_type="initialization",  # Context for run_llm_and_log internal error logging
        )
        logger.debug(
            f"[{power_name}] LLM response for initial state: {response[:300]}..."
        )  # Log a snippet

        parsed_successfully = False
        try:
            update_data = agent._extract_json_from_text(response)
            logger.debug(f"[{power_name}] Successfully parsed JSON: {update_data}")
            parsed_successfully = True
        except json.JSONDecodeError as e:
            logger.error(
                f"[{power_name}] All JSON extraction attempts failed: {e}. Response snippet: {response[:300]}..."
            )
            success_status = "Failure: JSONDecodeError"
            update_data = {}  # Ensure update_data exists for fallback logic below
            parsed_successfully = False  # Explicitly set here too
            # Fallback logic for goals/relationships will be handled later if update_data is empty

        # Defensive check for update_data type if parsing was initially considered successful
        if parsed_successfully:
            if isinstance(update_data, str):
                logger.error(
                    f"[{power_name}] _extract_json_from_text returned a string, not a dict/list, despite not raising an exception. This indicates an unexpected parsing issue. String returned: {update_data[:300]}..."
                )
                update_data = {}  # Treat as parsing failure
                parsed_successfully = False
                success_status = "Failure: ParsedAsStr"
            elif not isinstance(update_data, dict):  # Expecting a dict from JSON object
                logger.error(
                    f"[{power_name}] _extract_json_from_text returned a non-dict type ({type(update_data)}), expected dict. Data: {str(update_data)[:300]}"
                )
                update_data = {}  # Treat as parsing failure
                parsed_successfully = False
                success_status = "Failure: NotADict"

        initial_goals_applied = False
        initial_relationships_applied = False

        if parsed_successfully:
            initial_goals = update_data.get("initial_goals") or update_data.get("goals")
            initial_relationships = update_data.get(
                "initial_relationships"
            ) or update_data.get("relationships")

            if isinstance(initial_goals, list) and initial_goals:
                agent.goals = initial_goals
                agent.add_journal_entry(
                    f"[{current_phase}] Initial Goals Set by LLM: {agent.goals}"
                )
                logger.info(f"[{power_name}] Goals updated from LLM: {agent.goals}")
                initial_goals_applied = True
            else:
                logger.warning(
                    f"[{power_name}] LLM did not provide valid 'initial_goals' list (got: {initial_goals})."
                )

            if isinstance(initial_relationships, dict) and initial_relationships:
                valid_relationships = {}
                # ... (rest of relationship validation logic from before) ...
                for p_key, r_val in initial_relationships.items():
                    p_upper = str(p_key).upper()
                    r_title = (
                        str(r_val).title() if isinstance(r_val, str) else str(r_val)
                    )
                    if p_upper in ALL_POWERS and p_upper != power_name:
                        if r_title in ALLOWED_RELATIONSHIPS:
                            valid_relationships[p_upper] = r_title
                        else:
                            valid_relationships[p_upper] = "Neutral"
                if valid_relationships:
                    agent.relationships = valid_relationships
                    agent.add_journal_entry(
                        f"[{current_phase}] Initial Relationships Set by LLM: {agent.relationships}"
                    )
                    logger.info(
                        f"[{power_name}] Relationships updated from LLM: {agent.relationships}"
                    )
                    initial_relationships_applied = True
                else:
                    logger.warning(
                        f"[{power_name}] No valid relationships found in LLM response."
                    )
            else:
                logger.warning(
                    f"[{power_name}] LLM did not provide valid 'initial_relationships' dict (got: {initial_relationships})."
                )

            if initial_goals_applied or initial_relationships_applied:
                success_status = "Success: Applied LLM data"
            elif parsed_successfully:  # Parsed but nothing useful to apply
                success_status = "Success: Parsed but no data applied"
            # If not parsed_successfully, success_status is already "Failure: JSONDecodeError"

        # Fallback if LLM data was not applied or parsing failed
        if not initial_goals_applied:
            if not agent.goals:  # Only set defaults if no goals were set during agent construction or by LLM
                agent.goals = [
                    "Survive and expand",
                    "Form beneficial alliances",
                    "Secure key territories",
                ]
                agent.add_journal_entry(
                    f"[{current_phase}] Set default initial goals as LLM provided none or parse failed."
                )
                logger.info(f"[{power_name}] Default goals set.")

        if not initial_relationships_applied:
            # Check if relationships are still default-like before overriding
            is_default_relationships = True
            if agent.relationships:  # Check if it's not empty
                for p in ALL_POWERS:
                    if p != power_name and agent.relationships.get(p) != "Neutral":
                        is_default_relationships = False
                        break
            if is_default_relationships:
                agent.relationships = {
                    p: "Neutral" for p in ALL_POWERS if p != power_name
                }
                agent.add_journal_entry(
                    f"[{current_phase}] Set default neutral relationships as LLM provided none valid or parse failed."
                )
                logger.info(f"[{power_name}] Default neutral relationships set.")

    except Exception as e:
        logger.error(
            f"[{power_name}] Error during external agent state initialization: {e}",
            exc_info=True,
        )
        success_status = f"Failure: Exception ({type(e).__name__})"
        # Fallback logic for goals/relationships if not already set by earlier fallbacks
        if not agent.goals:
            agent.goals = [
                "Survive and expand",
                "Form beneficial alliances",
                "Secure key territories",
            ]
            logger.info(
                f"[{power_name}] Set fallback goals after top-level error: {agent.goals}"
            )
        if not agent.relationships or all(
            r == "Neutral" for r in agent.relationships.values()
        ):
            agent.relationships = {p: "Neutral" for p in ALL_POWERS if p != power_name}
            logger.info(
                f"[{power_name}] Set fallback neutral relationships after top-level error: {agent.relationships}"
            )
    finally:
        if log_file_path:  # Ensure log_file_path is provided
            log_llm_response(
                log_file_path=log_file_path,
                model_name=agent.client.model_name
                if agent and agent.client
                else "UnknownModel",
                power_name=power_name,
                phase=current_phase,
                response_type="initial_state_setup",  # Specific type for CSV logging
                raw_input_prompt=full_prompt,
                raw_response=response,
                success=success_status,
            )

    # Final log of state after initialization attempt
    logger.info(
        f"[{power_name}] Post-initialization state: Goals={agent.goals}, Relationships={agent.relationships}"
    )
