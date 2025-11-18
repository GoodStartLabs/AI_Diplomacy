# Scoring Methodology Explanation

This document explains the two different scoring systems used in the AI Diplomacy benchmark and how they are applied across different metrics and visualizations.

## Two Scoring Systems Used

### 1. Raw Supply Center Count

**What it is:** The simple count of supply centers a power controls at the end of the game.

**How it's calculated:**
- Directly counts the number of supply centers (territories that can produce units) owned by a power when the game ends
- Range: 0-34 supply centers (theoretical maximum, though 18 is winning threshold)
- No bonuses or penalties applied

**Example:**
- France ends game with 11 supply centers → Raw SC score = 11
- France eliminated with 0 supply centers → Raw SC score = 0
- France wins solo with 18+ supply centers → Raw SC score = 18-34

**When it's used:**
- Supplementary metric in both CSV files for transparency
- Useful for understanding territorial control independent of game outcome timing
- Easier to interpret for quick comparisons

### 2. Custom Game Score (DiploBench-style)

**What it is:** A sophisticated scoring system that rewards survival, victory speed, and penalizes early elimination.

**How it's calculated:**

The formula depends on the game outcome:

#### Case 1: Solo Winner (18+ supply centers)
```
score = max_year + (max_year - win_year) + 18
```
- `max_year`: Maximum game year (typically 1925) minus 1900 = 25
- `win_year`: Year when 18 supply centers were reached minus 1900
- The `(max_year - win_year)` term rewards faster victories
- The `+ 18` bonus represents the solo win achievement

**Example:**
- Game ends in 1925 (max_year = 25)
- France wins solo in 1920 (win_year = 20)
- Score = 25 + (25 - 20) + 18 = 25 + 5 + 18 = **48 points**
- If France won in 1915 instead: 25 + 10 + 18 = **53 points** (faster win = higher score)

#### Case 2: Survivor (active at game end, no solo winner)
```
score = max_year + final_supply_centers
```

**Example:**
- Game ends in 1925 (max_year = 25)
- France survives with 11 supply centers
- Score = 25 + 11 = **36 points**
- If France had 8 supply centers: 25 + 8 = **33 points**

#### Case 3: Eliminated (0 supply centers before game end)
```
score = elimination_year
```
- `elimination_year`: Year of elimination minus 1900

**Example:**
- France eliminated in 1910
- Score = 1910 - 1900 = **10 points**
- If eliminated in 1905: score = **5 points** (earlier elimination = lower score)

#### Case 4: Lost to Solo Winner (still had units but someone else won)
```
score = win_year
```
- Same as elimination year but marked differently

**Key Properties:**
- **Winning range:** Typically 42-70+ points (varies by win speed)
- **Survival range:** Typically 28-42 points (25 + low SCs to 25 + 17 SCs)
- **Elimination range:** Typically 5-24 points (early elimination to late elimination)

## Which Score is Used Where

### France Bar Chart Visualization (`france_scores_bar.png`)

**Score used:** Custom Game Score (DiploBench-style)

**Rationale:**
- The bar chart is titled "Average Game Score" and uses the `game_score` column
- This provides a more nuanced view of performance that accounts for survival time and victory quality
- Better differentiates between "survived weakly" vs "eliminated late" vs "won fast"

**Code reference:** `/Users/alxdfy/Documents/mldev/AI_Diplomacy/analyze_diplomacy_performance_v3_textured.py`, lines 595-596

### Overall Performance Leaderboard (`overall_performance.csv`)

**Primary metric:** Custom Game Score (columns: `france_mean_score`, `france_median_score`)

**Secondary metric:** Raw Supply Centers (columns: `raw_supply_centers_mean`, `raw_supply_centers_median`)

**Why both are included:**
- **Game Score** is the primary ranking metric because it better captures overall gameplay quality
- **Raw Supply Centers** provides context and transparency about territorial control
- Together they give a complete picture: a model might have high territorial control but poor survival time, or vice versa

**Example interpretation:**
- Model A: game_score = 45, raw_sc = 15 → Likely survived to 1925 with moderate territory
- Model B: game_score = 15, raw_sc = 8 → Likely eliminated early despite having reasonable territory at that point
- Model C: game_score = 55, raw_sc = 19 → Likely won solo or dominated late game

### Steerability Leaderboard (`steerability.csv`)

**Primary metric:** Custom Game Score difference (columns: `steerability_score`, `steerability_percentage`)

**Secondary metric:** Raw Supply Center difference (columns: `steerability_score_raw`, `steerability_percentage_raw`)

**Why both are included:**
- **Game Score steerability** measures the true impact of aggressive prompting on overall performance
- **Raw SC steerability** shows the pure territorial control difference
- Models can be steerable in different ways:
  - High game score steerability + low raw SC steerability → Better survival/timing, not just territory
  - High raw SC steerability + lower game score steerability → More territory but possibly worse timing

**Example interpretation:**
- Model X: steerability_score = +15, steerability_score_raw = +10
  - Aggressive prompting adds 15 game score points and 10 supply centers
  - The difference (15 vs 10) suggests better survival timing in addition to more territory

- Model Y: steerability_score = -5, steerability_score_raw = -2
  - Aggressive prompting actually hurts performance (negative steerability)
  - Loses 5 game score points and 2 supply centers
  - Model performs better with neutral/baseline prompting

## Why Both Scores Matter

### Complementary Insights

1. **Game Score** captures:
   - Victory quality (how fast)
   - Survival duration (eliminated when)
   - Overall strategic success
   - Risk-reward tradeoffs

2. **Raw Supply Centers** captures:
   - Territorial expansion ability
   - Pure diplomatic/military success
   - Easier to interpret and compare
   - Independent of timing considerations

### Research Value

Having both metrics allows researchers to:
- **Identify interesting patterns:** A model might be excellent at gaining territory (high raw SC) but poor at survival (low game score)
- **Understand steerability mechanisms:** Does aggressive prompting lead to more territory, better timing, or both?
- **Compare fairly:** Different use cases might prioritize different aspects of performance
- **Validate results:** If both metrics agree, it strengthens confidence in the findings

### Example Use Cases

**Use Case 1: Deployment Decision**
- If you want a model for long games → prioritize `game_score` (measures endurance)
- If you want a model for territorial expansion → consider `raw_supply_centers` (measures conquest)

**Use Case 2: Steerability Analysis**
- High `steerability_score` but low `steerability_score_raw` → Model becomes more strategic with timing
- Similar values → Steerability primarily affects territorial control
- Negative values → Model responds poorly to aggressive prompting

## Column Definitions

### overall_performance.csv

| Column | Definition |
|--------|------------|
| `model_name` | Base name of the model being benchmarked |
| `best_variant` | Which variant (baseline or aggressive) performed better |
| `france_mean_score` | Average Custom Game Score across all games (primary ranking metric) |
| `france_median_score` | Median Custom Game Score across all games (robust to outliers) |
| `raw_supply_centers_mean` | Average raw supply center count at game end |
| `raw_supply_centers_median` | Median raw supply center count at game end |
| `france_win_rate` | Percentage of games won (18+ supply centers) |
| `total_games` | Number of games played |
| `avg_phase_time_minutes` | Average time per game phase in minutes |
| `error_rate` | Percentage of API/LLM errors during gameplay |

**Sorting:** Descending by `france_mean_score` (higher is better)

### steerability.csv

| Column | Definition |
|--------|------------|
| `model_name` | Base name of the model being analyzed |
| `baseline_mean_score` | Average Custom Game Score for baseline (neutral) prompting |
| `aggressive_mean_score` | Average Custom Game Score for aggressive prompting |
| `baseline_raw_supply_centers` | Average raw supply centers for baseline prompting |
| `aggressive_raw_supply_centers` | Average raw supply centers for aggressive prompting |
| `steerability_score` | Difference in Custom Game Score (aggressive - baseline) |
| `steerability_percentage` | Percentage change in Custom Game Score ((aggressive - baseline) / baseline * 100) |
| `steerability_score_raw` | Difference in raw supply centers (aggressive - baseline) |
| `steerability_percentage_raw` | Percentage change in raw supply centers ((aggressive - baseline) / baseline * 100) |
| `direction` | "positive" if aggressive improves performance, "negative" if it hurts |
| `baseline_games` | Number of baseline games played |
| `aggressive_games` | Number of aggressive games played |

**Sorting:** Descending by `steerability_score` (higher positive values = more steerable toward aggression)

## Summary

- **Primary Metric:** Custom Game Score (DiploBench-style) - used for all rankings and bar chart
- **Secondary Metric:** Raw Supply Centers - provided for transparency and complementary analysis
- **France Bar Chart:** Uses Custom Game Score
- **Steerability:** Measures both metrics to understand different aspects of prompt influence
- **Both metrics together** provide a complete picture of model performance and behavior

For questions about the scoring implementation, see:
- Game score calculation: `/Users/alxdfy/Documents/mldev/AI_Diplomacy/experiment_runner/analysis/summary.py` (lines 77-118)
- Data collection: `/Users/alxdfy/Documents/mldev/AI_Diplomacy/analyze_diplomacy_performance_v3_textured.py` (lines 577-611)
