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

# DOGS LIMBO BOT - PART 2
# تایید و رد واریز و برداشت توسط مالک

# این بخش را به bot.py قبلی اضافه کن

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


async def admin_request_buttons(update, context):

    query = update.callback_query
    await query.answer()

    if query.from_user.id != OWNER_ID:
        return

    data = query.data.split("_")

    if data[0] == "dep":
        req_id = int(data[2])

        cur.execute(
            "SELECT user_id, amount FROM requests WHERE id=? AND type='deposit'",
            (req_id,)
        )

        row = cur.fetchone()

        if not row:
            return

        uid, amount = row

        if data[1] == "ok":
            change_balance(uid, amount)

            cur.execute(
                "UPDATE requests SET status='approved' WHERE id=?",
                (req_id,)
            )

            await context.bot.send_message(
                uid,
                "✅ واریز شما تایید شد"
            )

            await query.edit_message_text(
                "✅ واریز تایید شد"
            )

        else:

            cur.execute(
                "UPDATE requests SET status='rejected' WHERE id=?",
                (req_id,)
            )

            await context.bot.send_message(
                uid,
                "❌ واریز شما رد شد"
            )

            await query.edit_message_text(
                "❌ واریز رد شد"
            )


    elif data[0] == "with":

        uid = int(data[2])
        amount = int(data[3])

        if data[1] == "ok":

            if balance(uid) >= amount:
                change_balance(uid, -amount)

            await context.bot.send_message(
                uid,
                "✅ برداشت شما تایید شد"
            )

            await query.edit_message_text(
                "✅ برداشت تایید شد"
            )

        else:

            await context.bot.send_message(
                uid,
                "❌ برداشت شما رد شد"
            )

            await query.edit_message_text(
                "❌ برداشت رد شد"
            )


# این خط را هم به هندلرها اضافه کن:
# app.add_handler(CallbackQueryHandler(admin_request_buttons))
# DOGS LIMBO ADMIN PANEL + HANDLERS
# این بخش آماده اضافه شدن به bot.py است

BOT_STATUS = True


async def admin_panel(update, context):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ دسترسی ندارید")
        return

    keyboard = [
        [InlineKeyboardButton("💰 شارژ کاربر", callback_data="adm_add")],
        [InlineKeyboardButton("➖ کسر موجودی", callback_data="adm_remove")],
        [InlineKeyboardButton("📊 آمار", callback_data="adm_stats")],
        [InlineKeyboardButton("🟢/🔴 وضعیت ربات", callback_data="adm_toggle")]
    ]

    await update.message.reply_text(
        "👑 پنل مدیریت DOGS",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def admin_panel_buttons(update, context):
    global BOT_STATUS

    query = update.callback_query
    await query.answer()

    if query.from_user.id != OWNER_ID:
        return

    if query.data == "adm_stats":
        cur.execute("SELECT COUNT(*) FROM users")
        count = cur.fetchone()[0]
        await query.message.reply_text(f"📊 کاربران: {count}")

    elif query.data == "adm_toggle":
        BOT_STATUS = not BOT_STATUS
        await query.message.reply_text(
            "وضعیت: " + ("🟢 روشن" if BOT_STATUS else "🔴 خاموش")
        )

    elif query.data == "adm_add":
        context.user_data["admin_action"] = "add"
        await query.message.reply_text("فرمت:\nآیدی مقدار\nمثال:\n123456 5000")

    elif query.data == "adm_remove":
        context.user_data["admin_action"] = "remove"
        await query.message.reply_text("فرمت:\nآیدی مقدار\nمثال:\n123456 1000")


async def admin_text(update, context):
    if update.effective_user.id != OWNER_ID:
        return

    action = context.user_data.get("admin_action")

    if not action:
        return

    try:
        uid, amount = update.message.text.split()
        uid = int(uid)
        amount = int(amount)
    except:
        await update.message.reply_text("❌ فرمت اشتباه")
        return

    if action == "add":
        change_balance(uid, amount)
        await update.message.reply_text("✅ اضافه شد")

    if action == "remove":
        change_balance(uid, -amount)
        await update.message.reply_text("✅ کم شد")

    context.user_data.clear()


# هندلرهای آماده:
app.add_handler(CommandHandler("admin", admin_panel))
app.add_handler(CallbackQueryHandler(admin_panel_buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text))
# ==============================
# تایید و رد واریز و برداشت
# ==============================

async def request_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.from_user.id != OWNER_ID:
        return


    data = query.data.split("_")


    # تایید واریز
    if data[0] == "deposit":

        req_id = int(data[2])

        cur.execute(
            """
            SELECT user_id, amount
            FROM requests
            WHERE id=?
            """,
            (req_id,)
        )

        row = cur.fetchone()

        if not row:
            return


        uid, amount = row


        if data[1] == "ok":

            change_balance(uid, amount)


            cur.execute(
                """
                UPDATE requests
                SET status='approved'
                WHERE id=?
                """,
                (req_id,)
            )


            await context.bot.send_message(
                uid,
                "✅ واریز شما تایید شد و موجودی اضافه شد"
            )


            await query.edit_message_text(
                "✅ واریز تایید شد"
            )


        else:


            cur.execute(
                """
                UPDATE requests
                SET status='rejected'
                WHERE id=?
                """,
                (req_id,)
            )


            await context.bot.send_message(
                uid,
                "❌ واریز شما رد شد"
            )


            await query.edit_message_text(
                "❌ واریز رد شد"
            )



    # تایید برداشت
    elif data[0] == "withdraw":


        uid = int(data[2])
        amount = int(data[3])


        if data[1] == "ok":


            if balance(uid) >= amount:

                change_balance(
                    uid,
                    -amount
                )


                await context.bot.send_message(
                    uid,
                    f"""
✅ برداشت تایید شد

💰 مقدار:
{amount} DOGS
"""
                )

            else:

                await query.message.reply_text(
                    "❌ موجودی کافی نیست"
                )



            await query.edit_message_text(
                "✅ برداشت تایید شد"
            )


        else:


            await context.bot.send_message(
                uid,
                "❌ برداشت شما رد شد"
            )


            await query.edit_message_text(
                "❌ برداشت رد شد"
            )



# ==============================
# جلوگیری از چند اجرای ربات
# ==============================

print("🚀 DOGS LIMBO FINAL RUNNING")


app.add_handler(
    CallbackQueryHandler(
        request_confirm
    )
)
