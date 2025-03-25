from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})

# ✅ Make sure this path is correct for your setup
DB_PATH = "march_madness_prediction_with_teams.db"

# 🔹 Home route
@app.route('/')
def home():
    return jsonify({"message": "Backend is running!"})

# 🔹 Return all unique teams from the `teams` table
@app.route('/teams', methods=['GET'])
def get_teams():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT DISTINCT team_name FROM teams")
        rows = cursor.fetchall()
        teams = sorted([row[0] for row in rows if row[0]])
    except Exception as e:
        print("🔥 ERROR fetching teams:", e)
        teams = []

    conn.close()
    return jsonify({"teams": teams})

# 🔹 Predict winner based on seed and matchup history
@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()
    teams = data.get("teams", [])

    if len(teams) != 2:
        return jsonify({"error": "Please select exactly 2 teams."}), 400

    team1, team2 = teams
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get most recent seed for each team
    def get_latest_seed(team_name):
        cursor.execute("""
            SELECT seed FROM teams
            WHERE team_name = ?
            ORDER BY year DESC
            LIMIT 1
        """, (team_name,))
        result = cursor.fetchone()
        return result[0] if result else 8

    seed1 = get_latest_seed(team1)
    seed2 = get_latest_seed(team2)

    # Count head-to-head matchups from matchups table
    def get_head_to_head_wins(team_a, team_b):
        cursor.execute("""
            SELECT score1, score2 FROM matchups
            WHERE team1_name = ? AND team2_name = ?
        """, (team_a, team_b))
        matches = cursor.fetchall()
        return sum(1 for s1, s2 in matches if s1 > s2)

    wins1 = get_head_to_head_wins(team1, team2)
    wins2 = get_head_to_head_wins(team2, team1)

    conn.close()

    # Simple scoring logic
    score1 = (20 - seed1) + (wins1 * 3)
    score2 = (20 - seed2) + (wins2 * 3)

    if score1 == score2:
        winner, probability = team1, 50
    elif score1 > score2:
        winner = team1
        probability = round(50 + (score1 - score2) * 2, 1)
    else:
        winner = team2
        probability = round(50 + (score2 - score1) * 2, 1)

    probability = max(51, min(99, probability))  # Keep it realistic
    return jsonify({"winner": winner, "probability": probability})

# 🔹 Run server
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
