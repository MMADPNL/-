import os
import sqlite3
import logging
import asyncio

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
    ContextTypes,
    MessageHandler,
    filters
)


# ==========================
# تنظیمات
# ==========================

TOKEN = "8934137266:AAFqhml0_F3RdLExFZqhgASxl42tylMc_h8"

OWNER_ID = 8552447077

MINI_APP_URL = "https://mmadpnl.github.io/-/"


logging.basicConfig(
    level=logging.INFO
)


# ==========================
# دیتابیس
# ==========================

db = sqlite3.connect(
    "dogs.db",
    check_same_thread=False
)

cursor = db.cursor()


cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY,
    username TEXT,
    balance INTEGER DEFAULT 0
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS requests(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    type TEXT,
    amount INTEGER,
    username TEXT,
    status TEXT DEFAULT 'pending'
)
""")


db.commit()



# ==========================
# ساخت کاربر
# ==========================

def add_user(user):

    cursor.execute(
        """
        INSERT OR IGNORE INTO users
        (id,username,balance)
        VALUES(?,?,?)
        """,
        (
            user.id,
            user.username or "",
            0
        )
    )

    db.commit()



# ==========================
# موجودی
# ==========================

def get_balance(user_id):

    cursor.execute(
        """
        SELECT balance
        FROM users
        WHERE id=?
        """,
        (user_id,)
    )

    data = cursor.fetchone()

    if data:
        return data[0]

    return 0



def change_balance(user_id, amount):

    cursor.execute(
        """
        UPDATE users
        SET balance = balance + ?
        WHERE id=?
        """,
        (
            amount,
            user_id
        )
    )

    db.commit()



# ==========================
# منوی اصلی
# ==========================

def main_menu():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🚀 LIMBO",
                web_app=WebAppInfo(
                    url=MINI_APP_URL
                )
            )
        ],

        [
            InlineKeyboardButton(
                "💰 موجودی",
                callback_data="balance"
            )
        ],

        [
            InlineKeyboardButton(
                "💳 واریزی",
                callback_data="deposit"
            ),

            InlineKeyboardButton(
                "📤 برداشت",
                callback_data="withdraw"
            )
        ],

        [
            InlineKeyboardButton(
                "👑 پنل مدیریت",
                callback_data="admin"
            )
        ]

    ])



# ==========================
# پنل مالک
# ==========================

def admin_menu():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "💳 واریزی‌ها",
                callback_data="admin_deposit"
            )
        ],

        [
            InlineKeyboardButton(
                "📤 برداشت‌ها",
                callback_data="admin_withdraw"
            )
        ],

        [
            InlineKeyboardButton(
                "📊 آمار",
                callback_data="admin_stats"
            )
        ],

        [
            InlineKeyboardButton(
                "➕ شارژ کاربر",
                callback_data="admin_add"
            ),

            InlineKeyboardButton(
                "➖ کسر موجودی",
                callback_data="admin_remove"
            )
        ]

    ])
# ==========================
# /start
# ==========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    add_user(user)

    balance = get_balance(
        user.id
    )

    await update.message.reply_text(
        f"""
🚀 DOGS LIMBO

💰 موجودی شما:
{balance:,} DOGS
""",
        reply_markup=main_menu()
    )



# ==========================
# دکمه ها
# ==========================

async def buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    add_user(user)

    data = query.data



    # ----------------------
    # موجودی
    # ----------------------

    if data == "balance":

        balance = get_balance(
            user.id
        )

        await query.message.reply_text(
            f"""
💰 موجودی فعلی:

{balance:,} DOGS
"""
        )



    # ----------------------
    # واریزی
    # ----------------------

    elif data == "deposit":

        context.user_data[
            "deposit"
        ] = True


        await query.message.reply_text(
            """
💳 ثبت واریزی

فرمت ارسال:

ULTRA مقدار DOGS @username


مثال:

ULTRA 5000 DOGS @IQ7XA


بعد از ارسال متن، عکس یا شات رسید را بفرست.
"""
        )



    # ----------------------
    # برداشت
    # ----------------------

    elif data == "withdraw":

        context.user_data[
            "withdraw"
        ] = True


        await query.message.reply_text(
            """
📤 ثبت برداشت

فرمت:

مقدار @username


مثال:

5000 @IQ7XA
"""
        )



    # ----------------------
    # پنل مالک
    # ----------------------

    elif data == "admin":

        if user.id != OWNER_ID:

            await query.message.reply_text(
                "❌ دسترسی ندارید."
            )

            return


        await query.message.reply_text(
            """
👑 پنل مدیریت
""",
            reply_markup=admin_menu()
        )



# ==========================
# دریافت متن کاربر
# ==========================

async def user_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    text = update.message.text.strip()



    # ----------------------
    # واریزی
    # ----------------------

    if context.user_data.get(
        "deposit"
    ):


        parts = text.split()


        if len(parts) != 4:

            await update.message.reply_text(
                """
❌ فرمت اشتباه

مثال:

ULTRA 5000 DOGS @IQ7XA
"""
            )

            return


        if parts[0].upper() != "ULTRA":

            return


        amount = int(parts[1])

        username = parts[3]


        context.user_data[
            "deposit_info"
        ] = {
            "amount": amount,
            "username": username
        }


        await update.message.reply_text(
            """
✅ اطلاعات ثبت شد

حالا عکس رسید را ارسال کن.
"""
        )

        return



    # ----------------------
    # برداشت
    # ----------------------

    if context.user_data.get(
        "withdraw"
    ):


        parts = text.split()


        if len(parts) != 2:

            await update.message.reply_text(
                """
❌ فرمت اشتباه

مثال:

5000 @IQ7XA
"""
            )

            return


        amount = int(parts[0])

        username = parts[1]


        balance = get_balance(
            user.id
        )


        if amount > balance:

            await update.message.reply_text(
                "❌ موجودی کافی نیست."
            )

            return


        cursor.execute(
            """
            INSERT INTO requests
            (user_id,type,amount,username)
            VALUES(?,?,?,?)
            """,
            (
                user.id,
                "withdraw",
                amount,
                username
            )
        )


        db.commit()


        await update.message.reply_text(
            """
✅ درخواست برداشت ثبت شد.

منتظر تایید مالک باشید.
"""
        )


        await context.bot.send_message(
            OWNER_ID,
            f"""
📤 درخواست برداشت جدید

👤 کاربر:
{user.id}

💰 مقدار:
{amount} DOGS

📌 مقصد:
{username}
"""
        )


        context.user_data.clear()

        return
        # ==========================
# دریافت عکس رسید واریزی
# ==========================

async def photo_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user


    if not context.user_data.get(
        "deposit_info"
    ):

        return



    info = context.user_data[
        "deposit_info"
    ]


    amount = info["amount"]

    username = info["username"]



    cursor.execute(
        """
        INSERT INTO requests
        (user_id,type,amount,username)
        VALUES(?,?,?,?)
        """,
        (
            user.id,
            "deposit",
            amount,
            username
        )
    )


    db.commit()


    request_id = cursor.lastrowid



    await update.message.reply_text(
        """
✅ رسید ارسال شد.

منتظر تایید مالک باشید.
"""
    )



    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "✅ تایید واریز",
                callback_data=f"ok_dep_{request_id}"
            )
        ],

        [
            InlineKeyboardButton(
                "❌ رد واریز",
                callback_data=f"no_dep_{request_id}"
            )
        ]

    ])



    await context.bot.send_photo(

        OWNER_ID,

        photo=update.message.photo[-1].file_id,

        caption=f"""
💳 درخواست واریزی

🆔 شماره:
{request_id}

👤 کاربر:
{user.id}

💰 مقدار:
{amount} DOGS

📌 یوزر:
{username}
""",

        reply_markup=keyboard

    )


    context.user_data.clear()





# ==========================
# تایید و رد مالک
# ==========================


async def admin_actions(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()


    user = query.from_user


    if user.id != OWNER_ID:

        return



    data = query.data



    # ----------------------
    # تایید واریز
    # ----------------------

    if data.startswith(
        "ok_dep_"
    ):


        req_id = int(
            data.split("_")[2]
        )


        cursor.execute(
            """
            SELECT user_id,amount
            FROM requests
            WHERE id=?
            """,
            (req_id,)
        )


        req = cursor.fetchone()



        if not req:

            await query.message.reply_text(
                "❌ درخواست پیدا نشد."
            )

            return



        uid, amount = req



        change_balance(
            uid,
            amount
        )


        cursor.execute(
            """
            UPDATE requests
            SET status='approved'
            WHERE id=?
            """,
            (req_id,)
        )


        db.commit()



        await query.message.reply_text(
            "✅ واریزی تایید شد."
        )



        await context.bot.send_message(
            uid,
            f"""
✅ واریزی شما تایید شد.

➕ {amount} DOGS
"""
        )




    # ----------------------
    # رد واریز
    # ----------------------

    elif data.startswith(
        "no_dep_"
    ):


        req_id = int(
            data.split("_")[2]
        )


        cursor.execute(
            """
            SELECT user_id
            FROM requests
            WHERE id=?
            """,
            (req_id,)
        )


        req = cursor.fetchone()



        if req:

            cursor.execute(
                """
                UPDATE requests
                SET status='rejected'
                WHERE id=?
                """,
                (req_id,)
            )


            db.commit()



            await context.bot.send_message(
                req[0],
                """
❌ واریزی شما رد شد.
"""
            )



        await query.message.reply_text(
            "❌ واریزی رد شد."
        )
        # ==========================
# پنل مدیریت
# ==========================

async def admin_panel_buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user = query.from_user


    if user.id != OWNER_ID:

        return


    data = query.data



    # آمار

    if data == "admin_stats":

        cursor.execute(
            "SELECT COUNT(*) FROM users"
        )

        users = cursor.fetchone()[0]


        cursor.execute(
            "SELECT SUM(balance) FROM users"
        )

        total = cursor.fetchone()[0] or 0


        await query.message.reply_text(
            f"""
📊 آمار ربات

👥 کاربران:
{users}

💰 کل DOGS:
{total}
"""
        )



    # درخواست‌های واریز

    elif data == "admin_deposit":


        cursor.execute(
            """
            SELECT id,user_id,amount,username
            FROM requests
            WHERE type='deposit'
            AND status='pending'
            """
        )


        rows = cursor.fetchall()



        if not rows:

            await query.message.reply_text(
                "💳 واریزی در انتظار نداریم."
            )

            return



        text = "💳 واریزی‌های منتظر:\n\n"


        for r in rows:

            text += (
                f"ID: {r[0]}\n"
                f"User: {r[1]}\n"
                f"Amount: {r[2]} DOGS\n"
                f"{r[3]}\n\n"
            )


        await query.message.reply_text(
            text
        )




    # برداشت‌ها

    elif data == "admin_withdraw":


        cursor.execute(
            """
            SELECT id,user_id,amount,username
            FROM requests
            WHERE type='withdraw'
            AND status='pending'
            """
        )


        rows = cursor.fetchall()



        if not rows:

            await query.message.reply_text(
                "📤 برداشت در انتظار نداریم."
            )

            return



        text = "📤 برداشت‌ها:\n\n"


        for r in rows:

            text += (
                f"ID: {r[0]}\n"
                f"User: {r[1]}\n"
                f"Amount: {r[2]} DOGS\n"
                f"To: {r[3]}\n\n"
            )


        await query.message.reply_text(
            text
        )





# ==========================
# اجرای ربات
# ==========================

async def main():


    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )



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



    app.add_handler(
        CallbackQueryHandler(
            admin_actions,
            pattern="^(ok_dep_|no_dep_)"
        )
    )



    app.add_handler(
        CallbackQueryHandler(
            admin_panel_buttons,
            pattern="^admin_"
        )
    )



    app.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            user_text
        )
    )



    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            photo_handler
        )
    )



    print(
        "🚀 BOT STARTED"
    )



    await app.run_polling()





if __name__ == "__main__":

    asyncio.run(
        main()
        )
