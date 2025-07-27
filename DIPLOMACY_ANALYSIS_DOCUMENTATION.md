# AI Diplomacy Analysis Documentation

## Executive Summary

This repository contains comprehensive analysis tools for evaluating AI model performance in Diplomacy games. Through hundreds of experiments with 62+ unique AI models over 4000+ games, we've developed insights into how AI agents have evolved from passive, defensive play to active, strategic gameplay.

## Core Research Questions

### 1. Evolution of AI Strategy
**Question**: Have AI models evolved from passive (hold-heavy) to active (move/support/convoy) strategies?

**Finding**: Yes. Our analysis shows a clear trend from ~80% hold orders in early models to <40% holds in recent models, demonstrating strategic evolution.

### 2. Success Rate Importance
**Question**: Do active orders correlate with better performance?

**Finding**: Models with higher success rates on active orders (moves, supports, convoys) consistently outperform passive models. Top performers achieve 70-80% success rates on active orders.

### 3. Scaling Challenges
**Question**: Does performance degrade as unit count increases or games progress?

**Finding**: Yes. Most models show degraded performance when controlling 10+ units, confirming the complexity scaling hypothesis. Only a few models (o3, gpt-4.1) maintain performance at scale.

## Data Architecture

### Game Data Structure
```
results/
├── YYYYMMDD_HHMMSS_description/
│   ├── lmvsgame.json          # Complete game data (REQUIRED for completed games)
│   ├── llm_responses.csv      # Model responses and decisions (SOURCE OF TRUTH)
│   ├── overview.jsonl         # Game metadata
│   └── general_game.log       # Detailed game log
```

### Key Data Formats

#### New Format (2024+)
- Results stored in `order_results` field, keyed by power
- Success indicated by `"result": "success"`
- Orders categorized by type (hold, move, support, convoy)

#### Old Format (Pre-2024)
- Orders in `orders` field, results in `results` field
- Results keyed by unit location (e.g., "A PAR", "F LON")
- Success indicated by empty value (empty list, empty string, or None)
- Non-empty values indicate failure types: "bounce", "dislodged", "void"

## Analysis Pipeline

### 1. Data Collection
- **Source of Truth**: `llm_responses.csv` files contain actual model names
- **Completed Games Only**: Only analyze games with `lmvsgame.json` present
- **Model Name Extraction**: Direct from CSV, no normalization needed

### 2. Performance Metrics

#### Order Types
- **Hold**: Defensive/passive orders
- **Move**: Unit movement orders
- **Support**: Supporting other units
- **Convoy**: Naval convoy operations

#### Key Metrics
- **Active Order Percentage**: (Move + Support + Convoy) / Total Orders
- **Success Rate**: Successful Active Orders / Total Active Orders
- **Unit Scaling**: Performance vs number of units controlled
- **Temporal Evolution**: Changes over game decades (1900s, 1910s, etc.)

### 3. Visualization Suite

#### High-Quality Models Analysis
- Focus on models with 500+ active orders and 200+ phases
- Dual visualization: success rates + order composition
- Highlights top performers with substantial gameplay data

#### Success Rate Charts
- All models with 50+ active orders
- Sorted by performance
- Color-coded by activity level

#### Active Order Percentage
- Shows evolution from passive to active play
- Top 30 most active models
- Clear threshold visualization

#### Order Distribution Heatmap
- Visual matrix of order type percentages
- Models sorted by hold percentage
- Clear patterns of strategic approaches

#### Temporal Analysis
- Active order percentage over game decades
- Success rate evolution
- Shows learning and adaptation patterns

#### Additional Visualizations
- Power distribution across games
- Physical timeline of experiments
- Model comparison matrix
- Phase and game participation counts

## Technical Implementation

### Critical Bug Fixes

#### 1. Old Format Success Calculation
**Problem**: Old games store results by unit location, not power name
**Solution**: Extract unit location from order string and lookup results

```python
# Extract unit location (e.g., "A PAR - PIC" -> "A PAR")
parts = order_str.strip().split(' ')
if len(parts) >= 2 and parts[0] in ['A', 'F']:
    unit_loc = f"{parts[0]} {parts[1]}"

# Check results using unit location
if unit_loc in results_dict:
    result_value = results_dict[unit_loc]
    if isinstance(result_value, list) and len(result_value) == 0:
        # Empty list means success
```

#### 2. CSV as Source of Truth
**Problem**: Model names have various prefixes in different files
**Solution**: Use only CSV files for model names, ignore prefixes

### Best Practices

#### Data Processing
1. Always check for `lmvsgame.json` to identify completed games
2. Read entire CSV files, not just first N rows
3. Handle both old and new game formats
4. Use pandas for efficient CSV processing

#### Visualization Design
1. **Colors**: Use colorblind-friendly palette
2. **Labels**: Include counts and percentages
3. **Sorting**: Always sort for clarity (by performance, activity, etc.)
4. **Filtering**: Apply minimum thresholds for statistical significance
5. **Annotations**: Add context with titles and axis labels

## Key Findings

### Model Performance Tiers

#### Tier 1: Elite Performers (>70% success rate)
- o3 (78.8%)
- gpt-4.1 (79.6%)
- x-ai/grok-4 (74.2%)

#### Tier 2: Strong Performers (60-70% success rate)
- gemini-2.5-flash (71.8%)
- deepseek-reasoner (68.5%)
- Various llama models

#### Tier 3: Developing Models (<60% success rate)
- Earlier versions and experimental models
- Often show high activity but lower success

### Strategic Evolution Patterns
1. **Early Phase**: High hold percentage (70-80%), defensive play
2. **Middle Phase**: Increasing moves and supports (50-60% active)
3. **Current Phase**: Sophisticated multi-order strategies (60-80% active)

### Scaling Insights
- Performance peak: 4-8 units
- Degradation point: 10+ units
- Exception models: o3, gpt-4.1 maintain performance

## Usage Guide

### Running the Analysis
```bash
python diplomacy_unified_analysis_final.py [days]
```
- `days`: Number of days to analyze (default: 30)

### Output Structure
```
visualization_results/
└── csv_only_enhanced_TIMESTAMP_Ndays/
    ├── 00_high_quality_models.png
    ├── 01_success_rates_part1.png
    ├── 02_active_order_percentage_sorted.png
    ├── 03_order_distribution_heatmap.png
    ├── 04_temporal_analysis_by_decade.png
    ├── 05_power_distribution.png
    ├── 06_physical_dates_timeline.png
    ├── 07_phase_and_game_counts.png
    ├── 08_model_comparison_heatmap.png
    └── ANALYSIS_SUMMARY.md
```

## Future Directions

### Potential Enhancements
1. **Real-time Analysis**: Stream processing for ongoing games
2. **Strategic Pattern Recognition**: ML-based strategy classification
3. **Cross-Model Learning**: Identify successful strategy transfers
4. **Performance Prediction**: Forecast model performance based on early game behavior

### Research Questions
1. Do models learn from opponent strategies?
2. Can we identify "breakthrough" moments in model development?
3. What strategies emerge at different unit count thresholds?
4. How do models adapt to different power positions?

## Conclusion

This analysis framework provides comprehensive insights into AI Diplomacy performance, revealing clear evolution from passive to active play and identifying key performance factors. The visualization suite enables publication-quality presentations of these findings, suitable for academic conferences like AAAI.

The key achievement is demonstrating that modern AI models have developed sophisticated Diplomacy strategies, moving beyond simple defensive play to complex multi-unit coordination with high success rates.