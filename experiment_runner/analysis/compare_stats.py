"""
experiment_runner.analysis.compare_stats
----------------------------------------

Compares two completed Diplomacy experiments, printing every metric
whose confidence interval (1 – α) excludes 0.

Derived “maximum‐ever” metrics
• max_supply_centers_owned       – per-power max across phases
• max_territories_controlled     – per-power max across phases
• max_military_units             – per-power max across phases
• max_game_score                 – *game-level* max across powers
  (only used in the aggregated-across-powers comparison)

All CLI semantics, CSV outputs, significance tests, etc., remain intact.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats import multitest as smm
from statsmodels.stats import power as smp

import warnings
try:                                     # present from SciPy ≥ 1.10
    from scipy._lib._util import DegenerateDataWarning
except Exception:                        # fallback for older SciPy
    class DegenerateDataWarning(UserWarning):
        pass

warnings.filterwarnings(
    "ignore",
    category=RuntimeWarning,
    message="invalid value encountered in scalar divide",
)
warnings.filterwarnings(
    "ignore",
    category=RuntimeWarning,
    message="Precision loss occurred in moment calculation",
)
warnings.filterwarnings(
    "ignore",
    category=RuntimeWarning,
    message="The BCa confidence interval cannot be calculated.",
)

warnings.filterwarnings("ignore", category=DegenerateDataWarning)

# ───────────────────────── helpers ──────────────────────────
_EXCLUDE: set[str] = {
    "game_id",
    "llm_model",
    "power_name",
    "game_phase",
    "analyzed_response_type",
}

# Metrics that should use MAX when collapsing to one value per game
_MAX_METRICS: set[str] = {
    "max_supply_centers_owned",
    "max_territories_controlled",
    "max_game_score",          # derived below
    "max_military_units",
}

# Metrics that are *not* shown in the per-power breakdown
_PER_POWER_SKIP: set[str] = {
    "max_game_score",          # meaningful only at game level
}


def _numeric_columns(df: pd.DataFrame) -> List[str]:
    return [c for c in df.select_dtypes("number").columns if c not in _EXCLUDE]


# ──────────────────────── data loading ───────────────────────
def _load_games(exp: Path) -> pd.DataFrame:
    """
    Return a DataFrame with one row per (game_id, power_name) containing
    all numeric columns from *_game_analysis.csv plus these derived columns:

        max_supply_centers_owned       – per-power max across phases
        max_territories_controlled     – per-power max across phases
        max_military_units             – per-power max across phases
        max_game_score                 – game-level max across powers
    """
    root = exp / "analysis"

    # ----------- game-level CSVs -----------------------------------------
    game_csvs = list(root.rglob("*_game_analysis.csv"))
    if not game_csvs:
        raise FileNotFoundError(f"no *_game_analysis.csv found under {root}")
    df_game = pd.concat((pd.read_csv(p) for p in game_csvs), ignore_index=True)

    # ----------- derive max_game_score -----------------------------------
    if "game_score" in df_game.columns:
        df_game["max_game_score"] = (
            df_game.groupby("game_id")["game_score"].transform("max")
        )
    else:
        df_game["max_game_score"] = np.nan

    # ----------- per-power maxima from phase files -----------------------
    phase_csvs = list(root.rglob("*_phase_analysis.csv"))
    if phase_csvs:
        df_phase = pd.concat((pd.read_csv(p) for p in phase_csvs), ignore_index=True)
        mapping = {
            "supply_centers_owned_count": "max_supply_centers_owned",
            "territories_controlled_count": "max_territories_controlled",
            "military_units_count": "max_military_units",
        }
        present = [c for c in mapping if c in df_phase.columns]
        if present:
            max_df = (
                df_phase.groupby(["game_id", "power_name"])[present]
                .max()
                .rename(columns={c: mapping[c] for c in present})
                .reset_index()
            )
            df_game = df_game.merge(max_df, on=["game_id", "power_name"], how="left")

    # ----------- guarantee all max-columns exist -------------------------
    for col in _MAX_METRICS:
        if col not in df_game.columns:
            df_game[col] = np.nan

    # ----------- critical de-duplication (fixes doubled n) ---------------
    df_game = df_game.drop_duplicates(subset=["game_id", "power_name"], keep="first")

    return df_game


# ───────────────── Advanced Statistics Helpers ──────────────────
def _bayesian_t_test(a: np.ndarray, b: np.ndarray, alpha: float, n_samples: int = 10000):
    """Perform a simple Bayesian t-test assuming uninformative priors."""
    def posterior_samples(data):
        n, mean, var = len(data), np.mean(data), np.var(data, ddof=1)
        if n == 0 or var == 0: return np.full(n_samples, mean) # Handle edge cases
        # Posterior parameters for Normal-Inverse-Gamma
        mu_n, nu_n, alpha_n, beta_n = mean, n, n / 2, (n / 2) * var
        # Sample from posterior
        post_var = stats.invgamma.rvs(a=alpha_n, scale=beta_n, size=n_samples, random_state=0)
        post_mean = stats.norm.rvs(loc=mu_n, scale=np.sqrt(post_var / nu_n), size=n_samples, random_state=1)
        return post_mean

    try:
        post_a, post_b = posterior_samples(a), posterior_samples(b)
        diff_samples = post_b - post_a
        post_mean_diff = np.mean(diff_samples)
        ci_low, ci_high = np.percentile(diff_samples, [100 * alpha / 2, 100 * (1 - alpha / 2)])
        prob_b_gt_a = np.mean(diff_samples > 0)
        return {
            "Bayes_Post_Mean_Diff": post_mean_diff,
            "Bayes_CI_low": ci_low,
            "Bayes_CI_high": ci_high,
            "Bayes_Prob_B_gt_A": prob_b_gt_a,
        }
    except Exception:
        return {k: np.nan for k in ["Bayes_Post_Mean_Diff", "Bayes_CI_low", "Bayes_CI_high", "Bayes_Prob_B_gt_A"]}


# ───────────────────── Welch statistics ──────────────────────
def _welch(a: np.ndarray, b: np.ndarray, alpha: float) -> Dict:
    # --- Frequentist Welch's t-test ---
    _t, p_val = stats.ttest_ind(a, b, equal_var=False)
    mean_a, mean_b = a.mean(), b.mean()
    diff = mean_b - mean_a
    
    s1, s2 = a.var(ddof=1), b.var(ddof=1)
    n1, n2 = len(a), len(b)
    se = np.sqrt(s1/n1 + s2/n2)
    df = (s1/n1 + s2/n2)**2 / ((s1/n1)**2/(n1-1) + (s2/n2)**2/(n2-1))
    ci = stats.t.ppf(1 - alpha/2, df) * se
    
    # --- Standard Deviations and Cohen's d ---
    sd_a, sd_b = a.std(ddof=1), b.std(ddof=1)
    pooled_sd = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
    cohen_d = diff / pooled_sd if pooled_sd else np.nan

    # --- Normality/Symmetry Diagnostics ---
    skew_a, kurt_a = stats.skew(a), stats.kurtosis(a)
    skew_b, kurt_b = stats.skew(b), stats.kurtosis(b)

    # --- Non-parametric p-value (Permutation Test) ---
    try:
        perm_res = stats.permutation_test((a, b), lambda x, y: np.mean(y) - np.mean(x), n_resamples=9999, random_state=0)
        p_perm = perm_res.pvalue
    except Exception:
        p_perm = np.nan

    # --- Power for a minimally interesting effect (d=0.5) ---
    try:
        power = smp.TTestIndPower().solve_power(effect_size=0.5, nobs1=len(a), alpha=alpha, ratio=len(b)/len(a))
    except Exception:
        power = np.nan

    # --- Robust location estimate (Median difference with bootstrap CI) ---
    try:
        median_diff = np.median(b) - np.median(a)
        res = stats.bootstrap((a, b), lambda x, y: np.median(y) - np.median(x),
                              confidence_level=1-alpha, method='BCa', n_resamples=2499, random_state=0)
        median_ci_low, median_ci_high = res.confidence_interval
    except Exception:
        median_diff, median_ci_low, median_ci_high = np.nan, np.nan, np.nan

    # --- Leave-one-out influence summary ---
    try:
        loo_diffs_a = [np.mean(b) - np.mean(np.delete(a, i)) for i in range(len(a))]
        loo_diffs_b = [np.mean(np.delete(b, i)) - np.mean(a) for i in range(len(b))]
        all_loo_diffs = loo_diffs_a + loo_diffs_b
        loo_diff_min, loo_diff_max = np.min(all_loo_diffs), np.max(all_loo_diffs)
    except Exception:
        loo_diff_min, loo_diff_max = np.nan, np.nan

    # --- Bayesian analysis ---
    bayes_results = _bayesian_t_test(a, b, alpha)

    return {
        "Mean_A": mean_a, "Mean_B": mean_b, "Diff": diff,
        "SD_A": sd_a, "SD_B": sd_b,
        "SE_diff": se,
        "CI_low": diff - ci, "CI_high": diff + ci,
        "p_value": p_val, "p_perm": p_perm,
        "Cohen_d": cohen_d,
        "n_A": len(a), "n_B": len(b),
        "Skew_A": skew_a, "Kurtosis_A": kurt_a,
        "Skew_B": skew_b, "Kurtosis_B": kurt_b,
        "Power_d_0.5": power,
        "Median_Diff": median_diff, "Median_Diff_CI_low": median_ci_low, "Median_Diff_CI_high": median_ci_high,
        "LOO_Diff_min": loo_diff_min, "LOO_Diff_max": loo_diff_max,
        **bayes_results,
    }


# ───────────────── console helpers ───────────────────────────
def _fmt_row(label: str, r: Dict, width: int, ci_label: str) -> str:
    ci = f"[{r['CI_low']:+.2f}, {r['CI_high']:+.2f}]"
    p_perm_val = r.get('p_perm', np.nan)
    return (
        f"  {label:<{width}} "
        f"{r['Diff']:+6.2f}  "
        f"({r['Mean_A']:.2f} → {r['Mean_B']:.2f})   "
        f"{ci_label} {ci:<17}  "
        f"p={r['p_value']:.4g} "
        f"(p_perm={p_perm_val:.3f})   "
        f"d={r['Cohen_d']:+.2f}"
    )


def _print_hdr(title: str) -> None:
    print(f"\n{title}")
    print("─" * len(title))


def _significant(df: pd.DataFrame, alpha: float) -> pd.DataFrame:
    keep = (
        ((df["CI_low"] > 0) & (df["CI_high"] > 0))
        | ((df["CI_low"] < 0) & (df["CI_high"] < 0))
        | (df["p_value"] < alpha)
    )
    return df[keep].sort_values("p_value").reset_index(drop=True)


# ---------- phase-level helpers -----------------------------------------
def _load_phase(exp: Path) -> pd.DataFrame:
    root = exp / "analysis"
    phase_csvs = list(root.rglob("*_phase_analysis.csv"))
    if not phase_csvs:
        raise FileNotFoundError(f"no *_phase_analysis.csv found under {root}")
    return pd.concat((pd.read_csv(p) for p in phase_csvs), ignore_index=True)


def _phase_index(ph_series: pd.Series) -> pd.Series:
    _SEASON_ORDER = {"S": 0, "F": 1, "W": 2, "A": 3}
    def _key(ph: str) -> tuple[int, int]:
        year = int(ph[1:5]) if len(ph) >= 5 and ph[1:5].isdigit() else 0
        season = _SEASON_ORDER.get(ph[0], 9)
        return year, season
    uniq = sorted(ph_series.unique(), key=_key)
    return ph_series.map({ph: i for i, ph in enumerate(uniq)})


def _plot_phase_overlay(exp_a: Path, exp_b: Path, out_dir: Path) -> None:
    import seaborn as sns
    import matplotlib.pyplot as plt

    df_a = _load_phase(exp_a)
    df_b = _load_phase(exp_b)
    tag_a, tag_b = exp_a.name or str(exp_a), exp_b.name or str(exp_b)

    df_a["experiment"] = tag_a
    df_b["experiment"] = tag_b
    df = pd.concat([df_a, df_b], ignore_index=True)

    if "phase_index" not in df.columns:
        df["phase_index"] = _phase_index(df["game_phase"])

    num_cols = [c for c in df.select_dtypes("number").columns
                if c not in _EXCLUDE and c != "phase_index"]

    # aggregate across games: mean per phase × power × experiment
    agg = (
        df.groupby(["experiment", "phase_index", "game_phase", "power_name"],
                   as_index=False)[num_cols]
        .mean()
    )

    palette = sns.color_palette("tab10", n_colors=len(agg["power_name"].unique()))
    power_colors = dict(zip(sorted(agg["power_name"].unique()), palette))

    out_dir.mkdir(parents=True, exist_ok=True)
    n_phases = agg["phase_index"].nunique()
    fig_w = max(8, n_phases * 0.1 + 4)

    for col in num_cols:
        plt.figure(figsize=(fig_w, 6))
        for power in sorted(agg["power_name"].unique()):
            for exp_tag, style in [(tag_a, "--"), (tag_b, "-")]:
                sub = agg[(agg["power_name"] == power) &
                          (agg["experiment"] == exp_tag)]
                if sub.empty:
                    continue
                plt.plot(
                    sub["phase_index"],
                    sub[col],
                    linestyle=style,
                    color=power_colors[power],
                    marker="o",
                    label=f"{power} – {exp_tag}",
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
        plt.title(col.replace("_", " ").title())
        plt.xlabel("Game Phase")
        plt.legend(ncol=2, fontsize=8)
        plt.tight_layout()
        plt.savefig(out_dir / f"{col}.png", dpi=140)
        plt.close()


# ───────────────────────── public API ─────────────────────────
def run(exp_a: Path, exp_b: Path, alpha: float = 0.05, show_all: bool = False) -> None:
    df_a = _load_games(exp_a)
    df_b = _load_games(exp_b)

    metrics = sorted(set(_numeric_columns(df_a)) & set(_numeric_columns(df_b)))
    if not metrics:
        print("No overlapping numeric metrics to compare.")
        return

    ci_pct = int(round((1 - alpha) * 100))
    ci_label = f"{ci_pct}%CI"
    tag_a = exp_a.name or str(exp_a)
    tag_b = exp_b.name or str(exp_b)

    out_dir = exp_b / "analysis" / "comparison"
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── section 1: aggregated across powers ───────────────────
    rows_agg: List[Dict] = []
    for col in metrics:
        agg_fn = "max" if col in _MAX_METRICS else "mean"
        a_vals = df_a.groupby("game_id")[col].agg(agg_fn).dropna().to_numpy()
        b_vals = df_b.groupby("game_id")[col].agg(agg_fn).dropna().to_numpy()
        if len(a_vals) < 2 or len(b_vals) < 2:
            continue
        rows_agg.append({"Metric": col, **_welch(a_vals, b_vals, alpha)})

    agg_df = pd.DataFrame(rows_agg)
    if not agg_df.empty:
        p_vals = agg_df["p_value"].dropna()
    agg_csv = out_dir / f"comparison_aggregated_vs_{tag_b}.csv"
    agg_df.to_csv(agg_csv, index=False)

    print("\n\n")
    print(f"Comparing {tag_a} to {tag_b}: All comparisons are [{tag_b}] – [{tag_a}].")

    sig_agg = _significant(agg_df, alpha)
    rows_to_print = agg_df if show_all else _significant(agg_df, alpha)
    if rows_to_print.empty:
        _print_hdr(f"Aggregated Across Powers – no metric significant at {ci_pct}% CI")
    else:
        n_a, n_b = int(sig_agg.iloc[0]["n_A"]), int(sig_agg.iloc[0]["n_B"])
        _print_hdr(
            f"Aggregated Across Powers – "
            f"{'all metrics' if show_all else f'significant at {ci_pct}%'} "
            f"(n({tag_a})={n_a}, n({tag_b})={n_b})"
        )
        width = max(len(m) for m in sig_agg["Metric"]) + 2
        for _, r in rows_to_print.iterrows():
            print(_fmt_row(r["Metric"], r, width, ci_label))

    # ── section 2: per-power breakdown ────────────────────────
    rows_pow: List[Dict] = []
    powers = sorted(set(df_a["power_name"]) & set(df_b["power_name"]))
    for power in powers:
        sub_a = df_a[df_a["power_name"] == power]
        sub_b = df_b[df_b["power_name"] == power]
        for col in metrics:
            if col in _PER_POWER_SKIP:
                continue
            a_vals = sub_a[col].dropna().to_numpy()
            b_vals = sub_b[col].dropna().to_numpy()
            if len(a_vals) < 2 or len(b_vals) < 2:
                continue
            rows_pow.append(
                {"Power": power, "Metric": col, **_welch(a_vals, b_vals, alpha)}
            )

    pow_df = pd.DataFrame(rows_pow)
    if not pow_df.empty:
        p_vals = pow_df["p_value"].dropna()

    pow_csv = out_dir / f"comparison_by_power_vs_{tag_b}.csv"
    pow_df.to_csv(pow_csv, index=False)

    sig_pow = _significant(pow_df, alpha)
    
    rows_to_print_pow = pow_df if show_all else _significant(pow_df, alpha)
    if rows_to_print_pow.empty:
        _print_hdr(f"Per-Power Breakdown – no metric significant at {ci_pct}% CI")
    else:
        _print_hdr(
                f"Per-Power Breakdown – "
                f"{'all metrics' if show_all else f'metrics significant at {ci_pct}% CI'} "
                f"(α={alpha})"

        )
        width = max(len(m) for m in sig_pow["Metric"]) + 2
        for power in powers:
            sub = rows_to_print_pow[rows_to_print_pow["Power"] == power]
            if sub.empty:
                continue
            n_a, n_b = int(sub.iloc[0]["n_A"]), int(sub.iloc[0]["n_B"])
            print(f"\n{power} (n({tag_a})={n_a}, n({tag_b})={n_b})")
            for _, r in sub.iterrows():
                print(_fmt_row(r["Metric"], r, width, ci_label))

    # ── summary of output locations ───────────────────────────
    print("\nCSV outputs:")
    print(f"  • {agg_csv}")
    print(f"  • {pow_csv}")


    print('\n\nGenerating plots...')
    # overlay phase-level plots
    try:
        _plot_phase_overlay(exp_a, exp_b, out_dir / "phase_overlay")
        print(f"\nPhase overlay plots → {out_dir / 'phase_overlay'}")
    except Exception as exc:
        print(f"\n[warning] phase overlay plot generation failed: {exc}")
    
    print('Complete')