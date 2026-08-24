import os
import sqlite3
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# =========================================================
# SETTINGS
# =========================================================

TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 8552447077

OWNER_DOGS = 10_000
START_DOGS = 1_000

DB_NAME = "bot.db"


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)


# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            first_name TEXT DEFAULT '',
            dogs INTEGER NOT NULL DEFAULT 1000
        )
    """)

    conn.commit()
    conn.close()


# =========================================================
# USER
# =========================================================

def ensure_user(user):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT dogs FROM users WHERE user_id = ?",
        (user.id,)
    )

    row = cur.fetchone()

    if row is None:

        if user.id == OWNER_ID:
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
                user.id,
                user.username or "",
                user.first_name or "",
                dogs
            )
        )

    else:
        dogs = row[0]

        cur.execute(
            """
            UPDATE users
            SET username = ?, first_name = ?
            WHERE user_id = ?
            """,
            (
                user.username or "",
                user.first_name or "",
                user.id
            )
        )

    conn.commit()
    conn.close()

    return dogs


def get_dogs(user_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT dogs FROM users WHERE user_id = ?",
        (user_id,)
    )

    row = cur.fetchone()

    conn.close()

    if row is None:
        return None

    return row[0]


def change_dogs(user, amount):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT dogs FROM users WHERE user_id = ?",
        (user.id,)
    )

    row = cur.fetchone()

    if row is None:

        if user.id == OWNER_ID:
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
                user.id,
                user.username or "",
                user.first_name or "",
                dogs
            )
        )

    else:
        dogs = row[0]

    new_dogs = dogs + amount

    if new_dogs < 0:
        conn.close()
        return False, dogs

    cur.execute(
        """
        UPDATE users
        SET dogs = ?, username = ?, first_name = ?
        WHERE user_id = ?
        """,
        (
            new_dogs,
            user.username or "",
            user.first_name or "",
            user.id
        )
    )

    conn.commit()
    conn.close()

    return True, new_dogs


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    dogs = ensure_user(user)

    await update.message.reply_text(
        f"🎮 سلام {user.first_name}!\n\n"
        f"🐶 داگز شما: {dogs:,}\n\n"
        f"برای دیدن موجودی:\n"
        f"/balance\n\n"
        f"برای تست برد:\n"
        f"/win\n\n"
        f"برای تست باخت:\n"
        f"/lose"
    )


# =========================================================
# BALANCE
# =========================================================

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    ensure_user(user)

    dogs = get_dogs(user.id)

    await update.message.reply_text(
        f"👤 {user.first_name}\n\n"
        f"🐶 موجودی داگز: {dogs:,}"
    )


# =========================================================
# TEST WIN
# =========================================================

async def win(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    success, dogs = change_dogs(user, 100)

    if not success:
        await update.message.reply_text(
            "❌ خطا در تغییر موجودی."
        )
        return

    await update.message.reply_text(
        f"🎉 +100 داگز\n\n"
        f"🐶 موجودی جدید: {dogs:,}"
    )


# =========================================================
# TEST LOSE
# =========================================================

async def lose(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    success, dogs = change_dogs(user, -100)

    if not success:
        await update.message.reply_text(
            "❌ داگز کافی نیست."
        )
        return

    await update.message.reply_text(
        f"💸 -100 داگز\n\n"
        f"🐶 موجودی جدید: {dogs:,}"
    )


# =========================================================
# OWNER
# =========================================================

async def owner(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if user.id != OWNER_ID:
        await update.message.reply_text(
            "⛔ این دستور فقط برای مالک ربات است."
        )
        return

    await update.message.reply_text(
        f"👑 مالک ربات\n\n"
        f"🆔 ID: {OWNER_ID}\n"
        f"🐶 داگز: {get_dogs(OWNER_ID):,}"
    )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.error(
        "Bot error:",
        exc_info=context.error
    )


# =========================================================
# MAIN
# =========================================================

def main():

    if not TOKEN:

        print("❌ BOT_TOKEN پیدا نشد.")
        print("")
        print("در Environment / Secrets این مقدار را بساز:")
        print("BOT_TOKEN = توکن ربات")
        return

    init_db()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("balance", balance)
    )

    app.add_handler(
        CommandHandler("win", win)
    )

    app.add_handler(
        CommandHandler("lose", lose)
    )

    app.add_handler(
        CommandHandler("owner", owner)
    )

    app.add_error_handler(error_handler)

    print("================================")
    print("🚀 BOT STARTED")
    print("🐶 DOGS SYSTEM ENABLED")
    print(f"👑 OWNER ID: {OWNER_ID}")
    print(f"🐶 OWNER DOGS: {OWNER_DOGS}")
    print("================================")

    app.run_polling(
        drop_pending_updates=True
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
