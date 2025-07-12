# ai_diplomacy/diary_logic.py
import logging
import re
from typing import TYPE_CHECKING, Optional

from .utils import run_llm_and_log, log_llm_response, load_prompt

if TYPE_CHECKING:
    from diplomacy import Game
    from .agent import DiplomacyAgent

logger = logging.getLogger(__name__)

async def run_diary_consolidation(
    agent: "DiplomacyAgent",
    game: "Game",
    log_file_path: str,
    years_to_keep_unsummarised: int = 1,
    prompts_dir: Optional[str] = None,
):
    """
    Consolidate older diary entries while keeping recent ones.

    Parameters
    ----------
    agent : DiplomacyAgent
    game  : Game
    log_file_path : str
    years_to_keep_unsummarised : int, default 1
        Number of *distinct years* whose entries remain verbatim.
    prompts_dir : Optional[str]
    """
    logger.info(
        f"[{agent.power_name}] CONSOLIDATION START — "
        f"{len(agent.full_private_diary)} total full entries"
    )

    # Remove any earlier consolidated block first
    full_entries = [
        e for e in agent.full_private_diary
        if not e.startswith("[CONSOLIDATED HISTORY]")
    ]

    if not full_entries:
        agent.private_diary = []
        logger.warning(f"[{agent.power_name}] No diary entries found")
        return

    # Extract years by scanning from newest to oldest
    year_re = re.compile(r"\[[SFWRAB]\s*(\d{4})")  # matches “[S1901”, “[F1902”…”
    recent_years: list[int] = []

    for entry in reversed(full_entries):            # newest last
        match = year_re.search(entry)
        if not match:
            # Lines without a year tag are considered “dateless”; keep them
            continue
        yr = int(match.group(1))
        if yr not in recent_years:
            recent_years.append(yr)
        if len(recent_years) >= years_to_keep_unsummarised:
            break

    # If every distinct year falls inside the keep-window, skip consolidation
    all_years = {
        int(m.group(1))
        for e in full_entries
        if (m := year_re.search(e))
    }
    if len(all_years - set(recent_years)) == 0:
        agent.private_diary = list(agent.full_private_diary)
        logger.info(
            f"[{agent.power_name}] ≤ {years_to_keep_unsummarised} distinct years "
            "— skipping consolidation"
        )
        return

    # Partition entries
    keep_set = set(recent_years)

    def _entry_year(entry: str) -> Optional[int]:
        m = year_re.search(entry)
        return int(m.group(1)) if m else None

    entries_to_keep = [e for e in full_entries if (_entry_year(e) in keep_set)]
    entries_to_summarise = [e for e in full_entries if (_entry_year(e) not in keep_set)]

    logger.info(
        f"[{agent.power_name}] Summarising {len(entries_to_summarise)} entries "
        f"from years < {min(keep_set)}; keeping {len(entries_to_keep)} recent entries verbatim"
    )

    if not entries_to_summarise:
        agent.private_diary = list(agent.full_private_diary)
        logger.warning(
            f"[{agent.power_name}] No eligible entries to summarise; context diary left unchanged"
        )
        return

    prompt_template = load_prompt("diary_consolidation_prompt.txt", prompts_dir=prompts_dir)
    if not prompt_template:
        logger.error(f"[{agent.power_name}] diary_consolidation_prompt.txt missing — aborting")
        return

    prompt = prompt_template.format(
        power_name=agent.power_name,
        full_diary_text="\n\n".join(entries_to_summarise),
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
        logger.error(f"[{agent.power_name}] Diary consolidation failed: {exc}", exc_info=True)
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
