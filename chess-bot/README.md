# Chess Bot

An AI chess opponent with variable difficulty powered by the Stockfish engine.

**ELO Levels:** 800 (Beginner) · 1200 (Intermediate) · 1600 (Advanced) · 2000 (Expert)

## Quick Start

```bash
bash setup.sh
source .venv/bin/activate
python app.py
# → open http://localhost:5001
```

## Requirements

- Python 3.10+
- Stockfish engine (`brew install stockfish` on Mac)

## Manual Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
brew install stockfish      # macOS
# apt-get install stockfish  # Ubuntu/Debian

python app.py
```

## Custom Stockfish Path

If Stockfish is not on your PATH:

```bash
export STOCKFISH_PATH=/path/to/stockfish
python app.py
```

## API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/new_game` | Start a new game |
| POST | `/api/move` | Submit player move, get engine reply |
| POST | `/api/hint` | Get the best move for the current position |

## Running on the Club's RTX Machine (necron)

SSH in via Tailscale and run:

```bash
cd ~/projects/chess-bot
source .venv/bin/activate
STOCKFISH_PATH=$(which stockfish) python app.py
```

Access from any device on Tailscale at `http://necron:5001`

## Tech Stack

- **Backend:** Python · Flask · python-chess · Stockfish UCI
- **Frontend:** chessboard.js · chess.js · vanilla JS
