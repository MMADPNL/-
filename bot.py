import logging
import sqlite3
import random
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import asyncio

# ------ تنظیمات اولیه ------
TOKEN = "توکن_ربات_ت_را_اینجا_بگذار"  # از @BotFather بگیر
OWNER_ID = 8552447077
INITIAL_BALANCE = 1000
OWNER_INITIAL = 10000
WEBAPP_URL = "https://mmadpnl.github.io/-/"  # آدرس Mini App تو

logging.basicConfig(level=logging.INFO)

# ------ Flask برای API ------
app_flask = Flask(__name__)
CORS(app_flask)

# ------ دیتابیس ------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    dogs_balance INTEGER DEFAULT 1000
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    bet INTEGER,
                    target_multiplier REAL,
                    result_multiplier REAL,
                    win_loss TEXT,
                    date TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS deposits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount INTEGER,
                    info TEXT,
                    status TEXT DEFAULT 'pending'
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS withdrawals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount INTEGER,
                    username TEXT,
                    status TEXT DEFAULT 'pending'
                )''')
    c.execute("INSERT OR IGNORE INTO users (user_id, username, dogs_balance) VALUES (?, ?, ?)",
              (OWNER_ID, "owner", OWNER_INITIAL))
    conn.commit()
    conn.close()

init_db()

# ------ توابع کمکی دیتابیس ------
def get_balance(user_id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT dogs_balance FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def update_balance(user_id, amount):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("UPDATE users SET dogs_balance = dogs_balance + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()
    return get_balance(user_id)

def register_user(user_id, username):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, dogs_balance) VALUES (?, ?, ?)",
              (user_id, username, INITIAL_BALANCE))
    conn.commit()
    conn.close()

def save_game(user_id, bet, target, result, win_loss):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT INTO games (user_id, bet, target_multiplier, result_multiplier, win_loss, date) VALUES (?, ?, ?, ?, ?, ?)",
              (user_id, bet, target, result, win_loss, datetime.now().isoformat()))
    conn.commit()
    conn.close()

# ------ API های Flask برای Mini App ------
@app_flask.route('/api/balance', methods=['GET'])
def api_balance():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400
    try:
        user_id = int(user_id)
        balance = get_balance(user_id)
        if balance is None:
            return jsonify({'error': 'User not found'}), 404
        return jsonify({'balance': balance})
    except:
        return jsonify({'error': 'Invalid user_id'}), 400

@app_flask.route('/api/start-game', methods=['POST'])
def api_start_game():
    data = request.json
    user_id = data.get('user_id')
    bet = data.get('bet')
    target = data.get('target')
    if not user_id or not bet or not target:
        return jsonify({'error': 'Missing parameters'}), 400
    try:
        user_id = int(user_id)
        bet = int(bet)
        target = float(target)
        balance = get_balance(user_id)
        if balance is None:
            return jsonify({'error': 'User not found'}), 404
        if balance < bet:
            return jsonify({'error': 'Insufficient balance'}), 400
        
        # شبیه‌سازی بازی Crash
        crash_point = random.uniform(1.0, 5.0)
        win = False
        result_multiplier = crash_point
        if crash_point >= target:
            win = True
            win_amount = int(bet * target)
            new_balance = update_balance(user_id, win_amount - bet)  # برداشت شرط و اضافه کردن برد
        else:
            win_amount = 0
            new_balance = update_balance(user_id, -bet)  # کم کردن شرط
        
        save_game(user_id, bet, target, crash_point, 'win' if win else 'loss')
        
        return jsonify({
            'win': win,
            'crash_point': crash_point,
            'win_amount': win_amount,
            'new_balance': new_balance
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ------ دستورات ربات (Telegram) ------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user.id, user.username or "unknown")
    balance = get_balance(user.id)
    keyboard = [
        [InlineKeyboardButton("🚀 بازی DOGS Rocket", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("💰 موجودی", callback_data="balance")],
        [InlineKeyboardButton("📥 واریز", callback_data="deposit")],
        [InlineKeyboardButton("📤 برداشت", callback_data="withdraw")],
    ]
    if user.id == OWNER_ID:
        keyboard.append([InlineKeyboardButton("👑 پنل مدیریت", callback_data="admin_panel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"🐶 به DOGS Rocket خوش آمدی!\nموجودی شما: {balance} DOGS",
        reply_markup=reply_markup
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    balance = get_balance(user_id)
    await query.edit_message_text(f"💰 موجودی شما: {balance} DOGS")

async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📥 برای واریز، پیام زیر را به فرمت زیر ارسال کن:\n"
        "`ULTRA 5000 DOGS @IQ7XA`\n\n"
        "سپس منتظر تایید مالک باش."
    )

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📤 برای برداشت، مقدار و یوزرنیم خود را ارسال کن:\n"
        "مثلاً:\n`3000 @username`"
    )

async def handle_deposit_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    parts = text.split()
    if len(parts) >= 4 and parts[0].upper() == "ULTRA" and parts[2].upper() == "DOGS":
        try:
            amount = int(parts[1])
            code = parts[3]
            conn = sqlite3.connect("database.db")
            c = conn.cursor()
            c.execute("INSERT INTO deposits (user_id, amount, info) VALUES (?, ?, ?)",
                      (user_id, amount, f"{text}"))
            conn.commit()
            conn.close()
            await update.message.reply_text("✅ درخواست واریز ثبت شد، منتظر تایید مالک باشید.")
            await context.bot.send_message(
                OWNER_ID,
                f"📥 درخواست واریز جدید:\nکاربر: {user_id}\nمبلغ: {amount} DOGS\nکد: {code}\nبرای تایید /confirm_deposit {amount} {user_id}\nبرای رد /reject_deposit {amount} {user_id}"
            )
        except:
            await update.message.reply_text("❌ خطا در ثبت درخواست، دوباره تلاش کن.")
    else:
        await update.message.reply_text("❌ فرمت اشتباه، باید مثل: `ULTRA 5000 DOGS @IQ7XA`")

async def handle_withdraw_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    parts = text.split()
    if len(parts) == 2 and parts[0].isdigit():
        amount = int(parts[0])
        username = parts[1]
        balance = get_balance(user_id)
        if balance is None or balance < amount:
            await update.message.reply_text("❌ موجودی کافی نیست.")
            return
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT INTO withdrawals (user_id, amount, username) VALUES (?, ?, ?)",
                  (user_id, amount, username))
        conn.commit()
        conn.close()
        await update.message.reply_text("✅ درخواست برداشت ثبت شد، منتظر تایید مالک باشید.")
        await context.bot.send_message(
            OWNER_ID,
            f"📤 درخواست برداشت جدید:\nکاربر: {user_id}\nمبلغ: {amount} DOGS\nیوزر: {username}\nبرای تایید /confirm_withdraw {amount} {user_id}\nبرای رد /reject_withdraw {amount} {user_id}"
        )
    else:
        await update.message.reply_text("❌ فرمت اشتباه، باید مثل: `3000 @username`")

# ------ دستورات مدیریت مالک ------
async def confirm_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ دسترسی غیرمجاز")
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("فرمت: /confirm_deposit مقدار user_id")
        return
    amount = int(args[0])
    user_id = int(args[1])
    update_balance(user_id, amount)
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("UPDATE deposits SET status='confirmed' WHERE user_id=? AND amount=? AND status='pending'", (user_id, amount))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ واریز {amount} DOGS برای کاربر {user_id} تایید شد.")
    try:
        await context.bot.send_message(user_id, f"✅ واریز {amount} DOGS شما تایید شد و به موجودی اضافه گردید.")
    except:
        pass

async def reject_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ دسترسی غیرمجاز")
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("فرمت: /reject_deposit مقدار user_id")
        return
    amount = int(args[0])
    user_id = int(args[1])
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("UPDATE deposits SET status='rejected' WHERE user_id=? AND amount=? AND status='pending'", (user_id, amount))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"❌ واریز {amount} DOGS برای کاربر {user_id} رد شد.")
    try:
        await context.bot.send_message(user_id, f"❌ درخواست واریز {amount} DOGS شما رد شد.")
    except:
        pass

async def confirm_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ دسترسی غیرمجاز")
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("فرمت: /confirm_withdraw مقدار user_id")
        return
    amount = int(args[0])
    user_id = int(args[1])
    balance = get_balance(user_id)
    if balance is None or balance < amount:
        await update.message.reply_text("❌ موجودی کاربر کافی نیست.")
        return
    update_balance(user_id, -amount)
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("UPDATE withdrawals SET status='confirmed' WHERE user_id=? AND amount=? AND status='pending'", (user_id, amount))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ برداشت {amount} DOGS برای کاربر {user_id} تایید شد.")
    try:
        await context.bot.send_message(user_id, f"✅ برداشت {amount} DOGS شما تایید شد و از موجودی کسر گردید.")
    except:
        pass

async def reject_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ دسترسی غیرمجاز")
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("فرمت: /reject_withdraw مقدار user_id")
        return
    amount = int(args[0])
    user_id = int(args[1])
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("UPDATE withdrawals SET status='rejected' WHERE user_id=? AND amount=? AND status='pending'", (user_id, amount))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"❌ برداشت {amount} DOGS برای کاربر {user_id} رد شد.")
    try:
        await context.bot.send_message(user_id, f"❌ درخواست برداشت {amount} DOGS شما رد شد.")
    except:
        pass

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != OWNER_ID:
        await query.edit_message_text("⛔ دسترسی غیرمجاز")
        return
    keyboard = [
        [InlineKeyboardButton("👥 تعداد کاربران", callback_data="admin_users")],
        [InlineKeyboardButton("💰 کل موجودی", callback_data="admin_total_balance")],
        [InlineKeyboardButton("📥 لیست واریزها", callback_data="admin_deposits")],
        [InlineKeyboardButton("📤 لیست برداشت‌ها", callback_data="admin_withdrawals")],
        [InlineKeyboardButton("➕ اضافه کردن DOGS", callback_data="admin_add")],
        [InlineKeyboardButton("➖ کم کردن DOGS", callback_data="admin_sub")],
        [InlineKeyboardButton("📊 آمار بازی‌ها", callback_data="admin_stats")],
    ]
    await query.edit_message_text("👑 پنل مدیریت:", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != OWNER_ID:
        await query.edit_message_text("⛔ دسترسی غیرمجاز")
        return
    data = query.data
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    if data == "admin_users":
        c.execute("SELECT COUNT(*) FROM users")
        count = c.fetchone()[0]
        await query.edit_message_text(f"👥 تعداد کاربران: {count}")
    elif data == "admin_total_balance":
        c.execute("SELECT SUM(dogs_balance) FROM users")
        total = c.fetchone()[0] or 0
        await query.edit_message_text(f"💰 کل موجودی DOGS: {total}")
    elif data == "admin_deposits":
        c.execute("SELECT id, user_id, amount, status FROM deposits WHERE status='pending'")
        rows = c.fetchall()
        if not rows:
            await query.edit_message_text("📭 هیچ درخواست واریز در انتظاری نیست.")
        else:
            msg = "📥 لیست واریزهای در انتظار:\n"
            for row in rows:
                msg += f"ID: {row[0]} | کاربر: {row[1]} | مبلغ: {row[2]} | وضعیت: {row[3]}\n"
                msg += f"برای تایید: /confirm_deposit {row[2]} {row[1]}\nبرای رد: /reject_deposit {row[2]} {row[1]}\n\n"
            await query.edit_message_text(msg)
    elif data == "admin_withdrawals":
        c.execute("SELECT id, user_id, amount, status FROM withdrawals WHERE status='pending'")
        rows = c.fetchall()
        if not rows:
            await query.edit_message_text("📭 هیچ درخواست برداشت در انتظاری نیست.")
        else:
            msg = "📤 لیست برداشت‌های در انتظار:\n"
            for row in rows:
                msg += f"ID: {row[0]} | کاربر: {row[1]} | مبلغ: {row[2]} | وضعیت: {row[3]}\n"
                msg += f"برای تایید: /confirm_withdraw {row[2]} {row[1]}\nبرای رد: /reject_withdraw {row[2]} {row[1]}\n\n"
            await query.edit_message_text(msg)
    elif data == "admin_stats":
        c.execute("SELECT COUNT(*), SUM(win_loss='win'), SUM(win_loss='loss') FROM games")
        total, wins, losses = c.fetchone()
        await query.edit_message_text(f"📊 آمار بازی‌ها:\nکل بازی‌ها: {total}\nبرد: {wins or 0}\nباخت: {losses or 0}")
    elif data == "admin_add":
        await query.edit_message_text("برای اضافه کردن DOGS دستی، از دستور /add_dogs user_id amount استفاده کن.")
    elif data == "admin_sub":
        await query.edit_message_text("برای کم کردن DOGS دستی، از دستور /sub_dogs user_id amount استفاده کن.")
    conn.close()

async def add_dogs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ دسترسی غیرمجاز")
        return
    args = context.args
    if len(args) < 2 or not args[0].isdigit() or not args[1].isdigit():
        await update.message.reply_text("فرمت: /add_dogs user_id amount")
        return
    user_id, amount = int(args[0]), int(args[1])
    new_balance = update_balance(user_id, amount)
    await update.message.reply_text(f"✅ {amount} DOGS به کاربر {user_id} اضافه شد. موجودی جدید: {new_balance}")

async def sub_dogs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ دسترسی غیرمجاز")
        return
    args = context.args
    if len(args) < 2 or not args[0].isdigit() or not args[1].isdigit():
        await update.message.reply_text("فرمت: /sub_dogs user_id amount")
        return
    user_id, amount = int(args[0]), int(args[1])
    new_balance = update_balance(user_id, -amount)
    await update.message.reply_text(f"✅ {amount} DOGS از کاربر {user_id} کم شد. موجودی جدید: {new_balance}")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ دستور وجود ندارد")

# ------ اجرای همزمان Flask و Telegram ------
def run_flask():
    app_flask.run(host="0.0.0.0", port=5000)

def main():
    # اجرای Flask در ترد جداگانه
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # اجرای ربات تلگرام
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(balance, pattern="^balance$"))
    app.add_handler(CallbackQueryHandler(deposit, pattern="^deposit$"))
    app.add_handler(CallbackQueryHandler(withdraw, pattern="^withdraw$"))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))
    app.add_handler(CommandHandler("confirm_deposit", confirm_deposit))
    app.add_handler(CommandHandler("reject_deposit", reject_deposit))
    app.add_handler(CommandHandler("confirm_withdraw", confirm_withdraw))
    app.add_handler(CommandHandler("reject_withdraw", reject_withdraw))
    app.add_handler(CommandHandler("add_dogs", add_dogs))
    app.add_handler(CommandHandler("sub_dogs", sub_dogs))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_deposit_request))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_withdraw_request))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    print("ربات روشن شد 🚀")
    app.run_polling()

if __name__ == "__main__":
    main()
