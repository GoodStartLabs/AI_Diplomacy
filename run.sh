#!/bin/bash
#SBATCH --job-name=diplomo        # Job name
#SBATCH --output=diplomo.log      # Standard output and error log
#SBATCH --time=12:00:00          # Time limit hh:mm:ss
#SBATCH --gres=gpu:0           # Request 1 GPU (remove if not needed)

# note the summaries aren't actually used so the model doesn't matter here

# Set seeds
seeds=(0 1 2 3 4)

for seed in "${seeds[@]}"; do
    python3 lm_game.py \
        --max_year 1910 \
        --num_negotiation_rounds 0 \
        --seed "$seed"
done