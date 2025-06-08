"""
REAL Cicero Client - NO FALLBACKS

This client ONLY works with the actual Facebook Cicero model.
If Cicero is not properly installed, it will FAIL.

Requirements:
- x86_64 Linux (Ubuntu 20.04 recommended)
- Python 3.7 or 3.8
- PyTorch 1.7.1
- 2GB+ Cicero model weights
- All Cicero dependencies properly installed
"""

import logging
import os
import sys
from typing import List, Dict, Optional
from .clients import BaseModelClient

logger = logging.getLogger(__name__)

class CiceroClient(BaseModelClient):
    """
    Real Cicero client - NO FALLBACKS
    
    This will ONLY work if:
    1. Running on x86_64 Linux
    2. Python 3.7 or 3.8
    3. All Cicero dependencies installed
    4. Model weights downloaded
    
    ANY OTHER CONFIGURATION WILL FAIL
    """
    
    def __init__(self, model_name: str = "cicero"):
        super().__init__(model_name)
        
        # Check Python version
        if not (sys.version_info.major == 3 and sys.version_info.minor in [7, 8]):
            raise RuntimeError(f"Cicero requires Python 3.7 or 3.8, got {sys.version}")
        
        # Try to import Cicero - NO FALLBACKS
        self._import_real_cicero()
    
    def _import_real_cicero(self):
        """Import the REAL Cicero - fail if not available"""
        try:
            # Add Cicero path
            cicero_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                "diplomacy_cicero"
            )
            
            if not os.path.exists(cicero_path):
                raise RuntimeError(f"Cicero not found at {cicero_path}. Clone the submodule!")
            
            sys.path.insert(0, cicero_path)
            
            # Import Cicero components - these MUST work
            import conf.conf_cfgs
            from fairdiplomacy.agents.base_agent import BaseAgent
            from fairdiplomacy.agents.searchbot_agent import SearchBotAgent
            from fairdiplomacy.agents.bqre1p_agent import BQRE1PAgent
            
            # Check for model weights
            model_path = os.path.join(cicero_path, "models", "cicero.ckpt")
            if not os.path.exists(model_path):
                raise RuntimeError(f"Cicero model weights not found at {model_path}. Run download_model.py!")
            
            # Initialize REAL Cicero agent
            # TODO: Load actual config and initialize properly
            self.cicero_agent = BQRE1PAgent()  # This needs proper config
            
            logger.info(f"[{self.model_name}] REAL Cicero loaded successfully!")
            
        except Exception as e:
            logger.error(f"[{self.model_name}] Failed to load REAL Cicero: {e}")
            raise RuntimeError(f"REAL Cicero required but not available: {e}")
    
    async def generate_response(self, prompt: str) -> str:
        """Cicero doesn't generate text responses"""
        raise NotImplementedError("Cicero is an RL agent, not a text generator")
    
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
        """Generate orders using REAL Cicero"""
        
        logger.info(f"[{self.model_name}] Generating orders with REAL Cicero")
        
        try:
            # Convert game state to Cicero format
            # TODO: Implement proper game state conversion
            cicero_game = self._convert_to_cicero_game(game)
            
            # Get orders from REAL Cicero
            cicero_orders = self.cicero_agent.get_orders(
                cicero_game, 
                power_name
            )
            
            logger.info(f"[{self.model_name}] REAL Cicero orders: {cicero_orders}")
            
            return cicero_orders
            
        except Exception as e:
            logger.error(f"[{self.model_name}] REAL Cicero failed: {e}")
            raise  # NO FALLBACKS - fail hard
    
    def _convert_to_cicero_game(self, game):
        """Convert our game format to Cicero's format"""
        # TODO: Implement proper conversion
        raise NotImplementedError("Game conversion not yet implemented")
    
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
        """REAL Cicero negotiation"""
        # TODO: Implement Cicero's negotiation module
        raise NotImplementedError("Cicero negotiation not yet implemented")
    
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
        """REAL Cicero doesn't use text planning"""
        raise NotImplementedError("Cicero uses RL planning, not text")
    
    def fallback_orders(self, possible_orders: Dict[str, List[str]]) -> List[str]:
        """NO FALLBACKS - Cicero or nothing"""
        raise RuntimeError("NO FALLBACKS - Real Cicero required")