# WebSocket Diplomacy Client

This directory contains a WebSocket-based client for connecting to a Diplomacy server, designed as a drop-in replacement for direct `Game()` import usage in AI game simulations.

## Files

- **`websocket_diplomacy_client.py`** - Main WebSocket client class
- **`lm_game_websocket.py`** - WebSocket version of `lm_game.py` 
- **`websocket_client_example.py`** - Simple usage examples
- **`WEBSOCKET_CLIENT_README.md`** - This documentation

## Overview

The `WebSocketDiplomacyClient` provides a simplified interface for interacting with a remote Diplomacy server via WebSocket connections. It wraps the existing diplomacy client functionality and provides methods similar to the local `Game` class.

## Key Features

- **Drop-in replacement** for direct `Game()` usage
- **Async/await support** for all operations
- **Automatic reconnection** and synchronization
- **Multiple game management** (create, join, list)
- **Full game interaction** (orders, messages, state queries)
- **Authentication handling** with username/password

## Quick Start

### 1. Start a Diplomacy Server

First, start a Diplomacy server:

```bash
# From the diplomacy directory
python -m diplomacy.server.run --port 8432
```

### 2. Basic Client Usage

```python
import asyncio
from websocket_diplomacy_client import connect_to_diplomacy_server

async def main():
    # Connect to server
    client = await connect_to_diplomacy_server(
        hostname="localhost",
        port=8432,
        username="player1",
        password="mypassword"
    )
    
    # Create a new game
    game = await client.create_game(
        map_name="standard",
        power_name="FRANCE",
        n_controls=1  # For testing
    )
    
    # Get current state
    print(f"Current phase: {client.get_current_phase()}")
    print(f"France units: {client.get_units('FRANCE')}")
    
    # Submit orders
    await client.set_orders('FRANCE', ["A PAR H", "F BRE H", "A MAR H"])
    
    # Process game (if admin)
    await client.process_game()
    
    # Clean up
    await client.close()

asyncio.run(main())
```

### 3. Run the WebSocket Version of lm_game.py

```bash
# Make sure the server is running first
python lm_game_websocket.py --hostname localhost --port 8432 --username ai_player --create_multi_power_game
```

## API Reference

### Connection and Authentication

```python
# Connect to server
client = await connect_to_diplomacy_server(hostname, port, username, password)

# Or manual connection
client = WebSocketDiplomacyClient(hostname, port)
await client.connect_and_authenticate(username, password)
```

### Game Management

```python
# Create new game
game = await client.create_game(
    map_name="standard",
    rules=["NO_PRESS", "IGNORE_ERRORS", "POWER_CHOICE"],
    power_name="FRANCE",  # None for observer
    n_controls=7,
    deadline=None,
    registration_password=None
)

# Join existing game
game = await client.join_game(
    game_id="ABC123",
    power_name="ENGLAND",  # None for observer
    registration_password=None
)

# List available games
games = await client.list_games(
    game_id_filter=None,
    map_name=None,
    status=None,
    include_protected=False
)
```

### Game Interaction

```python
# Submit orders
await client.set_orders(power_name, ["A PAR H", "F BRE H"])

# Clear orders
await client.clear_orders(power_name)

# Set wait flag
await client.set_wait_flag(power_name, wait=True)

# Send diplomatic message
await client.send_message(
    sender="FRANCE",
    recipient="ENGLAND",  # or "GLOBAL"
    message="Hello!"
)

# Process game (admin only)
await client.process_game()

# Vote for draw
await client.vote(power_name, "yes")
```

### State Queries

```python
# Get current phase and state
current_phase = client.get_current_phase()
current_short_phase = client.get_current_short_phase()
state = client.get_state()

# Get power information
power = client.get_power("FRANCE")
units = client.get_units("FRANCE")
orderable_locations = client.get_orderable_locations("FRANCE")

# Get possible orders
all_possible_orders = client.get_all_possible_orders()

# Get game history
order_history = client.order_history
result_history = client.result_history
messages = client.messages

# Check game status
is_done = client.is_game_done
all_powers = client.powers
```

### Synchronization

```python
# Synchronize with server state
await client.synchronize()

# Get phase history
history = await client.get_phase_history(from_phase=None, to_phase=None)
```

## Differences from Local Game Class

### Async Operations
All operations that communicate with the server are async and must be awaited:

```python
# Local Game
game.set_orders("FRANCE", ["A PAR H"])

# WebSocket Client  
await client.set_orders("FRANCE", ["A PAR H"])
```

### Authentication Required
You must authenticate with the server before performing any operations:

```python
await client.connect_and_authenticate("username", "password")
```

### Game Creation/Joining
Instead of creating a local game object, you create or join games on the server:

```python
# Local
game = Game()

# WebSocket
game = await client.create_game(power_name="FRANCE")
```

### Limited Admin Operations
Some operations (like `process_game()`) require admin privileges on the server.

## Command Line Arguments for lm_game_websocket.py

```bash
python lm_game_websocket.py [options]

Options:
  --hostname HOST         Server hostname (default: localhost)
  --port PORT            Server port (default: 8432)
  --username USER        Username for authentication (default: ai_player)
  --password PASS        Password for authentication (default: password)
  --game_id ID           Join existing game instead of creating new one
  --max_year YEAR        Maximum year to simulate (default: 1901)
  --num_negotiation_rounds N  Number of negotiation rounds (default: 0)
  --models MODEL_LIST    Comma-separated list of models for powers
  --planning_phase       Enable planning phase
  --create_multi_power_game   Create game and join multiple powers (testing)
```

## Examples

### Basic Server Interaction

```bash
python websocket_client_example.py
```

### Join Existing Game

```bash
python websocket_client_example.py GAME_ID_HERE
```

### Run AI vs AI Game

```bash
# Start server in one terminal
python -m diplomacy.server.run --port 8432

# Run AI game in another terminal
python lm_game_websocket.py --create_multi_power_game --models "gpt-4,claude-3,gpt-3.5-turbo,gemini-pro,gpt-4,claude-3,gpt-3.5-turbo"
```

## Error Handling

The client includes automatic reconnection and synchronization. Common error scenarios:

- **Connection failures**: Automatically retried with exponential backoff
- **Authentication errors**: Raised immediately, check credentials
- **Permission errors**: Some operations require admin/moderator rights
- **Game state mismatches**: Automatic synchronization attempts to resolve

## Troubleshooting

1. **"Must connect and authenticate first"** - Call `connect_and_authenticate()` before other operations

2. **"Invalid client game"** - The game object is no longer valid, try synchronizing or rejoining

3. **Connection timeouts** - Check that the server is running and accessible

4. **Permission denied** - Some operations require admin rights or game ownership

5. **Game not found** - Verify the game ID exists and you have access

## Integration with Existing Code

To convert existing code from local `Game()` usage:

1. Replace `Game()` imports with `WebSocketDiplomacyClient`
2. Add authentication step
3. Add `await` to all game operations
4. Handle the async context properly
5. Replace direct game creation with `create_game()` or `join_game()`

The `lm_game_websocket.py` file demonstrates a complete conversion of the original `lm_game.py` script.