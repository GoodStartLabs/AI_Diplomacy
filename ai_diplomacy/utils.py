from dotenv import load_dotenv
import logging
import os
from typing import Dict, Optional
import random

logger = logging.getLogger("utils")
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

load_dotenv()

MODEL_OPTIONS = [
    'o3-mini', 
    'claude-3-5-sonnet-latest',
    'gemini-2.0-flash',
    'gemini-2.0-flash-lite',
    'gpt-4o',
    'gpt-4o-mini',
    'claude-3-5-haiku-20241022'
]


def assign_models_to_powers(seed: Optional[int] = None) -> Dict[str, str]:
    """
    Example usage: define which model each power uses.
    Return a dict: { power_name: model_id, ... }
    POWERS = ['AUSTRIA', 'ENGLAND', 'FRANCE', 'GERMANY', 'ITALY', 'RUSSIA', 'TURKEY']
    """
    
    if seed is not None:
        random.seed(seed)
        
    # get random perm
    random.shuffle(MODEL_OPTIONS)
    
    return {
        "AUSTRIA": MODEL_OPTIONS[0],
        "ENGLAND": MODEL_OPTIONS[1],
        "FRANCE": MODEL_OPTIONS[2],
        "GERMANY": MODEL_OPTIONS[3],
        "ITALY": MODEL_OPTIONS[4],
        "RUSSIA": MODEL_OPTIONS[5],
        "TURKEY": MODEL_OPTIONS[6],
    }


def gather_possible_orders(game, power_name):
    """
    Returns a dictionary mapping each orderable location to the list of valid orders.
    """
    orderable_locs = game.get_orderable_locations(power_name)
    all_possible = game.get_all_possible_orders()

    result = {}
    for loc in orderable_locs:
        result[loc] = all_possible.get(loc, [])
    return result


def get_valid_orders(
    game,
    client,
    board_state,
    power_name,
    possible_orders,
    game_history,
    model_error_stats,
):
    """
    Tries up to 'max_retries' to generate and validate orders.
    If invalid, we append the error feedback to the conversation
    context for the next retry. If still invalid, return fallback.
    """

    # Ask the LLM for orders
    orders = client.get_orders(
        game=game,
        board_state=board_state,
        power_name=power_name,
        possible_orders=possible_orders,
        conversation_text=game_history,
        model_error_stats=model_error_stats,
    )

    # Validate each order
    for move in orders:
        # Example move: "A PAR H" -> unit="A PAR", order_part="H"
        tokens = move.split(" ", 2)
        if len(tokens) < 3:
            invalid_info.append(
                f"Order '{move}' is malformed; expected 'A PAR H' style."
            )
            continue
        unit = " ".join(tokens[:2])  # e.g. "A PAR"
        order_part = tokens[2]  # e.g. "H" or "S A MAR"

        # Use the internal game validation method
        if order_part == "B":
            validity = 1  # hack because game._valid_order doesn't support 'B'
        else:
            validity = game._valid_order(
                game.powers[power_name], unit, order_part, report=1
            )

        if validity == 1:
            # All orders are fully valid
            return orders
        else:
            logger.warning(
                f"[{power_name}] failed to produce a valid order, using fallback."
            )
            model_error_stats[power_name]["order_decoding_errors"] += 1
            fallback = client.fallback_orders(possible_orders)
            return fallback
