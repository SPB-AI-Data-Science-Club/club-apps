import os
import shutil
import chess
import chess.engine
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Find Stockfish — check env var, system PATH, then common install locations
ENGINE_PATH = (
    os.environ.get("STOCKFISH_PATH") or
    shutil.which("stockfish") or
    "/usr/games/stockfish"
)

ELO_LEVELS = {
    1320: {"name": "Beginner",     "desc": "The engine's gentlest setting."},
    1600: {"name": "Intermediate", "desc": "Casual club-level strength."},
    2000: {"name": "Advanced",     "desc": "Strong tournament player."},
    2500: {"name": "Expert",       "desc": "Near master-level. Good luck."},
}

THINK_TIME = {1320: 0.05, 1600: 0.15, 2000: 0.3, 2500: 0.5}


def engine_move(fen: str, elo: int) -> tuple:
    """Return (uci_str, san_str) for Stockfish's chosen move."""
    board = chess.Board(fen)
    with chess.engine.SimpleEngine.popen_uci(ENGINE_PATH) as engine:
        # Clamp ELO to the range this Stockfish binary actually accepts
        elo_opt  = engine.options.get("UCI_Elo")
        min_elo  = int(elo_opt.min) if elo_opt and elo_opt.min is not None else 1320
        max_elo  = int(elo_opt.max) if elo_opt and elo_opt.max is not None else 3190
        clamped  = max(min_elo, min(max_elo, elo))
        engine.configure({"UCI_LimitStrength": True, "UCI_Elo": clamped})
        result = engine.play(board, chess.engine.Limit(time=THINK_TIME.get(elo, 0.1)))
        uci = result.move.uci()
        san = board.san(result.move)
        return uci, san


def board_status(board: chess.Board) -> dict:
    if not board.is_game_over():
        return {"game_over": False}
    result = board.result()
    reason = "checkmate" if board.is_checkmate() else \
             "stalemate" if board.is_stalemate() else \
             "insufficient material" if board.is_insufficient_material() else \
             "repetition" if board.is_repetition() else \
             "fifty-move rule" if board.is_fifty_moves() else "draw"
    winner = None
    if result == "1-0":
        winner = "White"
    elif result == "0-1":
        winner = "Black"
    return {"game_over": True, "result": result, "winner": winner, "reason": reason}


@app.route("/")
def index():
    return render_template("index.html", elo_levels=ELO_LEVELS)


@app.route("/api/new_game", methods=["POST"])
def new_game():
    data = request.get_json(force=True)
    elo = int(data.get("elo", 1600))
    player_color = data.get("color", "white")

    board = chess.Board()
    resp = {"fen": board.fen(), "elo": elo, "player_color": player_color, "game_over": False}

    if player_color == "black":
        uci, san = engine_move(board.fen(), elo)
        board.push(chess.Move.from_uci(uci))
        resp["fen"]          = board.fen()
        resp["engine_move"]  = uci
        resp["engine_san"]   = san

    return jsonify(resp)


@app.route("/api/move", methods=["POST"])
def make_move():
    data     = request.get_json(force=True)
    fen      = data.get("fen")
    move_uci = data.get("move")
    elo      = int(data.get("elo", 1600))

    board = chess.Board(fen)

    try:
        move = chess.Move.from_uci(move_uci)
        if move not in board.legal_moves:
            move = chess.Move.from_uci(move_uci + "q")   # default promotion to queen
        if move not in board.legal_moves:
            return jsonify({"error": "Illegal move"}), 400
        board.push(move)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    status = board_status(board)
    if status["game_over"]:
        return jsonify({"fen": board.fen(), **status})

    uci, san = engine_move(board.fen(), elo)
    board.push(chess.Move.from_uci(uci))
    status = board_status(board)

    return jsonify({
        "fen":          board.fen(),
        "engine_move":  uci,
        "engine_san":   san,
        **status,
    })


@app.route("/api/hint", methods=["POST"])
def get_hint():
    """Return the best move at full strength for learning."""
    data  = request.get_json(force=True)
    fen   = data.get("fen")
    board = chess.Board(fen)
    if board.is_game_over():
        return jsonify({"error": "Game is over"}), 400
    with chess.engine.SimpleEngine.popen_uci(ENGINE_PATH) as engine:
        result = engine.play(board, chess.engine.Limit(time=0.5))
        return jsonify({"hint": result.move.uci()})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
