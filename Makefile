# AI Diplomacy Makefile
# Simplifies setup and common operations

.PHONY: help install install-dev setup-cicero test run-game run-animation clean

# Default target - show help
help:
	@echo "AI Diplomacy - Available commands:"
	@echo "  make install        - Install base dependencies"
	@echo "  make install-dev    - Install development dependencies"
	@echo "  make setup-cicero   - Set up Cicero environment (full model, x86_64 Linux recommended)"
	@echo "  make test-cicero    - Test Cicero integration"
	@echo "  make run-game       - Run a test game (1 year, no negotiation)"
	@echo "  make run-animation  - Start the animation server"
	@echo "  make clean          - Clean up generated files"

# Install base dependencies
install:
	pip install -r requirements.txt
	@echo "✓ Base dependencies installed"

# Install development dependencies
install-dev: install
	pip install -r requirements_dev.txt
	@echo "✓ Development dependencies installed"

# Set up Cicero environment (full model - x86_64 Linux recommended)
setup-cicero:
	@echo "Setting up Cicero environment..."
	@if [ ! -d "diplomacy_cicero" ]; then \
		echo "Error: diplomacy_cicero not found. Run: git submodule init && git submodule update"; \
		exit 1; \
	fi
	@echo "Creating conda environment..."
	conda create -n cicero_env python=3.8 -y
	@echo "Installing Cicero dependencies..."
	cd diplomacy_cicero && conda run -n cicero_env pip install -r requirements.txt
	@echo "Building Cicero components..."
	cd diplomacy_cicero && conda run -n cicero_env make
	@echo "✓ Cicero environment ready (remember to download model weights)"

# Test Cicero integration (WILL FAIL without full setup)
test-cicero:
	@echo "Testing REAL Cicero integration (NO FALLBACKS)..."
	@python -c "from ai_diplomacy.clients import load_model_client; \
		try: \
			client = load_model_client('cicero'); \
			print('✓ REAL Cicero loaded successfully!'); \
		except Exception as e: \
			print(f'✗ REAL Cicero FAILED: {e}'); \
			exit(1)"

# Run a test game
run-game:
	python lm_game.py --max_year 1902 --num_negotiation_rounds 0

# Run game with planning
run-game-planning:
	python lm_game.py --max_year 1903 --num_negotiation_rounds 2 --planning_phase

# Start animation server
run-animation:
	@echo "Starting animation server..."
	cd ai_animation && npm install && npm run dev

# Clean up generated files
clean:
	rm -rf results/*
	rm -rf __pycache__
	rm -rf ai_diplomacy/__pycache__
	rm -rf *.egg-info
	find . -name "*.pyc" -delete
	find . -name ".DS_Store" -delete
	@echo "✓ Cleaned up generated files"

# Initialize git submodules
init-submodules:
	git submodule init
	git submodule update
	@echo "✓ Submodules initialized"

# Update all dependencies
update-deps:
	pip install --upgrade -r requirements.txt
	cd ai_animation && npm update
	@echo "✓ Dependencies updated"

# Run analysis on the latest game
analyze-latest:
	@LATEST=$$(ls -t results | grep "_FULL_GAME" | head -1); \
	if [ -z "$$LATEST" ]; then \
		echo "No completed games found"; \
	else \
		echo "Analyzing $$LATEST..."; \
		python analyze_game_moments_llm_new.py results/$$LATEST; \
	fi

# Generate statistics from all games
stats:
	python analyze_game_results.py
	@echo "✓ Statistics saved to model_power_statistics.csv"

# Development shortcuts
dev: install-dev test-cicero
	@echo "✓ Development environment ready"

# Quick test with mock data
test-quick:
	python lm_game.py --max_year 1901 --num_negotiation_rounds 0 --models "cicero,gemini-2.0-flash,gemini-2.0-flash,gemini-2.0-flash,gemini-2.0-flash,gemini-2.0-flash,gemini-2.0-flash"