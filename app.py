import nest_asyncio
import random
from itertools import cycle
import base64
import os
import psycopg2
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, ReplyKeyboardMarkup, \
    ReplyKeyboardRemove, KeyboardButton, MenuButtonWebApp, KeyboardButtonRequestChat, ChatAdministratorRights
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, ConversationHandler, \
    MessageHandler, filters
from telegram.error import TelegramError
from telegram.constants import ParseMode
from dotenv import load_dotenv

load_dotenv()

nest_asyncio.apply()

token = os.environ.get("BOT_TOKEN")

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

                data_up = \
                [dict((cur.description[i][0], value) for i, value in enumerate(row)) for row in cur.fetchall()][0]
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
        ),
    )

    reply_markup = InlineKeyboardMarkup.from_button(
        button=InlineKeyboardButton(
            text="Open wishmatch",
            url=f"https://t.me/wishmatch_bot/wishes?startapp={chat.id}",
            callback_data="open_webapp"
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


async def update_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with psycopg2.connect(**con) as conn:
        cur = conn.cursor()
        cur.execute(f"""
            select tg_user_id
            from users
            ;
        """)
        users = [dict((cur.description[i][0], value) for i, value in enumerate(row)) for row in cur.fetchall()]
    for user in users:
        await context.bot.set_chat_menu_button(
            chat_id=user["tg_user_id"],
            menu_button=MenuButtonWebApp(
                text="Open",
                web_app=WebAppInfo(
                    url=f"https://{os.environ.get('PG_HOST')}?chat_id={user['tg_user_id']}"
                )
            )
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


async def launch_secret_santa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user

    if user.id != chat.id:
        return

    reply_markup = ReplyKeyboardMarkup(
        [
            [
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
            ]
        ],
        resize_keyboard=True
    )

    msg = await context.bot.send_message(
        text="Please choose any group where you would like to launch Secret Santa.",
        chat_id=chat.id,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )


async def select_santa_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    chat_id = message.chat_shared.chat_id

    context.user_data["chat_id"] = chat_id

    await message.delete()

    reply_markup = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        text="Lock the list and draw lots",
                        callback_data="start_santa"
                    )
                ]
            ])

    await context.bot.send_message(
        chat_id=chat.id,
        text="The group has been selected!",
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardRemove()
    )

    await context.bot.send_message(
        chat_id=chat.id,
        text="Lock the list of recipients and draw lots once all users joined.",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

    reply_markup = InlineKeyboardMarkup.from_button(
        button=InlineKeyboardButton(
            text="Join | Leave",
            callback_data="join"
        )
    )

    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=f"@{user.username} has launched Secret Santa activity! Hurry up and join if you would like to participate!",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

    if chat_id not in context.bot_data:
        context.bot_data[chat_id] = {}
    context.bot_data[chat_id]["message"] = msg


async def start_secret_santa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = context.user_data["chat_id"]
    msg = context.bot_data[chat_id]["message"]

    if msg.reply_markup:
        await context.bot.edit_message_reply_markup(
            message_id=msg.id,
            chat_id=chat_id
        )

    await query.message.edit_reply_markup()

    await context.bot.send_message(
        chat_id=chat_id,
        text="Secret Santa has been started!\nCheck your private chat with @wishmatch_bot.",
        parse_mode=ParseMode.HTML
    )
    await secret_santa_randomize(context)

    context.bot_data[chat_id]["secret_santa_list"] = []

    await query.answer()


async def join_secret_santa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    query = update.callback_query
    user = query.from_user
    msg = context.bot_data[chat.id]["message"]

    if "secret_santa_list" not in context.bot_data[chat.id]:
        context.bot_data[chat.id]["secret_santa_list"] = []

    if user.id not in [u["user_id"] for u in context.bot_data[chat.id]["secret_santa_list"]]:
        try:
            await context.bot.send_message(
                chat_id=user.id,
                text=f"Great! You have joined Secret Santa activity in "
                     f"<b><a href='https://t.me/c/{str(chat.id)[4:]}'>{chat.title}</a></b>.\n"
                     f"Once the activity starts, you will get your secret recipient here.",
                parse_mode=ParseMode.HTML
            )
            context.bot_data[chat.id]["secret_santa_list"].append({"user_id": user.id, "username": user.username})
            await query.answer("Now you are in!")
        except TelegramError:
            await query.answer("Please start this bot in private chat.")

    else:
        context.bot_data[chat.id]["secret_santa_list"].remove({"user_id": user.id, "username": user.username})
        await query.answer("You left this activity")

    reply_markup = InlineKeyboardMarkup.from_button(
        button=InlineKeyboardButton(
            text="Join | Leave",
            callback_data="join"
        )
    )

    await query.message.edit_text(
        text=f"{msg.text}\n\nParticipants: {', '.join([user['username'] for user in context.bot_data[chat.id]['secret_santa_list']]) if context.bot_data[chat.id]['secret_santa_list'] else '-'}",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )


async def secret_santa_randomize(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = context.user_data["chat_id"]
    data = context.bot_data[chat_id]
    random.shuffle(data["secret_santa_list"])
    data_cycle = cycle(data["secret_santa_list"])
    next_elem = next(data_cycle)
    for _ in range(len(data["secret_santa_list"])):
        this_elem, next_elem = next_elem, next(data_cycle)
        await context.bot.send_message(
            chat_id=next_elem["user_id"],
            text=f"You are Secret Santa for @{this_elem['username']}. Check wishes in the webapp and gift a needed thing.",
            parse_mode=ParseMode.HTML
        )


def main() -> None:
    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("grant", grant_access))
    application.add_handler(CommandHandler("revoke", revoke_access))
    application.add_handler(CommandHandler("update_info", update_info))
    application.add_handler(CommandHandler("update_menu_button", update_menu_button))

    application.add_handler(CommandHandler("santa", launch_secret_santa))
    application.add_handler(MessageHandler(filters.StatusUpdate.CHAT_SHARED, select_santa_chat))
    application.add_handler(CallbackQueryHandler(join_secret_santa, pattern="join"))
    application.add_handler(CallbackQueryHandler(start_secret_santa, pattern="start_santa"))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

