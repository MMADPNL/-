# ==============================
# DOGS LIMBO BOT V1
# ==============================

import sqlite3

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)


TOKEN = "8934137266:AAFqhml0_F3RdLExFZqhgASxl42tylMc_h8"

OWNER_ID = 8552447077


# ==============================
# DATABASE
# ==============================

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


db.commit()



def add_user(uid):

    cur.execute(
        """
        INSERT OR IGNORE INTO users(id)
        VALUES(?)
        """,
        (uid,)
    )

    db.commit()



def get_balance(uid):

    add_user(uid)

    cur.execute(
        """
        SELECT balance FROM users
        WHERE id=?
        """,
        (uid,)
    )

    return cur.fetchone()[0]



# ==============================
# START
# ==============================

async def start(update:Update, context:ContextTypes.DEFAULT_TYPE):

    uid = update.effective_user.id

    add_user(uid)


    keyboard = [

        [
            InlineKeyboardButton(
                "🚀 LIMBO",
                web_app=WebAppInfo(
                    url="https://YOUR-MINI-APP-LINK.com"
                )
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

🎮 Choose:
""",

reply_markup=InlineKeyboardMarkup(keyboard)

)



# ==============================
# BUTTONS
# ==============================

async def buttons(update:Update, context:ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()


    if query.data=="deposit":

        await query.message.reply_text(
"""
💳 Deposit DOGS

به زودی فعال می‌شود.
"""
        )


    elif query.data=="withdraw":

        await query.message.reply_text(
"""
📤 Withdraw DOGS

به زودی فعال می‌شود.
"""
        )


    elif query.data=="admin":


        if query.from_user.id != OWNER_ID:

            await query.message.reply_text(
                "❌ دسترسی ندارید"
            )

            return


        await query.message.reply_text(
"""
👑 ADMIN PANEL

💰 شارژ
➖ کسر
💳 واریزی
📤 برداشت
📊 آمار
"""
        )



# ==============================
# RUN
# ==============================

app = Application.builder().token(TOKEN).build()


app.add_handler(
    CommandHandler(
        "start",
        start
    )
)


app.add_handler(
    CallbackQueryHandler(
        buttons
    )
)


print("🚀 DOGS BOT RUNNING")


app.run_polling()
