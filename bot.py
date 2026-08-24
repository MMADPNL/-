from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
import sqlite3


TOKEN = "8934137266:AAFqhml0_F3RdLExFZqhgASxl42tylMc_h8"
OWNER_ID = 8552447077


db = sqlite3.connect(
    "dogs.db",
    check_same_thread=False
)

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
    cur.execute(
        "INSERT OR IGNORE INTO users(id) VALUES(?)",
        (uid,)
    )
    db.commit()


def balance(uid):
    add_user(uid)

    cur.execute(
        "SELECT balance FROM users WHERE id=?",
        (uid,)
    )

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
        [
            InlineKeyboardButton(
                "🚀 LIMBO",
                callback_data="limbo"
            )
        ],
        [
            InlineKeyboardButton(
                "💳 Deposit",
                callback_data="deposit"
            ),
            InlineKeyboardButton(
                "📤 Withdraw",
                callback_data="withdraw"
            )
        ],
        [
            InlineKeyboardButton(
                "👑 Admin",
                callback_data="admin"
            )
        ]
    ]

    await update.message.reply_text(
        f"🚀 DOGS LIMBO\n\n💰 Balance: {balance(uid)} DOGS",
        reply_markup=InlineKeyboardMarkup(kb)

        async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query
    await q.answer()


    if q.data == "limbo":

        await q.message.reply_text(
            "🚀 LIMBO آماده است"
        )


    elif q.data == "deposit":

        context.user_data["step"] = "deposit"

        await q.message.reply_text(
"""
💳 Deposit DOGS

فرمت:

ULTRA 5000 DOGS @IQ7XA

ولت:

UQAhqiO6qZc_aRpkIygNulDUw64jCSR_VXX7Vg2Cbbv1Uz1h

شات یا لینک تراکنش را بفرست.
"""
        )


    elif q.data == "withdraw":

        context.user_data["step"] = "withdraw_amount"

        await q.message.reply_text(
            "📤 مقدار DOGS برای برداشت را بفرست."
        )


    elif q.data == "admin":

        if q.from_user.id == OWNER_ID:

            kb = [
                [
                    InlineKeyboardButton(
                        "📊 آمار",
                        callback_data="stats"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "📋 درخواست‌ها",
                        callback_data="requests"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "💰 شارژ",
                        callback_data="add_balance"
                    )
                ]
            ]


            await q.message.reply_text(
                "👑 پنل مدیریت",
                reply_markup=InlineKeyboardMarkup(kb)
            )

        else:

            await q.message.reply_text(
                "❌ دسترسی ندارید"
            )



async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    step = context.user_data.get("step")

    if not step:
        return


    uid = update.effective_user.id

    msg = update.message.text



    if step == "deposit":

        cur.execute(
"""
INSERT INTO requests
(user_id,type,amount,info,status)
VALUES(?,?,?,?,?)
""",
(
uid,
"deposit",
0,
msg,
"pending"
)
        )

        db.commit()


        await context.bot.send_message(
            OWNER_ID,
f"""
💳 واریزی جدید

👤 ID:
{uid}

📝:
{msg}
"""
        )


        await update.message.reply_text(
            "✅ درخواست واریزی ارسال شد"
        )



    elif step == "withdraw_amount":

        try:

            amount = int(msg)

        except:

            await update.message.reply_text(
                "❌ فقط عدد بفرست"
            )

            return


        context.user_data["amount"] = amount

        context.user_data["step"] = "withdraw_id"


        await update.message.reply_text(
            "👤 آیدی مقصد را بفرست (مثال: username@)"
        )



    elif step == "withdraw_id":

        amount = context.user_data["amount"]


        cur.execute(
"""
INSERT INTO requests
(user_id,type,amount,info,status)
VALUES(?,?,?,?,?)
""",
(
uid,
"withdraw",
amount,
msg,
"pending"
)
        )

        db.commit()


        await context.bot.send_message(
            OWNER_ID,
f"""
📤 برداشت جدید

👤 ID:
{uid}

💰 مقدار:
{amount} DOGS

📌 مقصد:
{msg}
"""
        )


        await update.message.reply_text(
            "✅ درخواست برداشت ارسال شد"
        )



    context.user_data.clear()

    # =========================
# ADMIN REQUESTS
# =========================


async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query
    await q.answer()


    if q.from_user.id != OWNER_ID:
        return



    if q.data == "stats":

        cur.execute(
            "SELECT COUNT(*) FROM users"
        )

        users = cur.fetchone()[0]


        await q.message.reply_text(
            f"📊 تعداد کاربران: {users}"
        )



    elif q.data == "requests":


        cur.execute(
"""
SELECT id,user_id,type,amount,info
FROM requests
WHERE status='pending'
"""
        )

        rows = cur.fetchall()



        if not rows:

            await q.message.reply_text(
                "📭 درخواست در انتظار نیست"
            )

            return



        for row in rows:

            rid, uid, typ, amount, info = row


            kb = [

                [
                    InlineKeyboardButton(
                        "✅ تایید",
                        callback_data=f"ok_{rid}"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "❌ رد",
                        callback_data=f"no_{rid}"
                    )
                ]

            ]


            await q.message.reply_text(
f"""
📋 درخواست جدید

👤 کاربر:
{uid}

📌 نوع:
{typ}

💰 مقدار:
{amount}

📝 اطلاعات:
{info}
""",
reply_markup=InlineKeyboardMarkup(kb)
            )



    elif q.data == "add_balance":

        context.user_data["admin_step"] = "add"

        await q.message.reply_text(
"""
💰 شارژ کاربر

فرمت:

ID مقدار

مثال:

123456 5000
"""
        )



# =========================
# تایید / رد
# =========================


async def confirm_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query
    await q.answer()


    if q.from_user.id != OWNER_ID:
        return


    action, rid = q.data.split("_")

    rid = int(rid)



    cur.execute(
"""
SELECT user_id,type,amount
FROM requests
WHERE id=?
""",
(rid,)
    )


    row = cur.fetchone()


    if not row:
        return



    uid, typ, amount = row



    if action == "ok":


        if typ == "deposit":

            # مقدار واریزی فعلا دستی است
            change_balance(
                uid,
                amount
            )


        elif typ == "withdraw":

            change_balance(
                uid,
                -amount
            )



        cur.execute(
"""
UPDATE requests
SET status='approved'
WHERE id=?
""",
(rid,)
        )


        await context.bot.send_message(
            uid,
            "✅ درخواست شما تایید شد"
        )


        await q.edit_message_text(
            "✅ تایید شد"
        )



    else:


        cur.execute(
"""
UPDATE requests
SET status='rejected'
WHERE id=?
""",
(rid,)
        )


        await context.bot.send_message(
            uid,
            "❌ درخواست شما رد شد"
        )


        await q.edit_message_text(
            "❌ رد شد"
        )


    db.commit()

    # =========================
# ADMIN TEXT
# =========================


async def admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        return


    step = context.user_data.get("admin_step")


    if step != "add":
        return


    try:

        uid, amount = update.message.text.split()

        uid = int(uid)

        amount = int(amount)


    except:

        await update.message.reply_text(
            "❌ فرمت اشتباه\nمثال:\n123456 5000"
        )

        return



    change_balance(
        uid,
        amount
    )


    await update.message.reply_text(
        "✅ موجودی اضافه شد"
    )


    await context.bot.send_message(
        uid,
        f"💰 {amount} DOGS به موجودی شما اضافه شد"
    )


    context.user_data.clear()



# =========================
# START BOT
# =========================


app = Application.builder().token(TOKEN).build()


# شروع
app.add_handler(
    CommandHandler(
        "start",
        start
    )
)


# همه دکمه‌ها
app.add_handler(
    CallbackQueryHandler(
        buttons
    )
)


# دکمه‌های مدیریت
app.add_handler(
    CallbackQueryHandler(
        admin_buttons
    )
)


# تایید و رد
app.add_handler(
    CallbackQueryHandler(
        confirm_buttons,
        pattern="^(ok|no)_"
    )
)


# پیام‌های کاربر
app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        text_handler
    )
)


# پیام‌های مدیر
app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        admin_text
    )
)


print("🚀 DOGS LIMBO BOT RUNNING")


app.run_polling()
    )
