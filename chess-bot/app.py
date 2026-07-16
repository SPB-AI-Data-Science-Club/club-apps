import os
import random
import shutil
import chess
import chess.engine
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Find Stockfish: env var, system PATH, then the usual install location
ENGINE_PATH = (
    os.environ.get("STOCKFISH_PATH") or
    shutil.which("stockfish") or
    "/usr/games/stockfish"
)

# The slider runs 100..3600. Stockfish's calibrated range is narrower,
# so the ends are emulated:
#   below ENGINE_MIN_ELO  -> engine at minimum strength, blended with
#                            random legal moves (more random = weaker)
#   above ENGINE_MAX_ELO  -> limiter off, full engine strength
ENGINE_MIN_ELO = 1320
ENGINE_MAX_ELO = 3190
SLIDER_MIN     = 100
SLIDER_MAX     = 3600

TERMINATION_LABELS = {
    chess.Termination.CHECKMATE:             "checkmate",
    chess.Termination.STALEMATE:             "stalemate",
    chess.Termination.INSUFFICIENT_MATERIAL: "insufficient material",
    chess.Termination.SEVENTYFIVE_MOVES:     "the 75-move rule",
    chess.Termination.FIVEFOLD_REPETITION:   "fivefold repetition",
    chess.Termination.FIFTY_MOVES:           "the fifty-move rule",
    chess.Termination.THREEFOLD_REPETITION:  "threefold repetition",
}


def clamp_elo(elo: int) -> int:
    return max(SLIDER_MIN, min(SLIDER_MAX, elo))


def think_time(elo: int) -> float:
    """Weaker settings answer fast; full strength thinks longer."""
    if elo >= ENGINE_MAX_ELO:
        return 0.6
    return 0.05 + 0.35 * (elo - SLIDER_MIN) / (ENGINE_MAX_ELO - SLIDER_MIN)


def eval_to_cp(score: chess.engine.PovScore) -> int:
    """White-POV centipawns; mate scores saturate at +/-10000."""
    cp = score.white().score(mate_score=10000)
    return max(-10000, min(10000, cp if cp is not None else 0))


def engine_move(fen: str, elo: int) -> tuple:
    """Return (uci, san, eval_cp) for the engine's reply at slider strength."""
    elo   = clamp_elo(elo)
    board = chess.Board(fen)

    with chess.engine.SimpleEngine.popen_uci(ENGINE_PATH) as engine:
        if elo >= ENGINE_MAX_ELO:
            engine.configure({"UCI_LimitStrength": False})
        else:
            engine.configure({
                "UCI_LimitStrength": True,
                "UCI_Elo": max(ENGINE_MIN_ELO, elo),
            })

        result = engine.play(board, chess.engine.Limit(time=think_time(elo)))
        move = result.move

        # Below the engine's calibrated floor, mix in random legal moves.
        # At 100 ELO most moves are random; at 1319 almost none are.
        if elo < ENGINE_MIN_ELO:
            p_random = (ENGINE_MIN_ELO - elo) / (ENGINE_MIN_ELO - SLIDER_MIN) * 0.85
            if random.random() < p_random:
                move = random.choice(list(board.legal_moves))

        san = board.san(move)
        board.push(move)

        # Quick eval of the resulting position for the eval bar
        info = engine.analyse(board, chess.engine.Limit(depth=10))
        cp   = eval_to_cp(info["score"])

        return move.uci(), san, cp


def position_eval(fen: str) -> int:
    board = chess.Board(fen)
    with chess.engine.SimpleEngine.popen_uci(ENGINE_PATH) as engine:
        info = engine.analyse(board, chess.engine.Limit(depth=10))
        return eval_to_cp(info["score"])


def board_status(board: chess.Board) -> dict:
    outcome = board.outcome(claim_draw=False)
    if outcome is None:
        return {"game_over": False}
    winner = None
    if outcome.winner is chess.WHITE:
        winner = "White"
    elif outcome.winner is chess.BLACK:
        winner = "Black"
    return {
        "game_over": True,
        "result":    outcome.result(),
        "winner":    winner,
        "reason":    TERMINATION_LABELS.get(outcome.termination,
                                            outcome.termination.name.lower()),
    }


@app.route("/")
def index():
    return render_template("index.html",
                           slider_min=SLIDER_MIN, slider_max=SLIDER_MAX,
                           default_elo=1600)


@app.route("/api/new_game", methods=["POST"])
def new_game():
    data = request.get_json(force=True)
    elo = clamp_elo(int(data.get("elo", 1600)))
    player_color = data.get("color", "white")

    board = chess.Board()
    resp = {"fen": board.fen(), "elo": elo, "player_color": player_color,
            "game_over": False, "eval_cp": 20}

    if player_color == "black":
        uci, san, cp = engine_move(board.fen(), elo)
        board.push(chess.Move.from_uci(uci))
        resp["fen"]         = board.fen()
        resp["engine_move"] = uci
        resp["engine_san"]  = san
        resp["eval_cp"]     = cp

    return jsonify(resp)


@app.route("/api/move", methods=["POST"])
def make_move():
    data     = request.get_json(force=True)
    fen      = data.get("fen")
    move_uci = data.get("move")
    elo      = clamp_elo(int(data.get("elo", 1600)))

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
        return jsonify({"fen": board.fen(),
                        "eval_cp": position_eval(board.fen()), **status})

    uci, san, cp = engine_move(board.fen(), elo)
    board.push(chess.Move.from_uci(uci))
    status = board_status(board)

    return jsonify({
        "fen":         board.fen(),
        "engine_move": uci,
        "engine_san":  san,
        "eval_cp":     cp,
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



@app.after_request
def _no_html_cache(resp):
    # Browsers heuristically cache HTML served without Cache-Control, which
    # leaves visitors on stale pages after a deploy. Force revalidation.
    if resp.mimetype == "text/html":
        resp.headers["Cache-Control"] = "no-cache"
    return resp

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
