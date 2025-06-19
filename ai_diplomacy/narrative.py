"""Generate engaging narrative summaries and transparently patch the Diplomacy
Game engine to use them.

Usage: simply import `ai_diplomacy.narrative` *before* the game loop starts
(e.g. at the top of `lm_game.py`).  Import side-effects monkey-patch
`diplomacy.engine.game.Game._generate_phase_summary` so that:

1. The original (statistical) summary logic still runs.
2. The returned text is stored in `GamePhaseData.statistical_summary`.
3. A short narrative is produced via OpenAI `o3` and saved as the main
   `.summary`.
"""

from loguru import logger
import os
from typing import Callable

from openai import OpenAI  # Import the new OpenAI client
from diplomacy.engine.game import Game


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OPENAI_MODEL = os.getenv("AI_DIPLOMACY_NARRATIVE_MODEL", "gpt-o3")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY not set – narrative summaries will be stubbed.")

# ---------------------------------------------------------------------------
# Helper to call the model synchronously
# ---------------------------------------------------------------------------


def _call_openai(statistical_summary: str, phase_key: str) -> str:
    """Return a 2–4 sentence spectator-friendly narrative."""
    if not OPENAI_API_KEY:
        return "(Narrative generation disabled – missing API key)."

    system = (
        "You are an energetic e-sports commentator narrating a game of Diplomacy. "
        "Turn the provided phase recap into a concise, thrilling story (max 4 sentences). "
        "Highlight pivotal moves, supply-center swings, betrayals, and momentum shifts."
    )
    user = f"PHASE {phase_key}\n\nSTATISTICAL SUMMARY:\n{statistical_summary}\n\nNow narrate this phase for spectators."

    try:
        # Initialize the OpenAI client with the API key
        client = OpenAI(api_key=OPENAI_API_KEY)

        # Use the new API format
        resp = client.chat.completions.create(
            model="o3",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:  # Broad – we only log and degrade gracefully
        logger.error("Narrative generation failed: %s", exc, exc_info=True)
        return "(Narrative generation failed)"


# ---------------------------------------------------------------------------
# Patch _generate_phase_summary
# ---------------------------------------------------------------------------

_original_gps: Callable = Game._generate_phase_summary  # type: ignore[attr-defined]


def _patched_generate_phase_summary(self: Game, phase_key, summary_callback=None):  # type: ignore[override]
    # 1) Call original implementation → statistical summary
    statistical = _original_gps(self, phase_key, summary_callback)
    logger.debug(f"[{phase_key}] Original summary returned: {statistical!r}")

    # 2) Persist statistical summary separately
    phase_data = None
    try:
        phase_data = self.get_phase_from_history(str(phase_key))
        if hasattr(phase_data, "statistical_summary"):
            logger.debug(
                f"[{phase_key}] Assigning to phase_data.statistical_summary: {statistical!r}"
            )
            phase_data.statistical_summary = statistical  # type: ignore[attr-defined]
        else:
            logger.warning(
                f"[{phase_key}] phase_data object does not have attribute 'statistical_summary'. Type: {type(phase_data)}"
            )
    except Exception as exc:
        logger.warning(
            "Could not retrieve phase_data or store statistical_summary for %s: %s",
            phase_key,
            exc,
        )

    # 3) Generate narrative summary
    narrative = _call_openai(statistical, phase_key)

    # 4) Save narrative as the canonical summary
    try:
        if phase_data:
            phase_data.summary = narrative  # type: ignore[attr-defined]
            self.phase_summaries[str(phase_key)] = narrative  # type: ignore[attr-defined]
            logger.debug(f"[{phase_key}] Narrative summary stored successfully.")
        else:
            logger.warning(
                f"[{phase_key}] Cannot store narrative summary because phase_data is None."
            )
    except Exception as exc:
        logger.warning("Could not store narrative summary for %s: %s", phase_key, exc)

    return narrative


# Monkey-patch
Game._generate_phase_summary = _patched_generate_phase_summary  # type: ignore[assignment]

logger.info("Game._generate_phase_summary patched with narrative generation.")

