"""
Enhanced mock Cicero agent with strategic reasoning inspired by Cicero's approach.
This provides Cicero-like behavior without requiring the full Cicero installation.
"""

import random
import logging
from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)

class EnhancedCiceroAgent:
    """
    Enhanced strategic agent inspired by Cicero's approach.
    Implements multi-step planning, alliance detection, and strategic reasoning.
    """
    
    def __init__(self, aggression_level: float = 0.7, cooperation_threshold: float = 0.5):
        self.aggression_level = aggression_level
        self.cooperation_threshold = cooperation_threshold
        self.alliance_memory = defaultdict(float)  # Track cooperation history
        
    def get_orders(self, possible_orders: Dict[str, List[str]], 
                   game_context: Optional[Dict] = None) -> List[str]:
        """
        Generate strategic orders with Cicero-like reasoning.
        
        Args:
            possible_orders: Dict mapping locations to possible orders
            game_context: Optional game state information
            
        Returns:
            List of selected orders
        """
        selected_orders = []
        
        # Analyze possible orders by type
        moves = defaultdict(list)
        supports = defaultdict(list)
        convoys = defaultdict(list)
        holds = defaultdict(list)
        
        for location, orders in possible_orders.items():
            for order in orders:
                if " S " in order:
                    supports[location].append(order)
                elif " C " in order:
                    convoys[location].append(order)
                elif order.endswith(" H"):
                    holds[location].append(order)
                else:
                    moves[location].append(order)
        
        # Strategic order selection
        for location, orders in possible_orders.items():
            if not orders:
                continue
                
            # Priority 1: Coordinated attacks (supports)
            if location in supports and random.random() < self.cooperation_threshold:
                # Look for support moves that help allies or ourselves
                strategic_supports = self._evaluate_supports(supports[location], game_context)
                if strategic_supports:
                    selected_orders.append(random.choice(strategic_supports))
                    continue
            
            # Priority 2: Aggressive moves
            if location in moves and random.random() < self.aggression_level:
                # Evaluate moves for strategic value
                strategic_moves = self._evaluate_moves(moves[location], game_context)
                if strategic_moves:
                    selected_orders.append(random.choice(strategic_moves))
                    continue
            
            # Priority 3: Convoy operations
            if location in convoys:
                selected_orders.append(convoys[location][0])
                continue
            
            # Priority 4: Defensive holds for important positions
            if location in holds:
                selected_orders.append(holds[location][0])
            else:
                # Fallback to any available order
                selected_orders.append(orders[0])
        
        return selected_orders
    
    def _evaluate_supports(self, support_orders: List[str], context: Optional[Dict]) -> List[str]:
        """Evaluate support orders for strategic value."""
        # In a full implementation, this would analyze:
        # - Whether the support helps an ally
        # - Whether it strengthens our position
        # - Whether it blocks an enemy
        
        # For now, prefer supports that mention multiple units (complex operations)
        complex_supports = [s for s in support_orders if s.count(" - ") > 0]
        return complex_supports if complex_supports else support_orders
    
    def _evaluate_moves(self, move_orders: List[str], context: Optional[Dict]) -> List[str]:
        """Evaluate move orders for strategic value."""
        # In a full implementation, this would analyze:
        # - Distance to supply centers
        # - Threat assessment
        # - Alliance considerations
        
        # For now, prefer moves to key territories
        key_territories = {'MUN', 'PAR', 'LON', 'ROM', 'VIE', 'BER', 'CON', 'WAR', 'MOS', 'STP'}
        strategic_moves = []
        
        for move in move_orders:
            # Check if move targets a key territory
            parts = move.split(" - ")
            if len(parts) > 1:
                target = parts[1].strip()
                if any(key in target for key in key_territories):
                    strategic_moves.append(move)
        
        return strategic_moves if strategic_moves else move_orders
    
    def analyze_game_state(self, game_state: Dict) -> Dict[str, float]:
        """
        Analyze game state to determine threats and opportunities.
        Returns threat scores for each power.
        """
        threat_scores = defaultdict(float)
        
        # This would implement Cicero's game state evaluation
        # For now, return mock threat assessment
        powers = ['AUSTRIA', 'ENGLAND', 'FRANCE', 'GERMANY', 'ITALY', 'RUSSIA', 'TURKEY']
        for power in powers:
            threat_scores[power] = random.uniform(0, 1)
        
        return dict(threat_scores)
    
    def suggest_alliance(self, our_power: str, threat_scores: Dict[str, float]) -> Optional[str]:
        """Suggest best alliance partner based on game analysis."""
        # Remove ourselves from consideration
        other_powers = {k: v for k, v in threat_scores.items() if k != our_power}
        
        # Find powers with moderate threat levels (potential allies)
        potential_allies = {
            power: score for power, score in other_powers.items()
            if 0.3 < score < 0.7  # Not too weak, not too strong
        }
        
        if potential_allies:
            # Choose the one with best cooperation history
            best_ally = max(potential_allies.keys(), 
                          key=lambda p: self.alliance_memory.get(p, 0))
            return best_ally
        
        return None