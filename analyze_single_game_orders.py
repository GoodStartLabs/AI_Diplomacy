#!/usr/bin/env python3
"""
Analyze order types and success rates for a single Diplomacy game.
"""

from pathlib import Path
import json
import sys
import csv
from collections import defaultdict

# Increase CSV field size limit to handle large fields
csv.field_size_limit(sys.maxsize)

def analyze_single_game(game_file_path):
    """
    Analyze order types and success rates for a single game.
    Returns statistics on holds, supports, moves, convoys and their success rates.
    """
    # Get the corresponding CSV file and overview
    game_dir = game_file_path.parent
    csv_file = game_dir / "llm_responses.csv"
    overview_file = game_dir / "overview.jsonl"
    
    # Load game data
    with open(game_file_path, 'r') as f:
        game_data = json.load(f)
    
    # Load model assignments from overview
    power_models = {}
    if overview_file.exists():
        with open(overview_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                # Check if this line contains power-model mapping
                if (isinstance(data, dict) and 
                    len(data) > 0 and
                    all(key in ['AUSTRIA', 'ENGLAND', 'FRANCE', 'GERMANY', 'ITALY', 'RUSSIA', 'TURKEY'] 
                        for key in data.keys()) and
                    all(isinstance(v, str) for v in data.values())):
                    power_models = data
                    break
    
    # Track order counts by type and result
    order_stats = {
        'hold': {'total': 0, 'success': 0, 'bounce': 0, 'cut': 0, 'dislodged': 0},
        'move': {'total': 0, 'success': 0, 'bounce': 0, 'cut': 0, 'dislodged': 0},
        'support': {'total': 0, 'success': 0, 'bounce': 0, 'cut': 0, 'dislodged': 0},
        'convoy': {'total': 0, 'success': 0, 'bounce': 0, 'cut': 0, 'dislodged': 0}
    }
    
    # Track stats by model
    model_stats = {}
    
    # Track LLM success/failure if CSV exists
    llm_stats = {
        'total_phases': 0,
        'successful_phases': 0,
        'failed_phases': 0
    }
    
    # Track LLM stats by model
    model_llm_stats = {}
    
    if csv_file.exists():
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['response_type'] == 'order_generation':
                    power = row.get('power', '')
                    model = power_models.get(power, row.get('model', 'unknown'))
                    
                    # Overall stats
                    llm_stats['total_phases'] += 1
                    if row['success'] == 'Success':
                        llm_stats['successful_phases'] += 1
                    else:
                        llm_stats['failed_phases'] += 1
                    
                    # Model-specific stats
                    if model not in model_llm_stats:
                        model_llm_stats[model] = {
                            'total_phases': 0,
                            'successful_phases': 0,
                            'failed_phases': 0
                        }
                    
                    model_llm_stats[model]['total_phases'] += 1
                    if row['success'] == 'Success':
                        model_llm_stats[model]['successful_phases'] += 1
                    else:
                        model_llm_stats[model]['failed_phases'] += 1
    
    # Analyze each movement phase
    for phase in game_data.get('phases', []):
        phase_name = phase.get('name', '')
        
        # Only analyze movement phases (skip retreat and build phases)
        if not phase_name.endswith('M'):
            continue
        
        # Process orders for all powers
        for power, power_orders in phase.get('order_results', {}).items():
            model = power_models.get(power, 'unknown')
            
            # Initialize model stats if needed
            if model not in model_stats:
                model_stats[model] = {
                    'hold': {'total': 0, 'success': 0, 'bounce': 0, 'cut': 0, 'dislodged': 0},
                    'move': {'total': 0, 'success': 0, 'bounce': 0, 'cut': 0, 'dislodged': 0},
                    'support': {'total': 0, 'success': 0, 'bounce': 0, 'cut': 0, 'dislodged': 0},
                    'convoy': {'total': 0, 'success': 0, 'bounce': 0, 'cut': 0, 'dislodged': 0}
                }
            
            # Process each order type
            for order_type in ['hold', 'move', 'support', 'convoy']:
                orders = power_orders.get(order_type, [])
                
                for order in orders:
                    # Overall stats
                    order_stats[order_type]['total'] += 1
                    
                    # Model-specific stats
                    model_stats[model][order_type]['total'] += 1
                    
                    # Analyze result
                    result = order.get('result', '')
                    if result == 'success':
                        order_stats[order_type]['success'] += 1
                        model_stats[model][order_type]['success'] += 1
                    elif result == 'bounce':
                        order_stats[order_type]['bounce'] += 1
                        model_stats[model][order_type]['bounce'] += 1
                    elif result == 'cut':
                        order_stats[order_type]['cut'] += 1
                        model_stats[model][order_type]['cut'] += 1
                    elif result == 'dislodged':
                        order_stats[order_type]['dislodged'] += 1
                        model_stats[model][order_type]['dislodged'] += 1
    
    return order_stats, llm_stats, power_models, model_stats, model_llm_stats

def print_results(order_stats, llm_stats, power_models, model_stats, model_llm_stats, game_file):
    """Print formatted results."""
    print(f"\nAnalyzing game: {game_file}")
    print("=" * 80)
    
    # Calculate total orders
    total_orders = sum(stats['total'] for stats in order_stats.values())
    print(f"Total orders analyzed: {total_orders}")
    
    # Print LLM stats if available
    if llm_stats['total_phases'] > 0:
        print(f"\nLLM Order Generation Success Rate:")
        print(f"  Total phases: {llm_stats['total_phases']}")
        print(f"  Successful: {llm_stats['successful_phases']} ({llm_stats['successful_phases']/llm_stats['total_phases']*100:.1f}%)")
        print(f"  Failed: {llm_stats['failed_phases']} ({llm_stats['failed_phases']/llm_stats['total_phases']*100:.1f}%)")
    
    print(f"\nOrder Type Analysis:")
    print(f"{'Type':<10} {'Count':>8} {'% Total':>10} {'Success':>10} {'Bounce':>10} {'Cut':>10} {'Dislodged':>10}")
    print("-" * 80)
    
    for order_type in ['hold', 'support', 'move', 'convoy']:
        stats = order_stats[order_type]
        count = stats['total']
        
        if total_orders > 0:
            percentage = count / total_orders * 100
        else:
            percentage = 0
        
        # Calculate result percentages
        if count > 0:
            success_pct = stats['success'] / count * 100
            bounce_pct = stats['bounce'] / count * 100
            cut_pct = stats['cut'] / count * 100
            dislodged_pct = stats['dislodged'] / count * 100
        else:
            success_pct = bounce_pct = cut_pct = dislodged_pct = 0
        
        print(f"{order_type.capitalize():<10} {count:>8} {percentage:>9.1f}% "
              f"{success_pct:>9.1f}% {bounce_pct:>9.1f}% {cut_pct:>9.1f}% {dislodged_pct:>9.1f}%")
    
    print()
    
    # Summary statistics
    print("Summary Statistics")
    print("=" * 80)
    
    # Overall success rate
    total_success = sum(stats['success'] for stats in order_stats.values())
    if total_orders > 0:
        print(f"Overall order success rate: {total_success/total_orders*100:.1f}%")
    
    # Most common order type
    most_common = max(order_stats.items(), key=lambda x: x[1]['total'])
    if most_common[1]['total'] > 0:
        print(f"Most common order type: {most_common[0].capitalize()} "
              f"({most_common[1]['total']} orders, {most_common[1]['total']/total_orders*100:.1f}%)")
    
    # Most successful order type (minimum 10 orders)
    success_rates = {}
    for order_type, stats in order_stats.items():
        if stats['total'] >= 10:
            success_rates[order_type] = stats['success'] / stats['total']
    
    if success_rates:
        most_successful = max(success_rates.items(), key=lambda x: x[1])
        print(f"Most successful order type: {most_successful[0].capitalize()} "
              f"({most_successful[1]*100:.1f}% success rate)")
    
    # Order failure analysis
    print(f"\nOrder Failure Breakdown:")
    for order_type in ['hold', 'support', 'move', 'convoy']:
        stats = order_stats[order_type]
        if stats['total'] > 0:
            failures = stats['bounce'] + stats['cut'] + stats['dislodged']
            print(f"  {order_type.capitalize()}: {failures}/{stats['total']} failed "
                  f"({failures/stats['total']*100:.1f}%)")
    
    # Print model-specific analysis if multiple models
    if len(model_stats) > 1:
        print("\n" + "=" * 80)
        print("ANALYSIS BY MODEL")
        print("=" * 80)
        
        # Print power-model mapping
        if power_models:
            print("\nPower-Model Assignments:")
            for power, model in sorted(power_models.items()):
                print(f"  {power}: {model}")
        
        # Print LLM success by model
        if model_llm_stats:
            print(f"\nLLM Order Generation Success by Model:")
            for model, stats in sorted(model_llm_stats.items()):
                if stats['total_phases'] > 0:
                    success_rate = stats['successful_phases'] / stats['total_phases'] * 100
                    print(f"  {model}: {stats['successful_phases']}/{stats['total_phases']} "
                          f"({success_rate:.1f}% success)")
        
        # Print order type distribution by model
        for model, m_stats in sorted(model_stats.items()):
            print(f"\n{model}:")
            model_total = sum(s['total'] for s in m_stats.values())
            
            if model_total > 0:
                print(f"  Total orders: {model_total}")
                print(f"  Order distribution:")
                for order_type in ['hold', 'support', 'move', 'convoy']:
                    count = m_stats[order_type]['total']
                    if count > 0:
                        pct = count / model_total * 100
                        success_rate = m_stats[order_type]['success'] / count * 100
                        print(f"    {order_type.capitalize()}: {count} ({pct:.1f}%), "
                              f"{success_rate:.1f}% success")

def main():
    if len(sys.argv) != 2:
        print("Usage: python analyze_single_game_orders.py <path_to_game_json>")
        print("Example: python analyze_single_game_orders.py results/v3_mixed_20250721_112549/lmvsgame.json")
        sys.exit(1)
    
    game_file = Path(sys.argv[1])
    
    if not game_file.exists():
        print(f"Error: File not found: {game_file}")
        sys.exit(1)
    
    if not game_file.suffix == '.json':
        print(f"Error: Expected a JSON file, got: {game_file}")
        sys.exit(1)
    
    try:
        order_stats, llm_stats, power_models, model_stats, model_llm_stats = analyze_single_game(game_file)
        print_results(order_stats, llm_stats, power_models, model_stats, model_llm_stats, game_file)
    except Exception as e:
        print(f"Error analyzing game: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()