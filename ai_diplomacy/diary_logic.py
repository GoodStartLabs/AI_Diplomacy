# ai_diplomacy/diary_logic.py
import logging
import re
from typing import TYPE_CHECKING, Optional

from .utils import run_llm_and_log, log_llm_response

if TYPE_CHECKING:
    from diplomacy import Game
    from .agent import DiplomacyAgent

logger = logging.getLogger(__name__)


def _load_prompt_file(filename: str, prompts_dir: Optional[str] = None) -> str | None:
    """A local copy of the helper from agent.py to avoid circular imports."""
    import os

    try:
        if prompts_dir:
            filepath = os.path.join(prompts_dir, filename)
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            default_prompts_dir = os.path.join(current_dir, "prompts")
            filepath = os.path.join(default_prompts_dir, filename)

        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error loading prompt file {filepath}: {e}")
        return None


async def run_diary_consolidation(
    agent: "DiplomacyAgent",
    game: "Game",
    log_file_path: str,
    entries_to_keep_unsummarized: int = 6,
    prompts_dir: Optional[str] = None,
):
    """
    Consolidate older diary entries while keeping recent ones.
    This is the logic moved from the DiplomacyAgent class.
    """
    logger.info(
        f"[{agent.power_name}] CONSOLIDATION START — "
        f"{len(agent.full_private_diary)} total full entries"
    )

    full_entries = [
        e
        for e in agent.full_private_diary
        if not e.startswith("[CONSOLIDATED HISTORY]")
    ]

    if len(full_entries) <= entries_to_keep_unsummarized:
        agent.private_diary = list(agent.full_private_diary)
        logger.info(
            f"[{agent.power_name}] ≤ {entries_to_keep_unsummarized} full entries — "
            "skipping consolidation"
        )
        return

    boundary_entry = full_entries[-entries_to_keep_unsummarized]
    match = re.search(r"\[[SFWRAB]\s*(\d{4})", boundary_entry)
    if not match:
        logger.error(
            f"[{agent.power_name}] Could not parse year from boundary entry; "
            "aborting consolidation"
        )
        agent.private_diary = list(agent.full_private_diary)
        return

    cutoff_year = int(match.group(1))
    logger.info(f"[{agent.power_name}] Cut-off year for consolidation: {cutoff_year}")

    def _entry_year(entry: str) -> int | None:
        m = re.search(r"\[[SFWRAB]\s*(\d{4})", entry)
        return int(m.group(1)) if m else None

    entries_to_summarize = [
        e
        for e in full_entries
        if (_entry_year(e) is not None and _entry_year(e) < cutoff_year)
    ]
    entries_to_keep = [
        e
        for e in full_entries
        if (_entry_year(e) is None or _entry_year(e) >= cutoff_year)
    ]

    logger.info(
        f"[{agent.power_name}] Summarising {len(entries_to_summarize)} entries; "
        f"keeping {len(entries_to_keep)} recent entries verbatim"
    )

    if not entries_to_summarize:
        agent.private_diary = list(agent.full_private_diary)
        logger.warning(
            f"[{agent.power_name}] No eligible entries to summarise; "
            "context diary left unchanged"
        )
        return

    prompt_template = _load_prompt_file(
        "diary_consolidation_prompt.txt", prompts_dir=prompts_dir
    )
    if not prompt_template:
        logger.error(
            f"[{agent.power_name}] diary_consolidation_prompt.txt missing — aborting"
        )
        return

    prompt = prompt_template.format(
        power_name=agent.power_name,
        full_diary_text="\n\n".join(entries_to_summarize),
    )

    raw_response = ""
    success_flag = "FALSE"
    consolidation_client = None
    try:
        consolidation_client = agent.client

        raw_response = await run_llm_and_log(
            client=consolidation_client,
            prompt=prompt,
            power_name=agent.power_name,
            phase=game.current_short_phase,
            response_type="diary_consolidation",
        )

        consolidated_text = raw_response.strip() if raw_response else ""
        if not consolidated_text:
            raise ValueError("LLM returned empty summary")

        new_summary_entry = f"[CONSOLIDATED HISTORY] {consolidated_text}"
        agent.private_diary = [new_summary_entry] + entries_to_keep
        success_flag = "TRUE"
        logger.info(
            f"[{agent.power_name}] Consolidation complete — "
            f"{len(agent.private_diary)} context entries now"
        )

    except Exception as exc:
        logger.error(
            f"[{agent.power_name}] Diary consolidation failed: {exc}", exc_info=True
        )
    finally:
        log_llm_response(
            log_file_path=log_file_path,
            model_name=(
                consolidation_client.model_name
                if consolidation_client is not None
                else agent.client.model_name
            ),
            power_name=agent.power_name,
            phase=game.current_short_phase,
            response_type="diary_consolidation",
            raw_input_prompt=prompt,
            raw_response=raw_response,
            success=success_flag,
        )

