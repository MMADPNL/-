import asyncio
import hashlib
import hmac
import json
import logging
import os
import sqlite3
import urllib.parse

from aiohttp import web
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
    ContextTypes,
    MessageHandler,
    filters,
)

# =========================================================
# SETTINGS
# =========================================================

TOKEN = "8934137266:AAFqhml0_F3RdLExFZqhgASxl42tylMc_h8"

OWNER_ID = 8552447077

MINI_APP_URL = "https://mmadpnl.github.io/-/"

# آدرس عمومی Replit را اینجا قرار بده
# مثال:
# https://your-project.replit.app
PUBLIC_API_URL = os.getenv(
    "PUBLIC_API_URL",
    "PUT_PUBLIC_REPLIT_URL_HERE"
)

PORT = int(os.getenv("PORT", "8080"))

DB_FILE = "dogs.db"

DEFAULT_BALANCE = 10000

BOT_STATUS = True

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

log = logging.getLogger("DOGS-LIMBO")

# =========================================================
# DATABASE
# =========================================================

db = sqlite3.connect(
    DB_FILE,
    check_same_thread=False
)

db.execute("PRAGMA journal_mode=WAL")
db.execute("PRAGMA busy_timeout=5000")

db.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY,
    username TEXT DEFAULT '',
    first_name TEXT DEFAULT '',
    balance INTEGER NOT NULL DEFAULT 10000
)
""")

db.commit()

db_lock = asyncio.Lock()


async def ensure_user(user):

    async with db_lock:

        db.execute(
            """
            INSERT INTO users(
                id,
                username,
                first_name,
                balance
            )
            VALUES(?,?,?,?)
            ON CONFLICT(id)
            DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name
            """,
            (
                user.id,
                user.username or "",
                user.first_name or "",
                DEFAULT_BALANCE
            )
        )

        db.commit()


async def get_balance(uid):

    async with db_lock:

        row = db.execute(
            """
            SELECT balance
            FROM users
            WHERE id=?
            """,
            (uid,)
        ).fetchone()

        if row is None:
            return 0

        return int(row[0])


async def change_balance(uid, amount):

    async with db_lock:

        row = db.execute(
            """
            SELECT balance
            FROM users
            WHERE id=?
            """,
            (uid,)
        ).fetchone()

        if row is None:
            return False

        old_balance = int(row[0])

        new_balance = old_balance + amount

        if new_balance < 0:
            return False

        db.execute(
            """
            UPDATE users
            SET balance=?
            WHERE id=?
            """,
            (
                new_balance,
                uid
            )
        )

        db.commit()

        return True


# =========================================================
# TELEGRAM MINI APP VALIDATION
# =========================================================

def validate_telegram_data(init_data):

    if not init_data:
        return None

    if TOKEN == "PUT_NEW_BOT_TOKEN_HERE":
        return None

    try:

        data = dict(
            urllib.parse.parse_qsl(
                init_data,
                keep_blank_values=True
            )
        )

        received_hash = data.pop(
            "hash",
            None
        )

        if not received_hash:
            return None

        data_check_string = "\n".join(
            f"{key}={data[key]}"
            for key in sorted(data)
        )

        secret_key = hmac.new(
            b"WebAppData",
            TOKEN.encode(),
            hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(
            calculated_hash,
            received_hash
        ):
            return None

        user_raw = data.get("user")

        if not user_raw:
            return None

        user = json.loads(user_raw)

        return int(user["id"])

    except Exception as e:

        log.error(
            "Mini App validation error: %s",
            e
        )

        return None


# =========================================================
# API
# =========================================================

async def api_health(request):

    return web.json_response({
        "ok": True,
        "status": "online",
        "service": "DOGS LIMBO"
    })


async def api_balance(request):

    init_data = request.headers.get(
        "X-Telegram-Init-Data",
        ""
    )

    uid = validate_telegram_data(
        init_data
    )

    if not uid:

        return web.json_response(
            {
                "ok": False,
                "error": "invalid_init_data"
            },
            status=401
        )

    balance = await get_balance(uid)

    return web.json_response({
        "ok": True,
        "user_id": uid,
        "balance": balance
    })


@web.middleware
async def cors_middleware(
    request,
    handler
):

    if request.method == "OPTIONS":

        response = web.Response(
            status=204
        )

    else:

        response = await handler(
            request
        )

    response.headers[
        "Access-Control-Allow-Origin"
    ] = "*"

    response.headers[
        "Access-Control-Allow-Headers"
    ] = (
        "Content-Type, "
        "X-Telegram-Init-Data"
    )

    response.headers[
        "Access-Control-Allow-Methods"
    ] = "GET, OPTIONS"

    return response


async def start_api():

    app = web.Application(
        middlewares=[
            cors_middleware
        ]
    )

    app.router.add_get(
        "/api/health",
        api_health
    )

    app.router.add_get(
        "/api/balance",
        api_balance
    )

    app.router.add_options(
        "/{tail:.*}",
        lambda request: web.Response(
            status=204
        )
    )

    runner = web.AppRunner(
        app
    )

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        PORT
    )

    await site.start()

    log.info(
        "API RUNNING ON PORT %s",
        PORT
    )


# =========================================================
# MAIN MENU
# =========================================================

def main_keyboard():

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
                "👑 پنل مدیریت",
                callback_data="admin"
            )
        ]

    ])


# =========================================================
# ADMIN MENU
# =========================================================

def admin_keyboard():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "📊 آمار",
                callback_data="admin_stats"
            ),

            InlineKeyboardButton(
                "👥 کاربران",
                callback_data="admin_users"
            )
        ],

        [
            InlineKeyboardButton(
                "💰 شارژ کاربر",
                callback_data="admin_add"
            ),

            InlineKeyboardButton(
                "➖ کسر موجودی",
                callback_data="admin_remove"
            )
        ],

        [
            InlineKeyboardButton(
                "🟢 وضعیت ربات",
                callback_data="admin_status"
            )
        ],

        [
            InlineKeyboardButton(
                "🔄 بروزرسانی",
                callback_data="admin"
            )
        ]

    ])


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    await ensure_user(user)

    balance = await get_balance(
        user.id
    )

    await update.message.reply_text(

        f"""
🚀 DOGS LIMBO

💰 موجودی شما:

{balance:,} DOGS
""",

        reply_markup=main_keyboard()
    )


# =========================================================
# BUTTONS
# =========================================================

async def buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    global BOT_STATUS

    query = update.callback_query

    await query.answer()

    user = query.from_user

    await ensure_user(user)

    data = query.data

    # -------------------------
    # BALANCE
    # -------------------------

    if data == "balance":

        balance = await get_balance(
            user.id
        )

        await query.message.reply_text(

            f"""
💰 موجودی شما

{balance:,} DOGS
"""
        )

        return

    # -------------------------
    # ADMIN
    # -------------------------

    if data == "admin":

        if user.id != OWNER_ID:

            await query.message.reply_text(
                "❌ دسترسی ندارید."
            )

            return

        await query.message.reply_text(

            """
👑 DOGS LIMBO ADMIN PANEL

پنل مدیریت را انتخاب کن:
""",

            reply_markup=admin_keyboard()
        )

        return

    # -------------------------
    # STATS
    # -------------------------

    if data == "admin_stats":

        if user.id != OWNER_ID:
            return

        async with db_lock:

            users = db.execute(
                """
                SELECT COUNT(*)
                FROM users
                """
            ).fetchone()[0]

            total = db.execute(
                """
                SELECT COALESCE(
                    SUM(balance),
                    0
                )
                FROM users
                """
            ).fetchone()[0]

        await query.message.reply_text(

            f"""
📊 آمار ربات

👥 کاربران:
{users}

💰 مجموع موجودی:
{total:,} DOGS

🟢 وضعیت:
{"روشن" if BOT_STATUS else "خاموش"}
"""
        )

        return

    # -------------------------
    # USERS
    # -------------------------

    if data == "admin_users":

        if user.id != OWNER_ID:
            return

        async with db_lock:

            rows = db.execute(
                """
                SELECT
                    id,
                    username,
                    first_name,
                    balance
                FROM users
                ORDER BY balance DESC
                LIMIT 20
                """
            ).fetchall()

        if not rows:

            await query.message.reply_text(
                "👥 کاربری وجود ندارد."
            )

            return

        text = "👥 کاربران\n\n"

        for uid, username, first_name, balance in rows:

            name = (
                first_name
                or username
                or str(uid)
            )

            text += (
                f"👤 {name}\n"
                f"🆔 {uid}\n"
                f"💰 {balance:,} DOGS\n\n"
            )

        await query.message.reply_text(
            text
        )

        return

    # -------------------------
    # ADD
    # -------------------------

    if data == "admin_add":

        if user.id != OWNER_ID:
            return

        context.user_data.clear()

        context.user_data[
            "admin_step"
        ] = "add"

        await query.message.reply_text(

            """
💰 شارژ کاربر

فرمت:

USER_ID AMOUNT

مثال:

123456789 5000
"""
        )

        return

    # -------------------------
    # REMOVE
    # -------------------------

    if data == "admin_remove":

        if user.id != OWNER_ID:
            return

        context.user_data.clear()

        context.user_data[
            "admin_step"
        ] = "remove"

        await query.message.reply_text(

            """
➖ کسر موجودی

فرمت:

USER_ID AMOUNT

مثال:

123456789 1000
"""
        )

        return

    # -------------------------
    # STATUS
    # -------------------------

    if data == "admin_status":

        if user.id != OWNER_ID:
            return

        await query.message.reply_text(

            f"""
🟢 وضعیت ربات

وضعیت:
{"🟢 روشن" if BOT_STATUS else "🔴 خاموش"}

🚀 API:
فعال
"""
        )

        return


# =========================================================
# ADMIN TEXT
# =========================================================

async def admin_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if user.id != OWNER_ID:
        return

    step = context.user_data.get(
        "admin_step"
    )

    if not step:
        return

    parts = update.message.text.split()

    if len(parts) != 2:

        await update.message.reply_text(
            "❌ فرمت اشتباه است."
        )

        return

    try:

        uid = int(parts[0])
        amount = int(parts[1])

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

    if step == "add":

        ok = await change_balance(
            uid,
            amount
        )

        if not ok:

            await update.message.reply_text(
                "❌ کاربر پیدا نشد."
            )

        else:

            new_balance = await get_balance(
                uid
            )

            await update.message.reply_text(

                f"""
✅ شارژ انجام شد

👤 ID:
{uid}

➕ مقدار:
{amount:,} DOGS

💰 موجودی جدید:
{new_balance:,} DOGS
"""
            )

    elif step == "remove":

        ok = await change_balance(
            uid,
            -amount
        )

        if not ok:

            await update.message.reply_text(
                "❌ کاربر پیدا نشد یا موجودی کافی نیست."
            )

        else:

            new_balance = await get_balance(
                uid
            )

            await update.message.reply_text(

                f"""
✅ کسر شد

👤 ID:
{uid}

➖ مقدار:
{amount:,} DOGS

💰 موجودی جدید:
{new_balance:,} DOGS
"""
            )

    context.user_data.clear()


# =========================================================
# ERROR
# =========================================================

async def error_handler(
    update,
    context
):

    log.error(
        "BOT ERROR",
        exc_info=context.error
    )


# =========================================================
# MAIN
# =========================================================

async def main():

    if TOKEN == "PUT_NEW_BOT_TOKEN_HERE":

        raise RuntimeError(
            "BOT_TOKEN را در Secrets قرار بده."
        )

    await start_api()

    application = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            buttons
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            admin_text
        )
    )

    application.add_error_handler(
        error_handler
    )

    print(
        "🚀 DOGS LIMBO BOT RUNNING"
    )

    await application.initialize()

    await application.start()

    await application.updater.start_polling(
        drop_pending_updates=True
    )

    await asyncio.Event().wait()


if __name__ == "__main__":

    asyncio.run(main())
