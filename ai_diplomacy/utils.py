from dotenv import load_dotenv
import logging
import os
from typing import Dict, List, Tuple, Set, Optional
from diplomacy import Game
import csv
from typing import TYPE_CHECKING
import random
import string
import json
import asyncio
from openai import RateLimitError, APIConnectionError, APITimeoutError
import aiohttp
import requests
from pathlib import Path
from config import config
from models import POWERS_ORDER
from datetime import datetime

# Avoid circular import for type hinting
if TYPE_CHECKING:
    from .clients import BaseModelClient
    # If DiplomacyAgent is used for type hinting for an 'agent' parameter:
    # from .agent import DiplomacyAgent

logger = logging.getLogger("utils")
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

load_dotenv()


def atomic_write_json(data: dict, filepath: str):
    """Writes a dictionary to a JSON file atomically."""
    try:
        # Ensure the directory exists
        dir_name = os.path.dirname(filepath)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        # Write to a temporary file in the same directory
        temp_filepath = f"{filepath}.tmp.{os.getpid()}"
        with open(temp_filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        # Atomically rename the temporary file to the final destination
        os.rename(temp_filepath, filepath)
    except Exception as e:
        logger.error(f"Failed to perform atomic write to {filepath}: {e}", exc_info=True)
        # Clean up temp file if it exists
        if os.path.exists(temp_filepath):
            try:
                os.remove(temp_filepath)
            except Exception as e_clean:
                logger.error(f"Failed to clean up temp file {temp_filepath}: {e_clean}")


def assign_models_to_powers() -> Dict[str, str]:
    """
    Example usage: define which model each power uses.
    Return a dict: { power_name: model_id, ... }
    POWERS = ['AUSTRIA', 'ENGLAND', 'FRANCE', 'GERMANY', 'ITALY', 'RUSSIA', 'TURKEY']
    Models supported: o3-mini, o4-mini, o3, gpt-4o, gpt-4o-mini,
                    claude-opus-4-20250514, claude-sonnet-4-20250514, claude-3-5-haiku-20241022, claude-3-5-sonnet-20241022, claude-3-7-sonnet-20250219
                    gemini-2.0-flash, gemini-2.5-flash-preview-04-17, gemini-2.5-pro-preview-03-25,
                    deepseek-chat, deepseek-reasoner,
                    kimi-k2-0905-preview,
                    openrouter-meta-llama/llama-3.3-70b-instruct, openrouter-qwen/qwen3-235b-a22b, openrouter-microsoft/phi-4-reasoning-plus:free,
                    openrouter-deepseek/deepseek-prover-v2:free, openrouter-meta-llama/llama-4-maverick:free, openrouter-nvidia/llama-3.3-nemotron-super-49b-v1:free,
                    openrouter-google/gemma-3-12b-it:free, openrouter-google/gemini-2.5-flash-preview-05-20
    """

    # POWER MODELS
    
    return {
        "AUSTRIA": "gpt-5-mini",
        "ENGLAND": "gpt-5-mini",
        "FRANCE": "gpt-5-mini",
        "GERMANY": "gpt-5-mini",
        "ITALY": "gemini-2.5-flash",
        "RUSSIA": "gemini-2.5-flash",
        "TURKEY": "gemini-2.5-flash",
    }
    
    # TEST MODELS
    """
    return {
        "AUSTRIA": "openrouter-mistralai/mistral-small-3.2-24b-instruct",
        "ENGLAND": "openrouter-mistralai/mistral-small-3.2-24b-instruct",
        "FRANCE": "openrouter-mistralai/mistral-small-3.2-24b-instruct",
        "GERMANY": "openrouter-mistralai/mistral-small-3.2-24b-instruct",
        "ITALY": "openrouter-mistralai/mistral-small-3.2-24b-instruct",
        "RUSSIA": "openrouter-mistralai/mistral-small-3.2-24b-instruct",
        "TURKEY": "openrouter-mistralai/mistral-small-3.2-24b-instruct",
    }
    """


def get_special_models() -> Dict[str, str]:
    """
    Define models for special purposes like phase summaries and formatting.

    These can be overridden via environment variables:
    - AI_DIPLOMACY_NARRATIVE_MODEL: Model for phase summaries (default: "o3")
    - AI_DIPLOMACY_FORMATTER_MODEL: Model for JSON formatting (default: "google/gemini-2.5-flash-lite-preview-06-17")

    Returns:
        dict: {
            "phase_summary": model for generating narrative phase summaries,
            "formatter": model for formatting natural language to JSON
        }

    Examples:
        # Use Claude for phase summaries
        export AI_DIPLOMACY_NARRATIVE_MODEL="claude-3-5-sonnet-20241022"

        # Use a different Gemini model for formatting
        export AI_DIPLOMACY_FORMATTER_MODEL="gemini-2.0-flash"
    """
    return {"phase_summary": config.AI_DIPLOMACY_NARRATIVE_MODEL, "formatter": config.AI_DIPLOMACY_FORMATTER_MODEL}


def gather_possible_orders(game: Game, power_name: str) -> Dict[str, List[str]]:
    """
    Returns a dictionary mapping each orderable location to the list of valid orders.
    """
    orderable_locs = game.get_orderable_locations(power_name)
    all_possible = game.get_all_possible_orders()

    result = {}
    for loc in orderable_locs:
        result[loc] = all_possible.get(loc, [])
    return result


async def get_valid_orders(
    game: Game,
    client,  # BaseModelClient instance
    board_state,
    power_name: str,
    possible_orders: Dict[str, List[str]],
    game_history,
    model_error_stats,
    agent_goals=None,
    agent_relationships=None,
    agent_private_diary_str=None,
    log_file_path: str = None,
    phase: str = None,
) -> Dict[str, List[str]]:
    """
    Generates orders with the LLM, validates them by round-tripping through the
    engine, and returns **both** the accepted and rejected orders so the caller
    can record invalid attempts.

    Returns
    -------
    dict : { "valid": [...], "invalid": [...] }
    """

    # ── 1. Ask the model ───────────────────────────────────────
    raw_orders = await client.get_orders(
        game=game,
        board_state=board_state,
        power_name=power_name,
        possible_orders=possible_orders,
        conversation_text=game_history,
        model_error_stats=model_error_stats,
        agent_goals=agent_goals,
        agent_relationships=agent_relationships,
        agent_private_diary_str=agent_private_diary_str,
        log_file_path=log_file_path,
        phase=phase,
    )

    invalid_info: list[str] = []
    valid: list[str] = []
    invalid: list[str] = []

    # ── 2. Type check ──────────────────────────────────────────
    if not isinstance(raw_orders, list):
        logger.warning("[%s] Orders received from LLM are not a list: %s. Using fallback.", power_name, raw_orders)
        model_error_stats[client.model_name]["order_decoding_errors"] += 1
        return {"valid": client.fallback_orders(possible_orders), "invalid": []}

    # ── 3. Round-trip validation with engine ───────────────────
    CODE_TO_ENGINE = {
        "AUT": "AUSTRIA",
        "ENG": "ENGLAND",
        "FRA": "FRANCE",
        "GER": "GERMANY",
        "ITA": "ITALY",
        "RUS": "RUSSIA",
        "TUR": "TURKEY",
    }
    engine_power = power_name if power_name in game.powers else CODE_TO_ENGINE[power_name]

    for move in raw_orders:
        if not move or not move.strip():
            continue

        upper = move.upper()

        # WAIVE is always valid
        if upper == "WAIVE":
            valid.append("WAIVE")
            continue

        game.clear_orders(engine_power)
        game.set_orders(engine_power, [upper])
        normed = game.get_orders(engine_power)

        if normed:  # accepted
            valid.append(normed[0])
        else:  # rejected
            invalid.append(upper)
            invalid_info.append(f"Order '{move}' is invalid for {power_name}")

    game.clear_orders(engine_power)  # clean slate for main engine flow

    # ── 4. Legacy logging & stats updates ──────────────────────
    if invalid_info:  # at least one bad move
        logger.debug("[%s] Invalid orders: %s", power_name, ", ".join(invalid_info))
        model_error_stats[client.model_name]["order_decoding_errors"] += 1
        logger.debug("[%s] Some orders invalid, using fallback.", power_name)
    else:
        logger.debug("[%s] All orders valid: %s", power_name, valid)

    # ── 5. Fallback when nothing survives ─────────────────────
    if not valid:
        fallback = client.fallback_orders(possible_orders)
        return {"valid": fallback, "invalid": invalid}

    return {"valid": valid, "invalid": invalid}


def normalize_and_compare_orders(
    issued_orders: Dict[str, List[str]],
    accepted_orders_dict: Dict[str, List[str]],
    game: Game,
) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    """
    Normalizes and compares issued orders against accepted orders from the game engine.
    Uses the map's built-in normalization methods to ensure consistent formatting.

    Args:
        issued_orders: Dictionary of orders issued by power {power_name: [orders]}
        accepted_orders_dict: Dictionary of orders accepted by the engine,
                              typically from game.get_state()["orders"].
        game: The current Game object containing the map.

    Returns:
        Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]: (orders_not_accepted, orders_not_issued)
            - orders_not_accepted: Orders issued but not accepted by engine (normalized).
            - orders_not_issued: Orders accepted by engine but not issued (normalized).
    """
    game_map = game.map

    def normalize_order(order: str) -> str:
        # Inner function to normalize a single order string using the game map.
        if not order:
            return order

        try:
            # Use map's normalization methods directly
            normalized = game_map.norm(order)
            # Further split and normalize parts for complex orders if necessary
            # (This part might need refinement depending on how complex orders are handled
            #  and represented after initial normalization by game_map.norm)

            # Example (simplified, game_map.norm often handles this):
            # Split support orders
            # parts = normalized.split(" S ")
            # normalized_parts = []
            # for part in parts:
            #     move_parts = part.split(" - ")
            #     move_parts = [game_map.norm(p.strip()) for p in move_parts]
            #     move_parts = [game_map.aliases.get(p, p) for p in move_parts]
            #     normalized_parts.append(" - ".join(move_parts))
            # return " S ".join(normalized_parts)

            return normalized  # Return the directly normalized string for now
        except Exception as e:
            logger.warning(f"Could not normalize order '{order}': {e}")
            return order  # Return original if normalization fails

    orders_not_accepted = {}
    orders_not_issued = {}

    all_powers = set(issued_orders.keys()) | set(accepted_orders_dict.keys())

    for pwr in all_powers:
        # Normalize issued orders for the power, handling potential absence
        issued_set = set()
        if pwr in issued_orders:
            try:
                issued_set = {normalize_order(o) for o in issued_orders.get(pwr, []) if o}
            except Exception as e:
                logger.error(f"Error normalizing issued orders for {pwr}: {e}")

        # Normalize accepted orders for the power, handling potential absence
        accepted_set = set()
        if pwr in accepted_orders_dict:
            try:
                accepted_set = {normalize_order(o) for o in accepted_orders_dict.get(pwr, []) if o}
            except Exception as e:
                logger.error(f"Error normalizing accepted orders for {pwr}: {e}")

        # Compare the sets
        missing_from_engine = issued_set - accepted_set
        missing_from_issued = accepted_set - issued_set

        if missing_from_engine:
            orders_not_accepted[pwr] = missing_from_engine
        if missing_from_issued:
            orders_not_issued[pwr] = missing_from_issued

    return orders_not_accepted, orders_not_issued


def load_prompt(fname: str | Path, prompts_dir: str | Path | None = None) -> str:
    """
    Resolve *fname* to an absolute path and return its contents.
    Resolution rules (first match wins):

    1. If *fname* is absolute -> use as-is.
    2. If *prompts_dir* is given -> prompts_dir / fname
    3. Otherwise -> <package_root>/prompts / fname
    """

    fname = Path(fname)

    if fname.is_absolute():
        prompt_path = fname

    else:
        if prompts_dir is not None:
            prompt_path = Path(prompts_dir) / fname
        else:
            package_root = Path(__file__).resolve().parent
            prompt_path = package_root / "prompts" / fname

    try:
        content = prompt_path.read_text(encoding="utf-8").strip()
        logger.debug(f"Loaded prompt from {prompt_path}, length: {len(content)}")
        return content
    except FileNotFoundError:
        logger.error("Prompt file not found: %s", prompt_path)
        raise Exception("Prompt file not found: " + str(prompt_path))



# == New LLM Response Logging Function ==
def log_llm_response(
    log_file_path: str,
    model_name: str,
    power_name: Optional[str],  # Optional for non-power-specific calls like summary
    phase: str,
    response_type: str,
    raw_input_prompt: str,  # Added new parameter for the raw input
    raw_response: str,
    success: str,  # Changed from bool to str
):
    """Appends a raw LLM response to a CSV log file."""
    try:
        # Ensure the directory exists
        log_dir = os.path.dirname(log_file_path)
        if log_dir:  # Ensure log_dir is not empty (e.g., if path is just a filename)
            os.makedirs(log_dir, exist_ok=True)

        # Check if file exists and has content to determine if we need headers
        file_exists = os.path.isfile(log_file_path) and os.path.getsize(log_file_path) > 0

        with open(log_file_path, "a", newline="", encoding="utf-8") as csvfile:
            # Added "raw_input" and "timestamp" to fieldnames
            fieldnames = ["timestamp", "model", "power", "phase", "response_type", "raw_input", "raw_response", "success"]
            writer = csv.DictWriter(
                csvfile,
                fieldnames=fieldnames,
                quoting=csv.QUOTE_ALL,  # Quote all fields to handle commas and newlines
                escapechar="\\",
            )  # Use backslash for escaping

            if not file_exists:
                writer.writeheader()  # Write header only if file is new

            writer.writerow(
                {
                    "timestamp": datetime.now().isoformat(),  # Add current timestamp in ISO format
                    "model": model_name,
                    "power": power_name if power_name else "game",  # Use 'game' if no specific power
                    "phase": phase,
                    "response_type": response_type,
                    "raw_input": raw_input_prompt,  # Added raw_input to the row
                    "raw_response": raw_response,
                    "success": success,
                }
            )
    except Exception as e:
        logger.error(f"Failed to log LLM response to {log_file_path}: {e}", exc_info=True)

# A tuple of exception types that we consider safe to retry.
# This includes network issues, timeouts, rate limits, and the ValueError
# we now raise for empty/invalid responses.
RETRYABLE_EXCEPTIONS = (
    RateLimitError,
    APIConnectionError,
    APITimeoutError,
    aiohttp.ClientError,
    requests.RequestException,
    asyncio.TimeoutError,
    ValueError,  # We explicitly raise this for empty responses, which might be a temporary glitch.
)

async def run_llm_and_log(
    client: "BaseModelClient",
    prompt: str,
    power_name: Optional[str],
    phase: str,
    response_type: str,
    temperature: float = 0.0,
    *,
    attempts: int = 5,
    backoff_base: float = 1.0,
    backoff_factor: float = 2.0,
    jitter: float = 0.3,
) -> str:
    """
    Calls `client.generate_response` with robust retry logic and returns the raw output.

    This function handles exceptions gracefully:
    - It retries on a specific set of `RETRYABLE_EXCEPTIONS` (e.g., network errors, rate limits).
    - It immediately stops and re-raises critical exceptions like `KeyboardInterrupt`.
    - It logs a warning for each failed retry attempt.
    - On final failure after all retries, it logs a detailed error and re-raises the last
      exception, ensuring the calling code is aware of the failure.
    """
    last_exception: Optional[Exception] = None

    for attempt in range(attempts):
        try:
            raw_response = await client.generate_response(prompt, temperature=temperature)

            # The clients now raise ValueError, but this is a final safeguard.
            if not raw_response or not raw_response.strip():
                raise ValueError("LLM client returned an empty or whitespace-only string.")

            # Success!
            return raw_response

        except RETRYABLE_EXCEPTIONS as e:
            last_exception = e
            if attempt == attempts - 1:
                # This was the last attempt, so we'll fall through to the final error handling.
                break

            # Calculate exponential backoff with jitter
            delay = backoff_base * (backoff_factor**attempt) + random.uniform(0, jitter)
            logger.warning(
                f"LLM call failed for {client.model_name}/{power_name} (Attempt {attempt + 1}/{attempts}). "
                f"Error: {type(e).__name__}('{e}'). Retrying in {delay:.2f} seconds."
            )
            await asyncio.sleep(delay)

        except (KeyboardInterrupt, asyncio.CancelledError):
            # If the user hits Ctrl-C or the task is cancelled, stop immediately.
            logger.warning(f"LLM call for {client.model_name}/{power_name} was cancelled or interrupted by user.")
            raise  # Re-raise to allow the application to exit cleanly.

        except Exception as e:
            last_exception = e
            if attempt == attempts - 1:
                # This was the last attempt, so we'll fall through to the final error handling.
                break

            # Calculate exponential backoff with jitter
            delay = backoff_base * (backoff_factor**attempt) + random.uniform(0, jitter)
            logger.error(
                f"An unexpected error occurred during LLM call for {client.model_name}/{power_name}: {e}"
                f"LLM call failed for {client.model_name}/{power_name} (Attempt {attempt + 1}/{attempts}). "
                f"Error: {type(e).__name__}('{e}'). Retrying in {delay:.2f} seconds.",
                exc_info=True,
            )
            await asyncio.sleep(delay)

    # This part of the code is only reached if all retry attempts have failed.
    final_error_message = (
        f"API Error after {attempts} attempts for {client.model_name}/{power_name}/{response_type} "
        f"in phase {phase}. Final error: {type(last_exception).__name__}('{last_exception}')"
    )
    logger.error(final_error_message, exc_info=last_exception)

    # Re-raise the last captured exception so the caller knows the operation failed.
    # 'from None' prevents chaining the exception with the try/except block itself.
    raise last_exception from None


# This generates a few lines of random alphanum chars to inject into the
# system prompt. This lets us use temp=0 while still getting variation
# between trials.
# Temp=0 is important for better performance on deciding moves, and to
# ensure valid json outputs.
def generate_random_seed(n_lines: int = 5, n_chars_per_line: int = 80):
    # Generate x lines of y random alphanumeric characters
    seed_lines = ["".join(random.choices(string.ascii_letters + string.digits, k=n_chars_per_line)) for _ in range(n_lines)]
    random_seed_block = "<RANDOM SEED PLEASE IGNORE>\n" + "\n".join(seed_lines) + "\n</RANDOM SEED>"
    return random_seed_block


def get_prompt_path(prompt_name: str) -> str:
    """Get the appropriate prompt path based on USE_UNFORMATTED_PROMPTS setting.

    Args:
        prompt_name: Base name of the prompt file (e.g., "conversation_instructions.txt")

    Returns:
        str: Either "unformatted/{prompt_name}" or just "{prompt_name}"
    """
    if config.USE_UNFORMATTED_PROMPTS:
        return f"unformatted/{prompt_name}"
    else:
        return prompt_name


def normalize_recipient_name(recipient: str) -> str:
    """Normalize recipient names to handle LLM typos and abbreviations."""
    if not recipient:
        return recipient

    recipient = recipient.upper().strip()

    # Handle common LLM typos and abbreviations found in data
    name_mapping = {
        "EGMANY": "GERMANY",
        "GERMAN": "GERMANY",
        "UK": "ENGLAND",
        "BRIT": "ENGLAND",
        "ENGLAND": "ENGLAND",  # Keep as-is
        "FRANCE": "FRANCE",  # Keep as-is
        "GERMANY": "GERMANY",  # Keep as-is
        "ITALY": "ITALY",  # Keep as-is
        "AUSTRIA": "AUSTRIA",  # Keep as-is
        "RUSSIA": "RUSSIA",  # Keep as-is
        "TURKEY": "TURKEY",  # Keep as-is
        "Germany": "GERMANY",
        "England": "ENGLAND",
        "France": "FRANCE",
        "Italy": "ITALY",
        "Russia": "RUSSIA",
        "Austria": "AUSTRIA",
        "Turkey": "TURKEY",
    }

    normalized = name_mapping.get(recipient, recipient)

    return normalized

def parse_prompts_dir_arg(raw: str | None) -> Dict[str, Path]:
    """
    Resolve --prompts_dir into a mapping {power: Path}.
    Accepts either a single path or 7 comma-separated paths.

    Every path is normalised to an **absolute** Path object
    (using Path(...).expanduser().resolve()) and checked for existence.
    """
    if not raw:
        return {}

    parts = [s.strip() for s in raw.split(",") if s.strip()]
    if len(parts) not in {1, 7}:
        raise ValueError(
            f"--prompts_dir expects 1 or 7 paths, got {len(parts)} "
            f"({raw})"
        )

    # Expand/resolve & verify
    def _norm(p: str) -> Path:
        path = Path(p).expanduser().resolve()
        if not path.is_dir():
            raise FileNotFoundError(f"Prompt directory not found: {path}")
        return path

    if len(parts) == 1:
        path = _norm(parts[0])
        return {pwr: path for pwr in POWERS_ORDER}

    paths = [_norm(p) for p in parts]
    return dict(zip(POWERS_ORDER, paths))

async def atomic_write_json_async(data: dict, filepath: str):
    """Writes a dictionary to a JSON file atomically using async I/O."""
    # Use asyncio.to_thread to run the synchronous atomic_write_json in a thread pool
    # This prevents blocking the event loop while maintaining all the safety guarantees
    await asyncio.to_thread(atomic_write_json, data, filepath)


async def log_llm_response_async(
    log_file_path: str,
    model_name: str,
    power_name: Optional[str],  
    phase: str,
    response_type: str,
    raw_input_prompt: str,  
    raw_response: str,
    success: str,  
):
    """Async version of log_llm_response that runs in a thread pool."""
    await asyncio.to_thread(
        log_llm_response,
        log_file_path,
        model_name,
        power_name,
        phase,
        response_type,
        raw_input_prompt,
        raw_response,
        success
    )




def get_board_state(board_state: dict, game: Game) -> Tuple[str, str]:
    # Build units representation with power status and counts
    units_lines = []
    for p, units in board_state["units"].items():
        units_str   = ", ".join(units)
        units_count = len(units)
        line = f"  {p}: {units_count} unit{'s' if units_count != 1 else ''} – {units_str}"
        if game.powers[p].is_eliminated():
            line += " [ELIMINATED]"
        units_lines.append(line)
    units_repr = "\n".join(units_lines)

    # Build centers representation with power status and counts
    centers_lines = []
    for p, centers in board_state["centers"].items():
        centers_str   = ", ".join(centers)
        centers_count = len(centers)
        line = f"  {p}: {centers_count} supply center{'s' if centers_count != 1 else ''} – {centers_str}"
        if game.powers[p].is_eliminated():
            line += " [ELIMINATED]"
        centers_lines.append(line)
    centers_repr = "\n".join(centers_lines)

    return (units_repr, centers_repr)