#!/bin/bash
set -e

echo "=== Chess Bot Setup ==="

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install Stockfish engine
if command -v brew &>/dev/null; then
  echo "Installing Stockfish via Homebrew..."
  brew install stockfish
elif command -v apt-get &>/dev/null; then
  echo "Installing Stockfish via apt..."
  sudo apt-get install -y stockfish
else
  echo "WARNING: Could not auto-install Stockfish."
  echo "Download from https://stockfishchess.org/download/ and set:"
  echo "  export STOCKFISH_PATH=/path/to/stockfish"
fi

echo ""
echo "=== Setup complete! ==="
echo "Run with:  source .venv/bin/activate && python app.py"
echo "Then open: http://localhost:5001"
