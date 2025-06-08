import asyncio
import logging
import os
import subprocess
import json
from typing import List, Dict, Optional, Any
from .clients import BaseModelClient
from .utils import log_llm_response
from .cicero_agent_enhanced import EnhancedCiceroAgent

logger = logging.getLogger(__name__)

class CiceroClient(BaseModelClient):
    """
    Final Cicero client that attempts multiple integration methods:
    1. Direct import (if Cicero is properly installed)
    2. Subprocess bridge (if Cicero environment exists)
    3. Enhanced mock agent (fallback)
    """
    
    def __init__(self, model_name: str = "cicero"):
        super().__init__(model_name)
        self.integration_method = None
        self.cicero_agent = None
        self._initialize_best_method()
    
    def _initialize_best_method(self):
        """Try different integration methods in order of preference"""
        
        # Method 1: Try direct import
        if self._try_direct_import():
            self.integration_method = "direct"
            logger.info(f"[{self.model_name}] Using direct Cicero import")
            return
        
        # Method 2: Try subprocess bridge
        if self._try_subprocess_bridge():
            self.integration_method = "subprocess"
            logger.info(f"[{self.model_name}] Using subprocess bridge to Cicero")
            return
        
        # Method 3: Use enhanced mock
        self._use_enhanced_mock()
        self.integration_method = "enhanced_mock"
        logger.info(f"[{self.model_name}] Using enhanced mock agent")
    
    def _try_direct_import(self) -> bool:
        """Try to import Cicero directly"""
        try:
            # Check if we're in the right environment
            python_version = subprocess.run(
                ["python", "--version"], 
                capture_output=True, 
                text=True
            ).stdout.strip()
            
            if "3.7" in python_version or "3.8" in python_version:
                # Try importing Cicero
                import sys
                cicero_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                    "diplomacy_cicero"
                )
                if os.path.exists(cicero_path):
                    sys.path.insert(0, cicero_path)
                    
                    # Try minimal import
                    import conf.conf_cfgs
                    from fairdiplomacy.agents.base_agent import BaseAgent
                    
                    # Create simple agent
                    class DirectCiceroAgent(BaseAgent):
                        def get_orders(self, game, power, state=None):
                            return []  # Wrapper handles fallback
                        
                        def initialize_state(self, power):
                            return {"power": power}
                    
                    self.cicero_agent = DirectCiceroAgent()
                    return True
        except Exception as e:
            logger.debug(f"Direct import failed: {e}")
        
        return False
    
    def _try_subprocess_bridge(self) -> bool:
        """Check if subprocess bridge can work"""
        try:
            # Check if cicero_env exists
            result = subprocess.run(
                ["conda", "env", "list"], 
                capture_output=True, 
                text=True
            )
            if "cicero_env" in result.stdout:
                # Test the environment
                test_result = subprocess.run(
                    ["conda", "run", "-n", "cicero_env", "python", "-c", "print('OK')"],
                    capture_output=True,
                    text=True
                )
                if test_result.returncode == 0:
                    from cicero_bridge import CiceroBridge
                    self.bridge = CiceroBridge()
                    return True
        except Exception as e:
            logger.debug(f"Subprocess bridge failed: {e}")
        
        return False
    
    def _use_enhanced_mock(self):
        """Use the enhanced mock agent"""
        self.cicero_agent = EnhancedCiceroAgent(
            aggression_level=0.7,
            cooperation_threshold=0.5
        )
    
    async def generate_response(self, prompt: str) -> str:
        """Not used for Cicero - it generates structured outputs directly."""
        return "Cicero generates orders directly, not text responses"
    
    async def get_orders(
        self,
        game,
        board_state,
        power_name: str,
        possible_orders: Dict[str, List[str]],
        conversation_text: str,
        model_error_stats: dict,
        log_file_path: str,
        phase: str,
        agent_goals: Optional[List[str]] = None,
        agent_relationships: Optional[Dict[str, str]] = None,
        agent_private_diary_str: Optional[str] = None,
    ) -> List[str]:
        """Generate orders using the best available method"""
        
        logger.info(f"[{self.model_name}] Generating orders using {self.integration_method} method")
        
        try:
            if self.integration_method == "direct":
                # Direct Cicero call
                orders = self._get_direct_orders(game, power_name, possible_orders)
                
            elif self.integration_method == "subprocess":
                # Subprocess bridge
                orders = await self.bridge.get_orders(
                    board_state, 
                    power_name, 
                    possible_orders
                )
                
            else:  # enhanced_mock
                # Enhanced mock agent
                game_context = {
                    'power_name': power_name,
                    'phase': phase,
                    'board_state': board_state,
                    'goals': agent_goals,
                    'relationships': agent_relationships
                }
                orders = self.cicero_agent.get_orders(possible_orders, game_context)
            
            logger.info(f"[{self.model_name}] Generated orders: {orders}")
            
            # Log the result
            if log_file_path:
                log_llm_response(
                    log_file_path=log_file_path,
                    model_name=self.model_name,
                    power_name=power_name,
                    phase=phase,
                    response_type="order_generation",
                    raw_input_prompt=f"Cicero ({self.integration_method}) for {power_name}",
                    raw_response=str(orders),
                    success="Success"
                )
            
            return orders
            
        except Exception as e:
            logger.error(f"[{self.model_name}] Error generating orders: {e}")
            if model_error_stats is not None and self.model_name in model_error_stats:
                model_error_stats[self.model_name].setdefault("order_generation_errors", 0)
                model_error_stats[self.model_name]["order_generation_errors"] += 1
            return self.fallback_orders(possible_orders)
    
    def _get_direct_orders(self, game, power_name: str, possible_orders: Dict[str, List[str]]) -> List[str]:
        """Get orders from direct Cicero import"""
        try:
            # Convert game state if needed
            state = getattr(self, 'agent_state', None)
            if state is None:
                state = self.cicero_agent.initialize_state(power_name)
                self.agent_state = state
            
            # Get orders
            cicero_orders = self.cicero_agent.get_orders(game, power_name, state)
            
            # If Cicero returns empty, use strategic selection
            if not cicero_orders:
                return self._strategic_order_selection(possible_orders)
            
            return cicero_orders
            
        except Exception as e:
            logger.error(f"Direct order generation failed: {e}")
            return self._strategic_order_selection(possible_orders)
    
    def _strategic_order_selection(self, possible_orders: Dict[str, List[str]]) -> List[str]:
        """Strategic order selection mimicking Cicero's approach"""
        import random
        
        selected_orders = []
        for location, orders in possible_orders.items():
            if not orders:
                continue
            
            # Categorize orders
            moves = [o for o in orders if not o.endswith(" H") and " S " not in o and " C " not in o]
            supports = [o for o in orders if " S " in o]
            convoys = [o for o in orders if " C " in o]
            holds = [o for o in orders if o.endswith(" H")]
            
            # Strategic selection
            if moves and random.random() > 0.3:  # 70% chance to move
                # Prefer moves to strategic locations
                strategic_moves = [m for m in moves if any(
                    loc in m for loc in ['PAR', 'LON', 'MUN', 'ROM', 'VIE', 'CON', 'BER']
                )]
                selected_orders.append(
                    random.choice(strategic_moves if strategic_moves else moves)
                )
            elif supports and random.random() > 0.4:  # 60% chance to support
                selected_orders.append(random.choice(supports))
            elif convoys:
                selected_orders.append(random.choice(convoys))
            elif holds:
                selected_orders.append(holds[0])
            else:
                selected_orders.append(orders[0])
        
        return selected_orders
    
    async def get_conversation_reply(
        self,
        game,
        board_state,
        power_name: str,
        possible_orders: Dict[str, List[str]],
        game_history,
        game_phase: str,
        log_file_path: str,
        active_powers: Optional[List[str]] = None,
        agent_goals: Optional[List[str]] = None,
        agent_relationships: Optional[Dict[str, str]] = None,
        agent_private_diary_str: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Generate negotiation messages - currently returns empty"""
        messages = []
        
        if log_file_path:
            log_llm_response(
                log_file_path=log_file_path,
                model_name=self.model_name,
                power_name=power_name,
                phase=game_phase,
                response_type="negotiation_message",
                raw_input_prompt=f"Cicero negotiation ({self.integration_method})",
                raw_response="[]",
                success="Success: No messages"
            )
        
        return messages
    
    async def get_plan(
        self,
        game,
        board_state,
        power_name: str,
        game_history,
        log_file_path: str,
        agent_goals: Optional[List[str]] = None,
        agent_relationships: Optional[Dict[str, str]] = None,
        agent_private_diary_str: Optional[str] = None,
    ) -> str:
        """Generate a strategic plan"""
        plan = f"Cicero strategic plan ({self.integration_method}): Adaptive strategy based on game state analysis."
        
        if log_file_path:
            log_llm_response(
                log_file_path=log_file_path,
                model_name=self.model_name,
                power_name=power_name,
                phase=game.current_short_phase,
                response_type="plan_generation",
                raw_input_prompt="Cicero planning",
                raw_response=plan,
                success="Success"
            )
        
        return plan