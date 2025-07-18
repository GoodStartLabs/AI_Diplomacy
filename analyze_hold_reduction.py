#!/usr/bin/env python3
"""
Analyze hold reduction experiment results comparing baseline vs intervention.
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def analyze_orders_for_experiment(exp_dir: Path):
    """
    Analyze order types across all runs in an experiment directory.
    Returns aggregated statistics for holds, supports, moves, and convoys.
    """
    order_stats = {
        'holds': [],
        'supports': [],
        'moves': [],
        'convoys': [],
        'total_units': []
    }
    
    for run_dir in sorted(exp_dir.glob("runs/run_*")):
        game_file = run_dir / "lmvsgame.json"
        if not game_file.exists():
            continue
            
        with open(game_file, 'r') as f:
            game_data = json.load(f)
        
        # Analyze each movement phase
        for phase in game_data.get('phases', []):
            phase_name = phase.get('name', phase.get('state', {}).get('name', ''))
            
            # Only analyze movement phases
            if not phase_name.endswith('M') or phase_name.endswith('R'):
                continue
                
            # Count orders by type for all powers
            phase_holds = 0
            phase_supports = 0
            phase_moves = 0
            phase_convoys = 0
            phase_units = 0
            
            for power, power_orders in phase.get('order_results', {}).items():
                # Count units
                units = phase['state']['units'].get(power, [])
                phase_units += len(units)
                
                # Count order types
                phase_holds += len(power_orders.get('hold', []))
                phase_supports += len(power_orders.get('support', []))
                phase_moves += len(power_orders.get('move', []))
                phase_convoys += len(power_orders.get('convoy', []))
            
            if phase_units > 0:
                order_stats['holds'].append(phase_holds)
                order_stats['supports'].append(phase_supports)
                order_stats['moves'].append(phase_moves)
                order_stats['convoys'].append(phase_convoys)
                order_stats['total_units'].append(phase_units)
    
    return order_stats

def calculate_rates(order_stats):
    """Calculate rates per unit for each order type."""
    holds = np.array(order_stats['holds'])
    supports = np.array(order_stats['supports'])
    moves = np.array(order_stats['moves'])
    convoys = np.array(order_stats['convoys'])
    total_units = np.array(order_stats['total_units'])
    
    # Avoid division by zero
    mask = total_units > 0
    
    rates = {
        'hold_rate': np.mean(holds[mask] / total_units[mask]),
        'support_rate': np.mean(supports[mask] / total_units[mask]),
        'move_rate': np.mean(moves[mask] / total_units[mask]),
        'convoy_rate': np.mean(convoys[mask] / total_units[mask]),
        'n_phases': len(holds[mask])
    }
    
    # Calculate standard errors
    rates['hold_se'] = np.std(holds[mask] / total_units[mask]) / np.sqrt(rates['n_phases'])
    rates['support_se'] = np.std(supports[mask] / total_units[mask]) / np.sqrt(rates['n_phases'])
    rates['move_se'] = np.std(moves[mask] / total_units[mask]) / np.sqrt(rates['n_phases'])
    rates['convoy_se'] = np.std(convoys[mask] / total_units[mask]) / np.sqrt(rates['n_phases'])
    
    return rates

def main():
    import sys
    
    # Check if specific experiment directories are provided
    if len(sys.argv) > 1:
        # Analyze specific experiments provided as arguments
        experiments = []
        for exp_path in sys.argv[1:]:
            exp_dir = Path(exp_path)
            if exp_dir.exists():
                experiments.append((exp_dir.name, exp_dir))
        
        print(f"Analyzing {len(experiments)} experiments")
        print("=" * 50)
        
        results = {}
        for exp_name, exp_dir in experiments:
            print(f"\nAnalyzing {exp_name}...")
            stats = analyze_orders_for_experiment(exp_dir)
            rates = calculate_rates(stats)
            results[exp_name] = rates
            
            print(f"\n{exp_name} Results (n={rates['n_phases']} phases):")
            print(f"  Hold rate:    {rates['hold_rate']:.3f} ± {rates['hold_se']:.3f}")
            print(f"  Support rate: {rates['support_rate']:.3f} ± {rates['support_se']:.3f}")
            print(f"  Move rate:    {rates['move_rate']:.3f} ± {rates['move_se']:.3f}")
            print(f"  Convoy rate:  {rates['convoy_rate']:.3f} ± {rates['convoy_se']:.3f}")
        
        # Create visualization for multiple experiments
        if len(results) > 2:
            # Group by model
            models = {}
            for exp_name, rates in results.items():
                if 'mistral' in exp_name.lower():
                    model = 'Mistral'
                elif 'gemini' in exp_name.lower():
                    model = 'Gemini'
                elif 'kimi' in exp_name.lower():
                    model = 'Kimi'
                else:
                    continue
                
                if model not in models:
                    models[model] = {}
                
                # Determine version
                if 'baseline' in exp_name:
                    version = 'Baseline'
                elif '_v3_' in exp_name:
                    version = 'V3'
                elif '_v2_' in exp_name:
                    version = 'V2'
                elif '_v1_' in exp_name or (model == 'Mistral' and 'hold_reduction_mistral_' in exp_name):
                    version = 'V1'
                else:
                    version = 'V1'  # Default for gemini/kimi first intervention
                
                models[model][version] = rates
            
            # Create subplots for each model
            fig, axes = plt.subplots(1, 3, figsize=(18, 6))
            
            for idx, (model, versions) in enumerate(sorted(models.items())):
                ax = axes[idx]
                
                # Sort versions
                version_order = ['Baseline', 'V1', 'V2', 'V3']
                sorted_versions = [(v, versions[v]) for v in version_order if v in versions]
                
                # Prepare data
                version_names = [v[0] for v in sorted_versions]
                hold_rates = [v[1]['hold_rate'] for v in sorted_versions]
                support_rates = [v[1]['support_rate'] for v in sorted_versions]
                move_rates = [v[1]['move_rate'] for v in sorted_versions]
                
                hold_errors = [v[1]['hold_se'] for v in sorted_versions]
                support_errors = [v[1]['support_se'] for v in sorted_versions]
                move_errors = [v[1]['move_se'] for v in sorted_versions]
                
                x = np.arange(len(version_names))
                width = 0.25
                
                # Create bars
                bars1 = ax.bar(x - width, hold_rates, width, yerr=hold_errors,
                               label='Hold', capsize=3, color='#ff7f0e')
                bars2 = ax.bar(x, support_rates, width, yerr=support_errors,
                               label='Support', capsize=3, color='#2ca02c')
                bars3 = ax.bar(x + width, move_rates, width, yerr=move_errors,
                               label='Move', capsize=3, color='#1f77b4')
                
                # Formatting
                ax.set_xlabel('Version')
                ax.set_ylabel('Orders per Unit')
                ax.set_title(f'{model} - Hold Reduction Progression')
                ax.set_xticks(x)
                ax.set_xticklabels(version_names)
                ax.legend()
                ax.grid(axis='y', alpha=0.3)
                ax.set_ylim(0, 1.0)
                
                # Add value labels on bars
                for bars in [bars1, bars2, bars3]:
                    for bar in bars:
                        height = bar.get_height()
                        if height > 0.02:  # Only label visible bars
                            ax.annotate(f'{height:.2f}',
                                        xy=(bar.get_x() + bar.get_width() / 2, height),
                                        xytext=(0, 2),
                                        textcoords="offset points",
                                        ha='center', va='bottom',
                                        fontsize=8)
            
            plt.suptitle('Hold Reduction Experiment Results Across Models', fontsize=16, y=1.02)
            plt.tight_layout()
            plt.savefig('experiments/hold_reduction_all_models_comparison.png', dpi=150, bbox_inches='tight')
            print(f"\nComparison plot saved to experiments/hold_reduction_all_models_comparison.png")
            
            # Save results to CSV
            csv_data = []
            for model, versions in models.items():
                for version, rates in versions.items():
                    csv_data.append({
                        'Model': model,
                        'Version': version,
                        'Hold_Rate': rates['hold_rate'],
                        'Hold_SE': rates['hold_se'],
                        'Support_Rate': rates['support_rate'],
                        'Support_SE': rates['support_se'],
                        'Move_Rate': rates['move_rate'],
                        'Move_SE': rates['move_se'],
                        'N_Phases': rates['n_phases']
                    })
            
            df = pd.DataFrame(csv_data)
            df = df.sort_values(['Model', 'Version'])
            df.to_csv('experiments/hold_reduction_all_results.csv', index=False)
            print(f"Results saved to experiments/hold_reduction_all_results.csv")
            
            # Print summary statistics
            print("\n" + "="*60)
            print("SUMMARY: Hold Rate Changes from Baseline")
            print("="*60)
            for model in sorted(models.keys()):
                print(f"\n{model}:")
                if 'Baseline' in models[model]:
                    baseline = models[model]['Baseline']['hold_rate']
                    for version in ['V1', 'V2', 'V3']:
                        if version in models[model]:
                            rate = models[model][version]['hold_rate']
                            change = (rate - baseline) / baseline * 100
                            print(f"  {version}: {rate:.3f} ({change:+.1f}% from baseline)")
        
        return
    
    # Default behavior - analyze baseline vs intervention
    baseline_dir = Path("experiments/hold_reduction_baseline_S1911M")
    intervention_dir = Path("experiments/hold_reduction_intervention_S1911M")
    
    print("Analyzing Hold Reduction Experiment")
    print("=" * 50)
    
    # Analyze baseline
    print("\nAnalyzing baseline experiment...")
    baseline_stats = analyze_orders_for_experiment(baseline_dir)
    baseline_rates = calculate_rates(baseline_stats)
    
    print(f"\nBaseline Results (n={baseline_rates['n_phases']} phases):")
    print(f"  Hold rate:    {baseline_rates['hold_rate']:.3f} ± {baseline_rates['hold_se']:.3f}")
    print(f"  Support rate: {baseline_rates['support_rate']:.3f} ± {baseline_rates['support_se']:.3f}")
    print(f"  Move rate:    {baseline_rates['move_rate']:.3f} ± {baseline_rates['move_se']:.3f}")
    print(f"  Convoy rate:  {baseline_rates['convoy_rate']:.3f} ± {baseline_rates['convoy_se']:.3f}")
    
    # Analyze intervention
    print("\nAnalyzing intervention experiment...")
    intervention_stats = analyze_orders_for_experiment(intervention_dir)
    intervention_rates = calculate_rates(intervention_stats)
    
    print(f"\nIntervention Results (n={intervention_rates['n_phases']} phases):")
    print(f"  Hold rate:    {intervention_rates['hold_rate']:.3f} ± {intervention_rates['hold_se']:.3f}")
    print(f"  Support rate: {intervention_rates['support_rate']:.3f} ± {intervention_rates['support_se']:.3f}")
    print(f"  Move rate:    {intervention_rates['move_rate']:.3f} ± {intervention_rates['move_se']:.3f}")
    print(f"  Convoy rate:  {intervention_rates['convoy_rate']:.3f} ± {intervention_rates['convoy_se']:.3f}")
    
    # Calculate changes
    print("\nChanges from Baseline to Intervention:")
    hold_change = (intervention_rates['hold_rate'] - baseline_rates['hold_rate']) / baseline_rates['hold_rate'] * 100
    support_change = (intervention_rates['support_rate'] - baseline_rates['support_rate']) / baseline_rates['support_rate'] * 100
    move_change = (intervention_rates['move_rate'] - baseline_rates['move_rate']) / baseline_rates['move_rate'] * 100
    
    print(f"  Hold rate:    {hold_change:+.1f}%")
    print(f"  Support rate: {support_change:+.1f}%")
    print(f"  Move rate:    {move_change:+.1f}%")
    
    # Create visualization
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x = np.arange(4)
    width = 0.35
    
    baseline_means = [
        baseline_rates['hold_rate'],
        baseline_rates['support_rate'],
        baseline_rates['move_rate'],
        baseline_rates['convoy_rate']
    ]
    baseline_errors = [
        baseline_rates['hold_se'],
        baseline_rates['support_se'],
        baseline_rates['move_se'],
        baseline_rates['convoy_se']
    ]
    
    intervention_means = [
        intervention_rates['hold_rate'],
        intervention_rates['support_rate'],
        intervention_rates['move_rate'],
        intervention_rates['convoy_rate']
    ]
    intervention_errors = [
        intervention_rates['hold_se'],
        intervention_rates['support_se'],
        intervention_rates['move_se'],
        intervention_rates['convoy_se']
    ]
    
    bars1 = ax.bar(x - width/2, baseline_means, width, yerr=baseline_errors,
                    label='Baseline', capsize=5)
    bars2 = ax.bar(x + width/2, intervention_means, width, yerr=intervention_errors,
                    label='Hold Reduction', capsize=5)
    
    ax.set_xlabel('Order Type')
    ax.set_ylabel('Orders per Unit')
    ax.set_title('Hold Reduction Experiment: Order Type Distribution')
    ax.set_xticks(x)
    ax.set_xticklabels(['Hold', 'Support', 'Move', 'Convoy'])
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.3f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom',
                        fontsize=8)
    
    plt.tight_layout()
    plt.savefig('experiments/hold_reduction_analysis.png', dpi=150)
    print(f"\nPlot saved to experiments/hold_reduction_analysis.png")
    
    # Save results to CSV
    results_df = pd.DataFrame({
        'Experiment': ['Baseline', 'Intervention'],
        'Hold_Rate': [baseline_rates['hold_rate'], intervention_rates['hold_rate']],
        'Support_Rate': [baseline_rates['support_rate'], intervention_rates['support_rate']],
        'Move_Rate': [baseline_rates['move_rate'], intervention_rates['move_rate']],
        'Convoy_Rate': [baseline_rates['convoy_rate'], intervention_rates['convoy_rate']],
        'N_Phases': [baseline_rates['n_phases'], intervention_rates['n_phases']]
    })
    results_df.to_csv('experiments/hold_reduction_results.csv', index=False)
    print(f"Results saved to experiments/hold_reduction_results.csv")

if __name__ == "__main__":
    main()