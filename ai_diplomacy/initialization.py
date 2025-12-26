# ai_diplomacy/initialization.py
import logging
import json
from typing import Optional
from config import config

# Forward declaration for type hinting, actual imports in function if complex
if False:  # TYPE_CHECKING
    from diplomacy import Game
    from diplomacy.models.game import GameHistory
    from .agent import DiplomacyAgent

from .agent import ALL_POWERS, ALLOWED_RELATIONSHIPS
from .utils import run_llm_and_log, log_llm_response, get_prompt_path, load_prompt
from .prompt_constructor import build_context_prompt
from .formatter import format_with_gemini_flash, FORMAT_INITIAL_STATE
from .template_renderer import render_template

logger = logging.getLogger(__name__)


async def initialize_agent_state_ext(
    agent: "DiplomacyAgent",
    game: "Game",
    game_history: "GameHistory",
    log_file_path: str,
    prompts_dir: Optional[str] = None,
):
    """Uses the LLM to set initial goals and relationships for the agent."""
    power_name = agent.power_name
    logger.info(f"[{power_name}] Initializing agent state using LLM (external function)...")
    current_phase = game.get_current_phase() if game else "UnknownPhase"

    full_prompt = ""  # Ensure full_prompt is defined in the outer scope for finally block
    response = ""  # Ensure response is defined for finally block
    success_status = "Failure: Initialized"  # Default status

    try:
        # Load the prompt template
        allowed_labels_str = ", ".join(ALLOWED_RELATIONSHIPS)
        prompt_file = get_prompt_path("initial_state_prompt.txt")
        # Use agent's prompts_dir if the parameter prompts_dir is not provided
        effective_prompts_dir = prompts_dir if prompts_dir is not None else agent.prompts_dir
        logger.info(f"[{power_name}] Loading initial state prompt: {prompt_file} from dir: {effective_prompts_dir}")
        initial_prompt_template = load_prompt(prompt_file, prompts_dir=effective_prompts_dir)

        # Format the prompt with variables (supports both {var} and {{var}} syntax)
        initial_prompt = render_template(initial_prompt_template, {"power_name": power_name, "allowed_labels_str": allowed_labels_str})
        logger.debug(f"[{power_name}] Initial prompt length: {len(initial_prompt)}")
        logger.info(f"[{power_name}] Initial state prompt loaded, length: {len(initial_prompt)}, starts with: {initial_prompt[:50]}...")

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
            possible_orders=None,  # Don't include orders for initial state setup
            game_history=game_history,
            agent_goals=None,
            agent_relationships=None,
            agent_private_diary=formatted_diary,
            prompts_dir=effective_prompts_dir,
        )
        full_prompt = initial_prompt + "\n\n" + context
        logger.info(
            f"[{power_name}] Full prompt constructed. Total length: {len(full_prompt)}, initial_prompt length: {len(initial_prompt)}, context length: {len(context)}"
        )
        logger.info(f"[{power_name}] Full prompt starts with: {full_prompt[:100]}...")
        # Log the end of the prompt to see if JSON format instructions are included
        logger.info(f"[{power_name}] Full prompt ends with: ...{full_prompt[-500:]}")

        response = await run_llm_and_log(
            client=agent.client,
            prompt=full_prompt,
            power_name=power_name,
            phase=current_phase,
            response_type="initialization",  # Context for run_llm_and_log internal error logging
        )
        logger.info(f"[{power_name}] LLM response length: {len(response)}")
        logger.info(f"[{power_name}] LLM response for initial state: {response[:500] if response else 'EMPTY RESPONSE'}...")  # Log a snippet

        parsed_successfully = False
        try:
            # Conditionally format the response based on USE_UNFORMATTED_PROMPTS
            if config.USE_UNFORMATTED_PROMPTS:
                # Format the natural language response into JSON
                formatted_response = await format_with_gemini_flash(
                    response, FORMAT_INITIAL_STATE, power_name=power_name, phase=current_phase, log_file_path=log_file_path
                )
            else:
                # Use the raw response directly (already formatted)
                formatted_response = response
            update_data = agent._extract_json_from_text(formatted_response)
            logger.debug(f"[{power_name}] Successfully parsed JSON: {update_data}")
            parsed_successfully = True
        except json.JSONDecodeError as e:
            logger.error(f"[{power_name}] All JSON extraction attempts failed: {e}. Response snippet: {response[:300]}...")
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
            initial_relationships = update_data.get("initial_relationships") or update_data.get("relationships")

            if isinstance(initial_goals, list) and initial_goals:
                agent.goals = initial_goals
                agent.add_journal_entry(f"[{current_phase}] Initial Goals Set by LLM: {agent.goals}")
                logger.info(f"[{power_name}] Goals updated from LLM: {agent.goals}")
                initial_goals_applied = True
            else:
                logger.warning(f"[{power_name}] LLM did not provide valid 'initial_goals' list (got: {initial_goals}).")

            if isinstance(initial_relationships, dict) and initial_relationships:
                valid_relationships = {}
                # ... (rest of relationship validation logic from before) ...
                for p_key, r_val in initial_relationships.items():
                    p_upper = str(p_key).upper()
                    r_title = str(r_val).title() if isinstance(r_val, str) else str(r_val)
                    if p_upper in ALL_POWERS and p_upper != power_name:
                        if r_title in ALLOWED_RELATIONSHIPS:
                            valid_relationships[p_upper] = r_title
                        else:
                            valid_relationships[p_upper] = "Neutral"
                if valid_relationships:
                    agent.relationships = valid_relationships
                    agent.add_journal_entry(f"[{current_phase}] Initial Relationships Set by LLM: {agent.relationships}")
                    logger.info(f"[{power_name}] Relationships updated from LLM: {agent.relationships}")
                    initial_relationships_applied = True
                else:
                    logger.warning(f"[{power_name}] No valid relationships found in LLM response.")
            else:
                logger.warning(f"[{power_name}] LLM did not provide valid 'initial_relationships' dict (got: {initial_relationships}).")

            if initial_goals_applied or initial_relationships_applied:
                success_status = "Success: Applied LLM data"
            elif parsed_successfully:  # Parsed but nothing useful to apply
                success_status = "Success: Parsed but no data applied"
            # If not parsed_successfully, success_status is already "Failure: JSONDecodeError"

        # Fallback if LLM data was not applied or parsing failed
        if not initial_goals_applied:
            if not agent.goals:  # Only set defaults if no goals were set during agent construction or by LLM
                agent.goals = []
                agent.add_journal_entry(f"[{current_phase}] Set default initial goals as LLM provided none or parse failed.")
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
                agent.relationships = {p: "Neutral" for p in ALL_POWERS if p != power_name}
                agent.add_journal_entry(f"[{current_phase}] Set default neutral relationships as LLM provided none valid or parse failed.")
                logger.info(f"[{power_name}] Default neutral relationships set.")

    except Exception as e:
        logger.error(f"[{power_name}] Error during external agent state initialization: {e}", exc_info=True)
        success_status = f"Failure: Exception ({type(e).__name__})"
        # Fallback logic for goals/relationships if not already set by earlier fallbacks
        if not agent.goals:
            agent.goals = []
            logger.info(f"[{power_name}] Set fallback goals after top-level error: {agent.goals}")
        if not agent.relationships or all(r == "Neutral" for r in agent.relationships.values()):
            agent.relationships = {p: "Neutral" for p in ALL_POWERS if p != power_name}
            logger.info(f"[{power_name}] Set fallback neutral relationships after top-level error: {agent.relationships}")
    finally:
        if log_file_path:  # Ensure log_file_path is provided
            log_llm_response(
                log_file_path=log_file_path,
                model_name=agent.client.model_name if agent and agent.client else "UnknownModel",
                power_name=power_name,
                phase=current_phase,
                response_type="initial_state_setup",  # Specific type for CSV logging
                raw_input_prompt=full_prompt,
                raw_response=response,
                success=success_status,
            )

    # Final log of state after initialization attempt
    logger.info(f"[{power_name}] Post-initialization state: Goals={agent.goals}, Relationships={agent.relationships}")
