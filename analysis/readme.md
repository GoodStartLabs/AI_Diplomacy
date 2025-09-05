# Analysis Pipeline

This folder contains the data processing pipeline for converting raw diplomacy game logs into structured analysis datasets.

## Overview

The module contains pipelines transforms raw game logs data (stored as json/csv files) into four analytical datasets:

1. **Orders Data** - one row per order given by each power in each phase
2. **Conversations Data** - one row per conversation between two powers in each phase  
3. **Phase Data** - one row per power per phase with aggregated state and action summaries
4. **Game Data** - Summary of overall game features

## Main entry point

### `make_all_analysis_data.py` - Primary orchestrator
**main use case**: process all games in a data folder, create corresponding orders, conversations, and phase datasets. Supports batch and individual processing.

```bash
# process all games in a folder
python analysis/make_all_analysis_data.py \
  --game_data_folder "/path/to/Game Data" \
  --output_folder "/path/to/Game Data - Analysis"

# process specific games
python analysis/make_all_analysis_data.py \
  --selected_game game1 game2 \
  --game_data_folder "/path/to/Game Data" \
  --output_folder "/path/to/Game Data - Analysis"
```

This script runs the three p1, p2 and p3 analysis scripts in sequence and saves outputs to organized subfolders. 

### Individual analysis scripts

#### `p1_make_longform_orders_data.py`
**what it does**: creates detailed order-level data with one row per order given
**key outputs**: 
- order classification (move, support, hold, etc.)
- unit locations and destinations
- support relationships and outcomes
- relationship matrices between powers
- llm reasoning for order generation

```bash
python analysis/p1_make_longform_orders_data.py \
  --game_data_folder "/path/to/Game Data" \
  --analysis_folder "/path/to/output"
```

#### `p2_make_convo_data.py` 
**what it does**: extracts conversation data between all pairs of powers
**key outputs**:
- message counts and streaks per party
- conversation transcripts
- relationship context for each conversation

```bash
python analysis/p2_make_convo_data.py \
  --game_data_folder "/path/to/Game Data" \
  --analysis_folder "/path/to/output"
```

#### `p3_make_phase_data.py`
**what it does**: creates power-phase level summaries combining state, actions, and conversations
**key outputs**:
- current state (units, centers, influence counts)
- action summaries (command counts, outcomes)
- conversation transcripts with each power
- change metrics between phases
- llm reasoning and diary entries

```bash
python analysis/p3_make_phase_data.py \
  --game_data_folder "/path/to/Game Data" \
  --analysis_folder "/path/to/output"
```

#### `statistical_game_analysis.py`
**what it does**: comprehensive statistical analysis of game results and llm performance
**key outputs**:
- game-level aggregated metrics and features
- response success/failure rates by type
- relationship dynamics and negotiation patterns
- phase-level analysis with response-type granularity
- comprehensive failure tracking and validation

```bash
# analyze single game folder
python analysis/statistical_game_analysis.py /path/to/game_folder

# batch analyze multiple games
python analysis/statistical_game_analysis.py /path/to/parent_folder --multiple

# specify output directory
python analysis/statistical_game_analysis.py /path/to/game_folder --output /path/to/output
```

**note**: this is a separate analysis tool that operates independently of the main pipeline


## supporting modules

### `analysis_helpers.py`
utility functions for:
- loading game data from folders or zip files
- mapping countries to their llm models
- standardizing data loading across scripts

### `schemas.py` 
constants and regex patterns:
- supply center lists and coastal variants
- country names
- order parsing regexes
- phase naming patterns

## expected input data structure

each game folder should contain:
- `overview.jsonl` - maps countries to llm models
- `lmvsgame.json` - full turn-by-turn game state and actions
- `llm_responses.csv` - all llm prompts and responses

## output structure

the pipeline creates organized subfolders:

output_folder/
├── orders_data/
│ └── {game_name}orders_data.csv
├── conversations_data/
│ └── {game_name}conversations_data.csv
└── phase_data/
│ └── {game_name}phase_data.csv

## Use cases

- **game analysis**: examine specific games in detail
- **model comparison**: compare llm performance across games
- **relationship analysis**: study diplomatic dynamics
- **order validation**: check llm order generation success rates
- **conversation analysis**: study negotiation patterns
- **phase progression**: track game state evolution