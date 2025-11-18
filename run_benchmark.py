#!/usr/bin/env python3
"""
Benchmark script for testing language models in Diplomacy.

This script orchestrates two experiments (baseline and aggressive) for a given model,
manages experiment results, creates leaderboard symlinks, and optionally runs
comprehensive comparison analysis.

Usage:
    # Full production benchmark (20 iterations, max_year=1925)
    python run_benchmark.py --model_id "openai:gpt-5-mini" --friendly_name "gpt_5_mini"

    # Quick test run (3 iterations, max_year=1901)
    python run_benchmark.py --model_id "openai:gpt-5-mini" --friendly_name "test_model" --test

    # Run only baseline
    python run_benchmark.py --model_id "..." --friendly_name "..." --baseline-only

    # Run only aggressive
    python run_benchmark.py --model_id "..." --friendly_name "..." --aggressive-only

    # Skip leaderboard comparison after experiments
    python run_benchmark.py --model_id "..." --friendly_name "..." --skip-leaderboard
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# ============================================================================
# Logging Configuration
# ============================================================================
LOG_FMT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FMT, datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("benchmark")


# ============================================================================
# Configuration Constants
# ============================================================================
class BenchmarkConfig:
    """Configuration for benchmark experiments."""

    # Production defaults
    PROD_MAX_YEAR = 1925
    PROD_ITERATIONS = 20
    PROD_PARALLEL = 20

    # Test mode defaults
    TEST_MAX_YEAR = 1901
    TEST_ITERATIONS = 3
    TEST_PARALLEL = 3

    # Model position (FRANCE is position 2 in 7-nation list, 0-indexed)
    # Order: AUSTRIA, ENGLAND, FRANCE, GERMANY, ITALY, RUSSIA, TURKEY
    MODEL_POSITION = 2

    # Baseline configuration
    BASELINE_OPPONENT = "openrouter:mistralai/devstral-small"
    BASELINE_PROMPTS = "ai_diplomacy/prompts/prompts_benchmark"

    # Aggressive configuration
    AGGRESSIVE_OPPONENT = "openrouter:mistralai/devstral-small"
    AGGRESSIVE_PROMPTS = "ai_diplomacy/prompts/prompts_hold_reduction_v3"

    # Paths
    REPO_ROOT = Path(__file__).resolve().parent
    RESULTS_DIR = REPO_ROOT / "results"
    LEADERBOARD_DIR = REPO_ROOT / "leaderboard"
    EXPERIMENT_RUNNER = REPO_ROOT / "experiment_runner.py"
    LEADERBOARD_SCRIPT = LEADERBOARD_DIR / "full_comparison.py"


# ============================================================================
# Utility Functions
# ============================================================================
def print_section(title: str, width: int = 80) -> None:
    """Print a formatted section header."""
    log.info("=" * width)
    log.info(f" {title}")
    log.info("=" * width)


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def build_model_string(test_model: str, opponent_model: str, position: int) -> str:
    """
    Build comma-separated model string with test model at specified position.

    Args:
        test_model: The model being tested
        opponent_model: The opponent model for all other positions
        position: Position (0-indexed) for the test model

    Returns:
        Comma-separated string of 7 models
    """
    models = [opponent_model] * 7
    models[position] = test_model
    return ",".join(models)


def create_symlink(target_dir: Path, link_name: Path, force: bool = True) -> bool:
    """
    Create a symlink, optionally removing existing link.

    Args:
        target_dir: Directory to link to
        link_name: Path for the symlink
        force: If True, remove existing link before creating

    Returns:
        True if successful, False otherwise
    """
    try:
        if link_name.exists() or link_name.is_symlink():
            if force:
                link_name.unlink()
                log.info(f"  Removed existing symlink: {link_name.name}")
            else:
                log.warning(f"  Symlink already exists: {link_name.name}")
                return False

        link_name.symlink_to(target_dir)
        log.info(f"  Created symlink: {link_name.name} -> {target_dir}")
        return True
    except Exception as e:
        log.error(f"  Failed to create symlink {link_name.name}: {e}")
        return False


def save_benchmark_metadata(
    exp_dir: Path,
    model_id: str,
    friendly_name: str,
    variant: str,
    config: dict
) -> None:
    """Save metadata about the benchmark run."""
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "model_id": model_id,
        "friendly_name": friendly_name,
        "variant": variant,
        "configuration": config
    }

    metadata_path = exp_dir / "benchmark_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    log.info(f"  Saved metadata to {metadata_path.name}")


# ============================================================================
# Experiment Runner
# ============================================================================
class ExperimentRunner:
    """Handles running individual experiments via experiment_runner.py."""

    def __init__(self, config: BenchmarkConfig):
        self.config = config

        if not self.config.EXPERIMENT_RUNNER.exists():
            raise FileNotFoundError(
                f"experiment_runner.py not found at {self.config.EXPERIMENT_RUNNER}"
            )

    def run_experiment(
        self,
        experiment_dir: Path,
        model_id: str,
        opponent_model: str,
        prompts_dir: str,
        max_year: int,
        iterations: int,
        parallel: int,
        variant: str
    ) -> bool:
        """
        Run a single experiment.

        Args:
            experiment_dir: Directory for experiment outputs
            model_id: Model being tested
            opponent_model: Opponent model
            prompts_dir: Path to prompts directory
            max_year: Maximum year to simulate
            iterations: Number of game iterations
            parallel: Number of parallel workers
            variant: "baseline" or "aggressive"

        Returns:
            True if successful, False otherwise
        """
        # Build model string (test model at position 3 = FRANCE)
        models_string = build_model_string(
            model_id,
            opponent_model,
            self.config.MODEL_POSITION
        )

        # Build command (use uv run to ensure correct environment)
        cmd = [
            "uv", "run", "python",
            str(self.config.EXPERIMENT_RUNNER),
            "--experiment_dir", str(experiment_dir),
            "--iterations", str(iterations),
            "--parallel", str(parallel),
            "--max_year", str(max_year),
            "--models", models_string,
            "--prompts_dir", prompts_dir,
        ]

        log.info(f"\nRunning {variant} experiment:")
        log.info(f"  Command: {' '.join(cmd)}")
        log.info(f"  Output: {experiment_dir}")
        log.info(f"  Model: {model_id}")
        log.info(f"  Iterations: {iterations}")
        log.info(f"  Max year: {max_year}")
        log.info(f"  Parallel: {parallel}")
        log.info("")

        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False
            )

            # Save console output
            log_file = experiment_dir / f"benchmark_{variant}_console.log"
            with open(log_file, 'w') as f:
                f.write(result.stdout)

            elapsed = time.time() - start_time

            if result.returncode == 0:
                log.info(f"✓ {variant.capitalize()} experiment completed successfully")
                log.info(f"  Duration: {format_duration(elapsed)}")
                log.info(f"  Console log: {log_file}")
                return True
            else:
                log.error(f"✗ {variant.capitalize()} experiment failed (return code: {result.returncode})")
                log.error(f"  Duration: {format_duration(elapsed)}")
                log.error(f"  Console log: {log_file}")
                log.error(f"  Check log file for details")
                return False

        except KeyboardInterrupt:
            elapsed = time.time() - start_time
            log.warning(f"\n✗ {variant.capitalize()} experiment interrupted by user")
            log.warning(f"  Duration before interrupt: {format_duration(elapsed)}")
            raise
        except Exception as e:
            elapsed = time.time() - start_time
            log.error(f"✗ {variant.capitalize()} experiment failed with exception: {e}")
            log.error(f"  Duration: {format_duration(elapsed)}")
            return False


# ============================================================================
# Benchmark Orchestrator
# ============================================================================
class BenchmarkOrchestrator:
    """Main orchestrator for benchmark runs."""

    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.config = BenchmarkConfig()
        self.runner = ExperimentRunner(self.config)

        # Determine run parameters
        if args.test:
            self.max_year = self.config.TEST_MAX_YEAR
            self.iterations = self.config.TEST_ITERATIONS
            self.parallel = self.config.TEST_PARALLEL
            log.info("TEST MODE: Using reduced parameters")
        else:
            self.max_year = self.config.PROD_MAX_YEAR
            self.iterations = self.config.PROD_ITERATIONS
            self.parallel = self.config.PROD_PARALLEL
            log.info("PRODUCTION MODE: Using full parameters")

        # Create output directories
        self.config.RESULTS_DIR.mkdir(exist_ok=True)
        self.config.LEADERBOARD_DIR.mkdir(exist_ok=True)

        # Determine which experiments to run
        self.run_baseline = not args.aggressive_only
        self.run_aggressive = not args.baseline_only
        self.run_leaderboard = not args.skip_leaderboard

        # Experiment directories
        self.baseline_dir = self.config.RESULTS_DIR / f"{args.friendly_name}_baseline"
        self.aggressive_dir = self.config.RESULTS_DIR / f"{args.friendly_name}_aggressive"

        # Leaderboard symlinks
        self.baseline_link = self.config.LEADERBOARD_DIR / f"{args.friendly_name}-baseline"
        self.aggressive_link = self.config.LEADERBOARD_DIR / f"{args.friendly_name}-aggressive"

    def print_configuration(self) -> None:
        """Print the benchmark configuration."""
        print_section("Benchmark Configuration")
        log.info(f"Model ID: {self.args.model_id}")
        log.info(f"Friendly name: {self.args.friendly_name}")
        log.info(f"Test mode: {self.args.test}")
        log.info("")
        log.info("Experiment parameters:")
        log.info(f"  Max year: {self.max_year}")
        log.info(f"  Iterations: {self.iterations}")
        log.info(f"  Parallel workers: {self.parallel}")
        log.info("")
        log.info("Experiments to run:")
        log.info(f"  Baseline: {self.run_baseline}")
        log.info(f"  Aggressive: {self.run_aggressive}")
        log.info(f"  Leaderboard comparison: {self.run_leaderboard}")
        log.info("")

        if self.run_baseline:
            log.info(f"Baseline configuration:")
            log.info(f"  Output: {self.baseline_dir}")
            log.info(f"  Prompts: {self.config.BASELINE_PROMPTS}")
            log.info(f"  Opponent: {self.config.BASELINE_OPPONENT}")
            log.info(f"  Symlink: {self.baseline_link}")
            log.info("")

        if self.run_aggressive:
            log.info(f"Aggressive configuration:")
            log.info(f"  Output: {self.aggressive_dir}")
            log.info(f"  Prompts: {self.config.AGGRESSIVE_PROMPTS}")
            log.info(f"  Opponent: {self.config.AGGRESSIVE_OPPONENT}")
            log.info(f"  Symlink: {self.aggressive_link}")
            log.info("")

    def run_baseline_experiment(self) -> bool:
        """Run the baseline experiment."""
        print_section("Running Baseline Experiment")

        success = self.runner.run_experiment(
            experiment_dir=self.baseline_dir,
            model_id=self.args.model_id,
            opponent_model=self.config.BASELINE_OPPONENT,
            prompts_dir=self.config.BASELINE_PROMPTS,
            max_year=self.max_year,
            iterations=self.iterations,
            parallel=self.parallel,
            variant="baseline"
        )

        if success:
            # Save metadata
            config_info = {
                "max_year": self.max_year,
                "iterations": self.iterations,
                "parallel": self.parallel,
                "opponent_model": self.config.BASELINE_OPPONENT,
                "prompts_dir": self.config.BASELINE_PROMPTS
            }
            save_benchmark_metadata(
                self.baseline_dir,
                self.args.model_id,
                self.args.friendly_name,
                "baseline",
                config_info
            )

            # Create symlink
            create_symlink(self.baseline_dir, self.baseline_link)

        return success

    def run_aggressive_experiment(self) -> bool:
        """Run the aggressive experiment."""
        print_section("Running Aggressive Experiment")

        success = self.runner.run_experiment(
            experiment_dir=self.aggressive_dir,
            model_id=self.args.model_id,
            opponent_model=self.config.AGGRESSIVE_OPPONENT,
            prompts_dir=self.config.AGGRESSIVE_PROMPTS,
            max_year=self.max_year,
            iterations=self.iterations,
            parallel=self.parallel,
            variant="aggressive"
        )

        if success:
            # Save metadata
            config_info = {
                "max_year": self.max_year,
                "iterations": self.iterations,
                "parallel": self.parallel,
                "opponent_model": self.config.AGGRESSIVE_OPPONENT,
                "prompts_dir": self.config.AGGRESSIVE_PROMPTS
            }
            save_benchmark_metadata(
                self.aggressive_dir,
                self.args.model_id,
                self.args.friendly_name,
                "aggressive",
                config_info
            )

            # Create symlink
            create_symlink(self.aggressive_dir, self.aggressive_link)

        return success

    def run_leaderboard_comparison(self) -> bool:
        """Run leaderboard comparison analysis."""
        print_section("Running Leaderboard Comparison")

        if not self.config.LEADERBOARD_SCRIPT.exists():
            log.warning(f"Leaderboard script not found at {self.config.LEADERBOARD_SCRIPT}")
            log.warning("Skipping leaderboard comparison")
            return False

        log.info("Running leaderboard auto-discovery and comparison...")
        log.info(f"Script: {self.config.LEADERBOARD_SCRIPT}")
        log.info("")

        try:
            result = subprocess.run(
                [sys.executable, str(self.config.LEADERBOARD_SCRIPT)],
                cwd=str(self.config.LEADERBOARD_DIR),
                capture_output=True,
                text=True,
                check=False
            )

            # Print output
            if result.stdout:
                print(result.stdout)

            if result.returncode == 0:
                log.info("✓ Leaderboard comparison completed successfully")
                comparison_dir = self.config.LEADERBOARD_DIR / "leaderboard_comparison"
                if comparison_dir.exists():
                    files = list(comparison_dir.glob("*.png"))
                    log.info(f"  Generated {len(files)} visualization(s) in {comparison_dir}")
                return True
            else:
                log.error(f"✗ Leaderboard comparison failed (return code: {result.returncode})")
                if result.stderr:
                    log.error(f"  Error: {result.stderr}")
                return False

        except Exception as e:
            log.error(f"✗ Leaderboard comparison failed with exception: {e}")
            return False

    def run(self) -> int:
        """
        Run the complete benchmark.

        Returns:
            Exit code (0 = success, 1 = failure)
        """
        start_time = time.time()

        try:
            self.print_configuration()

            results = {
                "baseline": None,
                "aggressive": None,
                "leaderboard": None
            }

            # Run baseline
            if self.run_baseline:
                results["baseline"] = self.run_baseline_experiment()
                if not results["baseline"]:
                    log.error("\nBaseline experiment failed")
                    if not self.run_aggressive:
                        return 1

            # Run aggressive
            if self.run_aggressive:
                results["aggressive"] = self.run_aggressive_experiment()
                if not results["aggressive"]:
                    log.error("\nAggressive experiment failed")
                    return 1

            # Run leaderboard comparison
            if self.run_leaderboard and (results["baseline"] or results["aggressive"]):
                results["leaderboard"] = self.run_leaderboard_comparison()

            # Print summary
            print_section("Benchmark Summary")
            elapsed = time.time() - start_time
            log.info(f"Total duration: {format_duration(elapsed)}")
            log.info("")

            log.info("Results:")
            if self.run_baseline:
                status = "✓ SUCCESS" if results["baseline"] else "✗ FAILED"
                log.info(f"  Baseline: {status}")
                if results["baseline"]:
                    log.info(f"    Directory: {self.baseline_dir}")
                    log.info(f"    Symlink: {self.baseline_link}")

            if self.run_aggressive:
                status = "✓ SUCCESS" if results["aggressive"] else "✗ FAILED"
                log.info(f"  Aggressive: {status}")
                if results["aggressive"]:
                    log.info(f"    Directory: {self.aggressive_dir}")
                    log.info(f"    Symlink: {self.aggressive_link}")

            if self.run_leaderboard:
                if results["leaderboard"] is not None:
                    status = "✓ SUCCESS" if results["leaderboard"] else "✗ FAILED"
                    log.info(f"  Leaderboard: {status}")
                    if results["leaderboard"]:
                        comparison_dir = self.config.LEADERBOARD_DIR / "leaderboard_comparison"
                        log.info(f"    Output: {comparison_dir}")

            log.info("")

            # Determine overall success
            if self.run_baseline and not results["baseline"]:
                return 1
            if self.run_aggressive and not results["aggressive"]:
                return 1

            log.info("✓ Benchmark completed successfully!")
            return 0

        except KeyboardInterrupt:
            elapsed = time.time() - start_time
            log.warning("\n\nBenchmark interrupted by user (Ctrl+C)")
            log.warning(f"Duration before interrupt: {format_duration(elapsed)}")
            return 130  # Standard exit code for SIGINT
        except Exception as e:
            log.exception(f"Benchmark failed with unexpected error: {e}")
            return 1


# ============================================================================
# Main Entry Point
# ============================================================================
def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Diplomacy benchmark for a language model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full production benchmark
  %(prog)s --model_id "openai:gpt-5-mini" --friendly_name "gpt_5_mini"

  # Quick test run
  %(prog)s --model_id "openai:gpt-5-mini" --friendly_name "test_model" --test

  # Run only baseline
  %(prog)s --model_id "openai:gpt-5-mini" --friendly_name "test_model" --baseline-only

  # Run only aggressive
  %(prog)s --model_id "openai:gpt-5-mini" --friendly_name "test_model" --aggressive-only

  # Skip leaderboard comparison
  %(prog)s --model_id "openai:gpt-5-mini" --friendly_name "test_model" --skip-leaderboard
        """
    )

    parser.add_argument(
        "--model_id",
        type=str,
        required=True,
        help="Model identifier (e.g., 'openai:gpt-5-mini', 'anthropic:claude-3-5-sonnet-20241022')"
    )

    parser.add_argument(
        "--friendly_name",
        type=str,
        required=True,
        help="Friendly name for the model (used in results directories and leaderboard)"
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode (max_year=1901, iterations=3, parallel=3)"
    )

    parser.add_argument(
        "--baseline-only",
        action="store_true",
        help="Run only the baseline experiment"
    )

    parser.add_argument(
        "--aggressive-only",
        action="store_true",
        help="Run only the aggressive experiment"
    )

    parser.add_argument(
        "--skip-leaderboard",
        action="store_true",
        help="Skip the leaderboard comparison after experiments complete"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.baseline_only and args.aggressive_only:
        parser.error("Cannot specify both --baseline-only and --aggressive-only")

    return args


def main() -> int:
    """Main entry point."""
    args = parse_args()

    print_section("Diplomacy Model Benchmark")
    log.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("")

    orchestrator = BenchmarkOrchestrator(args)
    return orchestrator.run()


if __name__ == "__main__":
    sys.exit(main())
