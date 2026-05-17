# ═══════════════════════════════════════════════════════════
# GoldenBatch AI — Database Manager
# Team DeepThinkers · IARE · AVEVA Hackathon
#
# This file:
# 1. Creates the SQLite database and all tables
# 2. Has functions to save and fetch data
# 3. Handles login verification and token generation
#
# The actual database file (goldenbatch.db) is created
# automatically when this code runs for the first time
# ═══════════════════════════════════════════════════════════

import sqlite3
import hashlib
import json
import time
from datetime import datetime


# ───────────────────────────────────────────
# DATABASE FILE NAME
# This is the file that gets created in your project folder
# ───────────────────────────────────────────
DB_FILE = "goldenbatch.db"


# ───────────────────────────────────────────
# HELPER — Get a database connection
# Every function that talks to the database
# calls this first to get a connection
# ───────────────────────────────────────────
def get_connection():
    """
    Opens a connection to the SQLite database file.
    If the file doesn't exist, SQLite creates it automatically.
    """
    conn = sqlite3.connect(DB_FILE)

    # This makes rows return as dictionaries
    # so we can access data like row["email"] instead of row[0]
    conn.row_factory = sqlite3.Row

    return conn


# ───────────────────────────────────────────
# CREATE ALL TABLES
# Called once when the server starts
# If tables already exist, does nothing (safe to call multiple times)
# ───────────────────────────────────────────
def create_tables():
    """
    Creates 3 tables in the database:
    - users: stores login credentials and role
    - messages: stores all messages between users
    - predictions: stores every prediction made
    """
    conn = get_connection()

    # ── USERS TABLE ──
    # Stores the 3 users (operator, engineer, manager)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            email       TEXT    UNIQUE NOT NULL,
            password    TEXT    NOT NULL,
            name        TEXT    NOT NULL,
            role        TEXT    NOT NULL,
            created_at  TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── MESSAGES TABLE ──
    # Stores every message sent between users
    conn.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            from_name   TEXT    NOT NULL,
            from_role   TEXT    NOT NULL,
            to_role     TEXT    NOT NULL,
            text        TEXT    NOT NULL,
            priority    TEXT    DEFAULT "normal",
            time        TEXT    NOT NULL,
            created_at  TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── PREDICTIONS TABLE ──
    # Stores every batch prediction made through the app
    conn.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email      TEXT,
            inputs          TEXT    NOT NULL,
            outputs         TEXT    NOT NULL,
            overall_pass    INTEGER NOT NULL,
            dissolution     REAL,
            hardness        REAL,
            created_at      TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── EVENTS TABLE ──
    # Stores login events and other activity logs
    conn.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type  TEXT    NOT NULL,
            user_email  TEXT,
            user_role   TEXT,
            created_at  TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()


# ───────────────────────────────────────────
# CREATE DEFAULT USERS
# Creates the 3 demo users when server starts
# If users already exist, does nothing
# ───────────────────────────────────────────
def create_default_users():
    """
    Creates 3 default users for the demo:
    - operator@plant.com  / operator123
    - engineer@plant.com  / engineer123
    - manager@plant.com   / manager123
    """
    default_users = [
        {
            "email": "operator@plant.com",
            "password": hash_password("operator123"),
            "name": "Navya Sri",
            "role": "operator"
        },
        {
            "email": "engineer@plant.com",
            "password": hash_password("engineer123"),
            "name": "B P S Kruthi",
            "role": "engineer"
        },
        {
            "email": "manager@plant.com",
            "password": hash_password("manager123"),
            "name": "Plant Manager",
            "role": "manager"
        }
    ]

    conn = get_connection()

    for user in default_users:
        # INSERT OR IGNORE means: if user already exists, skip it
        conn.execute('''
            INSERT OR IGNORE INTO users (email, password, name, role)
            VALUES (?, ?, ?, ?)
        ''', (user["email"], user["password"], user["name"], user["role"]))

    conn.commit()
    conn.close()


# ───────────────────────────────────────────
# PASSWORD HASHING
# We never store plain text passwords
# We store a hashed version for security
# ───────────────────────────────────────────
def hash_password(password: str) -> str:
    """
    Converts a plain text password into a hash.
    Example: "operator123" → "a3f5c8d9e2b1..."
    We store the hash, not the original password.
    """
    return hashlib.sha256(password.encode()).hexdigest()


# ───────────────────────────────────────────
# LOGIN VERIFICATION
# Checks if email + password match a user in database
# ───────────────────────────────────────────
def verify_login(email: str, password: str):
    """
    Looks up the email in the users table.
    Hashes the given password and compares it to the stored hash.
    Returns user data if match, None if no match.
    """
    conn = get_connection()

    hashed = hash_password(password)

    user = conn.execute('''
        SELECT id, email, name, role
        FROM users
        WHERE email = ? AND password = ?
    ''', (email, hashed)).fetchone()

    conn.close()

    if user:
        # Convert Row object to regular dictionary
        return {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"]
        }

    return None


# ───────────────────────────────────────────
# TOKEN GENERATION & VERIFICATION
# Simple token system for login sessions
# ───────────────────────────────────────────

# In-memory token store
# In production you'd use JWT, but for hackathon this is simpler
TOKEN_STORE = {}

def generate_token(email: str, role: str) -> str:
    """
    Creates a unique token for a logged-in user.
    Stores it in memory so we can look it up later.
    Returns the token string.
    """
    # Create token from email + current time + role
    raw = f"{email}:{role}:{time.time()}"
    token = hashlib.sha256(raw.encode()).hexdigest()

    # Store token → user info mapping
    TOKEN_STORE[token] = {
        "email": email,
        "role": role,
        "created_at": time.time()
    }

    return token


def get_user_from_token(token: str):
    """
    Looks up a token and returns the user info.
    Returns None if token not found or expired.
    """
    if token not in TOKEN_STORE:
        return None

    user_info = TOKEN_STORE[token]

    # Token expires after 24 hours (86400 seconds)
    if time.time() - user_info["created_at"] > 86400:
        del TOKEN_STORE[token]
        return None

    return user_info


# ───────────────────────────────────────────
# SAVE MESSAGE
# Called when a user sends a message
# ───────────────────────────────────────────
def save_message(from_name: str, from_role: str, to: str,
                 text: str, priority: str, time: str) -> int:
    """
    Saves a message to the messages table.
    Returns the ID of the saved message.
    """
    conn = get_connection()

    cursor = conn.execute('''
        INSERT INTO messages (from_name, from_role, to_role, text, priority, time)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (from_name, from_role, to, text, priority, time))

    message_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return message_id


# ───────────────────────────────────────────
# GET MESSAGES
# Called when frontend loads the messages page
# ───────────────────────────────────────────
def get_messages(role: str) -> list:
    """
    Returns messages visible to the given role.

    Rules:
    - Operator sees: messages sent to "all" or "operator"
    - Engineer sees: messages sent to "all" or "engineer"
    - Manager sees: ALL messages
    """
    conn = get_connection()

    if role == "manager":
        # Manager sees everything
        rows = conn.execute('''
            SELECT * FROM messages
            ORDER BY created_at DESC
            LIMIT 100
        ''').fetchall()
    else:
        # Others see messages sent to "all" or specifically to their role
        rows = conn.execute('''
            SELECT * FROM messages
            WHERE to_role = "all" OR to_role = ?
            ORDER BY created_at DESC
            LIMIT 100
        ''', (role,)).fetchall()

    conn.close()

    # Convert Row objects to dictionaries
    messages = []
    for row in rows:
        messages.append({
            "id": row["id"],
            "from_name": row["from_name"],
            "from_role": row["from_role"],
            "to_role": row["to_role"],
            "text": row["text"],
            "priority": row["priority"],
            "time": row["time"],
            "created_at": row["created_at"]
        })

    return messages


# ───────────────────────────────────────────
# SAVE PREDICTION
# Called every time a user runs a prediction
# ───────────────────────────────────────────
def save_prediction(user_email: str, inputs: dict, outputs: dict):
    """
    Saves a prediction record to the database.
    Inputs and outputs are stored as JSON strings.
    """
    conn = get_connection()

    conn.execute('''
        INSERT INTO predictions
        (user_email, inputs, outputs, overall_pass, dissolution, hardness)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        user_email,
        json.dumps(inputs),          # convert dict to JSON string for storage
        json.dumps(outputs),
        1 if outputs.get("overall_pass") else 0,
        outputs.get("dissolution_rate", 0),
        outputs.get("hardness", 0)
    ))

    conn.commit()
    conn.close()


# ───────────────────────────────────────────
# GET PREDICTION HISTORY
# Returns past predictions for a user
# ───────────────────────────────────────────
def get_prediction_history(user_email: str) -> list:
    """
    Returns the last 20 predictions made by a specific user.
    """
    conn = get_connection()

    rows = conn.execute('''
        SELECT * FROM predictions
        WHERE user_email = ?
        ORDER BY created_at DESC
        LIMIT 20
    ''', (user_email,)).fetchall()

    conn.close()

    predictions = []
    for row in rows:
        predictions.append({
            "id": row["id"],
            "inputs": json.loads(row["inputs"]),     # convert JSON string back to dict
            "outputs": json.loads(row["outputs"]),
            "overall_pass": bool(row["overall_pass"]),
            "dissolution": row["dissolution"],
            "hardness": row["hardness"],
            "created_at": row["created_at"]
        })

    return predictions


# ───────────────────────────────────────────
# LOG EVENT
# Logs logins and other activity
# ───────────────────────────────────────────
def log_prediction_or_event(event_type: str, user_email: str, user_role: str):
    """
    Saves a log entry for tracking activity.
    Example: when someone logs in, we log it here.
    """
    conn = get_connection()

    conn.execute('''
        INSERT INTO events (event_type, user_email, user_role)
        VALUES (?, ?, ?)
    ''', (event_type, user_email, user_role))

    conn.commit()
    conn.close()