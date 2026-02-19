"""
Formatter module for converting natural language LLM responses to structured JSON.
Uses Gemini 2.5 Flash via OpenRouter to extract and format information from reasoning-focused responses.
"""

import logging
from typing import Optional
from pathlib import Path

# Import logging function and model configuration
from .utils import log_llm_response, get_special_models, debug_log_llm_io
from config import config

# Import client loading function
from .clients import load_model_client

logger = logging.getLogger(__name__)

# Format type constants
FORMAT_STATE_UPDATE = "state_update"
FORMAT_CONVERSATION = "conversation"
FORMAT_NEGOTIATION_DIARY = "negotiation_diary"
FORMAT_ORDERS = "orders"
FORMAT_INITIAL_STATE = "initial_state"
FORMAT_ORDER_DIARY = "order_diary"


async def format_with_gemini_flash(
    raw_response: str, format_type: str, power_name: Optional[str] = None, phase: Optional[str] = None, log_file_path: Optional[str] = None
) -> str:
    """
    Format a natural language response into required JSON structure using Gemini Flash.

    Args:
        raw_response: Natural language response from primary LLM
        format_type: Type of formatting required (e.g., FORMAT_ORDERS, FORMAT_STATE_UPDATE)
        power_name: Optional power name for logging
        phase: Optional phase for logging
        log_file_path: Optional path for CSV logging

    Returns:
        JSON string in the expected format
    """
    # Map format types to prompt files
    format_prompts = {
        FORMAT_STATE_UPDATE: "formatting/format_state_update.txt",
        FORMAT_CONVERSATION: "formatting/format_conversation.txt",
        FORMAT_NEGOTIATION_DIARY: "formatting/format_negotiation_diary.txt",
        FORMAT_ORDERS: "formatting/format_orders.txt",
        FORMAT_INITIAL_STATE: "formatting/format_initial_state.txt",
        FORMAT_ORDER_DIARY: "formatting/format_order_diary.txt",
    }

    if format_type not in format_prompts:
        raise ValueError(f"Unknown format type: {format_type}")

    # Load the formatting prompt
    prompt_file = Path(__file__).parent / "prompts" / format_prompts[format_type]
    if not prompt_file.exists():
        raise FileNotFoundError(f"Formatting prompt not found: {prompt_file}")

    with open(prompt_file, "r") as f:
        format_prompt = f.read()

    # Replace placeholder with actual response
    format_prompt = format_prompt.replace("[RAW_RESPONSE]", raw_response)

    # Get model name from configuration
    special_models = get_special_models()
    model_name = special_models["formatter"]

    # Load the formatter client using the same logic as other models
    formatter_client = load_model_client(model_name)

    try:
        logger.info(f"[FORMATTER] Calling {model_name} for {format_type} formatting")

        # Create the full prompt with system message
        system_content = "You are a precise formatting assistant. Extract and format information exactly as requested."
        formatter_client.set_system_prompt(system_content)

        if getattr(config, "DEBUG", False):
            debug_log_llm_io("INPUT", model_name, None, "formatter", format_type, format_prompt)

        # Use the client's generate_response method
        formatted_response = await formatter_client.generate_response(
            prompt=format_prompt,
            temperature=0,  # Deterministic formatting
            inject_random_seed=False,  # No need for random seed in formatting
        )

        if not formatted_response:
            logger.warning(f"[FORMATTER] {model_name} returned empty response")
            return ""

        if getattr(config, "DEBUG", False):
            debug_log_llm_io("OUTPUT", model_name, None, "formatter", format_type, formatted_response)

        # Log successful formatting
        logger.info(f"[FORMATTER] Successfully formatted {format_type} response")

        # Strip any markdown formatting that Gemini might add
        if formatted_response.startswith("```json"):
            formatted_response = formatted_response[7:]
        if formatted_response.startswith("```"):
            formatted_response = formatted_response[3:]
        if formatted_response.endswith("```"):
            formatted_response = formatted_response[:-3]
        formatted_response = formatted_response.strip()

        # Log if requested
        if log_file_path:
            log_llm_response(
                log_file_path=log_file_path,
                model_name=model_name,
                power_name=power_name or "FORMATTER",
                phase=phase or "N/A",
                response_type=f"format_{format_type}",
                raw_input_prompt=format_prompt,
                raw_response=formatted_response,
                success="Success",
            )

        return formatted_response

    except Exception as e:
        logger.error(f"[FORMATTER] Error calling Gemini Flash: {e}")

        # Log error if requested
        if log_file_path:
            log_llm_response(
                log_file_path=log_file_path,
                model_name=model_name,
                power_name=power_name or "FORMATTER",
                phase=phase or "N/A",
                response_type=f"format_{format_type}",
                raw_input_prompt=format_prompt,
                raw_response=f"ERROR: {str(e)}",
                success=f"Failure: {type(e).__name__}",
            )

        # Return empty structure based on format type
        if format_type == FORMAT_CONVERSATION:
            return "[]"
        else:
            return "{}"
