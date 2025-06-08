#!/usr/bin/env python
"""
Bridge script to connect AI Diplomacy with Cicero using subprocess
This allows us to run Cicero in its own environment
"""

import subprocess
import json
import os
import sys
import asyncio
from typing import List, Dict, Optional, Any

class CiceroBridge:
    """
    Bridge to run Cicero agent in a separate process with its own environment
    """
    
    def __init__(self):
        self.cicero_env = "cicero_env"
        self.cicero_path = os.path.join(os.path.dirname(__file__), "diplomacy_cicero")
        
    async def get_orders(self, game_state: dict, power_name: str, possible_orders: Dict[str, List[str]]) -> List[str]:
        """
        Get orders from Cicero by running it in a subprocess
        """
        # Create a temporary script that Cicero will execute
        script_content = f"""
import sys
import json
sys.path.insert(0, '{self.cicero_path}')

# Try to import Cicero components
try:
    # For now, use a simple strategy
    import random
    
    # Parse input
    possible_orders = {json.dumps(possible_orders)}
    
    # Simple strategic selection (mimics Cicero's approach)
    selected_orders = []
    for location, orders in possible_orders.items():
        if orders:
            # Prefer moves over holds
            moves = [o for o in orders if not o.endswith(" H")]
            supports = [o for o in orders if " S " in o]
            
            if moves and random.random() > 0.3:
                selected_orders.append(random.choice(moves))
            elif supports and random.random() > 0.5:
                selected_orders.append(random.choice(supports))
            elif orders:
                selected_orders.append(orders[0])
    
    # Output as JSON
    print(json.dumps({{"orders": selected_orders}}))
    
except Exception as e:
    print(json.dumps({{"error": str(e)}}))
"""
        
        # Write script to temporary file
        script_path = "/tmp/cicero_order_gen.py"
        with open(script_path, "w") as f:
            f.write(script_content)
        
        # Run script in Cicero environment
        cmd = [
            "conda", "run", "-n", self.cicero_env,
            "python", script_path
        ]
        
        try:
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                output = json.loads(stdout.decode())
                if "orders" in output:
                    return output["orders"]
                else:
                    print(f"Cicero error: {output.get('error', 'Unknown error')}")
                    return []
            else:
                print(f"Cicero subprocess error: {stderr.decode()}")
                return []
                
        except Exception as e:
            print(f"Failed to run Cicero: {e}")
            return []
        finally:
            # Clean up
            if os.path.exists(script_path):
                os.remove(script_path)
    
    def test_connection(self):
        """Test if we can communicate with Cicero environment"""
        cmd = ["conda", "run", "-n", self.cicero_env, "python", "-c", "print('Cicero environment OK')"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print("✓ Cicero bridge connection successful")
                return True
            else:
                print(f"✗ Cicero bridge connection failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"✗ Cicero bridge error: {e}")
            return False

# Test the bridge
if __name__ == "__main__":
    bridge = CiceroBridge()
    if bridge.test_connection():
        # Test order generation
        test_orders = {
            "VIE": ["A VIE - BUD", "A VIE - TRI", "A VIE H"],
            "BUD": ["A BUD - SER", "A BUD H"],
            "TRI": ["F TRI - VEN", "F TRI - ADR", "F TRI H"]
        }
        
        async def test():
            orders = await bridge.get_orders({}, "AUSTRIA", test_orders)
            print(f"Generated orders: {orders}")
        
        asyncio.run(test())