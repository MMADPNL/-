import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

TOKEN = "TOKEN_BOT"

OWNER_ID = 8552447077  # آیدی عددی مالک


db = sqlite3.connect("users.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY,
balance INTEGER DEFAULT 0
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


async def start(update:Update, context:ContextTypes.DEFAULT_TYPE):

    uid = update.effective_user.id

    cur.execute(
        "INSERT OR IGNORE INTO users(id) VALUES(?)",
        (uid,)
    )

    db.commit()

    await update.message.reply_text(
        "سلام 👋\n"
        "برای واریز رسید خود را ارسال کنید."
    )



async def photo(update:Update, context:ContextTypes.DEFAULT_TYPE):

    uid = update.effective_user.id

    if uid == OWNER_ID:
        return


    amount = context.user_data.get("amount")

    if not amount:
        await update.message.reply_text(
            "اول مقدار DOGS را ارسال کن.\nمثال:\n5000"
        )
        return


    file_id = update.message.photo[-1].file_id


    cur.execute(
        """
        INSERT INTO deposits
        (user_id,amount,photo,status)
        VALUES(?,?,?,?)
        """,
        (
            uid,
            amount,
            file_id,
            "pending"
        )
    )

    deposit_id = cur.lastrowid

    db.commit()


    keyboard = [
        [
        InlineKeyboardButton(
            "✅ تایید",
            callback_data=f"ok_{deposit_id}"
        ),

        InlineKeyboardButton(
            "❌ رد",
            callback_data=f"no_{deposit_id}"
        )
        ]
    ]


    await context.bot.send_photo(
        chat_id=OWNER_ID,
        photo=file_id,
        caption=
        f"""
🔔 درخواست واریز

👤 کاربر:
{uid}

💰 مقدار:
{amount} DOGS

شماره:
{deposit_id}
        """,
        reply_markup=
        InlineKeyboardMarkup(keyboard)
    )


    await update.message.reply_text(
        "✅ رسید ارسال شد، منتظر تایید مالک باشید."
    )



async def button(update:Update, context:ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    if query.from_user.id != OWNER_ID:
        return


    data=query.data


    action, dep_id = data.split("_")

    dep_id=int(dep_id)


    cur.execute(
        """
        SELECT user_id,amount,status
        FROM deposits
        WHERE id=?
        """,
        (dep_id,)
    )

    dep=cur.fetchone()


    if not dep:
        return


    user_id,amount,status=dep


    if status!="pending":
        await query.answer(
            "قبلا بررسی شده"
        )
        return



    if action=="ok":


        cur.execute(
        """
        UPDATE users
        SET balance=balance+?
        WHERE id=?
        """,
        (
            amount,
            user_id
        ))


        cur.execute(
        """
        UPDATE deposits
        SET status='approved'
        WHERE id=?
        """,
        (dep_id,)
        )


        await context.bot.send_message(
            user_id,
            f"✅ واریز تایید شد\n+{amount} DOGS"
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
            user_id,
            "❌ واریز رد شد"
        )


        await query.edit_message_caption(
            "❌ رد شد"
        )


    db.commit()



app=Application.builder().token(TOKEN).build()


app.add_handler(
CommandHandler("start",start)
)


app.add_handler(
MessageHandler(
filters.PHOTO,
photo
)
)


app.add_handler(
CallbackQueryHandler(button)
)


print("BOT RUNNING")

app.run_polling()

# دریافت مقدار واریز از کاربر

async def get_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    text = update.message.text


    if not text.isdigit():
        return


    amount = int(text)


    context.user_data["deposit_amount"] = amount


    await update.message.reply_text(
        "✅ مبلغ ثبت شد\n\n"
        "حالا عکس رسید واریز DOGS را ارسال کن 📸"
    )





# دریافت عکس رسید

async def get_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id


    amount = context.user_data.get(
        "deposit_amount"
    )


    if not amount:

        await update.message.reply_text(
            "اول مقدار DOGS را بفرست."
        )

        return



    photo = update.message.photo[-1]


    file_id = photo.file_id



    keyboard = [
        [
            InlineKeyboardButton(
                "✅ تایید",
                callback_data=f"approve_{user_id}_{amount}"
            )
        ],
        [
            InlineKeyboardButton(
                "❌ رد",
                callback_data=f"reject_{user_id}"
            )
        ]
    ]



    await context.bot.send_photo(

        chat_id=OWNER_ID,

        photo=file_id,

        caption=
        f"""
🔔 درخواست واریز جدید

👤 کاربر:
{user_id}

💰 مقدار:
{amount} DOGS
        """,

        reply_markup=
        InlineKeyboardMarkup(keyboard)

    )



    await update.message.reply_text(
        "✅ رسید برای مالک ارسال شد."
    )





# دکمه های مالک

async def owner_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query


    if query.from_user.id != OWNER_ID:
        return



    data = query.data.split("_")



    if data[0]=="approve":

        user_id = int(data[1])

        amount = int(data[2])



        cur.execute(
        """
        INSERT OR IGNORE INTO users(id)
        VALUES(?)
        """,
        (user_id,)
        )



        cur.execute(
        """
        UPDATE users
        SET balance = balance + ?
        WHERE id=?
        """,
        (amount,user_id)
        )


        db.commit()



        await context.bot.send_message(
            user_id,
            f"✅ واریز تایید شد\n+{amount} DOGS"
        )


        await query.edit_message_caption(
            "✅ تایید شد"
        )



    elif data[0]=="reject":


        user_id=int(data[1])


        await context.bot.send_message(
            user_id,
            "❌ واریز رد شد"
        )


        await query.edit_message_caption(
            "❌ رد شد"
    )

app.add_handler(
MessageHandler(
filters.TEXT & ~filters.COMMAND,
get_amount
)
)


app.add_handler(
MessageHandler(
filters.PHOTO,
get_receipt
)
)


app.add_handler(
CallbackQueryHandler(
owner_buttons
)
)# اجرای ربات

app = Application.builder().token(TOKEN).build()


app.add_handler(
    CommandHandler("start", start)
)


app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        get_amount
    )
)


app.add_handler(
    MessageHandler(
        filters.PHOTO,
        get_receipt
    )
)


app.add_handler(
    CallbackQueryHandler(owner_buttons)
)


print("BOT IS RUNNING")


app.run_polling()
