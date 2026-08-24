# bot_final.py
# Virtual DOGS LIMBO BOT

import sqlite3
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = "8934137266:AAFqhml0_F3RdLExFZqhgASxl42tylMc_h8"
OWNER_ID = 8552447077

db = sqlite3.connect("dogs.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY,
balance INTEGER DEFAULT 10000
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS requests(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
type TEXT,
amount INTEGER,
status TEXT DEFAULT 'pending'
)""")
db.commit()


def add_user(uid):
    cur.execute("INSERT OR IGNORE INTO users(id) VALUES(?)", (uid,))
    db.commit()


def get_balance(uid):
    add_user(uid)
    cur.execute("SELECT balance FROM users WHERE id=?", (uid,))
    return cur.fetchone()[0]


def change_balance(uid, amount):
    add_user(uid)
    cur.execute("UPDATE users SET balance=balance+? WHERE id=?", (amount, uid))
    db.commit()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.reply_text(
        f"🚀 DOGS LIMBO\n💰 موجودی: {get_balance(uid)} DOGS\n\nبازی:\n100 2.5"
    )


async def limbo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        bet, target = update.message.text.split()
        bet = int(bet)
        target = float(target)
    except:
        return

    uid = update.effective_user.id

    if bet <= 0 or target < 1.10:
        return await update.message.reply_text("❌ مقدار اشتباه")

    if bet > get_balance(uid):
        return await update.message.reply_text("❌ موجودی کافی نیست")

    change_balance(uid, -bet)

    crash = round(random.uniform(1, 10), 2)

    if target <= crash:
        win = int(bet * target)
        change_balance(uid, win)
        msg = f"🚀 برد\n+{win} DOGS"
    else:
        msg = f"💥 باخت\nانفجار x{crash}"

    await update.message.reply_text(msg)


async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "deposit"
    await update.message.reply_text("💳 فرمت:\nULTRA 5000 DOGS @USER")


async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "withdraw"
    await update.message.reply_text("📤 مقدار برداشت را بفرست")


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    if not mode:
        return

    try:
        amount = int(update.message.text.split()[1] if mode=="deposit" else update.message.text)
    except:
        return await update.message.reply_text("❌ عدد اشتباه")

    uid = update.effective_user.id

    if mode == "withdraw" and amount > get_balance(uid):
        return await update.message.reply_text("❌ موجودی کافی نیست")

    cur.execute(
        "INSERT INTO requests(user_id,type,amount) VALUES(?,?,?)",
        (uid, mode, amount)
    )
    db.commit()

    rid = cur.lastrowid

    kb = [[
        InlineKeyboardButton("✅ تایید", callback_data=f"ok_{rid}"),
        InlineKeyboardButton("❌ رد", callback_data=f"no_{rid}")
    ]]

    await context.bot.send_message(
        OWNER_ID,
        f"🔔 درخواست {mode}\n👤 {uid}\n💰 {amount} DOGS\nID:{rid}",
        reply_markup=InlineKeyboardMarkup(kb)
    )

    await update.message.reply_text("✅ ارسال شد")
    context.user_data.clear()


async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query

    if q.from_user.id != OWNER_ID:
        return

    action, rid = q.data.split("_")
    rid = int(rid)

    cur.execute("SELECT user_id,type,amount,status FROM requests WHERE id=?", (rid,))
    row = cur.fetchone()

    if not row or row[3] != "pending":
        return await q.answer("قبلا پردازش شده")

    uid, typ, amount, _ = row

    if action == "ok":
        if typ == "deposit":
            change_balance(uid, amount)
        else:
            change_balance(uid, -amount)

        cur.execute("UPDATE requests SET status='approved' WHERE id=?", (rid,))
        await q.edit_message_text("✅ تایید شد")

    else:
        cur.execute("UPDATE requests SET status='rejected' WHERE id=?", (rid,))
        await q.edit_message_text("❌ رد شد")

    db.commit()


app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("deposit", deposit))
app.add_handler(CommandHandler("withdraw", withdraw))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, limbo))
app.add_handler(CallbackQueryHandler(admin_buttons))

print("BOT RUNNING")
app.run_polling()
