#!/usr/bin/env python3
"""
Experiment orchestration for Diplomacy self-play.
Launches many `lm_game` runs in parallel, captures their artefacts,
and executes a pluggable post-analysis pipeline.

Run  `python experiment_runner.py --help`  for CLI details.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import importlib
import json
import logging
import math
import os
import shutil
import subprocess
import sys
import textwrap
import time
import uuid
import multiprocessing as mp
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Iterable, List

# --------------------------------------------------------------------------- #
#  Logging                                                                    #
# --------------------------------------------------------------------------- #
LOG_FMT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FMT, datefmt="%H:%M:%S")
log = logging.getLogger("experiment_runner")



# ────────────────────────────────────────────────────────────────────────────
#  Flag definitions – full, un-shortened help strings                        #
# ────────────────────────────────────────────────────────────────────────────
def _add_experiment_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--experiment_dir",
        type=Path,
        required=True,
        help=(
            "Directory that will hold all experiment artefacts. "
            "A 'runs/' sub-folder is created for individual game runs and an "
            "'analysis/' folder for aggregated outputs.  Must be writable."
        ),
    )
    p.add_argument(
        "--iterations",
        type=int,
        default=1,
        help=(
            "Number of lm_game instances to launch for this experiment.  "
            "Each instance gets its own sub-directory under runs/."
        ),
    )
    p.add_argument(
        "--parallel",
        type=int,
        default=1,
        help=(
            "Maximum number of game instances to run concurrently.  "
            "Uses a ProcessPoolExecutor under the hood."
        ),
    )
    p.add_argument(
        "--analysis_modules",
        type=str,
        default="summary,statistical_game_analysis",
        help=(
            "Comma-separated list of analysis module names to execute after all "
            "runs finish.  Modules are imported from "
            "'experiment_runner.analysis.<name>' and must expose "
            "run(experiment_dir: Path, ctx: dict)."
        ),
    )
    p.add_argument(
        "--critical_state_base_run",
        type=Path,
        default=None,
        help=(
            "Path to an *existing* run directory produced by a previous lm_game "
            "execution.  When supplied, every iteration resumes from that "
            "snapshot using lm_game's --critical_state_analysis_dir mechanism."
        ),
    )
    p.add_argument(
        "--seed_base",
        type=int,
        default=42,
        help=(
            "Base RNG seed.  Run i will receive seed = seed_base + i.  "
            "Forwarded to lm_game via its --seed flag (you must have added that "
            "flag to lm_game for deterministic behaviour)."
        ),
    )
    p.add_argument(
        "--compare_to",
        type=Path,
        default=None,
        help=(
            "Path to another completed experiment directory. "
            "If supplied alongside --experiment_dir, the runner skips game "
            "execution and produces a statistical comparison between the two."
        ),
    )
    p.add_argument(
        "--sig_level",
        type=float,
        default=0.05,
        help="α for hypothesis tests in comparison mode (default 0.05).",
    )
    p.add_argument(
        "--showall",
        action="store_true",
        help=(
            "When used together with --compare_to, prints every metric in the "
            "console output, not just significant results (confidence intervals still use --sig_level)."
        ),
    )



def _add_lm_game_flags(p: argparse.ArgumentParser) -> None:
    # ---- all flags copied verbatim from lm_game.parse_arguments() ----
    p.add_argument(
        "--resume_from_phase",
        type=str,
        default="",
        help=(
            "Phase to resume from (e.g., 'S1902M'). Requires --run_dir. "
            "IMPORTANT: This option clears any existing phase results ahead of "
            "& including the specified resume phase."
        ),
    )
    p.add_argument(
        "--end_at_phase",
        type=str,
        default="",
        help="Phase to end the simulation after (e.g., 'F1905M').",
    )
    p.add_argument(
        "--max_year",
        type=int,
        default=1910,  # Increased default in lm_game
        help="Maximum year to simulate. The game will stop once this year is reached.",
    )
    p.add_argument(
        "--num_negotiation_rounds",
        type=int,
        default=0,
        help="Number of negotiation rounds per phase.",
    )
    p.add_argument(
        "--models",
        type=str,
        default="",
        help=(
            "Comma-separated list of model names to assign to powers in order. "
            "The order is: AUSTRIA, ENGLAND, FRANCE, GERMANY, ITALY, RUSSIA, TURKEY."
        ),
    )
    p.add_argument(
        "--planning_phase",
        action="store_true",
        help="Enable the planning phase for each power to set strategic directives.",
    )
    p.add_argument(
        "--max_tokens",
        type=int,
        default=16000,
        help="Maximum number of new tokens to generate per LLM call (default: 16000).",
    )
    p.add_argument(
        "--max_tokens_per_model",
        type=str,
        default="",
        help=(
            "Comma-separated list of 7 token limits (in order: AUSTRIA, ENGLAND, "
            "FRANCE, GERMANY, ITALY, RUSSIA, TURKEY). Overrides --max_tokens."
        ),
    )
    p.add_argument(
        "--prompts_dir",
        type=str,
        default=None,
        help=(
            "Path to the directory containing prompt files. "
            "Defaults to the packaged prompts directory."
        ),
    )
    p.add_argument(
        "--simple_prompts",
        type=_str2bool,
        nargs="?",
        const=True,
        default=False,
        help=(
            "When true (1 / true / yes) the engine switches to simpler prompts "
            "which low-midrange models handle better."
        ),
    )
    p.add_argument(
        "--generate_phase_summaries",
        type=_str2bool,
        nargs="?",
        const=True,
        default=True,
        help=(
            "When true (1 / true / yes / default) generates narrative phase summaries. "
            "Set to false (0 / false / no) to skip phase summary generation."
        ),
    )
    p.add_argument(
        "--use_unformatted_prompts",
        type=_str2bool,
        nargs="?",
        const=True,
        default=True,
        help=(
            "When true (1 / true / yes / default) uses two-step approach: unformatted prompts + Gemini Flash formatting. "
            "Set to false (0 / false / no) to use original single-step formatted prompts."
        ),
    )


# ────────────────────────────────────────────────────────────────────────────
#  One combined parser for banner printing                                    #
# ────────────────────────────────────────────────────────────────────────────
def _build_full_parser() -> argparse.ArgumentParser:
    fp = argparse.ArgumentParser(
        prog="experiment_runner.py",
        formatter_class=lambda prog: argparse.RawTextHelpFormatter(
            prog, max_help_position=45
        ),
        description=(
            "Batch-runner for Diplomacy self-play experiments.  "
            "All lm_game flags are accepted here as-is; they are validated "
            "before any game runs start."
        ),
    )
    _add_experiment_flags(fp)
    _add_lm_game_flags(fp)
    return fp


# ────────────────────────────────────────────────────────────────────────────
#  Robust parsing that always shows *full* help on error                      #
# ────────────────────────────────────────────────────────────────────────────
def _parse_cli() -> tuple[argparse.Namespace, list[str], argparse.Namespace]:
    full_parser = _build_full_parser()

    # Show full banner when no args
    if len(sys.argv) == 1:
        full_parser.print_help(sys.stderr)
        sys.exit(2)

    # Show full banner on explicit help
    if any(tok in ("-h", "--help") for tok in sys.argv[1:]):
        full_parser.print_help(sys.stderr)
        sys.exit(0)

    # Sub-parsers for separating experiment vs game flags
    class _ErrParser(argparse.ArgumentParser):
        def error(self, msg):
            full_parser.print_help(sys.stderr)
            self.exit(2, f"{self.prog}: error: {msg}\n")

    exp_parser  = _ErrParser(add_help=False)
    game_parser = _ErrParser(add_help=False)
    _add_experiment_flags(exp_parser)
    _add_lm_game_flags(game_parser)

    # Split argv tokens by flag ownership
    argv = sys.argv[1:]
    exp_flag_set = {opt for a in exp_parser._actions for opt in a.option_strings}

    exp_tok, game_tok, i = [], [], 0
    while i < len(argv):
        tok = argv[i]
        if tok in exp_flag_set:
            exp_tok.append(tok)
            action = exp_parser._option_string_actions[tok]
            needs_val = (
                action.nargs is None                         # default: exactly one value
                or (isinstance(action.nargs, int) and action.nargs > 0)
                or action.nargs in ("+", "*", "?")           # variable-length cases
            )
            if needs_val:
                exp_tok.append(argv[i + 1])
                i += 2
            else:                                            # store_true / store_false
                i += 1

        else:
            game_tok.append(tok)
            i += 1

    exp_args  = exp_parser.parse_args(exp_tok)
    game_args = game_parser.parse_args(game_tok)
    return exp_args, game_tok, game_args


# --------------------------------------------------------------------------- #
#  Helpers                                                                    #
# --------------------------------------------------------------------------- #
_RunInfo = collections.namedtuple(
    "_RunInfo", "index run_dir seed cmd_line returncode elapsed_s"
)

def _str2bool(v: str | bool) -> bool:
    """
    Accepts typical textual truthy / falsy values and returns a bool.
    Mirrors the helper used inside lm_game.
    """
    if isinstance(v, bool):
        return v
    val = v.lower()
    if val in ("yes", "y", "true", "t", "1"):
        return True
    if val in ("no", "n", "false", "f", "0"):
        return False
    raise argparse.ArgumentTypeError("boolean value expected")


def _mk_run_dir(exp_dir: Path, idx: int) -> Path:
    run_dir = exp_dir / "runs" / f"run_{idx:05d}"
    # Just ensure it exists; don't raise if it already does.
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _make_game_ids_unique(run_dirs: Iterable[Path]) -> None:
    """
    Ensures every lmvsgame.json in *run_dirs* carries a distinct `"id"`.
    If a duplicate is found we overwrite it with a fresh 16-char UUID
    **after** the game has finished but **before** the analysis phase.
    """
    seen: set[str] = set()

    for run_dir in run_dirs:
        json_path = run_dir / "lmvsgame.json"
        if not json_path.exists():
            continue                        # should not happen, but be tolerant

        try:
            meta = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            continue                        # invalid JSON → leave unchanged

        gid = str(meta.get("id", "")).strip()
        if not gid:
            continue                        # no id field → nothing to fix

        if gid in seen:                     # duplicate → replace
            meta["id"] = uuid.uuid4().hex[:16]
            json_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
            gid = meta["id"]

        seen.add(gid)


def _dump_seed(seed: int, run_dir: Path) -> None:
    seed_file = run_dir / "seed.txt"
    if not seed_file.exists():
        seed_file.write_text(str(seed))


def _build_cmd(
    lm_game_script: Path,
    base_cli: List[str],
    run_dir: Path,
    seed: int,
    critical_base: Path | None,
    resume_from_phase: str,
) -> List[str]:
    """
    Returns a list suitable for subprocess.run([...]).
    """
    cmd = [sys.executable, str(lm_game_script)]

    # Forward user CLI
    cmd.extend(base_cli)

    # Per-run mandatory overrides
    cmd.extend(["--run_dir", str(run_dir)])
    cmd.extend(["--seed", str(seed)])  # you may need to add a --seed flag to lm_game

    # Critical-state mode
    if critical_base:
        cmd.extend([
            "--critical_state_analysis_dir", str(run_dir),
            "--run_dir", str(critical_base)  # base run dir (already completed)
        ])
        if resume_from_phase:
            cmd.extend(["--resume_from_phase", resume_from_phase])

    return cmd


def _launch_one(args) -> _RunInfo:
    """
    Worker executed inside a ProcessPool; runs one game via subprocess.
    """
    (
        idx,
        lm_game_script,
        base_cli,
        run_dir,
        seed,
        critical_base,
        resume_phase,
    ) = args

    cmd = _build_cmd(
        lm_game_script, base_cli, run_dir, seed, critical_base, resume_phase
    )
    start = time.perf_counter()
    log.debug("Run %05d: CMD = %s", idx, " ".join(cmd))

    # Write out full command for traceability
    (run_dir / "command.txt").write_text(" ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        (run_dir / "console.log").write_text(result.stdout)
        rc = result.returncode
    except Exception as exc:  # noqa: broad-except
        (run_dir / "console.log").write_text(f"Exception launching run:\n{exc}\n")
        rc = 1

    elapsed = time.perf_counter() - start
    return _RunInfo(idx, run_dir, seed, " ".join(cmd), rc, elapsed)


def _load_analysis_fns(module_names: Iterable[str]):
    """
    Dynamically import analysis modules.
    Each module must expose `run(experiment_dir: Path, cfg: dict)`.
    """
    for name in module_names:
        mod_name = f"experiment_runner.analysis.{name.strip()}"
        try:
            mod = importlib.import_module(mod_name)
        except ModuleNotFoundError as e:
            log.warning("Analysis module %s not found (%s) – skipping", mod_name, e)
            continue

        if not hasattr(mod, "run"):
            log.warning("%s has no `run()` function – skipping", mod_name)
            continue
        yield mod.run


# --------------------------------------------------------------------------- #
#  Main driver                                                                #
# --------------------------------------------------------------------------- #
def main() -> None:
    exp_args, leftover_cli, game_args = _parse_cli()

    exp_dir: Path = exp_args.experiment_dir.expanduser().resolve()
    if exp_dir.exists():
        log.info("Appending to existing experiment: %s", exp_dir)
    exp_dir.mkdir(parents=True, exist_ok=True)

    if exp_args.compare_to is not None:
        from experiment_runner.analysis import compare_stats   # local import

        compare_stats.run(
            exp_dir,
            exp_args.compare_to,
            alpha=exp_args.sig_level,
            show_all=exp_args.showall,
        )

        log.info("comparison complete; artefacts in %s/analysis/comparison", exp_dir)
        return

    # Persist experiment-level config
    cfg_path = exp_dir / "config.json"
    if not cfg_path.exists():                     # ← new guard
        with cfg_path.open("w", encoding="utf-8") as fh:
            json.dump(
                {"experiment": vars(exp_args),
                "lm_game": vars(game_args),
                "forwarded_cli": leftover_cli},
                fh, indent=2, default=str,
            )
        log.info("Config saved to %s", cfg_path)
    else:
        log.info("Config already exists – leaving unchanged")


    log.info("Config saved to %s", cfg_path)

    # ------------------------------------------------------------------ #
    #  Launch games                                                      #
    # ------------------------------------------------------------------ #
    lm_game_script = Path(__file__).parent / "lm_game.py"
    if not lm_game_script.exists():
        log.error("lm_game.py not found at %s – abort", lm_game_script)
        sys.exit(1)

    run_args = []
    for i in range(exp_args.iterations):
        run_dir = _mk_run_dir(exp_dir, i)
        seed = exp_args.seed_base + i
        _dump_seed(seed, run_dir)

        run_args.append(
            (
                i, lm_game_script, leftover_cli, run_dir, seed,
                exp_args.critical_state_base_run,
                game_args.resume_from_phase,
            )
        )


    log.info(
        "Launching %d runs (max %d parallel, critical_state=%s)",
        exp_args.iterations,
        exp_args.parallel,
        bool(exp_args.critical_state_base_run),
    )

    runs_meta: list[_RunInfo] = []
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=exp_args.parallel,
        mp_context=mp.get_context("spawn"),
    ) as pool:
        for res in pool.map(_launch_one, run_args):
            runs_meta.append(res)
            status = "OK" if res.returncode == 0 else f"RC={res.returncode}"
            log.info(
                "run_%05d finished in %.1fs %s", res.index, res.elapsed_s, status
            )

    # Persist per-run status summary
    summary_path = exp_dir / "runs_summary.json"
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump([res._asdict() for res in runs_meta], fh, indent=2, default=str)
    log.info("Run summary written → %s", summary_path)

    # ------------------------------------------------------------------
    #  De-duplicate game IDs (critical-state runs reuse the snapshot ID)
    # ------------------------------------------------------------------
    _make_game_ids_unique([r.run_dir for r in runs_meta])

    # ------------------------------------------------------------------ #
    #  Post-analysis pipeline                                            #
    # ------------------------------------------------------------------ #
    mods = list(_load_analysis_fns(exp_args.analysis_modules.split(",")))
    if not mods:
        log.warning("No analysis modules loaded – done.")
        return

    analysis_root = exp_dir / "analysis"
    if analysis_root.exists():
        shutil.rmtree(analysis_root)      # ← wipes old outputs
    analysis_root.mkdir(exist_ok=True)

    # Collect common context
    ctx: dict = {
        "exp_dir": str(exp_dir),
        "runs": [str(r.run_dir) for r in runs_meta],
        "critical_state_base": str(exp_args.critical_state_base_run or ""),
        "resume_from_phase": game_args.resume_from_phase,
    }

    for fn in mods:
        name = fn.__module__.rsplit(".", 1)[-1]
        log.info("Running analysis module: %s", name)
        try:
            fn(exp_dir, ctx)
            log.info("✓ %s complete", name)
        except Exception as exc:  # noqa: broad-except
            log.exception("Analysis module %s failed: %s", name, exc)

    log.info("Experiment finished – artefacts in %s", exp_dir)


if __name__ == "__main__":
    main()
