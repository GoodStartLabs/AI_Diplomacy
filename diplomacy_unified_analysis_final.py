#!/usr/bin/env python3
"""
Enhanced CSV-Only Diplomacy Model Analysis Script
- Uses ONLY CSV data as the source of truth
- No JSON parsing that can mistake messages for model names
- Includes comprehensive visualization suite
- Proper scaling and ordering of visualizations
"""

import json
import sys
import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta
import argparse
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

# Increase CSV field size limit
csv.field_size_limit(sys.maxsize)

# AAAI publication quality styling
plt.rcParams.update({
    'font.size': 12,
    'axes.titlesize': 14,
    'axes.labelsize': 13,
    'xtick.labelsize': 11,
    'ytick.labelsize': 11,
    'legend.fontsize': 11,
    'figure.dpi': 150,
    'savefig.dpi': 300,
    'font.family': 'sans-serif',
    'axes.linewidth': 1.5,
    'lines.linewidth': 2.5,
    'lines.markersize': 8,
    'grid.alpha': 0.3,
    'axes.grid': True,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'figure.figsize': (10, 6),  # Default single figure size
})

# Color schemes
COLORS = {
    'hold': '#808080',      # Gray
    'move': '#2E5090',      # Deep Blue
    'support': '#009E73',   # Green
    'convoy': '#CC79A7',    # Purple
    'active': '#D55E00',    # Orange for active orders
    'success': '#2ECC71',   # Success Green
    'failure': '#E74C3C',   # Failure Red
}

def get_year_from_phase_name(phase_name):
    """Extract year from phase name (e.g., 'S1901M' -> 1901)"""
    if len(phase_name) >= 5:
        try:
            year_str = phase_name[1:5]
            return int(year_str)
        except:
            return None
    return None

def get_decade_bin(year):
    """Get decade bin for a year (e.g., 1903 -> '1900-1910')"""
    if year is None:
        return None
    decade_start = (year // 10) * 10
    decade_end = decade_start + 10
    return f"{decade_start}-{decade_end}"

def extract_models_from_csv(game_dir):
    """Extract ALL models from CSV file ONLY - this is the source of truth"""
    models = set()
    
    csv_file = game_dir / "llm_responses.csv"
    if csv_file.exists():
        try:
            print(f"  Reading CSV file: {csv_file}")
            
            # First, get total row count for progress tracking
            with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
                row_count = sum(1 for line in f) - 1  # Subtract header
            
            print(f"    Total rows: {row_count}")
            
            # Read the model column to get unique models
            df = pd.read_csv(csv_file, usecols=['model'])
            
            if 'model' in df.columns:
                # Get all unique models
                unique_models = df['model'].dropna().unique()
                for model in unique_models:
                    if model and str(model).strip() and str(model) != 'model':
                        models.add(str(model).strip())
                
                print(f"    Found {len(unique_models)} unique models in CSV")
            
        except Exception as e:
            print(f"  Error reading CSV: {e}")
    
    return models

def analyze_game(game_file_path):
    """Analyze a single game using CSV for model-power-phase mappings"""
    game_dir = game_file_path.parent
    game_timestamp = datetime.fromtimestamp(game_file_path.stat().st_mtime)
    
    print(f"\nAnalyzing game: {game_dir.name}")
    
    # Get all models from CSV only
    all_models = extract_models_from_csv(game_dir)
    
    # Initialize result
    result = {
        'game_id': game_dir.name,
        'timestamp': game_timestamp,
        'all_models': list(all_models),
        'power_models': {},  # We'll build this from CSV
        'phase_data': defaultdict(list)
    }
    
    # Load game data
    try:
        with open(game_file_path, 'r') as f:
            game_data = json.load(f)
    except:
        return result
    
    # Read CSV to get model-power-phase mappings
    csv_file = game_dir / "llm_responses.csv"
    if not csv_file.exists():
        return result
        
    try:
        # Read the CSV with phase, power, and model columns
        df = pd.read_csv(csv_file, usecols=['phase', 'power', 'model'])
        
        # Process each phase in the game
        for phase in game_data.get('phases', []):
            phase_name = phase.get('name', '')
            
            if not phase_name.endswith('M'):
                continue
            
            year = get_year_from_phase_name(phase_name)
            decade = get_decade_bin(year)
            
            # Get unit counts from phase state
            phase_state = phase.get('state', {})
            phase_units = phase_state.get('units', {})
            
            # Get all rows for this phase
            phase_df = df[df['phase'] == phase_name]
            
            # For each model that played in this phase, aggregate their orders
            model_phase_data = defaultdict(lambda: {
                'phase_name': phase_name,
                'year': year,
                'decade': decade,
                'power': 'AGGREGATE',  # Aggregating across all powers
                'game_id': game_dir.name,
                'total_orders': 0,
                'order_counts': {'hold': 0, 'move': 0, 'support': 0, 'convoy': 0},
                'order_successes': {'hold': 0, 'move': 0, 'support': 0, 'convoy': 0},
                'unit_count': 0,
            })
            
            # Process each power that played in this phase
            for power in ['AUSTRIA', 'ENGLAND', 'FRANCE', 'GERMANY', 'ITALY', 'RUSSIA', 'TURKEY']:
                # Get the model for this power in this phase
                power_phase_df = phase_df[phase_df['power'] == power]
                if len(power_phase_df) == 0:
                    continue
                    
                model = power_phase_df.iloc[0]['model']
                if pd.isna(model):
                    continue
                    
                model = str(model).strip()
                
                # Track this power-model mapping
                result['power_models'][power] = model
                
                # Count units for this power
                unit_count = len(phase_units.get(power, []))
                model_phase_data[model]['unit_count'] += unit_count
                
                # Process orders from the phase data
                # Try new format first
                if 'order_results' in phase and power in phase.get('order_results', {}):
                    power_orders = phase['order_results'][power]
                    for order_type in ['hold', 'move', 'support', 'convoy']:
                        orders = power_orders.get(order_type, [])
                        count = len(orders)
                        success_count = sum(1 for order in orders if order.get('result', '') == 'success')
                        
                        model_phase_data[model]['order_counts'][order_type] += count
                        model_phase_data[model]['order_successes'][order_type] += success_count
                        model_phase_data[model]['total_orders'] += count
                
                # Try old format
                elif 'orders' in phase and power in phase.get('orders', {}):
                    order_list = phase['orders'][power]
                    results_dict = phase.get('results', {})
                    
                    if order_list:
                        for idx, order_str in enumerate(order_list):
                            # Extract unit location from order (e.g., "A PAR - PIC" -> "A PAR")
                            unit_loc = None
                            if ' - ' in order_str or ' S ' in order_str or ' C ' in order_str or ' H' in order_str:
                                # Extract the unit and location part before the order
                                parts = order_str.strip().split(' ')
                                if len(parts) >= 2 and parts[0] in ['A', 'F']:
                                    unit_loc = f"{parts[0]} {parts[1]}"
                            
                            # Determine order type
                            if ' H' in order_str or order_str.endswith(' H'):
                                order_type = 'hold'
                            elif ' - ' in order_str:
                                order_type = 'move'
                            elif ' S ' in order_str:
                                order_type = 'support'
                            elif ' C ' in order_str:
                                order_type = 'convoy'
                            else:
                                order_type = 'hold'
                            
                            model_phase_data[model]['order_counts'][order_type] += 1
                            model_phase_data[model]['total_orders'] += 1
                            
                            # Check if successful using unit location
                            if unit_loc and unit_loc in results_dict:
                                result_value = results_dict[unit_loc]
                                # In old format: empty list or empty string means success
                                # Non-empty means some kind of failure (bounce, dislodged, void)
                                if isinstance(result_value, list) and len(result_value) == 0:
                                    # Empty list means success
                                    model_phase_data[model]['order_successes'][order_type] += 1
                                elif isinstance(result_value, str) and result_value == "":
                                    # Empty string means success
                                    model_phase_data[model]['order_successes'][order_type] += 1
                                elif result_value is None:
                                    # None might also mean success in some cases
                                    model_phase_data[model]['order_successes'][order_type] += 1
            
            # Append phase stats for each model
            for model, stats in model_phase_data.items():
                result['phase_data'][model].append(stats)
                
    except Exception as e:
        print(f"Error processing CSV for {game_dir.name}: {e}")
    
    return result

def create_comprehensive_charts(all_data, output_dir):
    """Create all visualization charts"""
    
    # Aggregate model statistics
    model_stats = defaultdict(lambda: {
        'games_participated': set(),
        'total_phases': 0,
        'total_orders': 0,
        'order_counts': {'hold': 0, 'move': 0, 'support': 0, 'convoy': 0},
        'order_successes': {'hold': 0, 'move': 0, 'support': 0, 'convoy': 0},
        'powers_played': defaultdict(int),
        'decade_distribution': defaultdict(int),
        'phase_details': [],
        'unit_counts': [],  # List of unit counts across all phases
        'unit_count_distribution': defaultdict(int)  # How many phases with X units
    })
    
    # First pass: collect all models mentioned anywhere
    all_models_found = set()
    models_missing_phases = defaultdict(set)  # Track which games have models without phases
    
    for game_data in all_data:
        all_models_found.update(game_data['all_models'])
        
        # Track models that appear in games but not in phase data
        models_in_phase_data = set(game_data['phase_data'].keys())
        models_missing = set(game_data['all_models']) - models_in_phase_data
        for model in models_missing:
            models_missing_phases[model].add(game_data['game_id'])
    
    # Second pass: aggregate phase data
    for game_data in all_data:
        game_id = game_data['game_id']
        
        # Track game participation for all models in game
        for model in game_data['all_models']:
            model_stats[model]['games_participated'].add(game_id)
        
        # Process phase data
        for model, phases in game_data['phase_data'].items():
            for phase in phases:
                model_stats[model]['total_phases'] += 1
                model_stats[model]['total_orders'] += phase['total_orders']
                model_stats[model]['powers_played'][phase['power']] += 1
                model_stats[model]['phase_details'].append(phase)
                
                # Track unit counts
                unit_count = phase.get('unit_count', 0)
                if unit_count > 0:
                    model_stats[model]['unit_counts'].append(unit_count)
                    model_stats[model]['unit_count_distribution'][unit_count] += 1
                
                if phase['decade']:
                    model_stats[model]['decade_distribution'][phase['decade']] += 1
                
                # Aggregate order counts and successes
                for order_type in ['hold', 'move', 'support', 'convoy']:
                    model_stats[model]['order_counts'][order_type] += phase['order_counts'][order_type]
                    model_stats[model]['order_successes'][order_type] += phase['order_successes'][order_type]
    
    # Calculate derived metrics
    for model, stats in model_stats.items():
        # Active order percentage
        total = stats['total_orders']
        active = total - stats['order_counts']['hold'] if total > 0 else 0
        stats['active_percentage'] = (active / total * 100) if total > 0 else 0
        
        # Success rates
        stats['success_rates'] = {}
        for order_type in ['hold', 'move', 'support', 'convoy']:
            count = stats['order_counts'][order_type]
            success = stats['order_successes'][order_type]
            stats['success_rates'][order_type] = (success / count * 100) if count > 0 else 0
        
        # Overall success rate on active orders (excluding holds)
        total_active = sum(stats['order_counts'][t] for t in ['move', 'support', 'convoy'])
        total_active_success = sum(stats['order_successes'][t] for t in ['move', 'support', 'convoy'])
        stats['active_success_rate'] = (total_active_success / total_active * 100) if total_active > 0 else 0
    
    # Create visualizations
    print("\nCreating comprehensive visualizations...")
    
    # 1. High-quality models analysis (must come first)
    create_high_quality_models_chart(model_stats, output_dir)
    
    # 2. Success rates charts
    create_success_rates_charts(model_stats, output_dir, all_models_found)
    
    # 3. Active order percentage charts
    create_active_order_percentage_charts(model_stats, output_dir)
    
    # 4. Order distribution charts
    create_order_distribution_charts(model_stats, output_dir)
    
    # 5. Temporal analysis
    create_temporal_analysis(model_stats, output_dir)
    
    # 6. Power distribution analysis
    create_power_distribution_analysis(model_stats, output_dir)
    
    # 7. Physical dates timeline
    create_physical_dates_timeline(all_data, model_stats, output_dir)
    
    # 8. Phase and game counts
    create_phase_game_counts(model_stats, output_dir)
    
    # 9. Model comparison heatmap
    create_comparison_heatmap(model_stats, output_dir)
    
    # 10. Unit control analysis
    create_unit_control_analysis(model_stats, output_dir)
    
    # 11. Success over physical time
    create_success_over_physical_time(all_data, model_stats, output_dir)
    
    # 12. Model evolution chart
    create_model_evolution_chart(all_data, model_stats, output_dir)
    
    # Save comprehensive analysis metadata
    save_metadata = {
        'total_games': len(all_data),
        'total_unique_models': len(all_models_found),
        'models_with_phase_data': len([m for m in model_stats if model_stats[m]['total_phases'] > 0]),
        'models_without_phase_data': len(models_missing_phases),
        'models_with_active_orders': len([m for m in model_stats if model_stats[m]['active_percentage'] > 0]),
        'timestamp': datetime.now().isoformat()
    }
    
    with open(output_dir / 'analysis_metadata.json', 'w') as f:
        json.dump(save_metadata, f, indent=2)
    
    # Create summary report
    create_summary_report(model_stats, all_models_found, models_missing_phases, output_dir)
    
    return model_stats

def create_high_quality_models_chart(model_stats, output_dir):
    """Create focused visualization for models with substantial gameplay data"""
    # Filter for models with meaningful data
    high_quality_models = []
    
    for model, stats in model_stats.items():
        total_orders = stats.get('total_orders', 0)
        non_hold_orders = total_orders - stats.get('order_counts', {}).get('hold', 0)
        phases = stats.get('total_phases', 0)
        
        # Only include models with substantial active gameplay
        if non_hold_orders >= 500 and phases >= 200:
            non_hold_successes = sum(stats.get('order_successes', {}).get(t, 0) 
                                    for t in ['move', 'support', 'convoy'])
            success_rate = (non_hold_successes / non_hold_orders * 100) if non_hold_orders > 0 else 0
            active_percentage = (non_hold_orders / total_orders * 100)
            
            high_quality_models.append({
                'model': model,
                'phases': phases,
                'games': len(stats.get('games_participated', set())),
                'success_rate': success_rate,
                'active_percentage': active_percentage,
                'non_hold_orders': non_hold_orders,
                'move_rate': stats['order_counts']['move'] / total_orders * 100,
                'support_rate': stats['order_counts']['support'] / total_orders * 100,
                'convoy_rate': stats['order_counts']['convoy'] / total_orders * 100
            })
    
    if not high_quality_models:
        print("No high-quality models found with 500+ active orders and 200+ phases")
        return
    
    # Sort by success rate
    high_quality_models.sort(key=lambda x: x['success_rate'], reverse=True)
    
    print(f"\nHigh-Quality Models: {len(high_quality_models)} models with 500+ active orders and 200+ phases")
    
    # Create visualization
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 10))
    
    # Left chart: Success rates
    model_names = []
    success_rates = []
    active_percentages = []
    
    for data in high_quality_models[:20]:  # Top 20
        model_display = data['model'].split('/')[-1] if '/' in data['model'] else data['model']
        model_display = model_display[:30]
        model_names.append(f"{model_display} ({data['phases']}p)")
        success_rates.append(data['success_rate'])
        active_percentages.append(data['active_percentage'])
    
    y_pos = np.arange(len(model_names))
    bars1 = ax1.barh(y_pos, success_rates, color=COLORS['success'], alpha=0.8)
    
    # Add value labels
    for i, (bar, rate) in enumerate(zip(bars1, success_rates)):
        ax1.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                f'{rate:.1f}%', va='center', fontsize=9)
    
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(model_names, fontsize=10)
    ax1.set_xlabel('Success Rate on Active Orders (%)', fontsize=12)
    ax1.set_title('Top Performing Models\n(500+ active orders, 200+ phases)', fontsize=14, fontweight='bold')
    ax1.axvline(x=50, color='red', linestyle='--', alpha=0.5, label='50% baseline')
    ax1.set_xlim(35, 70)
    
    # Right chart: Active order composition
    move_rates = [d['move_rate'] for d in high_quality_models[:20]]
    support_rates = [d['support_rate'] for d in high_quality_models[:20]]
    convoy_rates = [d['convoy_rate'] for d in high_quality_models[:20]]
    
    x = np.arange(len(model_names))
    width = 0.8
    
    bars_move = ax2.barh(x, move_rates, width, label='Move', color=COLORS['move'], alpha=0.8)
    bars_support = ax2.barh(x, support_rates, width, left=move_rates, label='Support', color=COLORS['support'], alpha=0.8)
    bars_convoy = ax2.barh(x, convoy_rates, width, 
                           left=[m+s for m,s in zip(move_rates, support_rates)], 
                           label='Convoy', color=COLORS['convoy'], alpha=0.8)
    
    ax2.set_yticks(x)
    ax2.set_yticklabels([])  # Hide labels on right chart
    ax2.set_xlabel('Order Type Distribution (%)', fontsize=12)
    ax2.set_title('Active Order Composition', fontsize=14, fontweight='bold')
    ax2.legend(loc='lower right')
    ax2.set_xlim(0, 100)
    
    plt.suptitle(f'High-Quality Model Analysis\n{len(high_quality_models)} models with substantial active gameplay',
                 fontsize=16, fontweight='bold')
    plt.tight_layout()
    fig.savefig(output_dir / '00_high_quality_models.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_success_rates_charts(model_stats, output_dir, all_models_found):
    """Create success rate charts for all models"""
    # Filter to models with actual phase data and calculate success rates
    models_with_data = []
    
    for model, stats in model_stats.items():
        if stats['total_phases'] > 0:
            # Calculate success rate on active orders only
            active_orders = sum(stats['order_counts'][t] for t in ['move', 'support', 'convoy'])
            active_successes = sum(stats['order_successes'][t] for t in ['move', 'support', 'convoy'])
            
            if active_orders > 0:
                success_rate = (active_successes / active_orders * 100)
            else:
                success_rate = 0
                
            models_with_data.append({
                'model': model,
                'success_rate': success_rate,
                'active_orders': active_orders,
                'total_phases': stats['total_phases'],
                'active_percentage': stats['active_percentage']
            })
    
    if not models_with_data:
        print("No models with phase data found!")
        return
    
    # Sort by total active orders (to show most active models first)
    models_with_data.sort(key=lambda x: x['active_orders'], reverse=True)
    
    # Create the main success rates chart
    fig, ax = plt.subplots(figsize=(16, max(10, len(models_with_data) * 0.25)))
    
    models = []
    success_rates = []
    colors = []
    
    for data in models_with_data:
        models.append(data['model'])
        success_rates.append(data['success_rate'])
        
        # Color based on success rate
        if data['success_rate'] > 50:
            colors.append(COLORS['success'])
        else:
            colors.append(COLORS['failure'])
    
    if models:
        y_pos = np.arange(len(models))
        
        # Create horizontal bars
        bars = ax.barh(y_pos, success_rates, color=colors)
        
        # Add value labels
        for i, (bar, rate, data) in enumerate(zip(bars, success_rates, models_with_data)):
            # Add success rate
            if rate > 0 or data['active_orders'] > 0:
                ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                       f'{rate:.1f}%\n({data["active_orders"]} active)',
                       va='center', fontsize=8)
            else:
                ax.text(1, bar.get_y() + bar.get_height()/2,
                       f'0.0%\n({data["total_phases"]} phases)\n{data["active_percentage"]:.0f}% active',
                       va='center', fontsize=8, color='gray')
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(models, fontsize=10)
        ax.set_xlabel('Active Order Success Rate (%)', fontsize=12)
        ax.set_title(f'Success Rates on Active Orders - {len(models)} Models', fontsize=14)
        ax.axvline(x=50, color='red', linestyle='--', alpha=0.5)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, 100)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'all_models_success_rates.png', dpi=300, bbox_inches='tight')
        plt.close()

def create_active_order_percentage_charts(model_stats, output_dir):
    """Create active order percentage chart (sorted by activity level)"""
    # Get models with order data
    models_with_orders = []
    
    for model, stats in model_stats.items():
        if stats['total_orders'] > 0:
            models_with_orders.append({
                'model': model,
                'active_percentage': stats['active_percentage'],
                'total_orders': stats['total_orders'],
                'total_phases': stats['total_phases']
            })
    
    if not models_with_orders:
        return
    
    # Sort by active percentage
    models_with_orders.sort(key=lambda x: x['active_percentage'], reverse=True)
    
    fig, ax = plt.subplots(figsize=(16, max(10, len(models_with_orders) * 0.25)))
    
    models = []
    active_pcts = []
    total_orders = []
    
    for data in models_with_orders:
        models.append(data['model'])
        active_pcts.append(data['active_percentage'])
        total_orders.append(data['total_orders'])
    
    if models:
        y_pos = np.arange(len(models))
        
        # Create gradient colors based on activity level
        colors = plt.cm.RdYlGn(np.array(active_pcts) / 100)
        bars = ax.barh(y_pos, active_pcts, color=colors)
        
        # Add value labels
        for i, (bar, pct, orders) in enumerate(zip(bars, active_pcts, total_orders)):
            ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                   f'{pct:.1f}%\n({orders} orders)',
                   va='center', fontsize=8)
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(models, fontsize=10)
        ax.set_xlabel('Active Order Percentage (%)', fontsize=12)
        ax.set_title(f'Active Order Percentage by Model - Sorted by Activity Level', fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, 100)
        
        # Add reference line at 50%
        ax.axvline(x=50, color='black', linestyle='--', alpha=0.5, label='50% threshold')
        
        plt.tight_layout()
        plt.savefig(output_dir / 'all_models_active_percentage.png', dpi=300, bbox_inches='tight')
        plt.close()

def create_order_distribution_charts(model_stats, output_dir):
    """Create order distribution heatmap"""
    # Filter models with orders
    models_with_orders = []
    
    for model, stats in model_stats.items():
        if stats['total_orders'] > 0:
            models_with_orders.append((model, stats))
    
    if not models_with_orders:
        return
    
    # Sort by total orders
    models_with_orders.sort(key=lambda x: x[1]['total_orders'], reverse=True)
    
    # Take top models that fit well in visualization
    max_models = min(50, len(models_with_orders))
    models_with_orders = models_with_orders[:max_models]
    
    fig, ax = plt.subplots(figsize=(12, max(10, len(models_with_orders) * 0.3)))
    
    # Prepare data for heatmap
    order_types = ['hold', 'move', 'support', 'convoy']
    heatmap_data = []
    model_names = []
    
    for model, stats in models_with_orders:
        model_names.append(model)
        row = []
        for order_type in order_types:
            pct = (stats['order_counts'][order_type] / stats['total_orders'] * 100)
            row.append(pct)
        heatmap_data.append(row)
    
    if heatmap_data:
        # Create heatmap
        sns.heatmap(heatmap_data, 
                   xticklabels=order_types,
                   yticklabels=model_names,
                   annot=True, fmt='.1f',
                   cmap='YlOrRd', 
                   cbar_kws={'label': 'Percentage of Orders (%)'},
                   ax=ax)
        
        ax.set_title('Order Type Distribution by Model', fontsize=14)
        ax.set_xlabel('Order Type', fontsize=12)
        ax.set_ylabel('Model', fontsize=12)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'all_models_order_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()

def create_temporal_analysis(model_stats, output_dir):
    """Create temporal analysis by decade"""
    # Get models with temporal data
    models_with_decades = []
    for model, stats in model_stats.items():
        if stats['decade_distribution'] and stats['total_phases'] >= 50:
            models_with_decades.append((model, stats))
    
    if not models_with_decades:
        print("No models with sufficient temporal data found")
        return
    
    models_with_decades.sort(key=lambda x: x[1]['total_phases'], reverse=True)
    
    # Take top models for clarity
    max_models = min(20, len(models_with_decades))
    models_with_decades = models_with_decades[:max_models]
    
    # Calculate grid dimensions
    cols = 4
    rows = (max_models + cols - 1) // cols
    
    fig, axes = plt.subplots(rows, cols, figsize=(20, 5 * rows))
    if rows == 1:
        axes = axes.reshape(1, -1)
    axes = axes.flatten()
    
    for idx, (model, stats) in enumerate(models_with_decades):
        ax = axes[idx]
        
        # Calculate success rates by decade
        decade_success = {}
        for phase in stats['phase_details']:
            if phase['decade']:
                if phase['decade'] not in decade_success:
                    decade_success[phase['decade']] = {'orders': 0, 'successes': 0}
                decade_success[phase['decade']]['orders'] += phase['total_orders']
                decade_success[phase['decade']]['successes'] += sum(phase['order_successes'].values())
        
        if not decade_success:
            ax.set_visible(False)
            continue
            
        decades = sorted(decade_success.keys())
        success_rates = []
        
        for decade in decades:
            data = decade_success[decade]
            rate = (data['successes'] / data['orders'] * 100) if data['orders'] > 0 else 0
            success_rates.append(rate)
        
        # Create bar chart
        x = range(len(decades))
        bars = ax.bar(x, success_rates, color=COLORS['move'], alpha=0.8)
        
        # Add value labels
        for i, (bar, rate) in enumerate(zip(bars, success_rates)):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                   f'{rate:.0f}%', ha='center', va='bottom', fontsize=8)
        
        ax.set_xticks(x)
        ax.set_xticklabels([d.split('-')[0] for d in decades], rotation=45)
        ax.set_ylim(0, 100)
        ax.axhline(y=50, color='red', linestyle='--', alpha=0.3)
        ax.set_ylabel('Success Rate (%)')
        ax.set_title(f'{model}\n({stats["total_phases"]} phases)', fontsize=10)
        ax.grid(True, alpha=0.3)
    
    # Hide unused subplots
    for idx in range(max_models, len(axes)):
        axes[idx].set_visible(False)
    
    fig.suptitle('Temporal Success Analysis by Decade', fontsize=16, fontweight='bold')
    plt.tight_layout()
    fig.savefig(output_dir / 'temporal_analysis_decades.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_power_distribution_analysis(model_stats, output_dir):
    """Create power distribution analysis"""
    # Get models with power data
    models_with_powers = []
    
    for model, stats in model_stats.items():
        if stats['powers_played'] and stats['total_phases'] >= 50:
            models_with_powers.append((model, stats))
    
    if not models_with_powers:
        return
    
    models_with_powers.sort(key=lambda x: x[1]['total_phases'], reverse=True)
    max_models = min(30, len(models_with_powers))
    
    fig, ax = plt.subplots(figsize=(14, max(10, max_models * 0.4)))
    
    # Prepare data
    powers = ['AUSTRIA', 'ENGLAND', 'FRANCE', 'GERMANY', 'ITALY', 'RUSSIA', 'TURKEY']
    power_colors = {
        'AUSTRIA': '#FF6B6B',
        'ENGLAND': '#4ECDC4',
        'FRANCE': '#45B7D1',
        'GERMANY': '#96CEB4',
        'ITALY': '#DDA0DD',
        'RUSSIA': '#F4A460',
        'TURKEY': '#FFD93D'
    }
    
    heatmap_data = []
    model_names = []
    
    for model, stats in models_with_powers[:max_models]:
        model_names.append(model)
        row = []
        total_power_phases = sum(stats['powers_played'].values())
        for power in powers:
            count = stats['powers_played'].get(power, 0)
            pct = (count / total_power_phases * 100) if total_power_phases > 0 else 0
            row.append(pct)
        heatmap_data.append(row)
    
    if heatmap_data:
        # Create heatmap
        sns.heatmap(heatmap_data,
                   xticklabels=powers,
                   yticklabels=model_names,
                   annot=True, fmt='.0f',
                   cmap='Blues',
                   cbar_kws={'label': 'Percentage of Phases (%)'},
                   ax=ax)
        
        ax.set_title('Power Distribution by Model', fontsize=14)
        ax.set_xlabel('Power', fontsize=12)
        ax.set_ylabel('Model', fontsize=12)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'power_distribution_heatmap.png', dpi=300, bbox_inches='tight')
        plt.close()

def create_physical_dates_timeline(all_data, model_stats, output_dir):
    """Create timeline showing model activity over actual dates"""
    # Extract dates from game IDs
    date_model_activity = defaultdict(lambda: defaultdict(int))
    
    for game_data in all_data:
        # Try to extract date from game_id
        game_id = game_data['game_id']
        game_date = None
        
        # Try different date formats
        if len(game_id) >= 8 and game_id[:8].isdigit():
            try:
                game_date = datetime.strptime(game_id[:8], '%Y%m%d').date()
            except:
                pass
        
        if not game_date:
            # Try to use timestamp
            if 'timestamp' in game_data:
                game_date = game_data['timestamp'].date()
        
        if game_date:
            for model in game_data['all_models']:
                date_model_activity[game_date][model] += 1
    
    if not date_model_activity:
        print("No date information found in game data")
        return
    
    # Get top models by total activity
    model_totals = defaultdict(int)
    for date_data in date_model_activity.values():
        for model, count in date_data.items():
            model_totals[model] += count
    
    top_models = sorted(model_totals.items(), key=lambda x: x[1], reverse=True)[:10]
    top_model_names = [m[0] for m in top_models]
    
    # Prepare data for plotting
    dates = sorted(date_model_activity.keys())
    
    fig, ax = plt.subplots(figsize=(16, 8))
    
    for model in top_model_names:
        model_dates = []
        model_counts = []
        
        for date in dates:
            if model in date_model_activity[date]:
                model_dates.append(date)
                model_counts.append(date_model_activity[date][model])
        
        if model_dates:
            ax.plot(model_dates, model_counts, marker='o', label=model, alpha=0.7)
    
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Games per Day', fontsize=12)
    ax.set_title('Model Activity Timeline', fontsize=14, fontweight='bold')
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.grid(True, alpha=0.3)
    
    # Format x-axis
    import matplotlib.dates as mdates
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    fig.savefig(output_dir / 'physical_dates_timeline.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_phase_game_counts(model_stats, output_dir):
    """Create phase and game count comparison"""
    # Get models with games
    models_with_games = [(m, s) for m, s in model_stats.items() 
                        if len(s['games_participated']) > 0]
    
    if not models_with_games:
        return
    
    models_with_games.sort(key=lambda x: (x[1]['total_phases'], len(x[1]['games_participated'])), 
                          reverse=True)
    
    # Take top models
    max_models = min(40, len(models_with_games))
    models_with_games = models_with_games[:max_models]
    
    fig, ax = plt.subplots(figsize=(14, 10))
    
    model_names = []
    phase_counts = []
    game_counts = []
    
    for model, stats in models_with_games:
        model_names.append(model)
        phase_counts.append(stats['total_phases'])
        game_counts.append(len(stats['games_participated']))
    
    x = np.arange(len(model_names))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, phase_counts, width, label='Phases', color=COLORS['move'])
    bars2 = ax.bar(x + width/2, game_counts, width, label='Games', color=COLORS['support'])
    
    # Add value labels for significant values
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            if height > 10:
                ax.annotate(f'{int(height)}',
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3), textcoords="offset points",
                           ha='center', va='bottom', fontsize=7, 
                           rotation=90 if height > 1000 else 0)
    
    ax.set_xlabel('Model')
    ax.set_ylabel('Count (log scale)')
    ax.set_yscale('log')
    ax.set_title(f'Phase and Game Counts by Model (Top {max_models})', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(model_names, rotation=45, ha='right', fontsize=8)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    fig.savefig(output_dir / 'phase_game_counts.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_comparison_heatmap(model_stats, output_dir):
    """Create comparison heatmap for top models"""
    # Get top models by phases
    top_models = [(m, s) for m, s in model_stats.items() if s['total_phases'] >= 50]
    
    if not top_models:
        return
    
    top_models.sort(key=lambda x: x[1]['total_phases'], reverse=True)
    top_models = top_models[:20]
    
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Prepare comparison data
    comparison_data = []
    model_names = []
    
    for model, stats in top_models:
        total_orders = stats['total_orders']
        if total_orders > 0:
            success_rate = sum(stats['order_successes'].values()) / total_orders * 100
            active_rate = (total_orders - stats['order_counts']['hold']) / total_orders * 100
            complexity = (stats['order_counts']['support'] + stats['order_counts']['convoy']) / total_orders * 100
            
            comparison_data.append([
                len(stats['games_participated']),
                stats['total_phases'],
                success_rate,
                active_rate,
                complexity
            ])
            
            model_names.append(model)
    
    if not comparison_data:
        return
    
    # Create DataFrame
    columns = ['Games', 'Phases', 'Success%', 'Active%', 'Complex%']
    df = pd.DataFrame(comparison_data, index=model_names, columns=columns)
    
    # Normalize for heatmap
    df_normalized = (df - df.min()) / (df.max() - df.min())
    
    sns.heatmap(df_normalized, annot=df.round(1), fmt='g', cmap='YlOrRd',
                ax=ax, cbar_kws={'label': 'Normalized Score'}, annot_kws={'size': 9})
    
    ax.set_title('Top 20 Models Comparison Heatmap', fontweight='bold', pad=20)
    ax.set_xlabel('Metrics')
    ax.set_ylabel('Model')
    
    plt.tight_layout()
    fig.savefig(output_dir / 'model_comparison_heatmap.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_unit_control_analysis(model_stats, output_dir):
    """Create unit control analysis showing performance vs unit count"""
    # Collect data for unit control analysis
    unit_performance_data = []
    
    for model, stats in model_stats.items():
        if stats['total_phases'] < 50:  # Minimum threshold
            continue
            
        # Group performance by unit count
        unit_buckets = defaultdict(lambda: {'orders': 0, 'successes': 0, 'phases': 0})
        
        for phase in stats['phase_details']:
            unit_count = phase.get('unit_count', 0)
            if unit_count > 0:
                # Bucket unit counts
                if unit_count <= 3:
                    bucket = '1-3'
                elif unit_count <= 6:
                    bucket = '4-6'
                elif unit_count <= 9:
                    bucket = '7-9'
                elif unit_count <= 12:
                    bucket = '10-12'
                else:
                    bucket = '13+'
                
                unit_buckets[bucket]['orders'] += phase['total_orders']
                unit_buckets[bucket]['successes'] += sum(phase['order_successes'].values())
                unit_buckets[bucket]['phases'] += 1
        
        # Calculate success rates per bucket
        for bucket, data in unit_buckets.items():
            if data['orders'] > 0:
                success_rate = (data['successes'] / data['orders']) * 100
                unit_performance_data.append({
                    'model': model,
                    'bucket': bucket,
                    'success_rate': success_rate,
                    'orders': data['orders'],
                    'phases': data['phases']
                })
    
    if not unit_performance_data:
        print("No unit control data found")
        return
    
    # Create visualization
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12))
    
    # Aggregate data by bucket
    bucket_order = ['1-3', '4-6', '7-9', '10-12', '13+']
    bucket_data = defaultdict(list)
    
    for data in unit_performance_data:
        bucket_data[data['bucket']].append(data['success_rate'])
    
    # Box plot showing distribution
    box_data = [bucket_data[b] for b in bucket_order]
    positions = range(len(bucket_order))
    
    bp = ax1.boxplot(box_data, positions=positions, patch_artist=True)
    for patch in bp['boxes']:
        patch.set_facecolor(COLORS['move'])
        patch.set_alpha(0.7)
    
    ax1.set_xticks(positions)
    ax1.set_xticklabels(bucket_order)
    ax1.set_xlabel('Unit Count Range', fontsize=12)
    ax1.set_ylabel('Success Rate (%)', fontsize=12)
    ax1.set_title('Success Rate Distribution by Unit Count', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=50, color='red', linestyle='--', alpha=0.5)
    
    # Line plot for top models
    top_models_data = defaultdict(lambda: defaultdict(list))
    
    # Get top models by total phases
    model_phases = [(m, sum(1 for d in unit_performance_data if d['model'] == m)) 
                    for m in set(d['model'] for d in unit_performance_data)]
    model_phases.sort(key=lambda x: x[1], reverse=True)
    top_models = [m[0] for m in model_phases[:10]]
    
    for data in unit_performance_data:
        if data['model'] in top_models:
            top_models_data[data['model']][data['bucket']] = data['success_rate']
    
    for model in top_models:
        y_values = []
        for bucket in bucket_order:
            if bucket in top_models_data[model]:
                y_values.append(top_models_data[model][bucket])
            else:
                y_values.append(None)
        
        # Plot line with None values ignored
        valid_points = [(i, y) for i, y in enumerate(y_values) if y is not None]
        if valid_points:
            x_vals, y_vals = zip(*valid_points)
            ax2.plot(x_vals, y_vals, marker='o', label=model[:30], alpha=0.7)
    
    ax2.set_xticks(positions)
    ax2.set_xticklabels(bucket_order)
    ax2.set_xlabel('Unit Count Range', fontsize=12)
    ax2.set_ylabel('Success Rate (%)', fontsize=12)
    ax2.set_title('Unit Control Performance - Top 10 Models', fontsize=14, fontweight='bold')
    ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=50, color='red', linestyle='--', alpha=0.5)
    
    plt.suptitle('Unit Control Analysis - Performance vs Unit Count', fontsize=16, fontweight='bold')
    plt.tight_layout()
    fig.savefig(output_dir / 'unit_control_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_success_over_physical_time(all_data, model_stats, output_dir):
    """Create success rate evolution over physical dates"""
    # Group data by week
    weekly_data = defaultdict(lambda: {'orders': 0, 'successes': 0, 'games': set()})
    
    for game_data in all_data:
        game_id = game_data['game_id']
        
        # Extract date
        game_date = None
        if len(game_id) >= 8 and game_id[:8].isdigit():
            try:
                game_date = datetime.strptime(game_id[:8], '%Y%m%d')
            except:
                continue
        
        if not game_date:
            continue
        
        # Get week start (Monday)
        week_start = game_date - timedelta(days=game_date.weekday())
        week_key = week_start.date()
        
        # Aggregate orders and successes
        for model, phases in game_data['phase_data'].items():
            for phase in phases:
                weekly_data[week_key]['orders'] += phase['total_orders']
                weekly_data[week_key]['successes'] += sum(phase['order_successes'].values())
                weekly_data[week_key]['games'].add(game_id)
    
    if not weekly_data:
        print("No temporal data found")
        return
    
    # Sort weeks
    weeks = sorted(weekly_data.keys())
    success_rates = []
    game_counts = []
    
    for week in weeks:
        data = weekly_data[week]
        if data['orders'] > 0:
            rate = (data['successes'] / data['orders']) * 100
        else:
            rate = 0
        success_rates.append(rate)
        game_counts.append(len(data['games']))
    
    # Create visualization
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), sharex=True)
    
    # Success rate over time
    ax1.plot(weeks, success_rates, marker='o', linewidth=2, markersize=8, color=COLORS['success'])
    ax1.fill_between(weeks, success_rates, alpha=0.3, color=COLORS['success'])
    ax1.set_ylabel('Average Success Rate (%)', fontsize=12)
    ax1.set_title('Success Rate Evolution Over Time', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=50, color='red', linestyle='--', alpha=0.5)
    ax1.set_ylim(0, 100)
    
    # Add trend line
    if len(weeks) > 3:
        x_numeric = np.arange(len(weeks))
        z = np.polyfit(x_numeric, success_rates, 1)
        p = np.poly1d(z)
        ax1.plot(weeks, p(x_numeric), "--", color='black', alpha=0.5, label=f'Trend: {z[0]:.2f}% per week')
        ax1.legend()
    
    # Game count over time
    ax2.bar(weeks, game_counts, alpha=0.7, color=COLORS['move'])
    ax2.set_xlabel('Week Starting', fontsize=12)
    ax2.set_ylabel('Games Analyzed', fontsize=12)
    ax2.set_title('Game Volume Over Time', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # Format x-axis
    import matplotlib.dates as mdates
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    plt.xticks(rotation=45)
    
    plt.suptitle('Temporal Success Analysis', fontsize=16, fontweight='bold')
    plt.tight_layout()
    fig.savefig(output_dir / 'success_over_physical_time.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_model_evolution_chart(all_data, model_stats, output_dir):
    """Create model evolution chart showing version improvements"""
    # Group models by family
    model_families = defaultdict(list)
    
    for model in model_stats.keys():
        # Extract base model name
        if '/' in model:
            family = model.split('/')[0]
        elif ':' in model:
            family = model.split(':')[0]
        else:
            family = model.split('-')[0] if '-' in model else model
        
        model_families[family].append(model)
    
    # Find families with multiple versions
    evolving_families = {f: models for f, models in model_families.items() 
                        if len(models) > 1 and f not in ['openrouter', 'openai']}
    
    if not evolving_families:
        print("No model families with multiple versions found")
        return
    
    # Create visualization
    fig, ax = plt.subplots(figsize=(14, 10))
    
    y_position = 0
    y_labels = []
    
    for family, models in sorted(evolving_families.items()):
        # Get stats for each model
        model_data = []
        for model in models:
            stats = model_stats[model]
            if stats['total_phases'] > 0:
                model_data.append({
                    'model': model,
                    'success_rate': stats['active_success_rate'],
                    'active_pct': stats['active_percentage'],
                    'phases': stats['total_phases']
                })
        
        if not model_data:
            continue
        
        # Sort by some metric (phases as proxy for version)
        model_data.sort(key=lambda x: x['phases'])
        
        # Plot evolution
        for i, data in enumerate(model_data):
            color = plt.cm.viridis(i / max(len(model_data) - 1, 1))
            
            # Plot point
            ax.scatter(data['success_rate'], y_position, s=data['phases']/10, 
                      color=color, alpha=0.7, edgecolors='black', linewidth=1)
            
            # Add label
            label = data['model'].split('/')[-1] if '/' in data['model'] else data['model']
            ax.text(data['success_rate'] + 1, y_position, f"{label[:20]} ({data['phases']}p)",
                   va='center', fontsize=8)
        
        y_labels.append(family)
        y_position += 1
    
    ax.set_yticks(range(len(y_labels)))
    ax.set_yticklabels(y_labels)
    ax.set_xlabel('Success Rate on Active Orders (%)', fontsize=12)
    ax.set_ylabel('Model Family', fontsize=12)
    ax.set_title('Model Family Evolution', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')
    ax.axvline(x=50, color='red', linestyle='--', alpha=0.5)
    ax.set_xlim(0, 100)
    
    # Add size legend
    sizes = [100, 500, 1000]
    legends = []
    for s in sizes:
        legends.append(plt.scatter([], [], s=s/10, c='gray', alpha=0.7, edgecolors='black', linewidth=1))
    ax.legend(legends, [f'{s} phases' for s in sizes], scatterpoints=1, loc='lower right', title='Data Volume')
    
    plt.tight_layout()
    fig.savefig(output_dir / 'model_evolution_chart.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_summary_report(model_stats, all_models_found, models_missing_phases, output_dir):
    """Create a comprehensive summary report"""
    with open(output_dir / 'ANALYSIS_SUMMARY.md', 'w') as f:
        f.write("# CSV-Only Diplomacy Analysis Summary\n\n")
        f.write(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Overall statistics
        f.write("## Overall Statistics\n\n")
        f.write(f"- **Total Unique Models:** {len(all_models_found)}\n")
        f.write(f"- **Models with Phase Data:** {len([m for m in model_stats if model_stats[m]['total_phases'] > 0])}\n")
        f.write(f"- **Models with Active Orders:** {len([m for m in model_stats if model_stats[m]['active_percentage'] > 0])}\n")
        f.write(f"- **Models Missing Phase Data:** {len(models_missing_phases)}\n\n")
        
        # Top performers
        f.write("## Top Performing Models (by Success Rate on Active Orders)\n\n")
        
        top_performers = []
        for model, stats in model_stats.items():
            if stats['active_percentage'] > 0:
                top_performers.append({
                    'model': model,
                    'success_rate': stats['active_success_rate'],
                    'active_orders': sum(stats['order_counts'][t] for t in ['move', 'support', 'convoy']),
                    'total_phases': stats['total_phases']
                })
        
        top_performers.sort(key=lambda x: x['success_rate'], reverse=True)
        
        f.write("| Model | Success Rate | Active Orders | Phases |\n")
        f.write("|-------|-------------|---------------|--------|\n")
        for p in top_performers[:20]:
            f.write(f"| {p['model']} | {p['success_rate']:.1f}% | {p['active_orders']} | {p['total_phases']} |\n")
        
        # Most active models
        f.write("\n## Most Active Models (by Active Order Percentage)\n\n")
        
        active_models = []
        for model, stats in model_stats.items():
            if stats['total_orders'] > 100:  # Minimum threshold
                active_models.append({
                    'model': model,
                    'active_pct': stats['active_percentage'],
                    'total_orders': stats['total_orders']
                })
        
        active_models.sort(key=lambda x: x['active_pct'], reverse=True)
        
        f.write("| Model | Active % | Total Orders |\n")
        f.write("|-------|----------|-------------|\n")
        for a in active_models[:20]:
            f.write(f"| {a['model']} | {a['active_pct']:.1f}% | {a['total_orders']} |\n")

def main():
    parser = argparse.ArgumentParser(
        description='Enhanced CSV-Only Diplomacy Model Analysis - Comprehensive Visualizations'
    )
    parser.add_argument('days', type=int, nargs='?', default=200,
                       help='Number of days to analyze (default: 200)')
    parser.add_argument('--results-dir', default='results',
                       help='Results directory containing game data')
    
    args = parser.parse_args()
    
    # Create output directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = Path('visualization_results') / f'csv_only_enhanced_{timestamp}_{args.days}days'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find games to analyze
    cutoff_date = datetime.now() - timedelta(days=args.days)
    results_path = Path(args.results_dir)
    
    if not results_path.exists():
        print(f"Error: Results directory not found: {results_path}")
        sys.exit(1)
    
    print(f"Enhanced CSV-Only Diplomacy Model Analysis")
    print(f"=========================================")
    print(f"Analyzing games from the last {args.days} days")
    print(f"Using CSV files as the ONLY source of truth")
    print(f"Creating comprehensive visualization suite\n")
    
    # Collect data from all games
    all_data = []
    game_count = 0
    
    for game_file in results_path.rglob("lmvsgame.json"):
        if datetime.fromtimestamp(game_file.stat().st_mtime) < cutoff_date:
            continue
        
        game_count += 1
        if game_count % 50 == 0:
            print(f"\nProcessing game {game_count}...")
        
        try:
            game_data = analyze_game(game_file)
            all_data.append(game_data)
        except Exception as e:
            print(f"✗ Failed {game_file.parent.name}: {e}")
    
    print(f"\n\nProcessed {game_count} games")
    
    # Count unique models
    all_models = set()
    for game_data in all_data:
        all_models.update(game_data['all_models'])
    
    print(f"Found {len(all_models)} unique models across all games")
    
    # Create comprehensive visualizations
    if all_data:
        model_stats = create_comprehensive_charts(all_data, output_dir)
        
        # Print summary
        models_with_data = sum(1 for m, s in model_stats.items() if s['total_phases'] > 0)
        models_with_active = sum(1 for m, s in model_stats.items() if s['active_percentage'] > 0)
        
        print(f"\nAnalysis complete!")
        print(f"- Total unique models: {len(all_models)}")
        print(f"- Models with phase data: {models_with_data}")
        print(f"- Models with active orders: {models_with_active}")
        print(f"- Visualizations saved to: {output_dir}")
    
if __name__ == "__main__":
    main()