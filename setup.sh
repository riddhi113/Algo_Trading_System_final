#!/bin/bash
# setup.sh — One-time setup for the Mini Algo Trading System
# Run this ONCE before running the project for the first time.
# Usage: bash setup.sh

set -e  # Exit immediately on any error

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*"; exit 1; }

info "Mini Algo Trading System — Setup"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
info "Project root: $SCRIPT_DIR"

# Check Python 3
info "Checking Python 3..."
if ! command -v python3 &>/dev/null; then
    error "Python 3 is not installed. Install it with: sudo apt install python3 python3-pip python3-venv"
fi
PYTHON_VER=$(python3 --version)
success "Found $PYTHON_VER"

# Check pip
info "Checking pip..."
if ! python3 -m pip --version &>/dev/null; then
    warn "pip not found. Attempting to install..."
    python3 -m ensurepip --upgrade || error "Could not install pip. Run: sudo apt install python3-pip"
fi
success "pip is available."

# Create virtual environment
VENV_DIR="$SCRIPT_DIR/.venv"
if [ -d "$VENV_DIR" ]; then
    warn "Virtual environment already exists at .venv — skipping creation."
else
    info "Creating virtual environment at .venv ..."
    python3 -m venv "$VENV_DIR" || error "Failed to create virtual environment. Install: sudo apt install python3-venv"
    success "Virtual environment created."
fi

# Activate venv
info "Activating virtual environment..."
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
success "Virtual environment activated."

# Upgrade pip inside venv
info "Upgrading pip inside venv..."
pip install --upgrade pip --quiet
success "pip upgraded."

# Install project dependencies
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"
if [ ! -f "$REQUIREMENTS" ]; then
    error "requirements.txt not found at $REQUIREMENTS"
fi

info "Installing dependencies from requirements.txt..."
pip install -r "$REQUIREMENTS"
success "All dependencies installed."

# Make run.sh executable
if [ -f "$SCRIPT_DIR/run.sh" ]; then
    chmod +x "$SCRIPT_DIR/run.sh"
    success "run.sh is now executable."
fi

success "Setup complete. Run the project with: ./run.sh"
