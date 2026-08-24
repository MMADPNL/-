# ==============================
# DOGS LIMBO BOT - FINAL
# ==============================

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import sqlite3
import logging
import re


# ==============================
# SETTINGS
# ==============================

TOKEN = "8934137266:AAFqhml0_F3RdLExFZqhgASxl42tylMc_h8"

OWNER_ID = 8552447077

MINI_APP_URL = "https://mmadpnl.github.io/-/"

DEFAULT_BALANCE = 10000

DB_FILE = "dogs.db"


# ==============================
# LOG
# ==============================

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ==============================
# DATABASE
# ==============================

db = sqlite3.connect(
    DB_FILE,
    check_same_thread=False
)

cur = db.cursor()


cur.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY,
    balance INTEGER NOT NULL DEFAULT 10000
)
""")


cur.execute("""
CREATE TABLE IF NOT EXISTS requests(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    amount INTEGER NOT NULL DEFAULT 0,
    info TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending'
)
""")


db.commit()


# ==============================
# USER
# ==============================

def add_user(uid):

    cur.execute(
        "INSERT OR IGNORE INTO users(id,balance) VALUES(?,?)",
        (uid, DEFAULT_BALANCE)
    )

    db.commit()


def get_balance(uid):

    add_user(uid)

    cur.execute(
        "SELECT balance FROM users WHERE id=?",
        (uid,)
    )

    row = cur.fetchone()

    if not row:
        return 0

    return int(row[0])


def change_balance(uid, amount):

    add_user(uid)

    current = get_balance(uid)

    new_balance = current + amount

    if new_balance < 0:
        return False

    cur.execute(
        "UPDATE users SET balance=? WHERE id=?",
        (new_balance, uid)
    )

    db.commit()

    return True


# ==============================
# START
# ==============================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    uid = update.effective_user.id

    balance = get_balance(uid)


    keyboard = [

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
{balance:,} DOGS
""",

        reply_markup=InlineKeyboardMarkup(
            keyboard
        )

    )


# ==============================
# BUTTONS
# ==============================

async def buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    uid = query.from_user.id


    # --------------------------
    # DEPOSIT
    # --------------------------

    if query.data == "deposit":

        context.user_data.clear()

        context.user_data["step"] = "deposit"


        await query.message.reply_text(

"""
💳 DEPOSIT DOGS

فرمت:

ULTRA 5000 DOGS @IQ7XA

ولت:

UQAhqiO6qZc_aRpkIygNulDUw64jCSR_VXX7Vg2Cbbv1Uz1h

شات یا لینک تراکنش یا رسید را ارسال کن.

بعد از ارسال، درخواست فوراً برای مالک ارسال می‌شود.
"""

        )

        return


    # --------------------------
    # WITHDRAW
    # --------------------------

    if query.data == "withdraw":

        context.user_data.clear()

        context.user_data["step"] = "withdraw_amount"


        await query.message.reply_text(

            "📤 مقدار DOGS برای برداشت را بفرست."

        )

        return


    # --------------------------
    # ADMIN
    # --------------------------

    if query.data == "admin":

        if uid != OWNER_ID:

            await query.message.reply_text(
                "❌ دسترسی ندارید."
            )

            return


        keyboard = [

            [
                InlineKeyboardButton(
                    "📊 آمار",
                    callback_data="admin_stats"
                )
            ],

            [
                InlineKeyboardButton(
                    "📋 درخواست‌ها",
                    callback_data="admin_requests"
                )
            ],

            [
                InlineKeyboardButton(
                    "💰 شارژ کاربر",
                    callback_data="admin_add"
                )
            ],

            [
                InlineKeyboardButton(
                    "➖ کسر موجودی",
                    callback_data="admin_remove"
                )
            ]

        ]


        await query.message.reply_text(

            "👑 DOGS ADMIN PANEL",

            reply_markup=InlineKeyboardMarkup(
                keyboard
            )

        )

        return


    # --------------------------
    # ADMIN STATS
    # --------------------------

    if query.data == "admin_stats":

        if uid != OWNER_ID:
            return


        cur.execute(
            "SELECT COUNT(*) FROM users"
        )

        users = cur.fetchone()[0]


        cur.execute(
            "SELECT COALESCE(SUM(balance),0) FROM users"
        )

        total = cur.fetchone()[0]


        await query.message.reply_text(

            f"""
📊 ADMIN STATS

👤 Users:
{users}

💰 Total DOGS:
{total:,}
"""

        )

        return


    # --------------------------
    # ADMIN REQUESTS
    # --------------------------

    if query.data == "admin_requests":

        if uid != OWNER_ID:
            return


        cur.execute("""

            SELECT
                id,
                user_id,
                type,
                amount,
                info

            FROM requests

            WHERE status='pending'

            ORDER BY id DESC

        """)


        rows = cur.fetchall()


        if not rows:

            await query.message.reply_text(
                "📭 درخواست در انتظار وجود ندارد."
            )

            return


        for row in rows:

            rid = row[0]

            user_id = row[1]

            typ = row[2]

            amount = row[3]

            info = row[4]


            if typ == "deposit":

                title = "💳 واریزی"

            else:

                title = "📤 برداشت"


            keyboard = [

                [

                    InlineKeyboardButton(
                        "✅ تایید",
                        callback_data=f"approve_{rid}"
                    ),

                    InlineKeyboardButton(
                        "❌ رد",
                        callback_data=f"reject_{rid}"
                    )

                ]

            ]


            await query.message.reply_text(

                f"""
{title}

🆔 Request:
{rid}

👤 User:
{user_id}

💰 Amount:
{amount:,} DOGS

📝 Info:
{info}

⏳ Pending
""",

                reply_markup=InlineKeyboardMarkup(
                    keyboard
                )

            )

        return


    # --------------------------
    # ADMIN ADD
    # --------------------------

    if query.data == "admin_add":

        if uid != OWNER_ID:
            return


        context.user_data.clear()

        context.user_data["admin_step"] = "add"


        await query.message.reply_text(

"""
💰 شارژ کاربر

فرمت:

ID مقدار

مثال:

123456789 5000
"""

        )

        return


    # --------------------------
    # ADMIN REMOVE
    # --------------------------

    if query.data == "admin_remove":

        if uid != OWNER_ID:
            return


        context.user_data.clear()

        context.user_data["admin_step"] = "remove"


        await query.message.reply_text(

"""
➖ کسر موجودی

فرمت:

ID مقدار

مثال:

123456789 1000
"""

        )

        return


# ==============================
# USER TEXT
# ==============================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    uid = update.effective_user.id

    text = update.message.text.strip()


    # ==========================
    # ADMIN
    # ==========================

    admin_step = context.user_data.get(
        "admin_step"
    )


    if uid == OWNER_ID and admin_step:

        parts = text.split()


        if len(parts) != 2:

            await update.message.reply_text(
                "❌ فرمت اشتباه است."
            )

            return


        try:

            target = int(parts[0])

            amount = int(parts[1])

        except ValueError:

            await update.message.reply_text(
                "❌ ID و مقدار باید عدد باشند."
            )

            return


        if amount <= 0:

            await update.message.reply_text(
                "❌ مقدار باید بیشتر از صفر باشد."
            )

            return


        if admin_step == "add":

            change_balance(
                target,
                amount
            )


            await update.message.reply_text(
                "✅ موجودی اضافه شد."
            )


            try:

                await context.bot.send_message(

                    target,

                    f"""
💰 موجودی شما شارژ شد.

+{amount:,} DOGS
"""

                )

            except Exception:

                pass


        elif admin_step == "remove":

            success = change_balance(
                target,
                -amount
            )


            if success:

                await update.message.reply_text(
                    "✅ موجودی کم شد."
                )

            else:

                await update.message.reply_text(
                    "❌ موجودی کاربر کافی نیست."
                )


        context.user_data.clear()

        return


    # ==========================
    # USER STEPS
    # ==========================

    step = context.user_data.get(
        "step"
    )


    if not step:

        return


    # ==========================
    # DEPOSIT
    # ==========================

    if step == "deposit":

        match = re.search(
            r"ULTRA\s+(\d+)",
            text,
            re.IGNORECASE
        )


        if match:

            amount = int(
                match.group(1)
            )

        else:

            amount = 0


        cur.execute(

"""
INSERT INTO requests
(user_id,type,amount,info,status)
VALUES(?,?,?,?,?)
""",

            (
                uid,
                "deposit",
                amount,
                text,
                "pending"
            )

        )


        request_id = cur.lastrowid

        db.commit()


        await context.bot.send_message(

            OWNER_ID,

            f"""
🔔 واریزی جدید

🆔 درخواست:
{request_id}

👤 کاربر:
{uid}

💰 مقدار:
{amount:,} DOGS

📝 رسید:
{text}

⏳ در انتظار تایید
"""

        )


        await update.message.reply_text(
            "✅ رسید برای مالک ارسال شد."
        )


        context.user_data.clear()

        return


    # ==========================
    # WITHDRAW AMOUNT
    # ==========================

    if step == "withdraw_amount":

        try:

            amount = int(text)

        except ValueError:

            await update.message.reply_text(
                "❌ فقط عدد وارد کن."
            )

            return


        if amount <= 0:

            await update.message.reply_text(
                "❌ مقدار باید بیشتر از صفر باشد."
            )

            return


        current_balance = get_balance(
            uid
        )


        if amount > current_balance:

            await update.message.reply_text(

                f"""
❌ موجودی کافی نیست.

💰 موجودی:
{current_balance:,} DOGS
"""

            )

            return


        context.user_data[
            "withdraw_amount"
        ] = amount


        context.user_data[
            "step"
        ] = "withdraw_id"


        await update.message.reply_text(

"""
🆔 آیدی عددی مقصد را بفرست.

مثال:

123456789

فقط آیدی عددی قبول می‌شود.
"""

        )

        return


    # ==========================
    # WITHDRAW ID
    # ==========================

    if step == "withdraw_id":

        try:

            destination = int(text)

        except ValueError:

            await update.message.reply_text(

                "❌ فقط آیدی عددی قبول می‌شود."

            )

            return


        if destination <= 0:

            await update.message.reply_text(
                "❌ آیدی نامعتبر است."
            )

            return


        amount = context.user_data.get(
            "withdraw_amount"
        )


        if not amount:

            context.user_data.clear()

            await update.message.reply_text(
                "❌ درخواست منقضی شد. دوباره شروع کن."
            )

            return


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
                str(destination),
                "pending"
            )

        )


        request_id = cur.lastrowid

        db.commit()


        await context.bot.send_message(

            OWNER_ID,

            f"""
🔔 برداشت جدید

🆔 درخواست:
{request_id}

👤 کاربر:
{uid}

💰 مقدار:
{amount:,} DOGS

📌 آیدی مقصد:
{destination}

⏳ در انتظار تایید
"""

        )


        await update.message.reply_text(
            "✅ درخواست برداشت برای مالک ارسال شد."
        )


        context.user_data.clear()

        return


# ==============================
# APPROVE / REJECT
# ==============================

async def request_action(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()


    if query.from_user.id != OWNER_ID:

        return


    action, request_id = query.data.split(
        "_",
        1
    )


    request_id = int(
        request_id
    )


    cur.execute(

"""
SELECT
    user_id,
    type,
    amount,
    info,
    status

FROM requests

WHERE id=?
""",

        (request_id,)

    )


    row = cur.fetchone()


    if not row:

        await query.edit_message_text(
            "❌ درخواست پیدا نشد."
        )

        return


    user_id = row[0]

    req_type = row[1]

    amount = row[2]

    status = row[4]


    if status != "pending":

        await query.edit_message_text(
            "ℹ️ این درخواست قبلاً بررسی شده."
        )

        return


    # ==========================
    # REJECT
    # ==========================

    if action == "reject":

        cur.execute(

"""
UPDATE requests
SET status='rejected'

WHERE id=?

AND status='pending'
""",

            (request_id,)

        )


        db.commit()


        await query.edit_message_text(
            "❌ درخواست رد شد."
        )


        try:

            await context.bot.send_message(

                user_id,

                "❌ درخواست شما رد شد."

            )

        except Exception:

            pass


        return


    # ==========================
    # APPROVE DEPOSIT
    # ==========================

    if req_type == "deposit":

        if amount <= 0:

            await query.edit_message_text(

                "❌ مبلغ واریزی از رسید تشخیص داده نشد. "
                "مقدار را از پنل شارژ کنید."

            )

            return


        change_balance(
            user_id,
            amount
        )


    # ==========================
    # APPROVE WITHDRAW
    # ==========================

    elif req_type == "withdraw":

        success = change_balance(
            user_id,
            -amount
        )


        if not success:

            await query.edit_message_text(

                "❌ موجودی کاربر کافی نیست؛ "
                "برداشت تایید نشد."

            )

            return


    cur.execute(

"""
UPDATE requests

SET status='approved'

WHERE id=?

AND status='pending'
""",

        (request_id,)

    )


    db.commit()


    await query.edit_message_text(
        "✅ درخواست تایید شد."
    )


    try:

        await context.bot.send_message(

            user_id,

            f"""
✅ درخواست شما تایید شد.

💰 مقدار:
{amount:,} DOGS

💳 موجودی فعلی:
{get_balance(user_id):,} DOGS
"""

        )

    except Exception:

        pass


# ==============================
# ERROR
# ==============================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.error(
        "BOT ERROR",
        exc_info=context.error
    )


# ==============================
# MAIN
# ==============================

def main():

    if TOKEN == "PUT_TOKEN_HERE":

        print(
            "❌ TOKEN را داخل bot.py وارد کن."
        )

        return


    app = Application.builder().token(
        TOKEN
    ).build()


    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )


    app.add_handler(

        CallbackQueryHandler(

            request_action,

            pattern=r"^(approve|reject)_\d+$"

        )

    )


    app.add_handler(

        CallbackQueryHandler(
            buttons
        )

    )


    app.add_handler(

        MessageHandler(

            filters.TEXT
            & ~filters.COMMAND,

            text_handler

        )

    )


    app.add_error_handler(
        error_handler
    )


    print(
        "🚀 DOGS LIMBO BOT RUNNING"
    )


    app.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":

    main()
