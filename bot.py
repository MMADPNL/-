import os
import sqlite3
import logging
import asyncio
from datetime import datetime

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

# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# بعداً آدرس Mini App واقعی خودت را اینجا می‌گذاریم
MINI_APP_URL = os.getenv(
    "MINI_APP_URL",
    "https://example.com"
)

DB_FILE = "limbo.db"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# DATABASE
# =========================================================

def db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            first_name TEXT DEFAULT '',
            balance REAL DEFAULT 0,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            wallet TEXT DEFAULT '',
            username TEXT DEFAULT '',
            proof TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            sender_id INTEGER,
            text TEXT,
            created_at TEXT
        )
    """)

    cur.execute(
        "INSERT OR IGNORE INTO settings(key, value) VALUES('bot_enabled', '1')"
    )

    conn.commit()
    conn.close()


def register_user(user):
    conn = db()
    conn.execute("""
        INSERT INTO users
        (user_id, username, first_name, balance, created_at)
        VALUES (?, ?, ?, 0, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username=excluded.username,
            first_name=excluded.first_name
    """, (
        user.id,
        user.username or "",
        user.first_name or "",
        datetime.now().isoformat(),
    ))

    conn.commit()
    conn.close()


def get_balance(user_id):
    conn = db()
    row = conn.execute(
        "SELECT balance FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()
    conn.close()

    return float(row["balance"]) if row else 0


def change_balance(user_id, amount):
    conn = db()

    row = conn.execute(
        "SELECT balance FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()

    if not row:
        conn.close()
        return False

    new_balance = float(row["balance"]) + amount

    if new_balance < 0:
        conn.close()
        return False

    conn.execute(
        "UPDATE users SET balance=? WHERE user_id=?",
        (new_balance, user_id)
    )

    conn.commit()
    conn.close()
    return True


def bot_enabled():
    conn = db()
    row = conn.execute(
        "SELECT value FROM settings WHERE key='bot_enabled'"
    ).fetchone()
    conn.close()

    return row and row["value"] == "1"


def set_bot_enabled(value):
    conn = db()
    conn.execute(
        "UPDATE settings SET value=? WHERE key='bot_enabled'",
        ("1" if value else "0",)
    )
    conn.commit()
    conn.close()


# =========================================================
# HELPERS
# =========================================================

def is_owner(user_id):
    return user_id == OWNER_ID


def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🎮 LIMBO",
                web_app=WebAppInfo(url=MINI_APP_URL)
            )
        ],
        [
            InlineKeyboardButton("🐶 موجودی", callback_data="balance"),
            InlineKeyboardButton("💳 واریز", callback_data="deposit"),
        ],
        [
            InlineKeyboardButton("💸 برداشت", callback_data="withdraw"),
        ],
        [
            InlineKeyboardButton("📞 تماس با ما", callback_data="support"),
        ],
    ])


def cancel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ لغو", callback_data="cancel")]
    ])


async def safe_edit(query, text, keyboard=None):
    try:
        await query.edit_message_text(
            text,
            reply_markup=keyboard
        )
    except Exception:
        try:
            await query.message.reply_text(
                text,
                reply_markup=keyboard
            )
        except Exception:
            pass


# =========================================================
# USER STATES
# =========================================================

# user_id -> state
states = {}


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    register_user(user)

    if not bot_enabled() and not is_owner(user.id):
        await update.message.reply_text(
            "⛔ ربات موقتاً خاموش است."
        )
        return

    balance = get_balance(user.id)

    await update.message.reply_text(
        f"🐶 **LIMBO DOGS**\n\n"
        f"موجودی شما:\n"
        f"💰 `{balance:,.2f} DOGS`\n\n"
        f"از منوی زیر استفاده کنید.",
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )


# =========================================================
# CALLBACKS
# =========================================================

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user = query.from_user
    register_user(user)

    data = query.data

    # -------------------------
    # CANCEL
    # -------------------------

    if data == "cancel":
        states.pop(user.id, None)

        await safe_edit(
            query,
            "❌ عملیات لغو شد.",
            main_keyboard()
        )
        return

    # -------------------------
    # BALANCE
    # -------------------------

    if data == "balance":

        balance = get_balance(user.id)

        await safe_edit(
            query,
            f"🐶 موجودی شما:\n\n"
            f"💰 `{balance:,.2f} DOGS`",
            main_keyboard()
        )
        return

    # -------------------------
    # DEPOSIT
    # -------------------------

    if data == "deposit":

        states[user.id] = {
            "action": "deposit_amount"
        }

        await safe_edit(
            query,
            "💳 **واریز مجازی DOGS**\n\n"
            "تعداد DOGS را وارد کنید:\n\n"
            "مثال:\n"
            "`500`",
            cancel_keyboard()
        )
        return

    # -------------------------
    # WITHDRAW
    # -------------------------

    if data == "withdraw":

        states[user.id] = {
            "action": "withdraw_amount"
        }

        await safe_edit(
            query,
            "💸 **برداشت مجازی DOGS**\n\n"
            "تعداد DOGS موردنظر را وارد کنید:",
            cancel_keyboard()
        )
        return

    # -------------------------
    # SUPPORT
    # -------------------------

    if data == "support":

        states[user.id] = {
            "action": "support_target"
        }

        await safe_edit(
            query,
            "📞 تماس با کاربر\n\n"
            "برای ارسال پیام، ابتدا ID عددی کاربر را وارد کنید:",
            cancel_keyboard()
        )
        return

    # -------------------------
    # ADMIN
    # -------------------------

    if data == "admin":

        if not is_owner(user.id):
            return

        await show_admin(query)
        return

    if data == "admin_deposits":

        if not is_owner(user.id):
            return

        await admin_requests(query, "deposit")
        return

    if data == "admin_withdrawals":

        if not is_owner(user.id):
            return

        await admin_requests(query, "withdraw")
        return

    if data == "admin_toggle":

        if not is_owner(user.id):
            return

        current = bot_enabled()
        set_bot_enabled(not current)

        status = "روشن 🟢" if not current else "خاموش 🔴"

        await safe_edit(
            query,
            f"وضعیت ربات تغییر کرد:\n\n{status}",
            admin_keyboard()
        )
        return

    if data == "admin_add":

        if not is_owner(user.id):
            return

        states[user.id] = {
            "action": "admin_add_user"
        }

        await safe_edit(
            query,
            "💰 شارژ موجودی\n\n"
            "ID عددی کاربر را وارد کنید:",
            cancel_keyboard()
        )
        return

    if data == "admin_remove":

        if not is_owner(user.id):
            return

        states[user.id] = {
            "action": "admin_remove_user"
        }

        await safe_edit(
            query,
            "➖ کسر موجودی\n\n"
            "ID عددی کاربر را وارد کنید:",
            cancel_keyboard()
        )
        return

    if data == "admin_transfer":

        if not is_owner(user.id):
            return

        states[user.id] = {
            "action": "transfer_owner"
        }

        await safe_edit(
            query,
            "👑 انتقال مالکیت\n\n"
            "ID عددی مالک جدید را وارد کنید:",
            cancel_keyboard()
        )
        return

    # -------------------------
    # REQUEST APPROVE / REJECT
    # -------------------------

    if data.startswith("approve_"):

        if not is_owner(user.id):
            return

        request_id = int(data.split("_")[1])
        await process_request(query, request_id, True)
        return

    if data.startswith("reject_"):

        if not is_owner(user.id):
            return

        request_id = int(data.split("_")[1])
        await process_request(query, request_id, False)
        return


# =========================================================
# ADMIN
# =========================================================

def admin_keyboard():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💳 واریزی‌ها",
                callback_data="admin_deposits"
            )
        ],
        [
            InlineKeyboardButton(
                "💸 برداشت‌ها",
                callback_data="admin_withdrawals"
            )
        ],
        [
            InlineKeyboardButton(
                "➕ شارژ موجودی",
                callback_data="admin_add"
            ),
            InlineKeyboardButton(
                "➖ کسر موجودی",
                callback_data="admin_remove"
            ),
        ],
        [
            InlineKeyboardButton(
                "👑 انتقال مالکیت",
                callback_data="admin_transfer"
            )
        ],
        [
            InlineKeyboardButton(
                "🔄 روشن/خاموش",
                callback_data="admin_toggle"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 برگشت",
                callback_data="back"
            )
        ],
    ])


async def show_admin(query):

    if not is_owner(query.from_user.id):
        return

    status = "🟢 روشن" if bot_enabled() else "🔴 خاموش"

    await safe_edit(
        query,
        f"👑 **پنل مدیریت**\n\n"
        f"وضعیت ربات: {status}",
        admin_keyboard()
    )


async def admin_requests(query, request_type):

    conn = db()

    rows = conn.execute("""
        SELECT *
        FROM requests
        WHERE type=? AND status='pending'
        ORDER BY id DESC
        LIMIT 20
    """, (request_type,)).fetchall()

    conn.close()

    title = "💳 واریزی‌های در انتظار" if request_type == "deposit" \
        else "💸 برداشت‌های در انتظار"

    if not rows:
        await safe_edit(
            query,
            f"{title}\n\nموردی وجود ندارد.",
            admin_keyboard()
        )
        return

    text = title + "\n\n"

    buttons = []

    for row in rows:

        text += (
            f"#{row['id']}\n"
            f"👤 `{row['user_id']}`\n"
            f"🐶 {row['amount']:,.2f} DOGS\n"
            f"📅 {row['created_at']}\n\n"
        )

        buttons.append([
            InlineKeyboardButton(
                f"✅ تأیید #{row['id']}",
                callback_data=f"approve_{row['id']}"
            ),
            InlineKeyboardButton(
                f"❌ رد #{row['id']}",
                callback_data=f"reject_{row['id']}"
            ),
        ])

    buttons.append([
        InlineKeyboardButton(
            "🔙 برگشت",
            callback_data="admin"
        )
    ])

    await safe_edit(
        query,
        text,
        InlineKeyboardMarkup(buttons)
    )


# =========================================================
# REQUEST PROCESSING
# =========================================================

async def process_request(query, request_id, approve):

    conn = db()

    row = conn.execute(
        "SELECT * FROM requests WHERE id=?",
        (request_id,)
    ).fetchone()

    if not row:
        conn.close()

        await safe_edit(
            query,
            "❌ درخواست پیدا نشد.",
            admin_keyboard()
        )
        return

    if row["status"] != "pending":
        conn.close()

        await safe_edit(
            query,
            "⚠️ این درخواست قبلاً بررسی شده است.",
            admin_keyboard()
        )
        return

    if approve:

        if row["type"] == "deposit":

            change_balance(
                row["user_id"],
                row["amount"]
            )

        elif row["type"] == "withdraw":

            # برای برداشت، موجودی قبلاً رزرو نشده؛
            # بنابراین هنگام تأیید کم می‌شود.
            if not change_balance(
                row["user_id"],
                -row["amount"]
            ):
                conn.close()

                await safe_edit(
                    query,
                    "❌ موجودی کاربر برای این برداشت کافی نیست.",
                    admin_keyboard()
                )
                return

        conn.execute(
            "UPDATE requests SET status='approved' WHERE id=?",
            (request_id,)
        )

        status_text = "تأیید شد ✅"

    else:

        conn.execute(
            "UPDATE requests SET status='rejected' WHERE id=?",
            (request_id,)
        )

        status_text = "رد شد ❌"

    conn.commit()
    conn.close()

    try:

        if approve:
            if row["type"] == "deposit":
                msg = (
                    "💳 درخواست واریز شما تأیید شد.\n\n"
                    f"🐶 +{row['amount']:,.2f} DOGS"
                )
            else:
                msg = (
                    "💸 درخواست برداشت شما تأیید شد.\n\n"
                    f"🐶 {row['amount']:,.2f} DOGS"
                )
        else:
            msg = (
                "❌ درخواست شما توسط مالک رد شد.\n\n"
                f"🐶 {row['amount']:,.2f} DOGS"
            )

        await query.get_bot().send_message(
            row["user_id"],
            msg
        )

    except Exception as e:
        logger.error(e)

    await safe_edit(
        query,
        f"درخواست #{request_id} {status_text}",
        admin_keyboard()
    )


# =========================================================
# TEXT HANDLER
# =========================================================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    register_user(user)

    text = update.message.text.strip()

    state = states.get(user.id)

    if not state:
        await update.message.reply_text(
            "از دکمه‌های منو استفاده کنید.",
            reply_markup=main_keyboard()
        )
        return

    action = state.get("action")

    # =====================================================
    # DEPOSIT AMOUNT
    # =====================================================

    if action == "deposit_amount":

        try:
            amount = float(text.replace(",", ""))

            if amount <= 0:
                raise ValueError

        except ValueError:

            await update.message.reply_text(
                "❌ فقط یک عدد معتبر وارد کنید.\n\n"
                "مثال: `500`",
                parse_mode="Markdown",
                reply_markup=cancel_keyboard()
            )
            return

        states[user.id] = {
            "action": "deposit_proof",
            "amount": amount
        }

        await update.message.reply_text(
            f"💳 مبلغ درخواست:\n"
            f"`{amount:,.2f} DOGS`\n\n"
            f"اکنون مدرک واریز مجازی را ارسال کنید.\n\n"
            f"می‌توانید پیام، لینک یا تصویر ارسال کنید.",
            parse_mode="Markdown",
            reply_markup=cancel_keyboard()
        )
        return

    # =====================================================
    # DEPOSIT PROOF
    # =====================================================

    if action == "deposit_proof":

        amount = state["amount"]

        proof = text

        if update.message.photo:
            proof = "[IMAGE]"

        elif update.message.document:
            proof = "[DOCUMENT]"

        conn = db()

        conn.execute("""
            INSERT INTO requests
            (user_id, type, amount, username, proof, status, created_at)
            VALUES (?, 'deposit', ?, ?, ?, 'pending', ?)
        """, (
            user.id,
            amount,
            user.username or "",
            proof,
            datetime.now().isoformat()
        ))

        conn.commit()
        request_id = conn.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]

        conn.close()

        states.pop(user.id, None)

        await update.message.reply_text(
            f"✅ درخواست واریز ثبت شد.\n\n"
            f"🐶 مبلغ: `{amount:,.2f} DOGS`\n"
            f"🆔 درخواست: `#{request_id}`\n\n"
            f"در انتظار بررسی مالک است.",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )

        await send_owner_request(
            context,
            request_id,
            "deposit",
            user,
            amount,
            proof
        )

        return

    # =====================================================
    # WITHDRAW AMOUNT
    # =====================================================

    if action == "withdraw_amount":

        try:
            amount = float(text.replace(",", ""))

            if amount <= 0:
                raise ValueError

        except ValueError:

            await update.message.reply_text(
                "❌ فقط عدد معتبر وارد کنید.",
                reply_markup=cancel_keyboard()
            )
            return

        balance = get_balance(user.id)

        if amount > balance:

            await update.message.reply_text(
                f"❌ موجودی کافی نیست.\n\n"
                f"موجودی شما: `{balance:,.2f} DOGS`",
                parse_mode="Markdown",
                reply_markup=cancel_keyboard()
            )
            return

        states[user.id] = {
            "action": "withdraw_info",
            "amount": amount
        }

        await update.message.reply_text(
            "💸 اطلاعات برداشت را در یک پیام بفرستید.\n\n"
            "فرمت پیشنهادی:\n"
            "`ID: 123456789`\n"
            "`Username: @example`\n"
            "`Wallet: ...`",
            parse_mode="Markdown",
            reply_markup=cancel_keyboard()
        )
        return

    # =====================================================
    # WITHDRAW INFO
    # =====================================================

    if action == "withdraw_info":

        amount = state["amount"]

        conn = db()

        conn.execute("""
            INSERT INTO requests
            (user_id, type, amount, wallet, username, proof,
             status, created_at)
            VALUES (?, 'withdraw', ?, '', ?, ?, 'pending', ?)
        """, (
            user.id,
            amount,
            user.username or "",
            text,
            datetime.now().isoformat()
        ))

        conn.commit()

        request_id = conn.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]

        conn.close()

        states.pop(user.id, None)

        await update.message.reply_text(
            f"✅ درخواست برداشت ثبت شد.\n\n"
            f"🐶 مبلغ: `{amount:,.2f} DOGS`\n"
            f"🆔 درخواست: `#{request_id}`\n\n"
            f"در انتظار تأیید مالک است.",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )

        await send_owner_request(
            context,
            request_id,
            "withdraw",
            user,
            amount,
            text
        )

        return

    # =====================================================
    # SUPPORT TARGET
    # =====================================================

    if action == "support_target":

        if not is_owner(user.id):
            states.pop(user.id, None)
            return

        try:
            target_id = int(text)
        except ValueError:

            await update.message.reply_text(
                "❌ آیدی باید عددی باشد.\n"
                "مثال: `123456789`",
                parse_mode="Markdown",
                reply_markup=cancel_keyboard()
            )
            return

        states[user.id] = {
            "action": "support_message",
            "target_id": target_id
        }

        await update.message.reply_text(
            "✉️ حالا پیام موردنظر را ارسال کنید.",
            reply_markup=cancel_keyboard()
        )
        return

    # =====================================================
    # SUPPORT MESSAGE
    # =====================================================

    if action == "support_message":

        if not is_owner(user.id):
            states.pop(user.id, None)
            return

        target_id = state["target_id"]

        try:

            await context.bot.send_message(
                target_id,
                f"📩 پیام از مدیریت:\n\n{text}"
            )

            await update.message.reply_text(
                "✅ پیام ارسال شد.",
                reply_markup=admin_keyboard()
            )

        except Exception as e:

            logger.error(e)

            await update.message.reply_text(
                "❌ ارسال پیام انجام نشد. "
                "ممکن است کاربر ربات را مسدود کرده باشد.",
                reply_markup=admin_keyboard()
            )

        states.pop(user.id, None)
        return

    # =====================================================
    # ADMIN ADD USER
    # =====================================================

    if action == "admin_add_user":

        if not is_owner(user.id):
            states.pop(user.id, None)
            return

        try:
            target_id = int(text)
        except ValueError:

            await update.message.reply_text(
                "❌ ID باید عددی باشد.",
                reply_markup=cancel_keyboard()
            )
            return

        states[user.id] = {
            "action": "admin_add_amount",
            "target_id": target_id
        }

        await update.message.reply_text(
            "مقدار DOGS برای شارژ را وارد کنید:",
            reply_markup=cancel_keyboard()
        )
        return

    # =====================================================
    # ADMIN ADD AMOUNT
    # =====================================================

    if action == "admin_add_amount":

        if not is_owner(user.id):
            return

        try:
            amount = float(text.replace(",", ""))

            if amount <= 0:
                raise ValueError

        except ValueError:

            await update.message.reply_text(
                "❌ عدد معتبر وارد کنید.",
                reply_markup=cancel_keyboard()
            )
            return

        target_id = state["target_id"]

        if change_balance(target_id, amount):

            await update.message.reply_text(
                f"✅ موجودی شارژ شد.\n\n"
                f"👤 `{target_id}`\n"
                f"🐶 +{amount:,.2f} DOGS",
                parse_mode="Markdown",
                reply_markup=admin_keyboard()
            )

            try:
                await context.bot.send_message(
                    target_id,
                    f"💰 موجودی شما توسط مدیریت افزایش یافت.\n\n"
                    f"🐶 +{amount:,.2f} DOGS"
                )
            except Exception:
                pass

        else:

            await update.message.reply_text(
                "❌ کاربر پیدا نشد.",
                reply_markup=admin_keyboard()
            )

        states.pop(user.id, None)
        return

    # =====================================================
    # ADMIN REMOVE USER
    # =====================================================

    if action == "admin_remove_user":

        if not is_owner(user.id):
            return

        try:
            target_id = int(text)
        except ValueError:

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
            "مقدار DOGS برای کسر را وارد کنید:",
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
            amount = float(text.replace(",", ""))

            if amount <= 0:
                raise ValueError

        except ValueError:

            await update.message.reply_text(
                "❌ عدد معتبر وارد کنید.",
                reply_markup=cancel_keyboard()
            )
            return

        target_id = state["target_id"]

        if change_balance(target_id, -amount):

            await update.message.reply_text(
                f"✅ موجودی کسر شد.\n\n"
                f"👤 `{target_id}`\n"
                f"🐶 -{amount:,.2f} DOGS",
                parse_mode="Markdown",
                reply_markup=admin_keyboard()
            )

            try:
                await context.bot.send_message(
                    target_id,
                    f"➖ موجودی شما توسط مدیریت کاهش یافت.\n\n"
                    f"🐶 -{amount:,.2f} DOGS"
                )
            except Exception:
                pass

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
        except ValueError:

            await update.message.reply_text(
                "❌ ID مالک جدید باید عددی باشد.",
                reply_markup=cancel_keyboard()
            )
            return

        await update.message.reply_text(
            "⚠️ در این نسخه انتقال مالکیت را فقط به‌صورت درخواست ثبت می‌کنیم.\n\n"
            f"مالک جدید: `{new_owner}`\n\n"
            "برای امنیت، مقدار OWNER_ID در GitHub Secret باید توسط شما تغییر کند.",
            parse_mode="Markdown",
            reply_markup=admin_keyboard()
        )

        states.pop(user.id, None)
        return


# =========================================================
# OWNER REQUEST MESSAGE
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
        title = "💳 درخواست واریز جدید"
    else:
        title = "💸 درخواست برداشت جدید"

    text = (
        f"{title}\n\n"
        f"🆔 درخواست: #{request_id}\n"
        f"👤 User ID: `{user.id}`\n"
        f"👤 Username: @{user.username or 'ندارد'}\n"
        f"🐶 مبلغ: `{amount:,.2f} DOGS`\n\n"
        f"📎 اطلاعات:\n{proof}"
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
            ),
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
        logger.error(e)


# =========================================================
# ADMIN COMMAND
# =========================================================

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_owner(update.effective_user.id):
        return

    await update.message.reply_text(
        "👑 پنل مدیریت",
        reply_markup=admin_keyboard()
    )


# =========================================================
# BACK
# =========================================================

async def back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.from_user.id == OWNER_ID:
        await show_admin(query)
    else:
        await safe_edit(
            query,
            "منوی اصلی",
            main_keyboard()
        )


# =========================================================
# UNKNOWN / PHOTO / DOCUMENT
# =========================================================

async def media_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    register_user(user)

    state = states.get(user.id)

    if not state:
        await update.message.reply_text(
            "لطفاً از منوی ربات استفاده کنید.",
            reply_markup=main_keyboard()
        )
        return

    if state.get("action") != "deposit_proof":
        await update.message.reply_text(
            "❌ در این مرحله فایل قابل قبول نیست.",
            reply_markup=cancel_keyboard()
        )
        return

    amount = state["amount"]

    proof = "[IMAGE]"

    if update.message.document:
        proof = "[DOCUMENT]"

    conn = db()

    conn.execute("""
        INSERT INTO requests
        (user_id, type, amount, username, proof, status, created_at)
        VALUES (?, 'deposit', ?, ?, ?, 'pending', ?)
    """, (
        user.id,
        amount,
        user.username or "",
        proof,
        datetime.now().isoformat()
    ))

    conn.commit()

    request_id = conn.execute(
        "SELECT last_insert_rowid()"
    ).fetchone()[0]

    conn.close()

    states.pop(user.id, None)

    await update.message.reply_text(
        f"✅ درخواست واریز ثبت شد.\n\n"
        f"🐶 `{amount:,.2f} DOGS`\n"
        f"🆔 `#{request_id}`\n\n"
        "در انتظار بررسی مالک.",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
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
# ERROR HANDLER
# =========================================================

async def error_handler(update, context):

    logger.error(
        "Exception while handling update:",
        exc_info=context.error
    )


# =========================================================
# MAIN
# =========================================================

def main():

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN در GitHub Secrets تنظیم نشده است."
        )

    if not OWNER_ID:
        raise RuntimeError(
            "OWNER_ID در GitHub Secrets تنظیم نشده است."
        )

    init_db()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("admin", admin_command)
    )

    application.add_handler(
        CallbackQueryHandler(
            back_callback,
            pattern="^back$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(callbacks)
    )

    application.add_handler(
        MessageHandler(
            filters.PHOTO | filters.Document.ALL,
            media_handler
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler
        )
    )

    application.add_error_handler(error_handler)

    print("LIMBO BOT STARTED")

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
