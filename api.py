import os
import sqlite3
import secrets
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_FILE = "limbo.db"

# فقط برای اعتبار مجازی
MIN_BET = 1
MAX_BET = 1_000_000
MIN_TARGET = 1.01
MAX_TARGET = 100.0


# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            first_name TEXT DEFAULT '',
            balance REAL DEFAULT 0
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            bet REAL NOT NULL,
            target REAL NOT NULL,
            crash REAL NOT NULL,
            win INTEGER NOT NULL,
            payout REAL NOT NULL,
            game_token TEXT UNIQUE NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def get_user(user_id):
    conn = get_db()

    row = conn.execute(
        "SELECT * FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()

    conn.close()
    return row


def get_balance(user_id):
    row = get_user(user_id)

    if not row:
        return None

    return float(row["balance"])


# =========================================================
# TELEGRAM USER
# =========================================================

def get_user_id():
    """
    فعلاً برای تست، user_id از Header گرفته می‌شود.

    در نسخه نهایی Mini App باید Telegram initData
    سمت سرور اعتبارسنجی شود و user_id از داده معتبر
    تلگرام استخراج شود.
    """

    value = request.headers.get("X-Telegram-User-ID")

    if not value:
        return None

    try:
        return int(value)
    except ValueError:
        return None


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/")
def home():
    return jsonify({
        "ok": True,
        "service": "LIMBO DOGS API",
        "mode": "virtual"
    })


# =========================================================
# BALANCE
# =========================================================

@app.get("/api/balance")
def balance():

    user_id = get_user_id()

    if not user_id:
        return jsonify({
            "ok": False,
            "error": "USER_ID_REQUIRED"
        }), 401

    amount = get_balance(user_id)

    if amount is None:
        return jsonify({
            "ok": False,
            "error": "USER_NOT_FOUND"
        }), 404

    return jsonify({
        "ok": True,
        "balance": amount,
        "currency": "DOGS"
    })


# =========================================================
# LIMBO
# =========================================================

@app.post("/api/limbo/play")
def limbo_play():

    user_id = get_user_id()

    if not user_id:
        return jsonify({
            "ok": False,
            "error": "USER_ID_REQUIRED"
        }), 401

    data = request.get_json(silent=True) or {}

    try:
        bet = float(data.get("bet"))
        target = float(data.get("target"))
    except (TypeError, ValueError):
        return jsonify({
            "ok": False,
            "error": "INVALID_NUMBER"
        }), 400

    # -------------------------
    # VALIDATION
    # -------------------------

    if bet < MIN_BET:
        return jsonify({
            "ok": False,
            "error": "BET_TOO_SMALL"
        }), 400

    if bet > MAX_BET:
        return jsonify({
            "ok": False,
            "error": "BET_TOO_LARGE"
        }), 400

    if target < MIN_TARGET:
        return jsonify({
            "ok": False,
            "error": "TARGET_TOO_SMALL"
        }), 400

    if target > MAX_TARGET:
        return jsonify({
            "ok": False,
            "error": "TARGET_TOO_LARGE"
        }), 400

    # -------------------------
    # DATABASE TRANSACTION
    # -------------------------

    conn = get_db()

    try:

        conn.execute("BEGIN IMMEDIATE")

        user = conn.execute(
            "SELECT balance FROM users WHERE user_id=?",
            (user_id,)
        ).fetchone()

        if not user:
            conn.rollback()

            return jsonify({
                "ok": False,
                "error": "USER_NOT_FOUND"
            }), 404

        balance = float(user["balance"])

        if bet > balance:
            conn.rollback()

            return jsonify({
                "ok": False,
                "error": "INSUFFICIENT_BALANCE",
                "balance": balance
            }), 400

        # -------------------------
        # LIMBO RESULT
        # -------------------------

        # ضریب تصادفی مجازی
        #
        # این نتیجه فقط برای اعتبار مجازی است.
        #
        # مقدار crash همیشه حداقل 1.00 است.
        random_value = secrets.randbelow(10_000_000) / 100_000

        crash = max(1.00, random_value)

        # -------------------------
        # RESULT
        # -------------------------

        if crash >= target:

            win = 1
            payout = bet * target
            new_balance = balance - bet + payout

        else:

            win = 0
            payout = 0
            new_balance = balance - bet

        # -------------------------
        # UPDATE BALANCE
        # -------------------------

        conn.execute(
            "UPDATE users SET balance=? WHERE user_id=?",
            (new_balance, user_id)
        )

        game_token = secrets.token_urlsafe(24)

        conn.execute("""
            INSERT INTO games
            (
                user_id,
                bet,
                target,
                crash,
                win,
                payout,
                game_token
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            bet,
            target,
            crash,
            win,
            payout,
            game_token
        ))

        conn.commit()

    except Exception as e:

        conn.rollback()

        return jsonify({
            "ok": False,
            "error": "DATABASE_ERROR"
        }), 500

    finally:
        conn.close()

    return jsonify({
        "ok": True,
        "game": {
            "bet": bet,
            "target": target,
            "crash": round(crash, 2),
            "win": bool(win),
            "payout": round(payout, 2),
            "balance": round(new_balance, 2),
            "game_token": game_token
        }
    })


# =========================================================
# GAME HISTORY
# =========================================================

@app.get("/api/limbo/history")
def history():

    user_id = get_user_id()

    if not user_id:
        return jsonify({
            "ok": False,
            "error": "USER_ID_REQUIRED"
        }), 401

    conn = get_db()

    rows = conn.execute("""
        SELECT
            id,
            bet,
            target,
            crash,
            win,
            payout,
            created_at
        FROM games
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 20
    """, (user_id,)).fetchall()

    conn.close()

    games = []

    for row in rows:
        games.append({
            "id": row["id"],
            "bet": row["bet"],
            "target": row["target"],
            "crash": row["crash"],
            "win": bool(row["win"]),
            "payout": row["payout"],
            "created_at": row["created_at"]
        })

    return jsonify({
        "ok": True,
        "games": games
    })


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    init_db()

    port = int(os.getenv("PORT", "8080"))

    app.run(
        host="0.0.0.0",
        port=port
  )
