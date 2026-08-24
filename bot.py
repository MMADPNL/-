# DOGS LIMBO BOT v3
# Virtual DOGS deposit format:
# ULTRA 5000 DOGS @IQ7XA
# Wallet is shown only as text

import sqlite3, random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = "PUT_YOUR_BOT_TOKEN"
OWNER_ID = 8552447077

db = sqlite3.connect("dogs.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY,
balance INTEGER DEFAULT 10000
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS deposits(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
amount INTEGER,
username TEXT,
status TEXT
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS withdrawals(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
amount INTEGER,
address TEXT,
status TEXT
)""")

db.commit()


def add_user(uid):
    cur.execute("INSERT OR IGNORE INTO users(id) VALUES(?)",(uid,))
    db.commit()


def balance(uid):
    add_user(uid)
    cur.execute("SELECT balance FROM users WHERE id=?",(uid,))
    return cur.fetchone()[0]


def change_balance(uid, amount):
    add_user(uid)
    cur.execute("UPDATE users SET balance=balance+? WHERE id=?",(amount,uid))
    db.commit()


async def start(update, context):
    uid=update.effective_user.id
    await update.message.reply_text(
        f"🚀 DOGS LIMBO\n💰 {balance(uid)} DOGS"
    )


async def deposit(update, context):
    context.user_data["deposit"]=True
    await update.message.reply_text(
"""💳 واریز DOGS

فرمت:
ULTRA 5000 DOGS @IQ7XA

بعد عکس رسید را بفرست."""
    )


async def deposit_text(update, context):
    if not context.user_data.get("deposit"):
        return

    txt=update.message.text.split()

    try:
        amount=int(txt[1])
        username=txt[3]
    except:
        await update.message.reply_text("فرمت اشتباه")
        return

    uid=update.effective_user.id

    cur.execute(
        "INSERT INTO deposits(user_id,amount,username,status) VALUES(?,?,?,?)",
        (uid,amount,username,"pending")
    )

    db.commit()

    await update.message.reply_text(
        "✅ درخواست ثبت شد، رسید را ارسال کن"
    )

    context.user_data["last_deposit"]=cur.lastrowid


async def deposit_photo(update, context):
    if not context.user_data.get("deposit"):
        return

    await context.bot.send_photo(
        OWNER_ID,
        update.message.photo[-1].file_id,
        caption="🔔 رسید واریز جدید\nبرای تایید از پنل استفاده کن"
    )


app=Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(CommandHandler("deposit",deposit))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,deposit_text))
app.add_handler(MessageHandler(filters.PHOTO,deposit_photo))

print("DOGS BOT V3 RUNNING")
app.run_polling()
