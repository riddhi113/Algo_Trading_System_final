#!/bin/bash
# =============================================================
# run.sh — Run the entire Mini Algo Trading System
# Step 1: Run the backtest pipeline
# Step 2: Start the FastAPI server
#
# Usage: ./run.sh
#        ./run.sh --download   (force re-download market data first)
# =============================================================

set -e

# Colours
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*"; exit 1; }

# Resolve project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
export PYTHONPATH="$SCRIPT_DIR"

info "Mini Algo Trading System — Starting..."

# Check setup was done
VENV_DIR="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    error "Setup not done. Please run: bash setup.sh"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"
success "Virtual environment ready."

# Step 1: Run the Backtest Pipeline
info "Running backtest pipeline..."
python3 mini_algo_trading/main.py "$@"
success "Backtest complete."

# Step 2: Start FastAPI Server
if lsof -ti:8080 &>/dev/null; then
    info "Port 8080 in use — stopping existing process."
    kill -9 $(lsof -ti:8080) 2>/dev/null || true
    sleep 1
fi

info "Starting FastAPI server at http://127.0.0.1:8080"
info "Docs at http://127.0.0.1:8080/docs — Press Ctrl+C to stop."
uvicorn mini_algo_trading.api.server:app --host 127.0.0.1 --port 8080 --reload
