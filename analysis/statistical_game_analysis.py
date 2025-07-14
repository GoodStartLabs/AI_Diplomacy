#!/usr/bin/env python3
"""
Statistical Game Analysis for AI Diplomacy

Production-ready tool that analyzes AI Diplomacy game results and generates comprehensive
statistical analysis in CSV format. Supports both single game analysis and batch processing.

Features:
- Phase-level analysis with response-type granularity
- Game-level aggregated metrics
- Comprehensive failure/success tracking
- Message composition and relationship analysis
- Data validation and error handling

Usage:
    python statistical_game_analysis.py <results_folder>
    python statistical_game_analysis.py <parent_folder> --batch

Author: Generated for AI Diplomacy project
Version: 2.0 (Hard Mode with complete validation)
"""

import os
import json
import csv
import sys
import argparse
from pathlib import Path
from collections import defaultdict, Counter
import re
from typing import Dict, List, Tuple, Optional, Any
import statistics
try:
    # Absolute import – works when the project root is on sys.path
    from models import PowerEnum
except ImportError:
    try:
        # Relative import – works when file is executed as part of the ai_diplomacy package
        from ..models import PowerEnum
    except ImportError as exc:
        # Re-raise with context so the root cause is visible
        raise ImportError(
            "models.PowerEnum not found via absolute or relative import. "
        ) from exc

csv.field_size_limit(sys.maxsize)

class StatisticalGameAnalyzer:
    """Production-ready analyzer for AI Diplomacy game statistics.
    
    This class handles comprehensive statistical analysis of AI Diplomacy games,
    including negotiation patterns, relationship dynamics, response quality metrics,
    and game state evolution. Designed for reliability and maintainability.
    """
    
    # Class constants for better maintainability
    RELATIONSHIP_VALUES = {
        'Enemy': -2,
        'Unfriendly': -1, 
        'Neutral': 0,
        'Friendly': 1,
        'Ally': 2
    }
    
    
    # Complete list of response types found in actual data
    RESPONSE_TYPES = [
        'negotiation_message', 'negotiation_diary', 'state_update', 'initial_state_setup',
        'order_generation', 'order_diary', 'state_update_parsing_empty_or_invalid_data',
        'diary_consolidation', 'state_update_partial_data', 'state_update_no_response'
    ]

    ORDER_TYPES = [
        "move", "hold", "support", "convoy",
        "build", "disband", "waive", "other",
        "retreat"
    ]
    
    def __init__(self):
        """Initialize analyzer with configuration constants."""
        self.relationship_values = self.RELATIONSHIP_VALUES
        
        
        
    def analyze_folder(self, folder_path: str, output_dir: str = None) -> Tuple[str, str]:
        """
        Analyze a single results folder and generate CSV outputs.
        
        Args:
            folder_path: Path to results folder containing llm_responses.csv and lmvsgame.json
            output_dir: Directory to save outputs (default: analysis subfolder)
            
        Returns:
            Tuple of (phase_csv_path, game_csv_path)
            
        Raises:
            FileNotFoundError: If required data files are missing
            ValueError: If data format is invalid
        """
        folder_path = Path(folder_path)
        
        # Validate input folder exists
        if not folder_path.exists() or not folder_path.is_dir():
            raise FileNotFoundError(f"Results folder not found: {folder_path}")
        
        # Set up output directory
        if output_dir is None:
            output_dir = folder_path / "analysis"
        else:
            output_dir = Path(output_dir)
        
        try:
            output_dir.mkdir(exist_ok=True)
        except PermissionError as e:
            raise PermissionError(f"Cannot create output directory {output_dir}: {e}")
            
        print(f"Analyzing folder: {folder_path}")
        
        # Validate required files exist
        llm_responses_path = folder_path / "llm_responses.csv"
        game_json_path = folder_path / "lmvsgame.json"
        
        if not llm_responses_path.exists():
            raise FileNotFoundError(f"Required file missing: {llm_responses_path}")
        if not game_json_path.exists():
            raise FileNotFoundError(f"Required file missing: {game_json_path}")
            
        try:
            # Load and validate data
            llm_responses = self._load_llm_responses(llm_responses_path)
            if not llm_responses:
                raise ValueError("llm_responses.csv is empty or contains no valid data")
            
            with open(game_json_path, 'r', encoding='utf-8') as f:
                game_data = json.load(f)
            
            if not game_data.get('phases'):
                raise ValueError("lmvsgame.json contains no phase data")
            
            # Generate analysis
            phase_features = self._extract_phase_features(llm_responses, game_data)
            game_features = self._extract_game_features(llm_responses, game_data)
            
            if not phase_features or not game_features:
                raise ValueError("Failed to extract analysis features from data")
            
            # Save outputs
            game_id = folder_path.name
            phase_csv_path = output_dir / f"{game_id}_phase_analysis.csv"
            game_csv_path = output_dir / f"{game_id}_game_analysis.csv"
            
            self._save_phase_csv(phase_features, phase_csv_path)
            self._save_game_csv(game_features, game_csv_path)
            
            print(f"Saved {len(phase_features)} phase records to {phase_csv_path}")
            print(f"Saved {len(game_features)} game records to {game_csv_path}")
            
            return str(phase_csv_path), str(game_csv_path)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {game_json_path}: {e}")
        except Exception as e:
            raise RuntimeError(f"Analysis failed: {e}") from e
    
    def analyze_multiple_folders(self, parent_folder: str, output_dir: str = None) -> None:
        """
        Analyze multiple results folders and combine outputs.
        
        Args:
            parent_folder: Path containing multiple results folders
            output_dir: Directory to save combined outputs
        """
        parent_path = Path(parent_folder)
        if output_dir is None:
            output_dir = parent_path / "statistical_analysis"
        else:
            output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        # Find all results folders (look for folders with llm_responses.csv)
        results_folders = []
        for item in parent_path.iterdir():
            if item.is_dir() and (item / "llm_responses.csv").exists():
                results_folders.append(item)
                
        if not results_folders:
            raise ValueError(f"No results folders found in {parent_folder}")
            
        print(f"Found {len(results_folders)} results folders to analyze")
        
        all_phase_data = []
        all_game_data = []
        
        # Analyze each folder
        for folder in results_folders:
            try:
                print(f"\nAnalyzing {folder.name}...")
                phase_csv, game_csv = self.analyze_folder(folder, output_dir / "individual")
                
                # Load and combine data
                phase_data = self._load_csv_as_dicts(phase_csv)
                game_data = self._load_csv_as_dicts(game_csv)
                
                all_phase_data.extend(phase_data)
                all_game_data.extend(game_data)
                
            except Exception as e:
                print(f"Error analyzing {folder.name}: {e}")
                continue
        
        # Combine all data
        if all_phase_data:
            # Save combined outputs
            combined_phase_path = output_dir / "combined_phase_analysis.csv"
            combined_game_path = output_dir / "combined_game_analysis.csv"
            
            self._save_phase_csv(all_phase_data, combined_phase_path)
            self._save_game_csv(all_game_data, combined_game_path)
            
            print(f"\nCombined phase analysis saved to: {combined_phase_path}")
            print(f"Combined game analysis saved to: {combined_game_path}")
            print(f"Total games analyzed: {len(set(row.get('game_id') for row in all_game_data))}")
            print(f"Total phase records: {len(all_phase_data)}")
    
    def _load_llm_responses(self, csv_path: Path) -> List[dict]:
        """Load and validate LLM responses CSV."""
        responses = []
        required_columns = ['model', 'power', 'phase', 'response_type', 'raw_response']
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Check required columns
            missing_columns = [col for col in required_columns if col not in reader.fieldnames]
            if missing_columns:
                raise ValueError(f"Missing required columns in CSV: {missing_columns}")
            
            for row in reader:
                responses.append(row)
                
        return responses
    
    def _extract_order_results_features(self, power: str, phase_data: dict) -> dict:
        """
        Count orders and outcomes for a single power in one phase and add
        a success-rate (0-1) for every order type.
        """
        features: dict[str, float | int] = {}
        for ot in self.ORDER_TYPES:
            plural = f"{ot}s" if not ot.endswith("s") else ot
            for metric in ("total", "success", "bounce", "void", "invalid"):
                features[f"orders_{plural}_{metric}"] = 0
            features[f"orders_{plural}_success_rate"] = 0.0      # ← new

        orders_by_type = phase_data.get("order_results", {}).get(power, {})
        if not orders_by_type:
            return features

        for otype, order_list in orders_by_type.items():
            otype = otype.lower()
            if otype not in self.ORDER_TYPES:
                otype = "other"
            plural = f"{otype}s" if not otype.endswith("s") else otype

            for entry in order_list:
                result = str(entry.get("result", "")).lower().strip()
                key_base = f"orders_{plural}"
                features[f"{key_base}_total"] += 1
                match result:
                    case "success":
                        features[f"{key_base}_success"] += 1
                    case "bounce":
                        features[f"{key_base}_bounce"] += 1
                    case "invalid":
                        features[f"{key_base}_invalid"] += 1
                    case _ if result in ("void", "void: no effect", ""):
                        features[f"{key_base}_void"] += 1

        # ── derive success rates ──
        for ot in self.ORDER_TYPES:
            plural = f"{ot}s" if not ot.endswith("s") else ot
            succ = features[f"orders_{plural}_success"]
            tot  = features[f"orders_{plural}_total"]
            features[f"orders_{plural}_success_rate"] = succ / tot if tot else 0.0

        return features



    # ────────────────── GAME-LEVEL ORDER TOTALS ──────────────────
    def _aggregate_order_results(self, power: str, game_data: dict) -> dict:
        """
        Sum every order-type/result pair over *all* phases for one power
        and add success-rate (0-1) columns.
        """
        totals: dict[str, float | int] = {}
        for ot in self.ORDER_TYPES:
            plural = f"{ot}s" if not ot.endswith("s") else ot
            for metric in ("total", "success", "bounce", "void", "invalid"):
                totals[f"orders_{plural}_{metric}"] = 0
            totals[f"orders_{plural}_success_rate"] = 0.0          # ← new

        for phase in game_data.get("phases", []):
            orders_by_type = phase.get("order_results", {}).get(power, {})
            if not orders_by_type:
                continue

            for otype, order_list in orders_by_type.items():
                otype = otype.lower()
                if otype not in self.ORDER_TYPES:
                    otype = "other"
                plural = f"{otype}s" if not otype.endswith("s") else otype

                for entry in order_list:
                    result = str(entry.get("result", "")).lower().strip()
                    key_base = f"orders_{plural}"
                    totals[f"{key_base}_total"] += 1
                    match result:
                        case "success":
                            totals[f"{key_base}_success"] += 1
                        case "bounce":
                            totals[f"{key_base}_bounce"] += 1
                        case "invalid":
                            totals[f"{key_base}_invalid"] += 1
                        case _ if result in ("void", "void: no effect", ""):
                            totals[f"{key_base}_void"] += 1

        # ── derive success rates ──
        for ot in self.ORDER_TYPES:
            plural = f"{ot}s" if not ot.endswith("s") else ot
            succ = totals[f"orders_{plural}_success"]
            tot  = totals[f"orders_{plural}_total"]
            totals[f"orders_{plural}_success_rate"] = succ / tot if tot else 0.0

        return totals




    def _extract_phase_features(self, llm_responses: List[dict], game_data: dict) -> List[dict]:
        """Extract phase-level features for all powers, phases, and response types."""
        phase_features = []
        
        # Get all unique phases from game data
        phases = [phase['name'] for phase in game_data['phases']]
        
        # Use class constant for response types
        response_types = self.RESPONSE_TYPES
        
        for phase_name in phases:
            # Get phase data from game JSON
            phase_data = next((p for p in game_data['phases'] if p['name'] == phase_name), None)
            if not phase_data:
                continue
                
            for power in PowerEnum:
                for response_type in response_types:
                    # Extract features for this specific power/phase/response_type combination
                    features = self._extract_power_phase_response_features(
                        power.value, phase_name, response_type, llm_responses, phase_data, game_data
                    )
                    if features:
                        phase_features.append(features)
                        
        return phase_features
    
    def _extract_power_phase_response_features(self, power: str, phase: str, response_type: str,
                                             llm_responses: List[dict], phase_data: dict, 
                                             game_data: dict) -> Optional[dict]:
        """Extract features for a specific power/phase/response_type combination."""
        
        # Get responses of this type for this power/phase
        relevant_responses = [
            response for response in llm_responses
            if (response.get('power') == power and 
                response.get('phase') == phase and
                response.get('response_type') == response_type)
        ]
        
        # Skip if no responses of this type
        if not relevant_responses:
            return None
        
        # Base feature dict with organized, descriptive names
        features = {
            # === PRIMARY IDENTIFIERS (ordered as requested) ===
            'game_id': game_data.get('id', 'unknown'),
            'llm_model': self._get_model_for_power(power, llm_responses),
            'game_phase': phase,
            'analyzed_response_type': response_type,
            'power_name': power,
            
            # === RESPONSE INFO ===
            'llm_responses_of_this_type': len(relevant_responses)
        }
        
        # === FAILURE ANALYSIS (HARD MODE) ===
        failure_metrics = self._analyze_failures(power, phase, response_type, llm_responses)
        features.update(failure_metrics)

        # === ORDER-RESULT METRICS ===
        order_result_features = self._extract_order_results_features(power, phase_data)
        features.update(order_result_features)
        
        
        # Add response-type specific features
        if response_type == 'negotiation_message':
            negotiation_features = self._extract_negotiation_features(power, phase, llm_responses, phase_data)
            features.update(negotiation_features)
        elif response_type in ['negotiation_diary', 'state_update', 'initial_state_setup']:
            reflection_features = self._extract_reflection_features(power, phase, llm_responses, phase_data, game_data, response_type)
            features.update(reflection_features)
        
        # Always include game state features for context
        game_state_features = self._extract_game_state_features(power, phase, phase_data, game_data)
        features.update(game_state_features)

        # Relationship snapshot column (e.g. "AUSTRIA:-1|FRANCE:2")
        relationships_for_phase = self._get_relationships_for_phase(power, phase, phase_data)
        features['relationships'] = '|'.join(
            f"{p}:{self.relationship_values.get(r, 0)}" for p, r in relationships_for_phase.items()
        )
        
        return features
    
    def _extract_negotiation_features(self, power: str, phase: str, 
                                    llm_responses: List[dict], phase_data: dict) -> dict:
        """Extract negotiation-related metrics for a power in a phase."""
        
        # Get negotiation messages for this power in this phase
        negotiation_msgs = [
            response for response in llm_responses
            if (response.get('power') == power and 
                response.get('phase') == phase and
                response.get('response_type') == 'negotiation_message')
        ]
        
        # Initialize negotiation features with descriptive names
        features = {
            # === NEGOTIATION METRICS ===
            'total_messages_sent': 0,
            'messages_to_allies': 0,
            'messages_to_enemies': 0, 
            'messages_to_neutrals': 0,
            'global_messages_count': 0,
            'private_messages_count': 0,
            'percent_global_messages': 0.0,
            'average_message_length_chars': 0.0
        }
        
        if not negotiation_msgs:
            return features
            
        # Parse messages from raw responses
        all_messages = []
        total_length = 0
        
        for response in negotiation_msgs:
            messages = self._parse_negotiation_messages(response.get('raw_response', ''), power, phase)
            all_messages.extend(messages)
            
        if not all_messages:
            return features
            
        # Get relationships for this phase
        relationships = self._get_relationships_for_phase(power, phase, phase_data)
        
        # Calculate message statistics
        features['total_messages_sent'] = len(all_messages)
        
        for msg in all_messages:
            msg_length = len(msg.get('content', ''))
            total_length += msg_length
            
            if msg.get('is_global', False):
                features['global_messages_count'] += 1
            else:
                features['private_messages_count'] += 1
                
                # Categorize by relationship
                recipient = msg.get('recipient_power')
                if recipient is None:
                    continue
                try:
                    normalized_recipient = PowerEnum(recipient).value
                except ValueError:
                    normalized_recipient = None
                
                # Skip self-messages and invalid recipients
                if normalized_recipient and normalized_recipient != power and normalized_recipient in relationships:
                    rel_value = self.relationship_values.get(relationships[normalized_recipient], 0)
                    if rel_value >= 1:  # Friendly or Ally
                        features['messages_to_allies'] += 1
                    elif rel_value <= -1:  # Enemy or Unfriendly
                        features['messages_to_enemies'] += 1
                    else:  # Neutral
                        features['messages_to_neutrals'] += 1
        
        # Calculate percentages and averages
        if features['total_messages_sent'] > 0:
            features['percent_global_messages'] = (features['global_messages_count'] / features['total_messages_sent']) * 100
            features['average_message_length_chars'] = total_length / features['total_messages_sent']
            
            # Calculate relationship-based message percentages
            total_categorized = features['messages_to_allies'] + features['messages_to_enemies'] + features['messages_to_neutrals']
            if total_categorized > 0:
                features['percent_messages_to_allies'] = (features['messages_to_allies'] / total_categorized) * 100
                features['percent_messages_to_enemies'] = (features['messages_to_enemies'] / total_categorized) * 100
                features['percent_messages_to_neutrals'] = (features['messages_to_neutrals'] / total_categorized) * 100
            else:
                features['percent_messages_to_allies'] = 0.0
                features['percent_messages_to_enemies'] = 0.0
                features['percent_messages_to_neutrals'] = 0.0
        else:
            features['percent_messages_to_allies'] = 0.0
            features['percent_messages_to_enemies'] = 0.0
            features['percent_messages_to_neutrals'] = 0.0
            
        return features
    
    def _extract_reflection_features(self, power: str, phase: str, 
                                   llm_responses: List[dict], phase_data: dict,
                                   game_data: dict, specific_response_type: str = None) -> dict:
        """Extract reflection-related metrics for a power in a phase."""
        
        features = {
            # === REFLECTION METRICS ===
            'llm_response_tokens_estimated': 0,
            'llm_response_time_ms': 0.0,
            'relationship_stability_vs_prev_phase': 1.0,
            'avg_sentiment_toward_others': 0.0,
            'avg_sentiment_from_others': 0.0,
            'sentiment_change_from_prev': 0.0
        }
        
        # Get diary entries for this power in this phase
        if specific_response_type:
            # Filter to only the specific response type
            diary_entries = [
                response for response in llm_responses
                if (response.get('power') == power and 
                    response.get('phase') == phase and
                    response.get('response_type') == specific_response_type)
            ]
        else:
            # Get all reflection-type responses
            diary_entries = [
                response for response in llm_responses
                if (response.get('power') == power and 
                    response.get('phase') == phase and
                    response.get('response_type') in ['negotiation_diary', 'state_update', 'initial_state_setup'])
            ]
        
        if not diary_entries:
            return features
        
        # Calculate reflection metrics
        total_tokens = 0
        for response in diary_entries:
            response_text = str(response.get('raw_response', ''))
            # Estimate tokens (rough approximation: words * 1.3)
            word_count = len(response_text.split())
            total_tokens += int(word_count * 1.3)
            
        features['llm_response_tokens_estimated'] = total_tokens
        
        # Calculate relationship similarity with previous phase
        current_relationships = self._get_relationships_for_phase(power, phase, phase_data)
        prev_phase_data = self._get_previous_phase_data(phase, game_data)
        
        if prev_phase_data:
            prev_relationships = self._get_relationships_for_phase(power, prev_phase_data['name'], prev_phase_data)
            features['relationship_stability_vs_prev_phase'] = self._calculate_relationship_similarity(
                prev_relationships, current_relationships
            )
            
        # Calculate sentiment metrics
        sentiment_metrics = self._calculate_sentiment_metrics(power, phase, phase_data)
        features.update(sentiment_metrics)
        
        return features
    
    def _extract_game_state_features(self, power: str, phase: str, 
                                   phase_data: dict, game_data: dict) -> dict:
        """Extract game state metrics for a power in a phase."""
        
        features = {
            # === GAME STATE ===
            'territories_controlled_count': 0,
            'supply_centers_owned_count': 0,
            'military_units_count': 0,
            'territories_gained_vs_prev_phase': 0,
            'supply_centers_gained_vs_prev_phase': 0,
            'military_units_gained_vs_prev_phase': 0,
            'relationships': ''
        }
        
        # Get current state
        state = phase_data.get('state', {})
        
        # Count current resources
        units = state.get('units', {}).get(power, [])
        centers = state.get('centers', {}).get(power, [])
        influence = state.get('influence', {}).get(power, [])
        
        features['military_units_count'] = len(units)
        features['supply_centers_owned_count'] = len(centers)
        features['territories_controlled_count'] = len(influence)
        
        # Calculate deltas from previous phase
        prev_phase_data = self._get_previous_phase_data(phase, game_data)
        if prev_phase_data:
            prev_state = prev_phase_data.get('state', {})
            prev_units = prev_state.get('units', {}).get(power, [])
            prev_centers = prev_state.get('centers', {}).get(power, [])
            prev_influence = prev_state.get('influence', {}).get(power, [])
            
            features['military_units_gained_vs_prev_phase'] = features['military_units_count'] - len(prev_units)
            features['supply_centers_gained_vs_prev_phase'] = features['supply_centers_owned_count'] - len(prev_centers)
            features['territories_gained_vs_prev_phase'] = features['territories_controlled_count'] - len(prev_influence)
            
        return features
    
    def _extract_game_features(self, llm_responses: List[dict], game_data: dict) -> List[dict]:
        """Extract game-level features (placeholder for future implementation)."""
        
        game_features = []
        game_scores = self._compute_game_scores(game_data)
        
        for power in PowerEnum:
            features = {
                # === IDENTIFIERS ===
                'game_id': game_data.get('id', 'unknown'),
                'llm_model': self._get_model_for_power(power, llm_responses),
                'power_name': power,
                
                # === FINAL STATE METRICS (End game snapshot) ===
                'final_territories_controlled': 0,
                'final_supply_centers_owned': 0,
                'final_military_units': 0,
                'game_result': 'unknown',  # win/loss/draw
                'final_ranking_by_supply_centers': 0,
                
                # === TOTALS (Complete game sums) ===
                'total_negotiation_messages_sent': 0,
                'total_messages_to_allies': 0,
                'total_messages_to_enemies': 0,
                'total_messages_to_neutrals': 0,
                'total_global_messages': 0,
                'total_private_messages': 0,
                'total_response_tokens_estimated': 0,
                'total_llm_interactions': 0,
                'total_phases_active': 0,
                
                # === AVERAGES (Behavioral patterns over time) ===
                'avg_negotiation_messages_per_phase': 0.0,
                'avg_relationship_stability_per_phase': 0.0,
                'avg_sentiment_toward_others': 0.0,
                'avg_sentiment_from_others': 0.0,
                'avg_response_tokens_per_interaction': 0.0,
                'avg_territories_controlled_per_phase': 0.0,
                'avg_supply_centers_owned_per_phase': 0.0,
                'avg_military_units_per_phase': 0.0,
                'percent_messages_to_allies_overall': 0.0,
                'percent_messages_to_enemies_overall': 0.0,
                'percent_global_vs_private_overall': 0.0,
                
                # === FAILURE ANALYSIS TOTALS (HARD MODE) ===
                'total_llm_calls_overall': 0,
                'total_failed_llm_calls': 0,
                'total_success_llm_calls': 0,
                'overall_failure_rate_percentage': 0.0,
                'overall_success_rate_percentage': 0.0,
                
            }

            features['game_score'] = game_scores.get(power)
            
            # === CALCULATE FINAL STATE METRICS ===
            if game_data['phases']:
                final_phase = game_data['phases'][-1]
                final_state = final_phase.get('state', {})
                
                # Final counts
                final_centers = final_state.get('centers', {}).get(power, [])
                final_units = final_state.get('units', {}).get(power, [])
                final_influence = final_state.get('influence', {}).get(power, [])
                
                features['final_supply_centers_owned'] = len(final_centers)
                features['final_military_units'] = len(final_units)
                features['final_territories_controlled'] = len(final_influence)
                
                # Calculate final ranking (1 = highest SC count, 7 = lowest)
                all_final_centers = final_state.get('centers', {})
                sc_counts = [(len(centers), pwr) for pwr, centers in all_final_centers.items()]
                sc_counts.sort(reverse=True)  # Sort by SC count descending
                
                for rank, (sc_count, pwr) in enumerate(sc_counts, 1):
                    if pwr == power:
                        features['final_ranking_by_supply_centers'] = rank
                        break
                
                # Determine game result
                if len(final_centers) >= 18:
                    features['game_result'] = 'solo_victory'
                elif rank == 1:
                    features['game_result'] = 'leading'
                elif rank <= 3:
                    features['game_result'] = 'survivor'
                else:
                    features['game_result'] = 'eliminated_or_weak'
            
            # === CALCULATE AVERAGED BEHAVIORAL METRICS ===
            self._calculate_averaged_game_metrics(features, power, llm_responses, game_data)
            
            game_features.append(features)
            
        return game_features
    
    def _calculate_averaged_game_metrics(self, features: dict, power: str, 
                                       llm_responses: List[dict], game_data: dict) -> None:
        """Calculate both totals and averaged behavioral metrics across the entire game."""
        
        # Initialize collections
        power_phases = []
        sentiment_toward_values = []
        sentiment_from_values = []
        territories_per_phase = []
        supply_centers_per_phase = []
        military_units_per_phase = []
        relationship_stability_values = []
        
        # Track previous relationships for stability calculation
        prev_relationships = None
        
        # Collect data from all phases
        for phase in game_data['phases']:
            phase_name = phase['name']
            power_phases.append(phase_name)
            
            # Get game state data for averages
            state = phase.get('state', {})
            territories = len(state.get('influence', {}).get(power, []))
            supply_centers = len(state.get('centers', {}).get(power, []))
            military_units = len(state.get('units', {}).get(power, []))
            
            territories_per_phase.append(territories)
            supply_centers_per_phase.append(supply_centers)
            military_units_per_phase.append(military_units)
            
            # Get relationship data for sentiment calculations
            if 'state_agents' in phase:
                sa = phase['state_agents']
                agent_relationships = {p: sa[p]['relationships'] for p in sa if 'relationships' in sa[p]}
            else:
                agent_relationships = phase.get('relationships', {})
            if power in agent_relationships:
                power_relationships = agent_relationships[power]
                
                # Calculate sentiment toward others
                if power_relationships:
                    outgoing_values = [self.relationship_values.get(rel, 0) for rel in power_relationships.values()]
                    if outgoing_values:
                        sentiment_toward_values.append(statistics.mean(outgoing_values))
                
                # Calculate sentiment from others
                incoming_values = []
                for other_power, relationships in agent_relationships.items():
                    if other_power != power and power in relationships:
                        incoming_values.append(self.relationship_values.get(relationships[power], 0))
                if incoming_values:
                    sentiment_from_values.append(statistics.mean(incoming_values))
                
                # Calculate relationship stability
                if prev_relationships is not None:
                    stability = self._calculate_relationship_similarity(prev_relationships, power_relationships)
                    relationship_stability_values.append(stability)
                
                prev_relationships = power_relationships.copy()
        
        # === CALCULATE TOTALS ===
        features['total_phases_active'] = len(power_phases)
        
        # Calculate total LLM interactions and tokens + message composition
        total_tokens = 0
        total_responses = 0
        total_ally_msgs = 0
        total_enemy_msgs = 0
        total_neutral_msgs = 0
        total_global_msgs = 0
        total_private_msgs = 0
        
        for response in llm_responses:
            if response.get('power') != power:
                continue
                
            total_responses += 1
            
            # Count tokens for all responses
            response_text = str(response.get('raw_response', ''))
            word_count = len(response_text.split())
            total_tokens += int(word_count * 1.3)
            
            # Parse negotiation messages for composition analysis
            if response.get('response_type') == 'negotiation_message':
                phase_name = response.get('phase')
                messages = self._parse_negotiation_messages(response_text, power, phase_name)
                
                # Get relationships for this phase
                phase_data = next((p for p in game_data['phases'] if p['name'] == phase_name), None)
                if phase_data:
                    relationships = self._get_relationships_for_phase(power, phase_name, phase_data)
                    
                    for msg in messages:
                        if msg.get('is_global', False):
                            total_global_msgs += 1
                        else:
                            total_private_msgs += 1
                            
                            # Categorize by relationship
                            recipient = msg.get('recipient_power')
                            if recipient is None:
                                continue
                            # This will coerce some known aliases to match the 7 acceptable names (see models.py)
                            normalized_recipient = PowerEnum(recipient)
                            
                            # Skip self-messages and invalid recipients
                            if normalized_recipient and normalized_recipient != power and normalized_recipient in relationships:
                                rel_value = self.relationship_values.get(relationships[normalized_recipient], 0)
                                if rel_value >= 1:  # Friendly or Ally
                                    total_ally_msgs += 1
                                elif rel_value <= -1:  # Enemy or Unfriendly
                                    total_enemy_msgs += 1
                                else:  # Neutral
                                    total_neutral_msgs += 1
        
        # Calculate total negotiation messages as sum of parsed individual messages
        features['total_negotiation_messages_sent'] = total_global_msgs + total_private_msgs
        
        features['total_llm_interactions'] = total_responses
        features['total_response_tokens_estimated'] = total_tokens
        features['total_messages_to_allies'] = total_ally_msgs
        features['total_messages_to_enemies'] = total_enemy_msgs
        features['total_messages_to_neutrals'] = total_neutral_msgs
        features['total_global_messages'] = total_global_msgs
        features['total_private_messages'] = total_private_msgs
        
        # === CALCULATE AVERAGES ===
        if power_phases:
            features['avg_negotiation_messages_per_phase'] = features['total_negotiation_messages_sent'] / len(power_phases)
            
        if territories_per_phase:
            features['avg_territories_controlled_per_phase'] = statistics.mean(territories_per_phase)
        if supply_centers_per_phase:
            features['avg_supply_centers_owned_per_phase'] = statistics.mean(supply_centers_per_phase)
        if military_units_per_phase:
            features['avg_military_units_per_phase'] = statistics.mean(military_units_per_phase)
            
        if sentiment_toward_values:
            features['avg_sentiment_toward_others'] = statistics.mean(sentiment_toward_values)
        if sentiment_from_values:
            features['avg_sentiment_from_others'] = statistics.mean(sentiment_from_values)
        
        if relationship_stability_values:
            features['avg_relationship_stability_per_phase'] = statistics.mean(relationship_stability_values)
        
        if total_responses > 0:
            features['avg_response_tokens_per_interaction'] = total_tokens / total_responses
        
        # Calculate message composition percentages
        total_categorized_msgs = total_ally_msgs + total_enemy_msgs + total_neutral_msgs
        total_all_msgs = total_global_msgs + total_private_msgs
        
        if total_categorized_msgs > 0:
            features['percent_messages_to_allies_overall'] = (total_ally_msgs / total_categorized_msgs) * 100
            features['percent_messages_to_enemies_overall'] = (total_enemy_msgs / total_categorized_msgs) * 100
        
        if total_all_msgs > 0:
            features['percent_global_vs_private_overall'] = (total_global_msgs / total_all_msgs) * 100
            
        # === FAILURE ANALYSIS AGGREGATION (HARD MODE) ===
        total_calls = 0
        total_failures = 0
        total_successes = 0
        
        # Get all responses for this power across all phases/response types
        power_responses = [r for r in llm_responses if r.get('power') == power]
        
        for response in power_responses:
            total_calls += 1
            success_status = response.get('success', '').strip()
            if self._is_failure_status(success_status):
                total_failures += 1
            elif self._is_success_status(success_status):
                total_successes += 1
        
        features['total_llm_calls_overall'] = total_calls
        features['total_failed_llm_calls'] = total_failures
        features['total_success_llm_calls'] = total_successes
        
        if total_calls > 0:
            features['overall_failure_rate_percentage'] = (total_failures / total_calls) * 100.0
            features['overall_success_rate_percentage'] = (total_successes / total_calls) * 100.0

        # === ORDER TOTALS (whole game) ===
        order_totals = self._aggregate_order_results(power, game_data)
        features.update(order_totals)
    
    # Helper methods
    
    def _parse_negotiation_messages(self, raw_response: str, sender: str, phase: str) -> List[dict]:
        """Parse negotiation messages from raw LLM response."""
        messages = []
        
        # Try to extract JSON messages
        json_blocks = re.findall(r'```json\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
        
        if not json_blocks:
            # Try to find direct JSON objects
            json_blocks = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', raw_response)
            
        for json_str in json_blocks:
            try:
                msg_data = json.loads(json_str)
                if isinstance(msg_data, dict) and 'content' in msg_data:
                    message = {
                        'sender_power': sender,
                        'phase': phase,
                        'content': msg_data.get('content', ''),
                        'is_global': msg_data.get('message_type') == 'global',
                        'recipient_power': msg_data.get('recipient') if msg_data.get('message_type') == 'private' else None
                    }
                    messages.append(message)
            except json.JSONDecodeError:
                continue
                
        return messages
    
    def _get_model_for_power(self, power: str, llm_responses: List[dict]) -> str:
        """Get the model used for a specific power."""
        for response in llm_responses:
            if response.get('power') == power:
                return response.get('model', 'unknown')
        return 'unknown'
    
    def _get_relationships_for_phase(self, power: str, phase: str, phase_data: dict) -> dict:
        """Get relationships for a power in a specific phase."""
        if (
            'state_agents' in phase_data and
            power in phase_data['state_agents'] and
            'relationships' in phase_data['state_agents'][power]
        ):
            agent_relationships = {power: phase_data['state_agents'][power]['relationships']}
        else:
            agent_relationships = phase_data.get('relationships', {})
        return agent_relationships.get(power, {})
    
    def _get_previous_phase_data(self, current_phase: str, game_data: dict) -> Optional[dict]:
        """Get the phase data for the phase before the current one."""
        phases = game_data['phases']
        for i, phase in enumerate(phases):
            if phase['name'] == current_phase and i > 0:
                return phases[i-1]
        return None
    
    def _calculate_relationship_similarity(self, prev_relationships: dict, current_relationships: dict) -> float:
        """Calculate similarity between two relationship dictionaries."""
        if not prev_relationships or not current_relationships:
            return 1.0
            
        all_powers = set(prev_relationships.keys()) | set(current_relationships.keys())
        if not all_powers:
            return 1.0
            
        matches = 0
        for power in all_powers:
            prev_rel = prev_relationships.get(power, 'Neutral')
            curr_rel = current_relationships.get(power, 'Neutral')
            if prev_rel == curr_rel:
                matches += 1
                
        return matches / len(all_powers)
    
    def _calculate_sentiment_metrics(self, power: str, phase: str, phase_data: dict) -> dict:
        """Calculate sentiment metrics for a power."""
        
        metrics = {
            'avg_sentiment_toward_others': 0.0,
            'avg_sentiment_from_others': 0.0,
            'sentiment_change_from_prev': 0.0
        }
        
        if 'state_agents' in phase_data:
            sa = phase_data['state_agents']
            agent_relationships = {p: sa[p]['relationships'] for p in sa if 'relationships' in sa[p]}
        else:
            agent_relationships = phase_data.get('relationships', {})
        if not agent_relationships:
            return metrics
            
        # Calculate how this power perceives others (outgoing sentiment)
        power_relationships = agent_relationships.get(power, {})
        if power_relationships:
            outgoing_values = [self.relationship_values.get(rel, 0) for rel in power_relationships.values()]
            avg_outgoing = statistics.mean(outgoing_values) if outgoing_values else 0
        else:
            avg_outgoing = 0
            
        # Calculate how others perceive this power (incoming sentiment)
        incoming_values = []
        for other_power, relationships in agent_relationships.items():
            if other_power != power and power in relationships:
                incoming_values.append(self.relationship_values.get(relationships[power], 0))
                
        avg_incoming = statistics.mean(incoming_values) if incoming_values else 0
        
        metrics['avg_sentiment_toward_others'] = avg_outgoing
        metrics['avg_sentiment_from_others'] = avg_incoming
        
        return metrics
    
    def _extract_territory_from_unit(self, unit_str: str) -> str:
        """Extract territory name from unit string (e.g., 'A BER' -> 'BER', 'F STP/SC' -> 'STP')."""
        parts = unit_str.strip().split()
        if len(parts) >= 2:
            territory = parts[1]
            # Handle special coast notation like 'STP/SC' -> 'STP'
            if '/' in territory:
                territory = territory.split('/')[0]
            return territory
        return unit_str
    
    # ───────────────── Diplobench style game score ──────────────────
    @staticmethod
    def _year_from_phase(name: str) -> int | None:
        """Return the 4-digit year embedded in a phase name such as 'F1903M'."""
        m = re.search(r'(\d{4})', name)
        return int(m.group(1)) if m else None


    def _phase_year(self, phases, idx: int) -> int | None:
        """
        Like _year_from_phase but walks backward if a phase itself has no year
        (e.g. 'COMPLETED').  Returns None if nothing is found.
        """
        for j in range(idx, -1, -1):
            y = self._year_from_phase(phases[j]["name"])
            if y is not None:
                return y
        return None


    def _compute_game_scores(self, game_data: dict) -> dict[str, int]:
        """
        Return {power → game_score} using the revised Diplobench scheme.

        Rules
        -----
        max_year   : taken from overview.jsonl (default 1930 → 30)
        win_year   : year in which a power reached 18+ SCs (1900 subtracted)
        score:
            • solo winner   : max_year + (max_year - win_year) + 18
            • survivor      : max_year + final_SCs
            • eliminated    : elimination_year
        """
        # ------------------------------------------------------------------
        # 1. Determine max_year from overview.jsonl (or default 1930 → 30)
        # ------------------------------------------------------------------
        max_year = 30  # default
        overview_path = Path(game_data.get("run_dir", "")) / "overview.jsonl"
        if overview_path.exists():
            with open(overview_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        obj = json.loads(line.strip())
                        if isinstance(obj, dict) and "max_year" in obj:
                            max_year = int(obj["max_year"]) - 1900
                            break
                    except Exception:
                        continue

        # ------------------------------------------------------------------
        # 2. Build helper: map phase index → turn number (year - 1900)
        # ------------------------------------------------------------------
        phases = game_data.get("phases", [])
        if not phases:
            return {}

        def _turn_from_phase(idx: int) -> int | None:
            """Return year-1900 for the given phase index, walking backward if needed."""
            for j in range(idx, -1, -1):
                m = re.search(r"(\d{4})", phases[j]["name"])
                if m:
                    return int(m.group(1)) - 1900
            return None

        # ------------------------------------------------------------------
        # 3. Determine solo winner and win_year
        # ------------------------------------------------------------------
        solo_winner = None
        win_year = None
        for idx, ph in enumerate(phases):
            for pwr, scs in ph.get("state", {}).get("centers", {}).items():
                if len(scs) >= 18:
                    solo_winner = pwr
                    win_year = _turn_from_phase(idx)
                    break
            if solo_winner:
                break

        # ------------------------------------------------------------------
        # 4. Determine elimination year for every power
        # ------------------------------------------------------------------
        elim_year: dict[str, int | None] = {p.value: None for p in PowerEnum}
        for idx, ph in enumerate(phases):
            turn = _turn_from_phase(idx)
            if turn is None:
                continue
            for pwr in elim_year:
                if elim_year[pwr] is None and not ph["state"]["centers"].get(pwr):
                    elim_year[pwr] = turn

        # ------------------------------------------------------------------
        # 5. Compute final scores
        # ------------------------------------------------------------------
        final_state = phases[-1]["state"]
        scores: dict[str, int] = {}

        for pwr in elim_year:
            if pwr == solo_winner:
                scores[pwr] = max_year + (max_year - (win_year or max_year)) + 18
            elif elim_year[pwr] is None:  # survived to max_year
                final_scs = len(final_state.get("centers", {}).get(pwr, []))
                scores[pwr] = max_year + final_scs
            else:  # eliminated
                scores[pwr] = elim_year[pwr]

        return scores

    
    def _load_csv_as_dicts(self, csv_path: str) -> List[dict]:
        """Load CSV file as list of dictionaries."""
        data = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        return data

    def _save_phase_csv(self, phase_features: List[dict], output_path: Path) -> None:
        """Save phase-level features to CSV."""
        if not phase_features:
            print("No phase features to save")
            return
        
        # Define explicit column order
        fieldnames = [
            # === PRIMARY IDENTIFIERS ===
            'game_id',
            'llm_model', 
            'game_phase',
            'analyzed_response_type',
            'power_name',
            
            # === RESPONSE INFO ===
            'llm_responses_of_this_type',
            
            # === RESPONSE QUALITY ANALYSIS (HARD MODE) ===
            'total_responses_analyzed',
            'failed_responses_count',
            'successful_responses_count',
            'response_failure_rate_percentage',
            'response_success_rate_percentage',
            
            
            # === NEGOTIATION METRICS ===
            'total_messages_sent',
            'messages_to_allies',
            'messages_to_enemies', 
            'messages_to_neutrals',
            'global_messages_count',
            'private_messages_count',
            'percent_global_messages',
            'percent_messages_to_allies',
            'percent_messages_to_enemies',
            'percent_messages_to_neutrals',
            'average_message_length_chars',
            
            # === REFLECTION METRICS ===
            'llm_response_tokens_estimated',
            'llm_response_time_ms',
            'relationship_stability_vs_prev_phase',
            'avg_sentiment_toward_others',
            'avg_sentiment_from_others',
            'sentiment_change_from_prev',
            
            # === GAME STATE ===
            'territories_controlled_count',
            'supply_centers_owned_count',
            'military_units_count',
            'territories_gained_vs_prev_phase',
            'supply_centers_gained_vs_prev_phase',
            'military_units_gained_vs_prev_phase',
            'relationships'
        ]

        # ensure order columns
        for ot in self.ORDER_TYPES:
            plural = f"{ot}s" if not ot.endswith("s") else ot
            for suffix in ("total", "success", "bounce", "void", "invalid", "success_rate"):
                col = f"orders_{plural}_{suffix}"
                if col not in fieldnames:
                    fieldnames.append(col)

        
        # Ensure all actual fields are included (in case we missed any)
        actual_fields = set()
        for row in phase_features:
            actual_fields.update(row.keys())
        
        # Add any missing fields at the end
        for field in sorted(actual_fields):
            if field not in fieldnames:
                fieldnames.append(field)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(phase_features)
        
        print(f"Saved {len(phase_features)} phase records to {output_path}")
    
    def _save_game_csv(self, game_features: List[dict], output_path: Path) -> None:
        """Save game-level features to CSV."""
        if not game_features:
            print("No game features to save")
            return
        
        # Define explicit column order for game-level CSV
        fieldnames = [
            # === PRIMARY IDENTIFIERS ===
            'game_id',
            'llm_model',
            'power_name',
            
            # === FINAL STATE METRICS (End game snapshot) ===
            'final_territories_controlled',
            'final_supply_centers_owned',
            'final_military_units',
            'game_result',
            'final_ranking_by_supply_centers',
            
            # === TOTALS (Complete game sums) ===
            'total_negotiation_messages_sent',
            'total_messages_to_allies',
            'total_messages_to_enemies',
            'total_messages_to_neutrals',
            'total_global_messages',
            'total_private_messages',
            'total_response_tokens_estimated',
            'total_llm_interactions',
            'total_phases_active',
            
            # === FAILURE ANALYSIS TOTALS (HARD MODE) ===
            'total_llm_calls_overall',
            'total_failed_llm_calls',
            'total_success_llm_calls',
            'overall_failure_rate_percentage',
            'overall_success_rate_percentage',
            
            
            # === AVERAGES (Behavioral patterns over time) ===
            'avg_negotiation_messages_per_phase',
            'avg_relationship_stability_per_phase', 
            'avg_sentiment_toward_others',
            'avg_sentiment_from_others',
            'avg_response_tokens_per_interaction',
            'avg_territories_controlled_per_phase',
            'avg_supply_centers_owned_per_phase',
            'avg_military_units_per_phase',
            'percent_messages_to_allies_overall',
            'percent_messages_to_enemies_overall',
            'percent_global_vs_private_overall',

            # === Diplobench style single scalar game score ===
            'game_score',
        ]

        # ensure order-total columns
        for ot in self.ORDER_TYPES:
            plural = f"{ot}s" if not ot.endswith("s") else ot
            base = f"orders_{plural}_total"
            for suffix in ("total", "success", "bounce", "void", "invalid", "success_rate"):
                col = f"orders_{plural}_{suffix}"
                if col not in fieldnames:
                    fieldnames.append(col)


        
        # Ensure all actual fields are included
        actual_fields = set()
        for row in game_features:
            actual_fields.update(row.keys())
        
        # Add any missing fields at the end
        for field in sorted(actual_fields):
            if field not in fieldnames:
                fieldnames.append(field)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(game_features)
        
        print(f"Saved {len(game_features)} game records to {output_path}")

    def _analyze_failures(self, power: str, phase: str, response_type: str, 
                         llm_responses: List[dict]) -> dict:
        """Analyze failure patterns for specific power/phase/response_type."""
        responses = [r for r in llm_responses 
                    if r['power'] == power and r['phase'] == phase and r['response_type'] == response_type]
        
        total_responses = len(responses)
        if total_responses == 0:
            return {
                'total_responses_analyzed': 0,
                'failed_responses_count': 0,
                'successful_responses_count': 0,
                'response_failure_rate_percentage': 0.0,
                'response_success_rate_percentage': 0.0
            }
        
        failed_count = 0
        success_count = 0
        
        for response in responses:
            success_status = response.get('success', '').strip()
            if self._is_failure_status(success_status):
                failed_count += 1
            elif self._is_success_status(success_status):
                success_count += 1
        
        return {
            'total_responses_analyzed': total_responses,
            'failed_responses_count': failed_count,
            'successful_responses_count': success_count,
            'response_failure_rate_percentage': (failed_count / total_responses) * 100.0 if total_responses > 0 else 0.0,
            'response_success_rate_percentage': (success_count / total_responses) * 100.0 if total_responses > 0 else 0.0
        }
    
    def _is_failure_status(self, status: str) -> bool:
        """Check if status indicates failure."""
        status_lower = status.lower()
        return any(indicator in status_lower for indicator in ['false', 'failure:', 'error', 'failed'])
    
    def _is_success_status(self, status: str) -> bool:
        """Check if status indicates success."""
        status_lower = status.lower()
        return any(indicator in status_lower for indicator in ['true', 'success:', 'success', 'partial'])
    


def main():
    """Main entry point for the Statistical Game Analysis tool."""
    parser = argparse.ArgumentParser(description='Statistical Game Analysis for AI Diplomacy')
    parser.add_argument('input_path', help='Path to results folder or parent folder containing multiple results')
    parser.add_argument('--output', '-o', help='Output directory (default: same as input)')
    parser.add_argument('--multiple', '-m', action='store_true', 
                       help='Treat input as parent folder containing multiple results folders')
    
    args = parser.parse_args()
    
    analyzer = StatisticalGameAnalyzer()
    
    try:
        if args.multiple:
            analyzer.analyze_multiple_folders(args.input_path, args.output)
        else:
            analyzer.analyze_folder(args.input_path, args.output)
            
        print("\nAnalysis complete!")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
        
    return 0


if __name__ == '__main__':
    exit(main())
