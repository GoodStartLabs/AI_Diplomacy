#!/usr/bin/env python3
"""
Auto-discovery leaderboard comparison script.

Automatically discovers all experiments in the leaderboard/ directory,
groups them by model name (baseline vs aggressive variants), and generates
comprehensive comparison visualizations.

Naming convention: {model_name}-baseline and {model_name}-aggressive
Example: gpt_5_medium-baseline, gpt_5_medium-aggressive
"""

import json
import subprocess
from pathlib import Path
import sys

def discover_experiments(leaderboard_dir="."):
    """
    Discover all experiments in the leaderboard directory.

    Returns:
        dict: Mapping of display labels to absolute paths
    """
    leaderboard_path = Path(leaderboard_dir)

    if not leaderboard_path.exists():
        print(f"Error: {leaderboard_dir} directory not found")
        sys.exit(1)

    experiments = {}

    # Scan for all directories/symlinks in leaderboard folder
    for item in sorted(leaderboard_path.iterdir()):
        # Skip the script itself, output directory, temp files, and log files
        if item.name in ['full_comparison.py', 'leaderboard_comparison', 'temp_leaderboard_paths.json'] or item.name.endswith('.log'):
            continue

        if item.is_dir() or item.is_symlink():
            # Get the name and resolve symlink if needed
            name = item.name
            resolved_path = item.resolve()

            # Create display label: replace underscores with spaces, capitalize words
            # e.g., gpt_5_medium-baseline -> GPT-5-medium (baseline)
            # e.g., sonoma_sky-aggressive -> Sonoma-sky (aggressive)

            if '-baseline' in name:
                model_name = name.replace('-baseline', '').replace('_', '-')
                display_label = f"{model_name}"
            elif '-aggressive' in name:
                model_name = name.replace('-aggressive', '').replace('_', '-')
                display_label = f"{model_name}-aggressive"
            else:
                # Fallback for any non-standard naming
                display_label = name.replace('_', '-')

            experiments[display_label] = str(resolved_path)

    return experiments

def main():
    print("=== Leaderboard Auto-Discovery Comparison ===\n")

    # Get absolute paths for script location and parent directory
    script_dir = Path(__file__).resolve().parent
    parent_dir = script_dir.parent

    # Discover all experiments (using absolute path to leaderboard dir)
    print("Discovering experiments in leaderboard directory...")
    experiments = discover_experiments(script_dir)

    if not experiments:
        print("No experiments found in leaderboard directory")
        return

    print(f"Found {len(experiments)} experiments:")
    for label in sorted(experiments.keys()):
        print(f"  - {label}")
    print()

    # Create output directory (absolute path)
    output_dir = script_dir / "leaderboard_comparison"
    output_dir.mkdir(exist_ok=True)
    print(f"Output directory: {output_dir}/\n")

    # Import visualization functions from parent directory
    print("Loading analysis modules...")
    sys.path.insert(0, str(parent_dir))
    from analyze_diplomacy_performance_v3_textured import (
        collect_timing_data_v3, create_stacked_bar_chart_v3,
        collect_move_type_data, create_move_type_chart,
        collect_error_data, create_error_chart
    )

    # Collect and generate timing analysis
    print("\nCollecting timing data (concurrent operations)...")
    timing_data = collect_timing_data_v3(experiments)
    if timing_data:
        create_stacked_bar_chart_v3(timing_data, output_dir / "phase_timing_comparison.png")
        print("  ✓ Generated phase_timing_comparison.png")

    # Collect and generate move type analysis
    print("\nCollecting move type data...")
    move_data = collect_move_type_data(experiments)
    if move_data:
        create_move_type_chart(move_data, output_dir / "move_type_comparison.png")
        print("  ✓ Generated move_type_comparison.png")

    # Collect and generate error analysis
    print("\nCollecting error data...")
    error_data = collect_error_data(experiments)
    if error_data:
        create_error_chart(error_data, output_dir / "error_comparison.png")
        print("  ✓ Generated error_comparison.png")

    # Import additional analysis functions
    print("\nGenerating additional visualizations...")
    from analyze_diplomacy_performance_v3_textured import (
        collect_france_scores,
        plot_france_scores_bar,
        plot_france_scores_box,
        plot_diplomatic_credit_heatmap,
        plot_relative_sentiment
    )

    # Reverse mapping for compatibility with existing functions
    path_to_label = {v: k for k, v in experiments.items()}

    # Generate remaining visualizations directly (no subprocess needed)
    try:
        # Collect France scores once and reuse
        print("  Collecting France game scores...")
        all_scores_df = collect_france_scores(path_to_label)

        if not all_scores_df.empty:
            print("  Generating score visualizations...")
            plot_france_scores_bar(all_scores_df, output_dir / "france_scores_bar.png")
            plot_france_scores_box(all_scores_df, output_dir / "france_scores_box.png")
            print("  ✓ Generated score visualizations")

        # Generate diplomatic heatmaps
        print("  Generating diplomatic heatmaps...")
        plot_diplomatic_credit_heatmap(path_to_label, "other_to_france", output_dir / "heatmap_other_to_france.png")
        plot_diplomatic_credit_heatmap(path_to_label, "france_to_other", output_dir / "heatmap_france_to_other.png")
        print("  ✓ Generated heatmaps")

        # Generate relative sentiment chart
        print("  Generating relative sentiment chart...")
        plot_relative_sentiment(path_to_label, output_dir / "relative_sentiment.png")
        print("  ✓ Generated relative sentiment chart")

        print("  ✓ Generated additional visualizations")

    except Exception as e:
        print(f"  ⚠ Warning: Some visualizations may have failed: {e}")

    # List generated files
    files = sorted(output_dir.glob("*.png"))
    print(f"\n=== Complete! ===")
    print(f"Generated {len(files)} visualizations in {output_dir}/:")
    for f in files:
        print(f"  - {f.name}")

    # Print summary by model family
    print("\n=== Experiments by Family ===")

    families = {
        'GPT-5': [],
        'GPT-OSS': [],
        'O-series': [],
        'Gemini': [],
        'Hermes': [],
        'Sonoma': [],
        'Other': []
    }

    for label in sorted(experiments.keys()):
        if 'gpt-5' in label.lower():
            families['GPT-5'].append(label)
        elif 'gpt-oss' in label.lower():
            families['GPT-OSS'].append(label)
        elif label.startswith('o3') or label.startswith('o4'):
            families['O-series'].append(label)
        elif 'gemini' in label.lower():
            families['Gemini'].append(label)
        elif 'hermes' in label.lower():
            families['Hermes'].append(label)
        elif 'sonoma' in label.lower():
            families['Sonoma'].append(label)
        else:
            families['Other'].append(label)

    for family, models in families.items():
        if models:
            print(f"\n{family}:")
            for model in models:
                print(f"  - {model}")

    print("\n✓ Leaderboard comparison complete!")

if __name__ == "__main__":
    main()
