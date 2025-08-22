"""
Aggregates results across all runs and writes:

• analysis/aggregated_results.csv
• analysis/score_summary_by_power.csv
• analysis/results_summary.png        (if matplotlib available)
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

log = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
#  Helpers copied (and lightly cleaned) from run_games.py                     #
# --------------------------------------------------------------------------- #
def _extract_diplomacy_results(game_json: Path) -> Dict[str, Dict[str, Any]]:
    with game_json.open("r", encoding="utf-8") as fh:
        gd = json.load(fh)

    phases = gd.get("phases", [])
    if not phases:
        raise ValueError("no phases")

    first_state = phases[0]["state"]
    last_state = phases[-1]["state"]

    powers = (
        list(first_state.get("homes", {}).keys())
        or list(first_state.get("centers", {}).keys())
    )
    if not powers:
        raise ValueError("cannot determine powers")

    scs_to_win = 18
    solo_winner = next(
        (p for p, sc in last_state["centers"].items() if len(sc) >= scs_to_win), None
    )

    results: Dict[str, Dict[str, Any]] = {}
    for p in powers:
        sc_count = len(last_state["centers"].get(p, []))
        units = len(last_state["units"].get(p, []))

        if solo_winner:
            if p == solo_winner:
                outcome, cat = f"Won solo", "Solo Win"
            else:
                outcome, cat = f"Lost to {solo_winner}", "Loss"
        elif sc_count == 0 and units == 0:
            outcome, cat = "Eliminated", "Eliminated"
        else:
            outcome, cat = "Ongoing/Draw", "Ongoing/Abandoned/Draw"

        results[p] = {
            "OutcomeCategory": cat,
            "StatusDetail": outcome,
            "SupplyCenters": sc_count,
            "LastPhase": last_state["name"],
        }
    return results


# simplistic "Diplobench" scoring from previous discussion ------------------ #
def _year(name: str) -> int | None:
    m = re.search(r"(\d{4})", name)
    return int(m.group(1)) if m else None


def _score_game(game_json: Path) -> Dict[str, int]:
    with open(game_json, "r") as fh:
        game = json.load(fh)
    phases = game["phases"]
    if not phases:
        return {}

    start = _year(phases[0]["state"]["name"])
    end_year = _year(phases[-1]["state"]["name"]) or start
    max_turns = (end_year - start + 1) if start is not None else len(phases)

    last_state = phases[-1]["state"]
    solo_winner = next(
        (p for p, scs in last_state["centers"].items() if len(scs) >= 18), None
    )

    elim_turn: Dict[str, int | None] = {}
    for p in last_state["centers"].keys():
        e_turn = None
        for idx, ph in enumerate(phases):
            if not ph["state"]["centers"].get(p, []):
                yr = _year(ph["state"]["name"]) or 0
                e_turn = (yr - start + 1) if start is not None else idx + 1
                break
        elim_turn[p] = e_turn

    scores: Dict[str, int] = {}
    for p, scs in last_state["centers"].items():
        if p == solo_winner:
            win_turn = (end_year - start + 1) if start is not None else len(phases)
            scores[p] = max_turns + 17 + (max_turns - win_turn)
        elif solo_winner:
            # losers in a solo game
            yr_win = _year(phases[-1]["state"]["name"]) or end_year
            turn_win = (yr_win - start + 1) if start is not None else len(phases)
            scores[p] = turn_win
        else:
            if elim_turn[p] is None:
                scores[p] = max_turns + len(scs)
            else:
                scores[p] = elim_turn[p]
    return scores


# --------------------------------------------------------------------------- #
#  Public entry point                                                         #
# --------------------------------------------------------------------------- #
def run(exp_dir: Path, ctx: dict):  # pylint: disable=unused-argument
    analysis_dir = exp_dir / "analysis"
    analysis_dir.mkdir(exist_ok=True)

    rows: List[Dict[str, Any]] = []
    for run_dir in (exp_dir / "runs").iterdir():
        game_json = run_dir / "lmvsgame.json"
        if not game_json.exists():
            continue

        gid = run_dir.name
        try:
            res = _extract_diplomacy_results(game_json)
        except Exception as e:  # noqa: broad-except
            log.warning("Could not parse %s (%s)", game_json, e)
            continue

        scores = _score_game(game_json)
        for pwr, info in res.items():
            out = {"GameID": gid, "Power": pwr, **info, "Score": scores.get(pwr, None)}
            rows.append(out)

    if not rows:
        log.warning("summary: no parsable runs found")
        return

    df = pd.DataFrame(rows)
    out_csv = analysis_dir / "aggregated_results.csv"
    df.to_csv(out_csv, index=False)

    summary = (
        df.groupby("Power")["Score"]
        .agg(["mean", "median", "count"])
        .reset_index()
        .rename(columns={"count": "n"})
    )
    summary.to_csv(analysis_dir / "score_summary_by_power.csv", index=False)

    log.info("summary: wrote %s rows to %s", len(df), out_csv)

    # Optional charts
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns

        sns.set_style("whitegrid")
        plt.figure(figsize=(10, 7))
        sns.boxplot(x="Power", y="SupplyCenters", data=df, palette="pastel")
        plt.ylim(0, 18)
        plt.title("Supply-center distribution")
        plt.savefig(analysis_dir / "results_summary.png", dpi=150)
        plt.close()
        log.info("summary: chart saved")
    except Exception as e:  # noqa: broad-except
        log.debug("Chart generation skipped (%s)", e)
