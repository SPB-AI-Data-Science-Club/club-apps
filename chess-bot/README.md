# Chess Bot

Play chess against Stockfish at calibrated strength, from 1320 to 2500 ELO.

## Features

- Four difficulty levels using Stockfish's `UCI_LimitStrength` and `UCI_Elo` options, clamped to the range the engine binary actually supports
- Play as white or black; the engine opens when you take black
- Drag-and-drop board with legal-move validation on both client and server
- Algebraic move history and a full-strength hint engine
- Engine-thinking lock so the board cannot be touched mid-computation

## How it works

The Flask backend drives Stockfish over the UCI protocol with `python-chess`. Each move request carries the current FEN; the server validates the player's move, asks the engine for a reply at the configured strength, and returns the new position plus the move in standard algebraic notation. The client (chessboard.js + chess.js) never trusts its own state for rules: promotion, checkmate, and draw detection all come from the server.

## API

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/new_game` | Start a new game |
| POST | `/api/move` | Submit player move, get engine reply |
| POST | `/api/hint` | Get the best move for the current position |

## Stack

Python, Flask, python-chess, Stockfish, chessboard.js, chess.js

## Local development

```bash
pip install flask python-chess
# install stockfish (apt install stockfish / brew install stockfish)
python app.py
```

Set `STOCKFISH_PATH` if the binary is not on your PATH.
