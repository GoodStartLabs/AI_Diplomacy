"""
experiment_runner.analysis.statistical_game_analysis
----------------------------------------------------

Runs the Statistical Game Analyzer to create per-run / combined CSVs,
then produces a suite of PNG plots:

analysis/
└── statistical_game_analysis/
    ├── individual/
    │   ├── run_00000_game_analysis.csv
    │   └── …
    └── plots/
        ├── game/
        │   ├── final_supply_centers_owned.png
        │   └── …
        ├── game_summary_heatmap.png
        └── phase/
            ├── supply_centers_owned_count.png
            └── …

Complies with experiment-runner’s plug-in contract:
    run(experiment_dir: pathlib.Path, ctx: dict) -> None
"""
from __future__ import annotations

import logging
import re
import json
from pathlib import Path
from typing import List, Any
import math
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba
import pandas as pd
import seaborn as sns

# third-party analyser that creates the CSVs
from analysis.statistical_game_analysis import StatisticalGameAnalyzer  # type: ignore

log = logging.getLogger(__name__)

# ───────────────────────── helpers ──────────────────────────
_SEASON_ORDER = {"S": 0, "F": 1, "W": 2, "A": 3}

_POWER_COLOUR = {
    "AUSTRIA":  "tab:red",
    "ENGLAND":  "tab:blue",
    "FRANCE":   "tab:green",
    "GERMANY":  "tab:purple",
    "ITALY":    "tab:olive",
    "RUSSIA":   "tab:brown",
    "TURKEY":   "tab:orange",
}


def _sanitize(name: str) -> str:
    return re.sub(r"[^\w\-\.]", "_", name)


def _discover_csvs(individual_dir: Path, pattern: str) -> List[Path]:
    return sorted(individual_dir.glob(pattern))


def _numeric_columns(df: pd.DataFrame, extra_exclude: set[str] | None = None) -> List[str]:
    exclude = {
        "game_id",
        "llm_model",
        "power_name",
        "game_phase",
        "analyzed_response_type",
    }
    if extra_exclude:
        exclude |= extra_exclude
    return [c for c in df.select_dtypes("number").columns if c not in exclude]


def _parse_relationships(rel_string: str) -> dict[str, int]:
    """
    "AUSTRIA:-1|FRANCE:2"  →  {"AUSTRIA": -1, "FRANCE": 2}
    Returns empty dict on blank / nan / bad input.
    """
    if not isinstance(rel_string, str) or not rel_string:
        return {}
    out: dict[str, int] = {}
    for part in rel_string.split("|"):
        try:
            pwr, val = part.split(":")
            out[pwr.strip().upper()] = int(val)
        except ValueError:
            continue
    return out


def _phase_sort_key(ph: str) -> tuple[int, int]:
    """
    Sort key that keeps normal phases chronological and forces the literal
    string 'COMPLETED' to the very end.

    • 'S1901M' → (1901, 0)
    • 'COMPLETED' → (9999, 9)
    """
    if ph.upper() == "COMPLETED":
        return (9999, 9)               # always last

    year = int(ph[1:5]) if len(ph) >= 5 and ph[1:5].isdigit() else 0
    season = _SEASON_ORDER.get(ph[0], 9)
    return year, season


def _phase_index(series: pd.Series) -> pd.Series:
    uniq = sorted(series.unique(), key=_phase_sort_key)
    mapping = {ph: i for i, ph in enumerate(uniq)}
    return series.map(mapping)

def _map_game_id_to_run_dir(exp_dir: Path) -> dict[str, str]:
    """
    Reads each runs/run_xxxxx/lmvsgame.json file and returns
    {game_id_string: 'run_xxxxx'}.
    """
    mapping: dict[str, str] = {}
    runs_root = exp_dir / "runs"
    for run_dir in runs_root.glob("run_*"):
        json_path = run_dir / "lmvsgame.json"
        if not json_path.exists():
            continue
        try:
            with json_path.open(encoding="utf-8") as fh:
                data = json.load(fh)
            gid = str(data.get("id", ""))          # use top-level "id"
            if gid:
                mapping[gid] = run_dir.name
        except Exception:                          # corrupt / unreadable → skip
            continue
    return mapping


# ───────────────────────── plots ────────────────────────────
def _plot_game_level(all_games: pd.DataFrame, plot_dir: Path) -> None:
    """
    • Box-plots per metric (hue = power, legend removed).
    • Z-score heat-map: powers × metrics, colour-coded by relative standing.
    """
    plot_dir.mkdir(parents=True, exist_ok=True)
    num_cols = _numeric_columns(all_games)

    # ── per-metric box-plots ──────────────────────────────────────────
    for col in num_cols:
        fig, ax = plt.subplots(figsize=(8, 6))
        sns.boxplot(
            data=all_games,
            x="power_name",
            y=col,
            hue="power_name",
            palette="pastel",
            dodge=False,
            ax=ax,
        )
        leg = ax.get_legend()
        if leg is not None:
            leg.remove()
        ax.set_title(col.replace("_", " ").title())
        fig.tight_layout()
        fig.savefig(plot_dir / f"{_sanitize(col)}.png", dpi=140)
        plt.close(fig)

    # ── summary heat-map (column-wise z-scores) ───────────────────────
    #   1) mean across runs  2) z-score each column
    summary = all_games.groupby("power_name")[num_cols].mean().sort_index()
    zscores = summary.apply(lambda col: (col - col.mean()) / col.std(ddof=0), axis=0)

    fig_w = max(6, len(num_cols) * 0.45 + 2)
    fig, ax = plt.subplots(figsize=(fig_w, 6))
    sns.heatmap(
        zscores,
        cmap="coolwarm",
        center=0,
        linewidths=0.4,
        annot=True,
        fmt=".2f",
        ax=ax,
    )
    ax.set_title("Relative Standing (column-wise z-score)")
    ax.set_ylabel("Power")
    fig.tight_layout()
    fig.savefig(plot_dir.parent / "game_summary_zscore_heatmap.png", dpi=160)
    plt.close(fig)


def _plot_relationships_per_game(
    all_phase: pd.DataFrame,
    root_dir: Path,
    gameid_to_rundir: dict[str, str],
) -> None:
    """
    For each game, create one PNG per *focal* power that shows
        • self-perceived relationship to every other power (solid, full colour)
        • how that other power perceives the focal power   (solid, lighter, thinner)

    The x-axis is dense and specific to each game (0…n-1) with tick labels set
    to the actual phase strings, so there are no gaps no matter which phases
    appear in different runs.

    To keep coincident traces legible, points that would sit on top of one
    another are given a minimal vertical jitter.  “Self” points are nudged
    down (negative), “other” points up (positive).  Powers keep their canonical
    AUSTRIA → TURKEY ordering within each direction so that the visual code is
    stable across games.
    """
    if all_phase.empty or "game_id" not in all_phase.columns:
        return

    # ── ensure rel_dict column exists ────────────────────────────────────
    if "rel_dict" not in all_phase.columns:
        all_phase = all_phase.copy()
        all_phase["rel_dict"] = all_phase["relationships"].apply(_parse_relationships)

    powers = list(_POWER_COLOUR.keys())          # AUSTRIA … TURKEY
    power_order = {p: i for i, p in enumerate(powers)}
    jitter_step = 0.04                          # vertical gap between stacked points

    for game_id, game_df in all_phase.groupby("game_id", sort=False):
        # ── make sure rel_dict exists ───────────────────────────────
        if "rel_dict" not in game_df.columns:
            game_df = game_df.copy()
            game_df["rel_dict"] = game_df["relationships"].apply(_parse_relationships)

        # ── NEW: discard rows with no relationship info ────────────
        game_df = game_df[game_df["rel_dict"].apply(bool)]
        # ── keep only MOVE phases; drop retreat (R) and adjustment (A) ─────
        game_df = game_df[game_df["game_phase"].str.upper().str.endswith("M")]
        if game_df.empty:               # nothing left to plot
            continue

        # ── dense phase ordering (0 … n-1) on the surviving phases ─
        phase_labels = sorted(game_df["game_phase"].unique(), key=_phase_sort_key)
        phase_to_x   = {ph: idx for idx, ph in enumerate(phase_labels)}
        fig_w = max(8, len(phase_labels) * 0.1 + 4)

        # quick lookup: (phase, power)  →  rel_dict
        rel_lookup = {
            (row.game_phase, row.power_name): row.rel_dict
            for row in game_df.itertuples()
        }

        run_label = gameid_to_rundir.get(str(game_id), f"game_{_sanitize(str(game_id))}")
        plot_dir  = root_dir / run_label
        plot_dir.mkdir(parents=True, exist_ok=True)

        for focal in powers:
            # ── pre-gather every trace so we can resolve collisions first ─
            traces: dict[tuple[str, str], dict[str, Any]] = {}
            for other in powers:
                if other == focal:
                    continue

                x_vals: list[int] = []
                self_vals:  list[float] = []
                other_vals: list[float] = []

                for ph in phase_labels:
                    x_vals.append(phase_to_x[ph])

                    # focal’s view of "other"
                    self_rels = rel_lookup.get((ph, focal), {})
                    self_vals.append(self_rels.get(other, float("nan")))

                    # other’s view of focal
                    other_rels = rel_lookup.get((ph, other), {})
                    other_vals.append(other_rels.get(focal, float("nan")))

                traces[(other, "self")]  = dict(x=x_vals, y=self_vals)
                traces[(other, "other")] = dict(x=x_vals, y=other_vals)

            # ── collision-aware jitter: build offset matrix ───────────────
            offsets: dict[tuple[str, str], list[float]] = {
                key: [0.0] * len(phase_labels) for key in traces
            }

            for idx in range(len(phase_labels)):
                # group all non-NaN points by their integer y level
                level_buckets: dict[float, list[tuple[str, str]]] = {}
                for key, data in traces.items():
                    y = data["y"][idx]
                    if not math.isnan(y):
                        level_buckets.setdefault(y, []).append(key)

                # de-stack each bucket independently
                for y_val, bucket in level_buckets.items():
                    if len(bucket) == 1:
                        continue  # nothing overlaps here

                    # split into self vs other, then power order
                    self_keys  = sorted(
                        [k for k in bucket if k[1] == "self"],
                        key=lambda k: power_order[k[0]],
                    )
                    other_keys = sorted(
                        [k for k in bucket if k[1] == "other"],
                        key=lambda k: power_order[k[0]],
                    )

                    # negative jitter for self
                    for j, key in enumerate(self_keys, start=1):
                        offsets[key][idx] = -j * jitter_step
                    # positive jitter for other
                    for j, key in enumerate(other_keys):
                        offsets[key][idx] = j * jitter_step  # first "other" gets 0

            # ── finally plot using the jittered values ───────────────────
            plt.figure(figsize=(fig_w, 5.5))
            y_min, y_max = -2, 2  # track extremes for ylim

            for other in powers:
                if other == focal:
                    continue

                for kind in ("self", "other"):
                    key   = (other, kind)
                    data  = traces[key]
                    y_off = [
                        v + off if not math.isnan(v) else v
                        for v, off in zip(data["y"], offsets[key])
                    ]

                    # track axis range
                    for v in y_off:
                        if not math.isnan(v):
                            y_min = min(y_min, v)
                            y_max = max(y_max, v)

                    base_colour = _POWER_COLOUR[other]
                    colour      = (
                        base_colour
                        if kind == "self"
                        else to_rgba(base_colour, alpha=0.35)
                    )

                    # ── “double” a lone point so it shows up as a short flat line ──
                    finite_pts = [(x, y) for x, y in zip(data["x"], y_off) if not math.isnan(y)]
                    if len(finite_pts) == 1:
                        x0, y0 = finite_pts[0]
                        xs = [x0 - 0.05, x0 + 0.05]   # tiny horizontal spread
                        ys = [y0, y0]
                    else:
                        xs, ys = data["x"], y_off

                    plt.plot(
                        xs,
                        ys,
                        label=f"{other} ({kind})",
                        color=colour,
                        linewidth=2,
                    )

            plt.xticks(list(phase_to_x.values()), phase_labels, rotation=90, fontsize=8)
            margin = 0.1
            plt.ylim(y_min - margin, y_max + margin)

            # ── custom y-tick labels ────────────────────────────────────
            plt.yticks(
                [-2, -1, 0, 1, 2],
                ["Enemy", "Unfriendly", "Neutral", "Friendly", "Ally"],
            )

            plt.ylabel("Relationship value")
            plt.xlabel("Game phase")
            plt.title(f"{focal} Relationships – {run_label}")
            plt.legend(ncol=3, fontsize=8)
            plt.tight_layout()

            plt.savefig(plot_dir / f"{focal}_relationships.png", dpi=140)
            plt.close()




def _plot_phase_level(
    all_phase: pd.DataFrame,
    plot_dir: Path,
    title_suffix: str = "",
) -> None:
    """
    Plots aggregated phase metrics.  If *title_suffix* is supplied it is
    appended to each chart title — handy for per-run plots.
    """
    if all_phase.empty:
        return
    plot_dir.mkdir(parents=True, exist_ok=True)

    if "phase_index" not in all_phase.columns:
        all_phase["phase_index"] = _phase_index(all_phase["game_phase"])

    num_cols = _numeric_columns(all_phase)

    agg = (
        all_phase
        .groupby(["phase_index", "game_phase", "power_name"], as_index=False)[num_cols]
        .mean()
    )

    n_phases = agg["phase_index"].nunique()
    fig_w = max(8, n_phases * 0.1 + 4)

    for col in num_cols:
        plt.figure(figsize=(fig_w, 6))
        sns.lineplot(
            data=agg,
            x="phase_index",
            y=col,
            hue="power_name",
            marker="o",
        )

        phases_sorted = (
            agg.drop_duplicates("phase_index")
            .sort_values("phase_index")[["phase_index", "game_phase"]]
        )
        plt.xticks(
            phases_sorted["phase_index"],
            phases_sorted["game_phase"],
            rotation=90,
            fontsize=8,
        )
        title = col.replace("_", " ").title()
        if title_suffix:
            title = f"{title} – {title_suffix}"
        plt.title(title)
        plt.xlabel("Game Phase")
        plt.tight_layout()
        plt.savefig(plot_dir / f"{_sanitize(col)}.png", dpi=140)
        plt.close()


def _plot_phase_level_per_game(
    all_phase: pd.DataFrame,
    root_dir: Path,
    gameid_to_rundir: dict[str, str],
) -> None:
    """
    Writes one folder of phase-plots per iteration.
    Folder name and chart titles use the run directory (e.g. run_00003).
    """
    if all_phase.empty or "game_id" not in all_phase.columns:
        return

    for game_id, sub in all_phase.groupby("game_id"):
        run_label = gameid_to_rundir.get(str(game_id), f"game_{_sanitize(str(game_id))}")
        target = root_dir / run_label

        # ── critical change: drop global phase_index so we rebuild a dense one ──
        sub = sub.copy().drop(columns=["phase_index"], errors="ignore")

        _plot_phase_level(sub, target, title_suffix=run_label)




# ───────────────────────── entry-point ─────────────────────────
def run(experiment_dir: Path, ctx: dict) -> None:  # pylint: disable=unused-argument
    root = experiment_dir / "analysis" / "statistical_game_analysis"
    indiv_dir = root / "individual"
    plots_root = root / "plots"

    # 1. (re)generate CSVs
    try:
        StatisticalGameAnalyzer().analyze_multiple_folders(
            str(experiment_dir / "runs"), str(root)
        )
        log.info("statistical_game_analysis: CSV generation complete")
    except Exception as exc:  # noqa: broad-except
        log.exception("statistical_game_analysis: CSV generation failed – %s", exc)
        return

    # 2. load CSVs
    game_csvs = _discover_csvs(indiv_dir, "*_game_analysis.csv")
    phase_csvs = _discover_csvs(indiv_dir, "*_phase_analysis.csv")

    if not game_csvs:
        log.warning("statistical_game_analysis: no *_game_analysis.csv found")
        return

    all_game_df = pd.concat((pd.read_csv(p) for p in game_csvs), ignore_index=True)
    all_phase_df = (
        pd.concat((pd.read_csv(p) for p in phase_csvs), ignore_index=True)
        if phase_csvs else pd.DataFrame()
    )

    # 3. plots
    sns.set_theme(style="whitegrid")
    log.info("Generating aggregated plots")
    _plot_game_level(all_game_df, plots_root / "game")
    _plot_phase_level(all_phase_df, plots_root / "phase")    
    game_map = _map_game_id_to_run_dir(experiment_dir)
    log.info("Generating per-game plots")
    _plot_phase_level_per_game(
        all_phase_df,
        plots_root / "phase_by_game",
        game_map,
    )
    log.info("Generating relationship plots")
    _plot_relationships_per_game(
        all_phase_df,
        plots_root / "relationships",
        game_map,
    )


    log.info("statistical_game_analysis: plots written → %s", plots_root)
