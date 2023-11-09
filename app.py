import nest_asyncio
import json
import base64
import os
import psycopg2
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, MenuButtonWebApp, KeyboardButtonRequestChat, ChatAdministratorRights
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

    user_photos = (await user.get_profile_photos(limit=1))
    user_photo_base64 = "NULL"
    if user_photos.total_count > 0:
        user_photo = (await user_photos.photos[0][0].get_file())
        user_photo_bytearray = (await user_photo.download_as_bytearray())
        user_photo_base64_encoded_str = base64.b64encode(user_photo_bytearray)
        user_photo_base64 = user_photo_base64_encoded_str.decode()

    try:
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
                    tg_last_name,
                    tg_profile_photo
                ) 
                values (
                    {user.id}, 
                    {f"'{user.username}'" if user.username else "NULL"},
                    {f"'{user.first_name}'" if user.first_name else "NULL"},
                    {f"'{user.last_name}'" if user.last_name else "NULL"},
                    {f"'{user_photo_base64}'" if user_photos.total_count > 0 else "NULL"}
                );
                """)

            cur.execute(f"""
                select count(*)>0 as is_chat_exists
                from chats
                where tg_chat_id = {chat.id}
                ;
            """)

            data_c = [dict((cur.description[i][0], value) for i, value in enumerate(row)) for row in cur.fetchall()][0]
            if not data_c["is_chat_exists"]:
                chat_photo = (await context.bot.get_chat(chat.id)).photo
                chat_photo_base64 = "NULL"
                if chat_photo:
                    chat_photo_small = (await chat_photo.get_small_file())
                    chat_photo_bytearray = (await chat_photo_small.download_as_bytearray())
                    chat_photo_base64_encoded_str = base64.b64encode(chat_photo_bytearray)
                    chat_photo_base64 = chat_photo_base64_encoded_str.decode()

                cur.execute(f"""
                    insert into chats (
                        tg_chat_id, 
                        tg_chat_name,
                        tg_chat_photo
                    ) 
                    values (
                        {chat.id}, 
                        {f"'{chat.title}'" if chat.title else "NULL"},
                        {f"'{chat_photo_base64}'" if chat_photo else "NULL"}
                    );
                    """)

            if user.id == chat.id:
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
                        );
                    """)

                else:
                    cur.execute(f"""
                        update permissions 
                        set is_deleted = false
                        where tg_user_id = {user.id}
                        and tg_chat_id = {chat.id}
                        ;
                    """)
            conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)

    await context.bot.set_chat_menu_button(
        chat_id=user.id,
        menu_button=MenuButtonWebApp(
            text="Open",
            web_app=WebAppInfo(
                url=f"https://{os.environ.get('PG_HOST')}?chat_id={user.id}"
            )
        )
    )

    reply_markup = InlineKeyboardMarkup.from_button(
        button=InlineKeyboardButton(
            text="Open wishmatch",
            url=f"https://t.me/wishmatch_bot/wishes?startapp={chat.id}",
        )
    )

    msg_text = f"""Hi {f"@{user.username}" if user.id == chat.id else "chat"}\!\n
Please /grant access to your wishes to this chat\.
You can always /revoke the access if you want\.\n
Use the button below to open wishmatch app\.\n
For better interaction it is recommended to pin this message\. In this way you are getting instant access to the app via button right from the pinned message\."""
    await context.bot.send_message(
        text=msg_text,
        chat_id=chat.id,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=reply_markup,
    )


async def grant_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat

    try:
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

                user_photos = (await user.get_profile_photos(limit=1))
                user_photo_base64 = "NULL"
                if user_photos.total_count > 0:
                    user_photo = (await user_photos.photos[0][0].get_file())
                    user_photo_bytearray = (await user_photo.download_as_bytearray())
                    user_photo_base64_encoded_str = base64.b64encode(user_photo_bytearray)
                    user_photo_base64 = user_photo_base64_encoded_str.decode()

                cur.execute(f"""
                insert into users (
                    tg_user_id, 
                    tg_username,
                    tg_first_name,
                    tg_last_name,
                    tg_profile_photo
                ) 
                values (
                    {user.id}, 
                    {f"'{user.username}'" if user.username else "NULL"},
                    {f"'{user.first_name}'" if user.first_name else "NULL"},
                    {f"'{user.last_name}'" if user.last_name else "NULL"},
                    {f"'{user_photo_base64}'" if user_photos.total_count > 0 else "NULL"}
                );
                """)

            cur.execute(f"""
                select count(*)>0 as is_chat_exists
                from chats
                where tg_chat_id = {chat.id}
                ;
            """)

            data_c = [dict((cur.description[i][0], value) for i, value in enumerate(row)) for row in cur.fetchall()][0]
            if not data_c["is_chat_exists"]:

                chat_photo = (await context.bot.get_chat(chat.id)).photo
                chat_photo_base64 = "NULL"
                if chat_photo:
                    chat_photo_small = (await chat_photo.get_small_file())
                    chat_photo_bytearray = (await chat_photo_small.download_as_bytearray())
                    chat_photo_base64_encoded_str = base64.b64encode(chat_photo_bytearray)
                    chat_photo_base64 = chat_photo_base64_encoded_str.decode()

                cur.execute(f"""
                insert into chats (
                    tg_chat_id, 
                    tg_chat_name,
                    tg_chat_photo
                ) 
                values (
                    {chat.id}, 
                    {f"'{chat.title}'" if chat.title else "NULL"},
                    {f"'{chat_photo_base64}'" if chat_photo else "NULL"}
                );
                """)

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

            else:
                cur.execute(f"""
                    update permissions 
                    set is_deleted = false
                    where tg_user_id = {user.id}
                    and tg_chat_id = {chat.id}
                ;""")
            conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)

    await update.effective_message.reply_text(
        text="You have successfully shared your wishes with the chat."
    )


async def grant_access_inline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    query = update.callback_query

    try:
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

                user_photos = (await user.get_profile_photos(limit=1))
                user_photo_base64 = "NULL"
                if user_photos.total_count > 0:
                    user_photo = (await user_photos.photos[0][0].get_file())
                    user_photo_bytearray = (await user_photo.download_as_bytearray())
                    user_photo_base64_encoded_str = base64.b64encode(user_photo_bytearray)
                    user_photo_base64 = user_photo_base64_encoded_str.decode()

                cur.execute(f"""
                    insert into users (
                        tg_user_id, 
                        tg_username,
                        tg_first_name,
                        tg_last_name,
                        tg_profile_photo
                    ) 
                    values (
                        {user.id}, 
                        {f"'{user.username}'" if user.username else "NULL"},
                        {f"'{user.first_name}'" if user.first_name else "NULL"},
                        {f"'{user.last_name}'" if user.last_name else "NULL"},
                        {f"'{user_photo_base64}'" if user_photos.total_count > 0 else "NULL"}
                    );
                    """)

            cur.execute(f"""
                    select count(*)>0 as is_chat_exists
                    from chats
                    where tg_chat_id = {chat.id}
                    ;
                """)

            data_c = [dict((cur.description[i][0], value) for i, value in enumerate(row)) for row in cur.fetchall()][0]
            if not data_c["is_chat_exists"]:

                chat_photo = (await context.bot.get_chat(chat.id)).photo
                chat_photo_base64 = "NULL"
                if chat_photo:
                    chat_photo_small = (await chat_photo.get_small_file())
                    chat_photo_bytearray = (await chat_photo_small.download_as_bytearray())
                    chat_photo_base64_encoded_str = base64.b64encode(chat_photo_bytearray)
                    chat_photo_base64 = chat_photo_base64_encoded_str.decode()

                cur.execute(f"""
                    insert into chats (
                        tg_chat_id, 
                        tg_chat_name,
                        tg_chat_photo
                    ) 
                    values (
                        {chat.id}, 
                        {f"'{chat.title}'" if chat.title else "NULL"},
                        {f"'{chat_photo_base64}'" if chat_photo else "NULL"}
                    );
                    """)

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

            else:
                cur.execute(f"""
                        update permissions 
                        set is_deleted = false
                        where tg_user_id = {user.id}
                        and tg_chat_id = {chat.id}
                    ;""")
            conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)

    await query.answer(
        text="You have successfully shared your wishes with the chat."
    )


async def revoke_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat

    try:
        with psycopg2.connect(**con) as conn:
            cur = conn.cursor()
            cur.execute(f"""
                update permissions 
                set is_deleted = true
                where tg_user_id = {user.id}
                and tg_chat_id = {chat.id}
            ;""")
            conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)

    await update.effective_message.reply_text(
        text="You have successfully hidden your wishes from the chat."
    )


async def update_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat

    try:
        with psycopg2.connect(**con) as conn:
            cur = conn.cursor()
            cur.execute(f"""
                select count(*)>0 as is_permission_exists
                from permissions p
                where p.tg_chat_id = {chat.id}
                and p.tg_user_id = {user.id}
                ;
            """)

            data_u = [dict((cur.description[i][0], value) for i, value in enumerate(row)) for row in cur.fetchall()][0]
            if not data_u["is_permission_exists"]:

                msg_text = f"""{f"{user.first_name}" if user.first_name else f"@{user.username}"}\, it seems you did not /grant access to your information yet so we have nothing to update for now\.\n
Please note you can always /revoke the access if you want\.\n"""
                await context.bot.send_message(
                    text=msg_text,
                    chat_id=chat.id,
                    parse_mode=ParseMode.MARKDOWN_V2
                )
            else:
                if user.id == chat.id:
                    user_photos = (await user.get_profile_photos(limit=1))
                    user_photo_base64 = "NULL"
                    if user_photos.total_count > 0:
                        user_photo = (await user_photos.photos[0][0].get_file())
                        user_photo_bytearray = (await user_photo.download_as_bytearray())
                        user_photo_base64_encoded_str = base64.b64encode(user_photo_bytearray)
                        user_photo_base64 = user_photo_base64_encoded_str.decode()

                    cur.execute(f"""
                    update users 
                    set tg_username = {f"'{user.username}'" if user.username else "NULL"},
                        tg_first_name = {f"'{user.first_name}'" if user.first_name else "NULL"},
                        tg_last_name = {f"'{user.last_name}'" if user.last_name else "NULL"},
                        tg_profile_photo = {f"'{user_photo_base64}'" if user_photos.total_count > 0 else "NULL"}
                    where tg_user_id = {user.id}
                    ;
                    """)
                else:

                    chat_photo = (await context.bot.get_chat(chat.id)).photo
                    chat_photo_base64 = "NULL"
                    if chat_photo:
                        chat_photo_small = (await chat_photo.get_small_file())
                        chat_photo_bytearray = (await chat_photo_small.download_as_bytearray())
                        chat_photo_base64_encoded_str = base64.b64encode(chat_photo_bytearray)
                        chat_photo_base64 = chat_photo_base64_encoded_str.decode()

                    cur.execute(f"""
                    update chats
                    set tg_chat_name = {f"'{chat.title}'" if chat.title else "NULL"},
                        tg_chat_photo = {f"'{chat_photo_base64}'" if chat_photo else "NULL"}
                    where tg_chat_id = {chat.id}
                    ;
                    """)
                conn.commit()

                if user.id == chat.id:
                    msg_text = f"""{f"{user.first_name}" if user.first_name else f"@{user.username}"}\, you have successfully updated your information\."""
                else:
                    msg_text = f"""{f"{user.first_name}" if user.first_name else f"@{user.username}"}{f" {user.last_name}" if user.first_name and user.last_name else ''} has successfully updated information of this chat\."""
                await context.bot.send_message(
                    text=msg_text,
                    chat_id=chat.id,
                    parse_mode=ParseMode.MARKDOWN_V2
                )
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)


async def launch_santa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat

    reply_markup = ReplyKeyboardMarkup(
        [[
            KeyboardButton(
                text='Choose group',
                request_chat=KeyboardButtonRequestChat(
                    request_id=1,
                    bot_is_member=True,
                    chat_is_channel=False,
                    user_administrator_rights=ChatAdministratorRights(
                        is_anonymous=False,
                        can_manage_chat=True,
                        can_delete_messages=True,
                        can_manage_video_chats=True,
                        can_restrict_members=True,
                        can_promote_members=True,
                        can_change_info=True,
                        can_invite_users=True
                    ),
                    bot_administrator_rights=ChatAdministratorRights(
                        is_anonymous=False,
                        can_manage_chat=True,
                        can_delete_messages=True,
                        can_manage_video_chats=True,
                        can_restrict_members=False,
                        can_promote_members=False,
                        can_change_info=True,
                        can_invite_users=True
                    ),
                )
            )
        ]],
        resize_keyboard=True
    )

    await context.bot.send_message(
        text='Please choose any group where you would like to launch Secret Santa\.',
        chat_id=chat.id,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=reply_markup
    )


async def get_shared_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    chat_id = message.chat_shared.chat_id

    reply_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            text="I'm in!",
            callback_data="join"
        ),
        ReplyKeyboardRemove()
    ]]
    )

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"@{user.username} has launched Secret Santa activity\! Hurry up and join if you would like to participate\!",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=reply_markup
    )


async def join_secret_santa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query.data == "join":
        await query.answer("Nothing happened cause it is test")


def main() -> None:
    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("grant", grant_access))
    # application.add_handler(CallbackQueryHandler(grant_access_inline))
    application.add_handler(CommandHandler("revoke", revoke_access))
    application.add_handler(CommandHandler("update_info", update_info))

    application.add_handler(CommandHandler("santa", launch_santa))
    application.add_handler(MessageHandler(filters.StatusUpdate.CHAT_SHARED, get_shared_chat))
    application.add_handler(CallbackQueryHandler(join_secret_santa))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
