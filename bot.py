# DOGS LIMBO BOT V1
# واریزی، برداشت، پنل، LIMBO پایه
# توکن و OWNER_ID را خودت وارد کن

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import sqlite3

TOKEN = "8934137266:AAFqhml0_F3RdLExFZqhgASxl42tylMc_h8"
OWNER_ID = 8552447077

db = sqlite3.connect("dogs.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY,
balance INTEGER DEFAULT 10000
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS requests(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
type TEXT,
amount INTEGER,
info TEXT,
status TEXT
)
""")

db.commit()


def add_user(uid):
    cur.execute("INSERT OR IGNORE INTO users(id) VALUES(?)", (uid,))
    db.commit()


def balance(uid):
    add_user(uid)
    cur.execute("SELECT balance FROM users WHERE id=?", (uid,))
    return cur.fetchone()[0]


def change_balance(uid, amount):
    add_user(uid)
    cur.execute(
        "UPDATE users SET balance=balance+? WHERE id=?",
        (amount, uid)
    )
    db.commit()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    kb = [
        [InlineKeyboardButton("🚀 LIMBO", web_app=WebAppInfo(url="YOUR_MINI_APP_LINK"))],
        [
            InlineKeyboardButton("💳 Deposit", callback_data="deposit"),
            InlineKeyboardButton("📤 Withdraw", callback_data="withdraw")
        ],
        [InlineKeyboardButton("👑 Admin Panel", callback_data="admin")]
    ]

    await update.message.reply_text(
        f"🚀 DOGS LIMBO\n\n💰 Balance: {balance(uid)} DOGS",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "deposit":
        context.user_data["step"] = "deposit"
        await q.message.reply_text(
            "💳 Deposit DOGS\n\n"
            "فرمت:\nULTRA 5000 DOGS @IQ7XA\n\n"
            "ولت:\nUQAhqiO6qZc_aRpkIygNulDUw64jCSR_VXX7Vg2Cbbv1Uz1h\n\n"
            "شات یا لینک تراکنش را ارسال کن."
        )

    elif q.data == "withdraw":
        context.user_data["step"] = "withdraw_amount"
        await q.message.reply_text("📤 تعداد DOGS برداشت را بفرست.")

    elif q.data == "admin":
        if q.from_user.id == OWNER_ID:
            await q.message.reply_text("👑 پنل مدیریت\n\n💳 واریزی‌ها\n📤 برداشت‌ها\n📊 آمار")
        else:
            await q.message.reply_text("❌ دسترسی ندارید")


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("step")

    if not step:
        return

    uid = update.effective_user.id
    text = update.message.text

    if step == "deposit":
        cur.execute(
            "INSERT INTO requests(user_id,type,amount,info,status) VALUES(?,?,?,?,?)",
            (uid, "deposit", 0, text, "pending")
        )
        db.commit()

        await context.bot.send_message(
            OWNER_ID,
            f"🔔 واریزی جدید\n\n👤 {uid}\n📝 {text}\n\n⏳ در انتظار تایید"
        )
        await update.message.reply_text("✅ برای مالک ارسال شد")
        context.user_data.clear()

    elif step == "withdraw_amount":
        context.user_data["amount"] = int(text)
        context.user_data["step"] = "withdraw_user"
        await update.message.reply_text("👤 آیدی کاربری مقصد را بفرست (مثال: username@)")

    elif step == "withdraw_user":
        amount = context.user_data["amount"]

        cur.execute(
            "INSERT INTO requests(user_id,type,amount,info,status) VALUES(?,?,?,?,?)",
            (uid, "withdraw", amount, text, "pending")
        )
        db.commit()

        await context.bot.send_message(
            OWNER_ID,
            f"🔔 برداشت جدید\n\n👤 {uid}\n💰 {amount} DOGS\n👤 مقصد: {text}\n\n⏳ در انتظار تایید"
        )

        await update.message.reply_text("✅ درخواست برداشت ارسال شد")
        context.user_data.clear()


app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

print("DOGS BOT RUNNING")
app.run_polling()
