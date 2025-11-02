from flask import Flask, jsonify, render_template, request
import chess
import chess.engine
import random
import datetime
import os

app = Flask(__name__)

# --- Global state ---
board = chess.Board()
player_name = None

# Path to store all game results
RESULTS_PATH = r"C:\Users\aadit\OneDrive\Desktop\webchess\results.txt"


@app.route("/")
def index():
    """Serve the main web page."""
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
    """Start a new chess game and set player name."""
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
    """Return all valid moves from a given square."""
    try:
        sq = chess.parse_square(square)
        moves = [m.uci() for m in board.legal_moves if m.from_square == sq]
        return jsonify({"moves": moves})
    except Exception as e:
        print("Error getting valid moves:", e)
        return jsonify({"moves": []})


@app.route("/player_move", methods=["POST"])
def player_move():
    """Handle player's move and make AI move."""
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

    # If player wins or draw
    if board.is_game_over():
        result = get_result_text(player, difficulty)
        log_result(result)
        return jsonify({
            "status": "finished",
            "result": result,
            "fen": board.fen()
        })

    # --- AI Move ---
    if not board.is_game_over():
        ai_move = get_ai_move(difficulty)
        if ai_move:
            board.push(ai_move)
            print(f"AI ({difficulty}) played: {ai_move.uci()}")

    # If AI wins or draw
    if board.is_game_over():
        result = get_result_text(player, difficulty)
        log_result(result)
        return jsonify({
            "status": "finished",
            "result": result,
            "fen": board.fen()
        })

    return jsonify({"status": "ok", "fen": board.fen()})


def get_ai_move(level="medium"):
    """Generate an AI move using Stockfish or fallback to random."""
    global board
    # Update this path to your actual Stockfish executable
    engine_path = r"C:\Users\aadit\OneDrive\Desktop\webchess\stockfish-windows-x86-64-avx2.exe"

    levels = {
        "easy": 0.1,    # 100 ms think time
        "medium": 0.5,  # 500 ms
        "hard": 1.5     # 1.5 s
    }
    think_time = levels.get(level, 0.5)

    try:
        with chess.engine.SimpleEngine.popen_uci(engine_path) as engine:
            result = engine.play(board, chess.engine.Limit(time=think_time))
            return result.move
    except Exception as e:
        print("Engine error:", e)
        legal_moves = list(board.legal_moves)
        return random.choice(legal_moves) if legal_moves else None


def get_result_text(player, difficulty):
    """Build a formatted game summary."""
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
    """Append result text to results.txt file."""
    try:
        os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
        with open(RESULTS_PATH, "a", encoding="utf-8") as f:
            f.write(result_text)
        print("Result saved to:", RESULTS_PATH)
    except Exception as e:
        print("Error writing results file:", e)


@app.route("/logs")
def get_logs():
    """Return results.txt content for sidebar display."""
    try:
        if not os.path.exists(RESULTS_PATH):
            return "No game logs yet."
        with open(RESULTS_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading logs: {e}"


if __name__ == "__main__":
    app.run(debug=True)
