from flask import Flask, render_template, request, jsonify
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime
import os

# Load credentials from .env
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

# Game state (one game at a time for now)
board = [""] * 9
current_player = "X"
placed_X = []
placed_O = []
move_number = 0
game_id = 1

def check_win():
    winning_lines = [
        [0,1,2],[3,4,5],[6,7,8],
        [0,3,6],[1,4,7],[2,5,8],
        [0,4,8],[2,4,6]
    ]
    for a, b, c in winning_lines:
        if board[a] == board[b] == board[c] and board[a] != "":
            return board[a]
    return None

def check_draw():
    return all(cell != "" for cell in board)

def log_move(vanished, result):
    supabase.table("moves").insert({
        "game_id": game_id,
        "date": datetime.now().isoformat(),
        "move_number": move_number,
        "player": current_player,
        "cell": last_cell_played,
        "board_state": ",".join(board),
        "vanished_cell": str(vanished) if vanished is not None else "",
        "result": result
    }).execute()

def reset_game():
    global board, current_player, placed_X, placed_O, move_number
    board = [""] * 9
    current_player = "X"
    placed_X = []
    placed_O = []
    move_number = 0

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/move", methods=["POST"])
def make_move():
    global board, current_player, placed_X, placed_O
    global move_number, last_cell_played, game_id

    data = request.get_json()
    index = data["index"]

    # Ignore if cell occupied
    if board[index] != "":
        return jsonify({"status": "invalid"})

    # Place symbol
    board[index] = current_player
    move_number += 1
    last_cell_played = index

    # Add to queue
    if current_player == "X":
        placed_X.append(index)
    else:
        placed_O.append(index)

    # Check win BEFORE vanishing
    winner = check_win()
    if winner:
        log_move(None, f"{winner} wins")
        response = {"status": "win", "winner": winner, "board": board, "vanished": None}
        game_id += 1
        reset_game()
        return jsonify(response)

    # Vanish oldest if queue > 3
    vanished = None
    if current_player == "X" and len(placed_X) > 3:
        vanished = placed_X.pop(0)
        board[vanished] = ""
    elif current_player == "O" and len(placed_O) > 3:
        vanished = placed_O.pop(0)
        board[vanished] = ""

    # Check win AFTER vanishing
    winner = check_win()
    if winner:
        log_move(vanished, f"{winner} wins")
        response = {"status": "win", "winner": winner, "board": board, "vanished": vanished}
        game_id += 1
        reset_game()
        return jsonify(response)

    # Check draw
    if check_draw():
        log_move(vanished, "draw")
        response = {"status": "draw", "board": board, "vanished": vanished}
        game_id += 1
        reset_game()
        return jsonify(response)

    # Ongoing
    log_move(vanished, "ongoing")
    current_player = "O" if current_player == "X" else "X"
    return jsonify({
        "status": "ongoing",
        "board": board,
        "current_player": current_player,
        "vanished": vanished,
        "placed_X": placed_X,
        "placed_O": placed_O
    })

@app.route("/reset", methods=["POST"])
def reset():
    global game_id
    game_id += 1
    reset_game()
    return jsonify({"status": "reset", "board": board, "current_player": current_player})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)