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



def get_balance(uid):

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


    keyboard = [

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
                "👑 Admin Panel",
                callback_data="admin"
            )
        ]

    ]


    await update.message.reply_text(
        f"""
🚀 DOGS LIMBO

💰 Balance:
{get_balance(uid)} DOGS
""",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

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


شات یا لینک تراکنش را ارسال کن.
"""
        )



    elif q.data == "withdraw":

        context.user_data["step"] = "withdraw_amount"


        await q.message.reply_text(
            "📤 مقدار برداشت DOGS را بفرست."
        )



    elif q.data == "admin":

        if q.from_user.id == OWNER_ID:

            await q.message.reply_text(
                "👑 پنل مدیریت"
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

    text = update.message.text




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
text,
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


📝 رسید:

{text}


⏳ در انتظار تایید
"""
        )


        await update.message.reply_text(
            "✅ درخواست واریزی ارسال شد"
        )



    elif step == "withdraw_amount":


        try:

            amount = int(text)


        except:


            await update.message.reply_text(
                "❌ فقط عدد بفرست"
            )

            return



        context.user_data["amount"] = amount

        context.user_data["step"] = "withdraw_id"



        await update.message.reply_text(
            "👤 آیدی مقصد را بفرست\nمثال: username@"
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
text,
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
{text}
"""
        )



        await update.message.reply_text(
            "✅ درخواست برداشت ارسال شد"
        )



    context.user_data.clear()

async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query

    await q.answer()


    if q.from_user.id != OWNER_ID:
        return



    if q.data == "stats":

        cur.execute(
            "SELECT COUNT(*) FROM users"
        )

        count = cur.fetchone()[0]


        await q.message.reply_text(
            f"📊 تعداد کاربران: {count}"
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
                "📭 درخواستی وجود ندارد"
            )

            return



        for row in rows:


            rid, uid, typ, amount, info = row


            keyboard = [

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
📋 درخواست

👤 کاربر:
{uid}

📌 نوع:
{typ}

💰 مقدار:
{amount}

📝 اطلاعات:
{info}
""",
reply_markup=InlineKeyboardMarkup(keyboard)
            )





async def confirm_request(update: Update, context: ContextTypes.DEFAULT_TYPE):

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
# RUN BOT
# =========================


app = Application.builder().token(TOKEN).build()



# شروع
app.add_handler(
    CommandHandler(
        "start",
        start
    )
)



# دکمه‌های اصلی
app.add_handler(
    CallbackQueryHandler(
        buttons
    )
)



# تایید و رد مالک
app.add_handler(
    CallbackQueryHandler(
        confirm_request,
        pattern="^(ok|no)_"
    )
)



# پنل مدیریت
app.add_handler(
    CallbackQueryHandler(
        admin_buttons,
        pattern="^(stats|requests)$"
    )
)



# پیام‌های کاربر
app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        text_handler
    )
)



print("🚀 DOGS LIMBO BOT RUNNING")


app.run_polling()
