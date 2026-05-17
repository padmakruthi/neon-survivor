from flask import Flask, render_template, request, jsonify
import sqlite3

app = Flask(__name__)

import os
import tempfile

DB_PATH = os.path.join(tempfile.gettempdir(), 'scores.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS scores
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, score INTEGER)''')
    conn.commit()
    conn.close()

# Initialize DB when the app is loaded by Vercel
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/scores', methods=['GET'])
def get_scores():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT name, score FROM scores ORDER BY score DESC')
    scores = [{'name': row[0], 'score': row[1]} for row in c.fetchall()]
    conn.close()
    return jsonify(scores)

@app.route('/api/scores', methods=['POST'])
def add_score():
    data = request.json
    name = data.get('name', 'Anonymous')
    score = data.get('score', 0)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO scores (name, score) VALUES (?, ?)', (name, score))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
