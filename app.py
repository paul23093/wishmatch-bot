import nest_asyncio
import json
import os
import psycopg2
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from telegram.constants import ParseMode
from dotenv import load_dotenv

load_dotenv()

nest_asyncio.apply()

token = os.environ.get("TOKEN")

con = {
    'host': os.environ.get("PG_HOST"),
    'port': os.environ.get("PG_PORT"),
    'user': os.environ.get("PG_USER"),
    'password': os.environ.get("PG_PASSWORD"),
    'database': os.environ.get("PG_DB")
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    reply_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text="Provide access to your wishes",
                callback_data="grant_access"
            )
        ]
    ]
    )
    await context.bot.send_message(
        text=f"Hi {user.username}\n\nLaunch [WishMatch](https://t.me/wishmatch_bot/wishes?startapp={chat.id})",
        chat_id=chat.id,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=reply_markup,
    )


async def grant_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat

    with psycopg2.connect(**con) as conn:
        cur = conn.cursor()

        cur.execute(f"""
        select count(*)>0 as is_user_exists
        from users
        where tg_user_id = {user.id}
        ;
        """)

        data_u = [dict((cur.description[i][0], value) for i, value in enumerate(row)) for row in cur.fetchall()][0]
        if not data_u["is_user_exists"]:

            cur.execute(f"""
            insert into users (
                tg_user_id, 
                tg_username,
                tg_first_name,
                tg_last_name
            ) 
            values (
                {user.id}, 
                {f"'{user.username}'" if user.username else "NULL"},
                {f"'{user.first_name}'" if user.first_name else "NULL"},
                {f"'{user.last_name}'" if user.last_name else "NULL"}
            );
            """)
            conn.commit()

        cur.execute(f"""
            select count(*)>0 as is_user_permission_exists
            from permissions
            where tg_user_id = {user.id}
            and tg_chat_id = {chat.id}
            ;
        """)

        data_up = [dict((cur.description[i][0], value) for i, value in enumerate(row)) for row in cur.fetchall()][0]
        if not data_up["is_user_permission_exists"]:
            cur.execute(f"""
            insert into permissions (
                tg_user_id, 
                tg_chat_id
            ) 
            values (
                {user.id}, 
                {chat.id}
            );""")
            conn.commit()

    await update.effective_message.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup.from_button(
            button=InlineKeyboardButton(
                text="Revoke access",
                callback_data="revoke_access"
            ),
        )
    )


async def revoke_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    with psycopg2.connect(**con) as conn:
        cur = conn.cursor()
        cur.execute(f"""
        delete from permissions 
        where tg_user_id = {user.id}
        and tg_chat_id = {chat.id};""")
        conn.commit()

    await update.effective_message.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup.from_button(
            button=InlineKeyboardButton(
                text="Provide access to your wishes",
                callback_data="grant_access"
            ),
        )
    )


def main() -> None:
    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("grant", grant_access))
    application.add_handler(CommandHandler("revoke", revoke_access))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    print("App started.")
    main()
