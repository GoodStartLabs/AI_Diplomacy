# Running Benchmarks

## Quick Start

```bash
python run_benchmark.py --model_id "MODEL_ID" --friendly_name "model_name"
```

## Examples

```bash
# OpenAI model
python run_benchmark.py --model_id "gpt-4o" --friendly_name "gpt-4o"

# OpenRouter model
python run_benchmark.py --model_id "openrouter:anthropic/claude-3.5-sonnet" --friendly_name "claude-3.5-sonnet"

# Anthropic model
python run_benchmark.py --model_id "claude-sonnet-4-20250514" --friendly_name "claude-sonnet-4"
```

## What it does

1. Runs 20 games with **baseline** prompts (`prompts_benchmark`)
2. Runs 20 games with **aggressive** prompts (`prompts_hold_reduction_v3`)
3. Generates leaderboard comparison charts (8 visualizations)

Results saved to:
- `results/{model_name}_baseline/`
- `results/{model_name}_aggressive/`
- `leaderboard/{model_name}-baseline/` (symlink)
- `leaderboard/{model_name}-aggressive/` (symlink)
- `leaderboard/leaderboard_comparison/` (charts)

## Options

```bash
--test                  # Quick test: 3 games, max_year=1901
--baseline-only         # Run only baseline
--aggressive-only       # Run only aggressive
--skip-leaderboard      # Don't generate charts
```

## Requirements

- Model plays as FRANCE (position 2)
- Opponents: `openrouter:mistralai/devstral-small`
- Max year: 1925
- Parallel: 20 games at once
