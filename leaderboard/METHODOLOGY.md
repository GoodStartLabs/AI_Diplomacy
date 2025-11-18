# Diplomacy LLM Benchmark Methodology

## Overview

This benchmark evaluates Large Language Models (LLMs) on their ability to play the strategic board game Diplomacy, with a specific focus on measuring both **performance** (how well the model plays) and **steerability** (how responsive the model is to strategic prompt modifications). Each model plays as France against six identical opponent models (Mistral Devstral-Small) across multiple game iterations.

## Performance Score Calculation

### Game Score Formula

The benchmark uses a modified DiploBench scoring system that rewards both survival and victory:

- **Solo Winner**: `max_year + (max_year - win_year) + 18`
  - Where `win_year` is when the power reached 18+ supply centers
  - Rewards faster victories with bonus points

- **Survivor** (active at game end): `max_year + final_supply_centers`
  - Rewards territorial control for nations that survive to the end

- **Eliminated**: `elimination_year`
  - Year of elimination (relative to 1900)

**Key parameters:**
- `max_year`: Maximum game year (default: 1925) minus 1900 = 25
- All years are normalized by subtracting 1900
- Supply centers range from 0-34 (total centers on the board)

### Aggregation

Performance is calculated as the **mean game score across all iterations** for the test model playing as France. In the production benchmark:
- 20 game iterations per experiment
- Games run to 1925 (25 years of gameplay)
- Parallel execution for efficiency

### Why These Metrics Matter

The game score formula captures:
- **Territorial expansion**: Higher supply center counts indicate successful negotiation and military strategy
- **Survival**: Avoiding elimination is critical in Diplomacy
- **Victory speed**: Faster solo victories earn bonus points
- **Competitive balance**: Scores are comparable across different game lengths

## Steerability Score Calculation

### Definition

Steerability quantifies how much a model's behavior changes in response to modified strategic prompts. We compare two prompt variants:

1. **Baseline prompts** (`prompts_benchmark`): Standard strategic guidance emphasizing balanced diplomacy
2. **Aggressive prompts** (`prompts_hold_reduction_v3`): Modified prompts encouraging more aggressive territorial expansion and reduced defensive holds

### Calculation Method

```
Steerability = Performance_aggressive - Performance_baseline
```

Where performance is measured by mean game score across all iterations.

### Interpretation

- **Positive steerability** (+): Model performs better with aggressive prompts, indicating successful behavioral adaptation
- **Negative steerability** (−): Model performs worse with aggressive prompts, suggesting either:
  - Failure to adapt to prompt modifications
  - Over-aggressive behavior that undermines diplomatic strategy
- **Near-zero steerability** (~0): Model behavior is largely invariant to prompt changes

### Why Steerability Matters

Steerability is a critical but under-explored dimension of LLM capability:
- **Controllability**: Models should adapt their strategy when users provide different instructions
- **Prompt sensitivity**: Measures whether models genuinely understand strategic guidance vs. memorized patterns
- **Real-world utility**: Production systems need models that can be steered toward desired behaviors
- **Safety implications**: Models that can't be steered may be difficult to align or control

## Experimental Setup

### Game Configuration
- **Test position**: France (3rd position in 7-nation setup)
- **Opponent model**: Mistral Devstral-Small (all 6 opposing nations)
- **Max year**: 1925 (production) / 1901 (test mode)
- **Iterations**: 20 games per experiment (production) / 3 games (test mode)
- **Parallel workers**: 20 concurrent games (production) / 3 (test mode)

### Prompt Variants
- **Baseline**: `ai_diplomacy/prompts/prompts_benchmark`
  - Standard diplomatic and strategic guidance
  - Balanced approach to offense and defense

- **Aggressive**: `ai_diplomacy/prompts/prompts_hold_reduction_v3`
  - Emphasis on territorial expansion
  - Reduction in defensive hold orders
  - More assertive negotiation stance

### Test Model Configuration
- Models are inserted at position 2 (France) in the power order
- Order: Austria, England, **France**, Germany, Italy, Russia, Turkey
- All opponent positions use the same baseline opponent model

## Data Collection

### Per-Game Metrics
For each game iteration, the system records:
- Supply center progression by phase
- Order types and success rates (moves, holds, supports, convoys)
- Diplomatic messaging patterns
- LLM response statistics and errors
- Game outcome and final rankings

### Aggregated Analysis
The `statistical_game_analysis` module produces:
- **Game-level CSV**: Per-game summaries with 88 metrics including game score, final supply centers, order statistics, and messaging patterns
- **Phase-level CSV**: Turn-by-turn state including supply centers, military units, relationships, and sentiment
- **Combined analysis**: Aggregated statistics across all game iterations

### Performance Tracking
- Console logs for each benchmark run
- Metadata files documenting model IDs and configuration
- Symlinks in `leaderboard/` directory for experiment discovery
- Automated comparison visualizations

## Limitations and Considerations

### Statistical Validity
- Sample size: 20 games per condition provides reasonable statistical power but may not capture rare outcomes
- Opponent variance: Using a single opponent model reduces confounding factors but may not generalize to diverse opponents

### Prompt Engineering
- Steerability measurement is sensitive to prompt design quality
- "Aggressive" may not be the optimal prompt modification for all models
- Some models may benefit from different strategic guidance

### Game Complexity
- Diplomacy involves significant stochasticity from opponent behavior
- Alliance formation and betrayal introduce non-deterministic outcomes
- Long game duration (1901-1925) increases variance in results

### Measurement Scope
- Benchmark focuses on win condition (supply centers) rather than other strategic dimensions
- Does not explicitly measure negotiation quality, deception capability, or long-term planning
- Performance as a single nation (France) may not generalize to other starting positions

### Technical Constraints
- Model errors and API failures can affect game completion rates
- Longer generation times may indicate different reasoning patterns but are not directly scored
- Prompt formatting differences across model providers may introduce artifacts
