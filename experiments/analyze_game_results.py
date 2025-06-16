#!/usr/bin/env python3
"""
Analyze Diplomacy game results from FULL_GAME folders.
Creates a CSV showing how many times each model played as each power and won.
"""

import json
import os
import glob
from collections import defaultdict
import csv
from pathlib import Path


def find_overview_file(folder_path):
    """Find overview.jsonl or overviewN.jsonl in a folder."""
    # Check for numbered overview files first (overview1.jsonl, overview2.jsonl, etc.)
    numbered_files = glob.glob(os.path.join(folder_path, "overview[0-9]*.jsonl"))
    if numbered_files:
        # Return the one with the highest number
        return max(numbered_files)
    
    # Check for regular overview.jsonl
    regular_file = os.path.join(folder_path, "overview.jsonl")
    if os.path.exists(regular_file):
        return regular_file
    
    return None


def parse_lmvsgame_for_winner(folder_path):
    """Parse lmvsgame.json file to find the winner."""
    lmvsgame_path = os.path.join(folder_path, "lmvsgame.json")
    if not os.path.exists(lmvsgame_path):
        return None
    
    try:
        with open(lmvsgame_path, 'r') as f:
            data = json.load(f)
            
        # Look for phases with "COMPLETED" status
        if 'phases' in data:
            for phase in data['phases']:
                if phase.get('name') == 'COMPLETED':
                    # Check for victory note
                    if 'state' in phase and 'note' in phase['state']:
                        note = phase['state']['note']
                        if 'Victory by:' in note:
                            winner = note.split('Victory by:')[1].strip()
                            return winner
                    
                    # Also check centers to see who has 18
                    if 'state' in phase and 'centers' in phase['state']:
                        centers = phase['state']['centers']
                        for power, power_centers in centers.items():
                            if len(power_centers) >= 18:
                                return power
    
    except Exception as e:
        print(f"Error parsing lmvsgame.json in {folder_path}: {e}")
    
    return None


def parse_overview_file(filepath):
    """Parse overview.jsonl file and extract power-model mappings and winner."""
    power_model_map = {}
    winner = None
    
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
            
            # The second line typically contains the power-model mapping
            if len(lines) >= 2:
                try:
                    second_line_data = json.loads(lines[1].strip())
                    # Check if this line contains power names as keys
                    if all(power in second_line_data for power in ['AUSTRIA', 'ENGLAND', 'FRANCE', 'GERMANY', 'ITALY', 'RUSSIA', 'TURKEY']):
                        power_model_map = second_line_data
                except:
                    pass
            
            # Search all lines for winner information
            for line in lines:
                if line.strip():
                    try:
                        data = json.loads(line)
                        
                        # Look for winner in various possible fields
                        if 'winner' in data:
                            winner = data['winner']
                        elif 'game_status' in data and 'winner' in data['game_status']:
                            winner = data['game_status']['winner']
                        elif 'result' in data and 'winner' in data['result']:
                            winner = data['result']['winner']
                        
                        # Also check if there's a phase result with winner info
                        if 'phase_results' in data:
                            for phase_result in data['phase_results']:
                                if 'winner' in phase_result:
                                    winner = phase_result['winner']
                    except:
                        continue
    
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
    
    return power_model_map, winner


def analyze_game_folders(results_dir):
    """Analyze all FULL_GAME folders and collect statistics."""
    # Dictionary to store stats: model -> power -> (games, wins)
    stats = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    
    # Find all FULL_GAME folders
    full_game_folders = glob.glob(os.path.join(results_dir, "*_FULL_GAME"))
    
    print(f"Found {len(full_game_folders)} FULL_GAME folders")
    
    for folder in full_game_folders:
        print(f"\nAnalyzing: {os.path.basename(folder)}")
        
        # Find overview file
        overview_file = find_overview_file(folder)
        if not overview_file:
            print(f"  No overview file found in {folder}")
            continue
        
        print(f"  Using: {os.path.basename(overview_file)}")
        
        # Parse the overview file
        power_model_map, winner = parse_overview_file(overview_file)
        
        if not power_model_map:
            print(f"  No power-model mapping found")
            continue
        
        # If no winner found in overview, check lmvsgame.json
        if not winner:
            winner = parse_lmvsgame_for_winner(folder)
        
        print(f"  Power-Model mappings: {power_model_map}")
        print(f"  Winner: {winner}")
        
        # Update statistics
        for power, model in power_model_map.items():
            # Increment games played
            stats[model][power][0] += 1
            
            # Increment wins if this power won
            if winner:
                # Handle different winner formats (e.g., "FRA", "FRANCE", etc.)
                winner_upper = winner.upper()
                power_upper = power.upper()
                
                # Check if winner matches power (could be abbreviated)
                if (winner_upper == power_upper or 
                    winner_upper == power_upper[:3] or
                    (len(winner_upper) == 3 and power_upper.startswith(winner_upper))):
                    stats[model][power][1] += 1
    
    return stats


def write_csv_output(stats, output_file):
    """Write statistics to CSV file."""
    # Get all unique models and powers
    all_models = sorted(stats.keys())
    all_powers = ['AUSTRIA', 'ENGLAND', 'FRANCE', 'GERMANY', 'ITALY', 'RUSSIA', 'TURKEY']
    
    # Create CSV
    with open(output_file, 'w', newline='') as csvfile:
        # Header row
        header = ['Model'] + all_powers
        writer = csv.writer(csvfile)
        writer.writerow(header)
        
        # Data rows
        for model in all_models:
            row = [model]
            for power in all_powers:
                games, wins = stats[model][power]
                if games > 0:
                    cell_value = f"{games} ({wins} wins)"
                else:
                    cell_value = ""
                row.append(cell_value)
            writer.writerow(row)
    
    print(f"\nResults written to: {output_file}")


def main():
    """Main function."""
    results_dir = "/Users/alxdfy/Documents/mldev/AI_Diplomacy/results"
    output_file = "/Users/alxdfy/Documents/mldev/AI_Diplomacy/model_power_statistics.csv"
    
    print("Analyzing Diplomacy game results...")
    stats = analyze_game_folders(results_dir)
    
    # Print summary
    print("\n=== Summary ===")
    total_games = 0
    for model, power_stats in stats.items():
        model_games = sum(games for games, wins in power_stats.values())
        model_wins = sum(wins for games, wins in power_stats.values())
        total_games += model_games
        print(f"{model}: {model_games} games, {model_wins} wins")
    
    print(f"\nTotal games analyzed: {total_games // 7}")  # Divide by 7 since each game has 7 players
    
    # Write to CSV
    write_csv_output(stats, output_file)


if __name__ == "__main__":
    main()