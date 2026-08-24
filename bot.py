import os
import sqlite3
import logging
import time
import hmac
import hashlib
import json
import urllib.parse
import secrets
from threading import Thread

from flask import Flask, request, jsonify, send_from_directory

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# =========================================================
# SETTINGS
# =========================================================

TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "").rstrip("/")

OWNER_ID = 8552447077

OWNER_DOGS = 10_000
START_DOGS = 1_000

DB_NAME = "bot.db"

# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

# =========================================================
# FLASK
# =========================================================

web = Flask(
    __name__,
    static_folder="webapp",
)

# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            first_name TEXT DEFAULT '',
            dogs INTEGER NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS games (
            game_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            bet INTEGER NOT NULL,
            crash REAL NOT NULL,
            status TEXT NOT NULL,
            payout INTEGER DEFAULT 0,
            created_at INTEGER NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# =========================================================
# USERS
# =========================================================

def ensure_user(user_id, username="", first_name=""):

    conn = get_db()
    cur = conn.cursor()

    row = cur.execute(
        "SELECT dogs FROM users WHERE user_id = ?",
        (user_id,),
    ).fetchone()

    if row is None:

        if user_id == OWNER_ID:
            dogs = OWNER_DOGS
        else:
            dogs = START_DOGS

        cur.execute(
            """
            INSERT INTO users
            (user_id, username, first_name, dogs)
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                username or "",
                first_name or "",
                dogs,
            ),
        )

    else:

        dogs = row["dogs"]

        cur.execute(
            """
            UPDATE users
            SET username = ?,
                first_name = ?
            WHERE user_id = ?
            """,
            (
                username or "",
                first_name or "",
                user_id,
            ),
        )

    conn.commit()
    conn.close()

    return dogs


def get_balance(user_id):

    conn = get_db()

    row = conn.execute(
        "SELECT dogs FROM users WHERE user_id = ?",
        (user_id,),
    ).fetchone()

    conn.close()

    if row is None:
        return None

    return int(row["dogs"])


# =========================================================
# TELEGRAM WEBAPP SECURITY
# =========================================================

def validate_telegram_data(init_data):

    if not TOKEN or not init_data:
        return None

    try:

        data = dict(
            urllib.parse.parse_qsl(
                init_data,
                keep_blank_values=True,
            )
        )

        received_hash = data.pop("hash", None)

        if not received_hash:
            return None

        auth_date = int(
            data.get("auth_date", "0")
        )

        # Session expires after 24 hours
        if time.time() - auth_date > 86400:
            return None

        check_string = "\n".join(
            f"{key}={data[key]}"
            for key in sorted(data)
        )

        secret_key = hmac.new(
            b"WebAppData",
            TOKEN.encode(),
            hashlib.sha256,
        ).digest()

        calculated_hash = hmac.new(
            secret_key,
            check_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(
            calculated_hash,
            received_hash,
        ):
            return None

        telegram_user = json.loads(
            data["user"]
        )

        return telegram_user

    except Exception as e:

        logger.warning(
            "Telegram validation error: %s",
            e,
        )

        return None


def get_web_user():

    init_data = request.headers.get(
        "X-Telegram-Init-Data",
        "",
    )

    return validate_telegram_data(
        init_data
    )


# =========================================================
# CRASH POINT
# =========================================================

def generate_crash():

    # Demo-only virtual game.
    # Generates a value between 1.00 and 10.00.

    number = secrets.randbelow(900) + 100

    return round(
        number / 100,
        2,
    )


# =========================================================
# WEB APP
# =========================================================

@web.get("/")
def home():

    return send_from_directory(
        "webapp",
        "index.html",
    )


# =========================================================
# BALANCE API
# =========================================================

@web.post("/api/balance")
def balance_api():

    user = get_web_user()

    if not user:
        return jsonify({
            "error": "جلسه تلگرام معتبر نیست"
        }), 401

    user_id = int(user["id"])

    dogs = ensure_user(
        user_id,
        user.get("username"),
        user.get("first_name"),
    )

    return jsonify({
        "ok": True,
        "dogs": dogs,
    })


# =========================================================
# START GAME
# =========================================================

@web.post("/api/start-game")
def start_game():

    user = get_web_user()

    if not user:
        return jsonify({
            "error": "جلسه تلگرام معتبر نیست"
        }), 401

    user_id = int(user["id"])

    ensure_user(
        user_id,
        user.get("username"),
        user.get("first_name"),
    )

    data = request.get_json(
        silent=True
    ) or {}

    try:
        bet = int(
            data.get("bet", 0)
        )
    except Exception:
        bet = 0

    if bet < 1:
        return jsonify({
            "error": "مبلغ شرط نامعتبر است"
        }), 400

    conn = get_db()

    try:

        # Check balance
        row = conn.execute(
            "SELECT dogs FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        if not row:
            return jsonify({
                "error": "کاربر پیدا نشد"
            }), 400

        balance = int(row["dogs"])

        if balance < bet:
            return jsonify({
                "error": "داگز کافی نیست",
                "dogs": balance,
            }), 400

        # Prevent multiple active games
        active = conn.execute(
            """
            SELECT game_id
            FROM games
            WHERE user_id = ?
            AND status = 'active'
            """,
            (user_id,),
        ).fetchone()

        if active:
            return jsonify({
                "error": "یک بازی فعال دارید"
            }), 400

        # Deduct bet
        conn.execute(
            """
            UPDATE users
            SET dogs = dogs - ?
            WHERE user_id = ?
            """,
            (
                bet,
                user_id,
            ),
        )

        # Generate server-side crash
        crash = generate_crash()

        game_id = secrets.token_urlsafe(
            18
        )

        conn.execute(
            """
            INSERT INTO games
            (game_id, user_id, bet, crash, status, payout, created_at)
            VALUES (?, ?, ?, ?, 'active', 0, ?)
            """,
            (
                game_id,
                user_id,
                bet,
                crash,
                int(time.time()),
            ),
        )

        conn.commit()

        new_balance = get_balance(
            user_id
        )

        return jsonify({
            "ok": True,
            "game_id": game_id,
            "crash": crash,
            "dogs": new_balance,
        })

    finally:
        conn.close()


# =========================================================
# CASHOUT
# =========================================================

@web.post("/api/cashout")
def cashout():

    user = get_web_user()

    if not user:
        return jsonify({
            "error": "جلسه تلگرام معتبر نیست"
        }), 401

    user_id = int(user["id"])

    data = request.get_json(
        silent=True
    ) or {}

    game_id = str(
        data.get("game_id", "")
    )

    try:
        multiplier = float(
            data.get("multiplier", 0)
        )
    except Exception:
        multiplier = 0

    if not game_id:
        return jsonify({
            "error": "بازی نامعتبر است"
        }), 400

    conn = get_db()

    try:

        game = conn.execute(
            """
            SELECT *
            FROM games
            WHERE game_id = ?
            AND user_id = ?
            """,
            (
                game_id,
                user_id,
            ),
        ).fetchone()

        if not game:
            return jsonify({
                "error": "بازی پیدا نشد"
            }), 404

        if game["status"] != "active":
            return jsonify({
                "error": "این بازی قبلاً تمام شده"
            }), 400

        crash = float(
            game["crash"]
        )

        # Cannot cash out after crash
        if multiplier >= crash:

            conn.execute(
                """
                UPDATE games
                SET status = 'lost'
                WHERE game_id = ?
                """,
                (game_id,),
            )

            conn.commit()

            return jsonify({
                "ok": False,
                "lost": True,
                "dogs": get_balance(
                    user_id
                ),
            })

        # Minimum cashout
        if multiplier < 1.01:
            return jsonify({
                "error": "ضریب برداشت نامعتبر است"
            }), 400

        multiplier = round(
            multiplier,
            2,
        )

        bet = int(
            game["bet"]
        )

        payout = int(
            bet * multiplier
        )

        conn.execute(
            """
            UPDATE users
            SET dogs = dogs + ?
            WHERE user_id = ?
            """,
            (
                payout,
                user_id,
            ),
        )

        conn.execute(
            """
            UPDATE games
            SET status = 'won',
                payout = ?
            WHERE game_id = ?
            """,
            (
                payout,
                game_id,
            ),
        )

        conn.commit()

        return jsonify({
            "ok": True,
            "payout": payout,
            "dogs": get_balance(
                user_id
            ),
        })

    finally:
        conn.close()


# =========================================================
# TELEGRAM COMMANDS
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user = update.effective_user

    dogs = ensure_user(
        user.id,
        user.username,
        user.first_name,
    )

    if WEBAPP_URL:

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🚀 بازی موشک",
                    web_app=WebAppInfo(
                        url=WEBAPP_URL
                    ),
                )
            ]
        ])

        await update.message.reply_text(
            f"سلام {user.first_name} 👋\n\n"
            f"🐶 داگز: {dogs:,}\n\n"
            f"برای ورود به بازی موشک "
            f"روی دکمه زیر بزن.",
            reply_markup=keyboard,
        )

    else:

        await update.message.reply_text(
            f"سلام {user.first_name} 👋\n\n"
            f"🐶 داگز: {dogs:,}\n\n"
            f"⚠️ WEBAPP_URL تنظیم نشده."
        )


async def balance_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user = update.effective_user

    dogs = ensure_user(
        user.id,
        user.username,
        user.first_name,
    )

    await update.message.reply_text(
        f"🐶 موجودی داگز شما:\n\n"
        f"{dogs:,} DOGS"
    )


# =========================================================
# WEB SERVER
# =========================================================

def run_web():

    port = int(
        os.getenv(
            "PORT",
            "8080",
        )
    )

    web.run(
        host="0.0.0.0",
        port=port,
        debug=False,
    )


# =========================================================
# MAIN
# =========================================================

def main():

    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN تنظیم نشده است."
        )

    init_db()

    Thread(
        target=run_web,
        daemon=True,
    ).start()

    application = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        CommandHandler(
            "balance",
            balance_command,
        )
    )

    print(
        "🚀 BOT + CRASH MINI APP STARTED"
    )

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
