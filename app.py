from flask import Flask, jsonify, render_template, request
import chess
import chess.engine
import random
import datetime
import os
import platform

app = Flask(__name__)

# --- Global state ---
board = chess.Board()
player_name = None

# ✅ Cross-platform results path
if os.name == "nt":
    RESULTS_PATH = r"C:\Users\aadit\OneDrive\Desktop\webchess\results.txt"
else:
    RESULTS_PATH = "/tmp/results.txt"  # Render safe temporary folder


@app.route("/")
def index():
    """Serve main page."""
    return render_template("index.html")


@app.route("/get_state")
def get_state():
    """Return current game state."""
    return jsonify({
        "fen": board.fen(),
        "turn": "white" if board.turn == chess.WHITE else "black",
        "game_over": board.is_game_over(),
        "player": player_name
    })


@app.route("/start", methods=["POST"])
def start_game():
    """Start a new game with player name."""
    global board, player_name
    board = chess.Board()
    data = request.get_json() or {}
    player_name = data.get("player", "Guest")
    print(f"New game started by: {player_name}")
    return jsonify({
        "status": "started",
        "player": player_name,
        "fen": board.fen()
    })


@app.route("/valid_moves/<square>")
def valid_moves(square):
    """Return valid moves for given square."""
    try:
        sq = chess.parse_square(square)
        moves = [m.uci() for m in board.legal_moves if m.from_square == sq]
        return jsonify({"moves": moves})
    except Exception as e:
        print("Error getting valid moves:", e)
        return jsonify({"moves": []})


@app.route("/player_move", methods=["POST"])
def player_move():
    """Handle player's move, then AI's."""
    data = request.get_json()
    move_uci = data.get("move", "")
    difficulty = data.get("difficulty", "medium")
    player = data.get("player", "Guest")

    try:
        move = chess.Move.from_uci(move_uci)
        if move in board.legal_moves:
            board.push(move)
        else:
            return jsonify({"status": "illegal", "fen": board.fen()})
    except Exception as e:
        print("Move error:", e)
        return jsonify({"status": "error", "fen": board.fen()})

    # Player finishes game
    if board.is_game_over():
        result = get_result_text(player, difficulty)
        log_result(result)
        return jsonify({"status": "finished", "result": result, "fen": board.fen()})

    # --- AI Move ---
    ai_move = get_ai_move(difficulty)
    if ai_move:
        board.push(ai_move)
        print(f"AI ({difficulty}) played: {ai_move.uci()}")

    # AI finishes game
    if board.is_game_over():
        result = get_result_text(player, difficulty)
        log_result(result)
        return jsonify({"status": "finished", "result": result, "fen": board.fen()})

    return jsonify({"status": "ok", "fen": board.fen()})


def get_ai_move(level="medium"):
    """
    Generate AI move.
    - On Windows local machine: use Stockfish.
    - On Render/Linux: fallback to random for instant response.
    """
    global board
    import random

    is_windows = (os.name == "nt")
    on_render = os.environ.get("RENDER", "") != "" or platform.system() == "Linux"

    levels = {"easy": 0.1, "medium": 0.5, "hard": 1.5}
    think_time = levels.get(level, 0.5)

    # ✅ Stockfish only on local Windows
    if is_windows and not on_render:
        engine_path = r"C:\Users\aadit\OneDrive\Desktop\webchess\stockfish-windows-x86-64-avx2.exe"
        try:
            if os.path.exists(engine_path):
                with chess.engine.SimpleEngine.popen_uci(engine_path) as engine:
                    result = engine.play(board, chess.engine.Limit(time=think_time))
                    return result.move
        except Exception as e:
            print("Stockfish error, using random:", e)

    # ✅ Render fallback — instant random legal move
    legal_moves = list(board.legal_moves)
    return random.choice(legal_moves) if legal_moves else None


def get_result_text(player, difficulty):
    """Format game result info."""
    result = board.result()
    status = (
        "White wins" if result == "1-0" else
        "Black wins" if result == "0-1" else
        "Draw"
    )
    time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"Game ended at {time_str}\n"
        f"Player: {player}\n"
        f"Difficulty: {difficulty}\n"
        f"Result: {status} ({result})\n"
        f"Final FEN: {board.fen()}\n"
        f"{'-'*60}\n"
    )


def log_result(result_text):
    """Append result to results.txt (cross-platform safe)."""
    try:
        os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
        with open(RESULTS_PATH, "a", encoding="utf-8") as f:
            f.write(result_text)
        print(f"Result saved to: {RESULTS_PATH}")
    except Exception as e:
        print("Error writing results:", e)


@app.route("/logs")
def get_logs():
    """Return log file contents."""
    try:
        if not os.path.exists(RESULTS_PATH):
            return "No game logs yet."
        with open(RESULTS_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading logs: {e}"


if __name__ == "__main__":
    # ✅ Allow LAN / Render connections
    app.run(host="0.0.0.0", port=5000, debug=True)
