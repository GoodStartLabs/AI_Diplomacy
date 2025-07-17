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
    # Define experiment directories
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