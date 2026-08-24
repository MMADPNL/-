import os
import sqlite3
import logging
import random
import hashlib
import hmac
from datetime import datetime

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
# CONFIG
# ==========================

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

OWNER_ID = 8552447077

MINI_APP_URL = os.getenv(
    "MINI_APP_URL",
    "https://mmadpnl.github.io/-/"
)

DB_FILE = "limbo.db"

DEPOSIT_FORMAT = "ULTRA {amount} DOGS @IQ7XA"


logging.basicConfig(
    level=logging.INFO
)

logger = logging.getLogger(__name__)


# ==========================
# DATABASE
# ==========================

def db():

    conn = sqlite3.connect(DB_FILE)

    conn.row_factory = sqlite3.Row

    return conn



def init_db():

    conn = db()


    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        username TEXT DEFAULT '',
        balance REAL DEFAULT 0,
        created_at TEXT
    )
    """)


    conn.execute("""
    CREATE TABLE IF NOT EXISTS requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        type TEXT,
        amount REAL,
        proof TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT
    )
    """)


    conn.commit()

    conn.close()



def register_user(user):

    conn = db()

    conn.execute("""
    INSERT INTO users(
        user_id,
        username,
        created_at
    )

    VALUES(?,?,?)

    ON CONFLICT(user_id)

    DO UPDATE SET
    username=excluded.username
    """,
    (
        user.id,
        user.username or "",
        datetime.now().isoformat()
    ))

    conn.commit()

    conn.close()



def get_balance(user_id):

    conn = db()

    row = conn.execute(
        """
        SELECT balance
        FROM users
        WHERE user_id=?
        """,
        (user_id,)
    ).fetchone()

    conn.close()


    if not row:

        return 0


    return float(row["balance"])



def change_balance(
    user_id,
    amount
):

    conn = db()

    row = conn.execute(
        """
        SELECT balance
        FROM users
        WHERE user_id=?
        """,
        (user_id,)
    ).fetchone()


    if not row:

        conn.close()

        return False



    new_balance = (
        float(row["balance"])
        +
        amount
    )


    if new_balance < 0:

        conn.close()

        return False



    conn.execute(
        """
        UPDATE users
        SET balance=?
        WHERE user_id=?
        """,
        (
            new_balance,
            user_id
        )
    )


    conn.commit()

    conn.close()


    return True



# ==========================
# LIMBO GAME
# ==========================

def play_game(
    user_id,
    bet,
    target
):

    balance = get_balance(user_id)


    if bet <= 0:

        return {
            "ok":False,
            "error":"مبلغ اشتباه است"
        }


    if bet > balance:

        return {
            "ok":False,
            "error":"موجودی کافی نیست"
        }


    change_balance(
        user_id,
        -bet
    )


    crash = round(
        min(
            20,
            max(
                1,
                1 / max(
                    0.05,
                    random.random()
                )
            )
        ),
        2
    )


    if crash >= target:

        payout = bet * target

        change_balance(
            user_id,
            payout
        )


        return {
            "ok":True,
            "win":True,
            "crash":crash,
            "payout":payout,
            "balance":get_balance(user_id)
        }



    return {
        "ok":True,
        "win":False,
        "crash":crash,
        "payout":0,
        "balance":get_balance(user_id)
    }

# ==========================
# KEYBOARDS
# ==========================

def main_keyboard(user_id):

    buttons = [

        [
            InlineKeyboardButton(
                "🎮 LIMBO",
                web_app=WebAppInfo(
                    url=MINI_APP_URL
                )
            )
        ],

        [
            InlineKeyboardButton(
                "🐶 موجودی",
                callback_data="balance"
            ),

            InlineKeyboardButton(
                "💳 واریز",
                callback_data="deposit"
            )
        ]

    ]


    if user_id == OWNER_ID:

        buttons.append(
            [
                InlineKeyboardButton(
                    "👑 مدیریت",
                    callback_data="admin"
                )
            ]
        )


    return InlineKeyboardMarkup(buttons)



def admin_keyboard():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "💳 واریزی‌ها",
                callback_data="deposits"
            )
        ],

        [
            InlineKeyboardButton(
                "🔙 برگشت",
                callback_data="back"
            )
        ]

    ])



# ==========================
# START
# ==========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    register_user(user)


    await update.message.reply_text(

        f"🐶 LIMBO DOGS\n\n"
        f"💰 موجودی:\n"
        f"{get_balance(user.id):,.2f} DOGS",

        reply_markup=main_keyboard(
            user.id
        )
    )



# ==========================
# CALLBACKS
# ==========================

async def callbacks(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()


    user = query.from_user


    if query.data == "balance":


        await query.edit_message_text(

            f"🐶 موجودی شما:\n\n"
            f"{get_balance(user.id):,.2f} DOGS",

            reply_markup=main_keyboard(
                user.id
            )
        )


        return



    if query.data == "deposit":


        await query.edit_message_text(

            "💳 واریز DOGS\n\n"
            "مقدار را ارسال کنید.\n\n"
            "فرمت واریز:\n"
            "ULTRA مقدار DOGS @IQ7XA"

        )


        context.user_data["action"] = "deposit"

        return




    if query.data == "admin":


        if user.id != OWNER_ID:

            return


        await query.edit_message_text(

            "👑 پنل مدیریت",

            reply_markup=admin_keyboard()

        )

        return



    if query.data == "deposits":


        if user.id != OWNER_ID:

            return


        conn = db()


        rows = conn.execute(
            """
            SELECT *
            FROM requests
            WHERE type='deposit'
            AND status='pending'
            """
        ).fetchall()


        conn.close()



        if not rows:


            await query.edit_message_text(
                "موردی نیست.",
                reply_markup=admin_keyboard()
            )

            return



        text = "💳 واریزی‌های جدید:\n\n"


        buttons = []


        for row in rows:


            text += (

                f"🆔 #{row['id']}\n"
                f"👤 {row['user_id']}\n"
                f"🐶 {row['amount']} DOGS\n"
                f"📎 {row['proof']}\n\n"

            )


            buttons.append([

                InlineKeyboardButton(

                    "✅ تایید",

                    callback_data=
                    f"approve_{row['id']}"

                ),

                InlineKeyboardButton(

                    "❌ رد",

                    callback_data=
                    f"reject_{row['id']}"

                )

            ])



        await query.edit_message_text(

            text,

            reply_markup=InlineKeyboardMarkup(
                buttons
            )

        )

        return



    if query.data.startswith("approve_"):


        if user.id != OWNER_ID:

            return


        rid = int(
            query.data.split("_")[1]
        )


        process = await approve_request(
            rid,
            True,
            context
        )


        await query.edit_message_text(
            process,
            reply_markup=admin_keyboard()
        )


        return




    if query.data.startswith("reject_"):


        if user.id != OWNER_ID:

            return


        rid = int(
            query.data.split("_")[1]
        )


        process = await approve_request(
            rid,
            False,
            context
        )


        await query.edit_message_text(
            process,
            reply_markup=admin_keyboard()
        )

        return

    # =====================================================
    # ADMIN REMOVE USER
    # =====================================================

    if action == "admin_remove_user":

        if not is_owner(user.id):
            return

        try:
            target_id = int(text)

        except:

            await update.message.reply_text(
                "❌ ID باید عددی باشد.",
                reply_markup=cancel_keyboard()
            )

            return


        states[user.id] = {
            "action": "admin_remove_amount",
            "target_id": target_id
        }


        await update.message.reply_text(
            "🐶 مقدار DOGS برای کسر را وارد کنید:",
            reply_markup=cancel_keyboard()
        )

        return


    # =====================================================
    # ADMIN REMOVE AMOUNT
    # =====================================================

    if action == "admin_remove_amount":

        if not is_owner(user.id):
            return


        try:

            amount = float(
                text.replace(",", "")
            )

            if amount <= 0:
                raise ValueError


        except:

            await update.message.reply_text(
                "❌ عدد معتبر وارد کنید.",
                reply_markup=cancel_keyboard()
            )

            return


        target_id = state["target_id"]


        if change_balance(
            target_id,
            -amount
        ):


            await update.message.reply_text(
                f"✅ موجودی کسر شد.\n\n"
                f"👤 `{target_id}`\n"
                f"🐶 -{amount:,.2f} DOGS",
                parse_mode="Markdown",
                reply_markup=admin_keyboard()
            )


        else:

            await update.message.reply_text(
                "❌ کاربر پیدا نشد یا موجودی کافی نیست.",
                reply_markup=admin_keyboard()
            )


        states.pop(user.id, None)

        return



    # =====================================================
    # TRANSFER OWNER
    # =====================================================

    if action == "transfer_owner":

        if not is_owner(user.id):

            states.pop(user.id, None)

            return


        try:

            new_owner = int(text)


        except:

            await update.message.reply_text(
                "❌ ID باید عددی باشد.",
                reply_markup=cancel_keyboard()
            )

            return


        states.pop(user.id, None)


        await update.message.reply_text(
            f"👑 مالک جدید:\n"
            f"`{new_owner}`\n\n"
            f"برای تغییر دائمی باید OWNER_ID در کد عوض شود.",
            parse_mode="Markdown",
            reply_markup=admin_keyboard()
        )

        return



# =========================================================
# MEDIA HANDLER
# =========================================================

async def media_handler(update, context):

    user = update.effective_user

    register_user(user)

    state = states.get(user.id)


    if not state:

        await update.message.reply_text(
            "از منوی ربات استفاده کنید.",
            reply_markup=main_keyboard(user.id)
        )

        return


    if state.get("action") != "deposit_proof":

        await update.message.reply_text(
            "❌ در این مرحله فایل قابل قبول نیست.",
            reply_markup=cancel_keyboard()
        )

        return


    amount = state["amount"]

    deposit_format = state["deposit_format"]


    if update.message.photo:

        proof = "[IMAGE]"

    elif update.message.document:

        proof = "[DOCUMENT]"

    else:

        proof = "[FILE]"



    conn = db()


    conn.execute(
        """
        INSERT INTO requests
        (
            user_id,
            type,
            amount,
            username,
            proof,
            status,
            created_at
        )
        VALUES (
            ?,
            'deposit',
            ?,
            ?,
            ?,
            'pending',
            ?
        )
        """,
        (
            user.id,
            amount,
            user.username or "",
            proof,
            datetime.now().isoformat()
        )
    )


    conn.commit()


    request_id = conn.execute(
        "SELECT last_insert_rowid()"
    ).fetchone()[0]


    conn.close()


    states.pop(user.id,None)


    await update.message.reply_text(
        f"✅ درخواست واریز ثبت شد\n\n"
        f"🐶 `{amount:,.2f} DOGS`\n"
        f"📋 `{deposit_format}`\n"
        f"🆔 #{request_id}\n\n"
        f"⏳ در انتظار بررسی مالک.",
        parse_mode="Markdown",
        reply_markup=main_keyboard(user.id)
    )


    await send_owner_request(
        context,
        request_id,
        "deposit",
        user,
        amount,
        proof
    )

# =========================================================
# OWNER REQUEST
# =========================================================

async def send_owner_request(
    context,
    request_id,
    request_type,
    user,
    amount,
    proof
):

    if request_type == "deposit":

        title = "💳 **واریز جدید**"

        deposit_format = (
            f"{DEPOSIT_PREFIX} "
            f"{amount:g} DOGS "
            f"{DEPOSIT_WALLET}"
        )

        extra = (
            f"📋 فرمت واریز:\n"
            f"`{deposit_format}`\n\n"
        )

    else:

        title = "💸 **برداشت جدید**"

        extra = ""


    text = (
        f"{title}\n\n"
        f"🆔 درخواست: `#{request_id}`\n"
        f"👤 User ID: `{user.id}`\n"
        f"👤 Username: @{user.username or 'ندارد'}\n"
        f"🐶 مبلغ: `{amount:,.2f} DOGS`\n\n"
        f"{extra}"
        f"📎 اطلاعات:\n"
        f"{proof}"
    )


    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ تأیید",
                callback_data=f"approve_{request_id}"
            ),
            InlineKeyboardButton(
                "❌ رد",
                callback_data=f"reject_{request_id}"
            )
        ]
    ])


    try:

        await context.bot.send_message(
            OWNER_ID,
            text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )


    except Exception as e:

        logger.error(
            "OWNER SEND ERROR: %s",
            e
        )



# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(update, context):

    logger.error(
        "BOT ERROR",
        exc_info=context.error
    )



# =========================================================
# MAIN
# =========================================================

def main():

    if not BOT_TOKEN:

        raise RuntimeError(
            "BOT_TOKEN تنظیم نشده است."
        )


    init_db()


    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )


    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )


    application.add_handler(
        CommandHandler(
            "admin",
            admin_command
        )
    )


    application.add_handler(
        CallbackQueryHandler(
            callbacks
        )
    )


    application.add_handler(
        MessageHandler(
            filters.PHOTO |
            filters.Document.ALL,
            media_handler
        )
    )


    application.add_handler(
        MessageHandler(
            filters.TEXT &
            ~filters.COMMAND,
            text_handler
        )
    )


    application.add_error_handler(
        error_handler
    )


    print(
        "🐶 LIMBO DOGS BOT STARTED"
    )


    application.run_polling(
        drop_pending_updates=True
    )



# =========================================================
# START BOT
# =========================================================

if __name__ == "__main__":

    main()
