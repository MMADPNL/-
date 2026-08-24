# ==============================
# DOGS LIMBO BOT
# Virtual DOGS
# ==============================

import sqlite3
import random

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)


# ==============================
# تنظیمات
# ==============================

TOKEN = "8934137266:AAFqhml0_F3RdLExFZqhgASxl42tylMc_h8"

OWNER_ID = 8552447077

BOT_STATUS = True



# ==============================
# دیتابیس
# ==============================

db = sqlite3.connect(
    "dogs_limbo.db",
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
CREATE TABLE IF NOT EXISTS history(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
text TEXT
)
""")


cur.execute("""
CREATE TABLE IF NOT EXISTS deposits(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
amount INTEGER,
photo TEXT,
status TEXT
)
""")


db.commit()



# ==============================
# توابع کاربر
# ==============================

def add_user(uid):

    cur.execute(
        """
        INSERT OR IGNORE INTO users(id)
        VALUES(?)
        """,
        (uid,)
    )

    db.commit()



def balance(uid):

    add_user(uid)

    cur.execute(
        """
        SELECT balance
        FROM users
        WHERE id=?
        """,
        (uid,)
    )

    return cur.fetchone()[0]



def change_balance(uid,amount):

    add_user(uid)

    cur.execute(
        """
        UPDATE users
        SET balance = balance + ?
        WHERE id=?
        """,
        (
            amount,
            uid
        )
    )

    db.commit()



def save_history(uid,text):

    cur.execute(
        """
        INSERT INTO history(user_id,text)
        VALUES(?,?)
        """,
        (
            uid,
            text
        )
    )

    db.commit()



# ==============================
# شروع
# ==============================

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    uid = update.effective_user.id

    add_user(uid)

    await update.message.reply_text(
f"""
🚀 DOGS LIMBO

💰 موجودی:
{balance(uid)} DOGS


🎮 بازی:
مبلغ و ضریب را بفرست

مثال:

100 2.5
"""
    )

# ==============================
# بازی LIMBO 🚀
# ==============================

async def limbo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global BOT_STATUS


    if not BOT_STATUS:

        await update.message.reply_text(
            "🔴 ربات خاموش است"
        )
        return


    uid = update.effective_user.id

    add_user(uid)


    try:

        text = update.message.text.split()

        bet = int(text[0])

        target = float(text[1])


    except:

        await update.message.reply_text(
"""
❌ فرمت اشتباه

مثال:

100 2.5

100 = شرط DOGS
2.5 = ضریب هدف
"""
        )

        return



    if bet <= 0:

        await update.message.reply_text(
            "❌ مبلغ اشتباه است"
        )

        return



    if bet > balance(uid):

        await update.message.reply_text(
            "❌ DOGS کافی نداری"
        )

        return



    if target < 1.10:

        await update.message.reply_text(
            "❌ ضریب باید حداقل 1.10 باشد"
        )

        return



    # کم کردن شرط

    change_balance(
        uid,
        -bet
    )



    # ضریب انفجار

    crash = round(
        random.uniform(1.00,10.00),
        2
    )



    if target <= crash:


        win = int(
            bet * target
        )


        change_balance(
            uid,
            win
        )


        result = f"""
🚀 LIMBO

✅ بردی

🎯 ضریب:
x{target}

💰 شرط:
{bet} DOGS

🏆 جایزه:
+{win} DOGS
"""



    else:


        result = f"""
🚀 LIMBO

💥 باختی

🎯 ضریب انتخابی:
x{target}

💣 انفجار:
x{crash}

❌ باخت:
{bet} DOGS
"""



    save_history(
        uid,
        result
    )


    await update.message.reply_text(
        result
    )

# ==============================
# پنل مدیریت 👑
# ==============================


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:

        await update.message.reply_text(
            "❌ دسترسی ندارید"
        )

        return



    keyboard = [

        [
            InlineKeyboardButton(
                "💰 شارژ DOGS",
                callback_data="add"
            )
        ],

        [
            InlineKeyboardButton(
                "➖ کسر DOGS",
                callback_data="remove"
            )
        ],

        [
            InlineKeyboardButton(
                "📊 آمار",
                callback_data="stats"
            )
        ],

        [
            InlineKeyboardButton(
                "🟢/🔴 روشن خاموش",
                callback_data="toggle"
            )
        ],

        [
            InlineKeyboardButton(
                "🔄 انتقال مالکیت",
                callback_data="owner"
            )
        ]

    ]


    await update.message.reply_text(

        "👑 پنل مدیریت DOGS LIMBO",

        reply_markup=
        InlineKeyboardMarkup(keyboard)

    )





async def admin_buttons(update:Update, context:ContextTypes.DEFAULT_TYPE):

    global BOT_STATUS
    global OWNER_ID


    query = update.callback_query


    if query.from_user.id != OWNER_ID:

        return



    data = query.data



    if data=="stats":


        cur.execute(
            "SELECT COUNT(*) FROM users"
        )

        count = cur.fetchone()[0]


        await query.message.reply_text(
            f"📊 کاربران: {count}"
        )





    elif data=="toggle":


        BOT_STATUS = not BOT_STATUS


        status = (
            "🟢 روشن"
            if BOT_STATUS
            else
            "🔴 خاموش"
        )


        await query.message.reply_text(
            "وضعیت ربات: "+status
        )





    elif data=="add":


        context.user_data["admin_mode"]="add"


        await query.message.reply_text(
"""
💰 شارژ DOGS

فرمت:

آیدی مقدار

مثال:

123456 5000
"""
        )





    elif data=="remove":


        context.user_data["admin_mode"]="remove"


        await query.message.reply_text(
"""
➖ کسر DOGS

فرمت:

آیدی مقدار

مثال:

123456 1000
"""
        )





    elif data=="owner":


        context.user_data["admin_mode"]="owner"


        await query.message.reply_text(
            "🔄 آیدی مالک جدید را بفرست"
        )






async def admin_text(update:Update, context:ContextTypes.DEFAULT_TYPE):

    global OWNER_ID


    if update.effective_user.id != OWNER_ID:

        return



    mode = context.user_data.get(
        "admin_mode"
    )


    if not mode:

        return



    data = update.message.text.split()



    if mode=="add":


        uid = int(data[0])

        amount = int(data[1])


        change_balance(
            uid,
            amount
        )


        await update.message.reply_text(
            "✅ DOGS اضافه شد"
        )




    elif mode=="remove":


        uid = int(data[0])

        amount = int(data[1])


        change_balance(
            uid,
            -amount
        )


        await update.message.reply_text(
            "✅ DOGS کم شد"
        )




    elif mode=="owner":


        OWNER_ID = int(data[0])


        await update.message.reply_text(
            "✅ مالک تغییر کرد"
        )



    context.user_data.clear()

# ==============================
# واریز مجازی DOGS 📸
# ==============================


async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["deposit"] = True


    await update.message.reply_text(
"""
💳 درخواست واریز DOGS

مقدار DOGS را بفرست:

مثال:
5000
"""
    )





async def deposit_amount(update:Update, context:ContextTypes.DEFAULT_TYPE):


    if not context.user_data.get("deposit"):

        return



    try:

        amount = int(update.message.text)

    except:

        return



    context.user_data["deposit_amount"] = amount


    await update.message.reply_text(
        "📸 حالا عکس رسید را ارسال کن"
    )





async def deposit_photo(update:Update, context:ContextTypes.DEFAULT_TYPE):


    amount = context.user_data.get(
        "deposit_amount"
    )


    if not amount:

        return



    uid = update.effective_user.id


    photo = update.message.photo[-1].file_id



    cur.execute(
"""
INSERT INTO deposits
(user_id,amount,photo,status)

VALUES(?,?,?,?)
""",
(
uid,
amount,
photo,
"pending"
)
)


    dep_id = cur.lastrowid


    db.commit()



    keyboard = [

        [
            InlineKeyboardButton(
                "✅ تایید",
                callback_data=f"approve_{dep_id}"
            )
        ],

        [
            InlineKeyboardButton(
                "❌ رد",
                callback_data=f"reject_{dep_id}"
            )
        ]

    ]



    await context.bot.send_photo(

        chat_id=OWNER_ID,

        photo=photo,

        caption=f"""
🔔 درخواست واریز DOGS

👤 کاربر:
{uid}

💰 مقدار:
{amount} DOGS

شماره:
{dep_id}
""",

        reply_markup=
        InlineKeyboardMarkup(keyboard)

    )



    await update.message.reply_text(
        "✅ رسید برای مالک ارسال شد"
    )


    context.user_data.clear()





async def deposit_buttons(update:Update, context:ContextTypes.DEFAULT_TYPE):


    query = update.callback_query


    if query.from_user.id != OWNER_ID:

        return



    action, dep_id = query.data.split("_")


    dep_id = int(dep_id)



    cur.execute(
"""
SELECT user_id,amount,status
FROM deposits
WHERE id=?
""",
(dep_id,)
)


    data = cur.fetchone()



    if not data:

        return



    uid, amount, status = data



    if status != "pending":

        return





    if action=="approve":


        change_balance(
            uid,
            amount
        )


        cur.execute(
"""
UPDATE deposits
SET status='approved'
WHERE id=?
""",
(dep_id,)
)


        await context.bot.send_message(

            uid,

            f"""
✅ واریز تایید شد

+{amount} DOGS
"""
        )


        await query.edit_message_caption(
            "✅ تایید شد"
        )





    else:


        cur.execute(
"""
UPDATE deposits
SET status='rejected'
WHERE id=?
""",
(dep_id,)
)


        await context.bot.send_message(
            uid,
            "❌ واریز رد شد"
        )


        await query.edit_message_caption(
            "❌ رد شد"
        )



    db.commit()





# ==============================
# هندلرها
# ==============================


app.add_handler(
CommandHandler(
"admin",
admin
)
)


app.add_handler(
CommandHandler(
"deposit",
deposit
)
)


app.add_handler(
MessageHandler(
filters.PHOTO,
deposit_photo
)
)


app.add_handler(
CallbackQueryHandler(
deposit_buttons
)
)


app.add_handler(
CallbackQueryHandler(
admin_buttons
)
)


app.add_handler(
MessageHandler(
filters.TEXT & ~filters.COMMAND,
admin_text
)
)


app.add_handler(
MessageHandler(
filters.TEXT & ~filters.COMMAND,
limbo
)
)
