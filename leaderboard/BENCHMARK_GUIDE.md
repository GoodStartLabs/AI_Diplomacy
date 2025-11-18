# Diplomacy Benchmark Guide

## Single Model Benchmark

```bash
# Production: 20 games to 1925
python run_benchmark.py --model_id "openai:gpt-4o" --friendly_name "gpt_4o"

# Test: 3 games to 1901
python run_benchmark.py --model_id "openai:gpt-4o" --friendly_name "test" --test

# Baseline only
python run_benchmark.py --model_id "..." --friendly_name "..." --baseline-only

# Aggressive only
python run_benchmark.py --model_id "..." --friendly_name "..." --aggressive-only
```

## Queue Multiple Models

Edit `run_benchmark_queue.sh`:
```bash
MODELS=(
    "model_id|friendly_name|baseline_only|aggressive_only"
    "openai:gpt-4o|gpt_4o||"              # Both modes
    "gemini-2.5-flash|gemini|true|"       # Baseline only
    "claude-3.5-sonnet|claude||true"      # Aggressive only
)
```

Run:
```bash
./run_benchmark_queue.sh
```

## Check Status

```bash
# Queue progress
tail -f /tmp/benchmark_queue/queue.log

# Individual model logs
tail -f /tmp/benchmark_queue/{friendly_name}_{baseline|aggressive}.log

# Running games (check FRANCE progress)
ls -la results/{friendly_name}_{baseline|aggressive}/games/*/
```

## Visualize Results

```bash
# Generate comparison plots
python leaderboard/full_comparison.py

# View plots
open leaderboard/*.png
```

## Key Locations

| Item | Path |
|------|------|
| **Results** | `results/{friendly_name}_{baseline\|aggressive}/` |
| **Leaderboard Links** | `leaderboard/{friendly_name}-{baseline\|aggressive}` |
| **Queue Logs** | `/tmp/benchmark_queue/` |
| **Prompts Baseline** | `prompts_benchmark/` |
| **Prompts Aggressive** | `prompts_hold_reduction_v3/` |

## Notes

- Test model plays FRANCE (position 2, 0-indexed)
- Opponents: devstral-small
- Results auto-symlinked to leaderboard/
- Benchmark handles retries, logging, error recovery