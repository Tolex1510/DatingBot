import uuid

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.keyboards import main_menu_keyboard
from app.db import session as db_session
from app.services import chat_service, match_service, user_service


def matches_keyboard(matches_data: list):
    from telegram import ReplyKeyboardMarkup

    rows = []
    for i, (match_id, name) in enumerate(matches_data):
        rows.append([f"💬 {name}"])
    rows.append(["◀️ Назад"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def chat_keyboard():
    from telegram import ReplyKeyboardMarkup

    return ReplyKeyboardMarkup(
        [["📜 История", "◀️ К мэтчам"]],
        resize_keyboard=True,
    )


async def matches_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show list of matches."""
    tg_user = update.effective_user
    context.user_data.pop("active_chat_id", None)
    context.user_data.pop("chat_partner_name", None)

    async with db_session.async_session_factory() as session:
        user = await user_service.get_user_by_tg_id(session, tg_user.id)
        if not user:
            await update.message.reply_text("Вы не зарегистрированы.")
            return

        matches = await match_service.get_matches(session, user.id)

        if not matches:
            await update.message.reply_text(
                "У вас пока нет мэтчей.",
                reply_markup=main_menu_keyboard(),
            )
            return

        matches_data = []
        for match in matches:
            other_id = match.matched_user_id if match.user_id == user.id else match.user_id
            other_user = await user_service.get_user(session, other_id)
            name = other_user.profile.name if other_user and other_user.profile else "Пользователь"
            matches_data.append((str(match.id), name))

        context.user_data["matches_map"] = {
            f"💬 {name}": {"match_id": mid, "name": name}
            for mid, name in matches_data
        }

    text = f"Ваши мэтчи ({len(matches_data)}):\nНажмите на имя, чтобы написать."
    await update.message.reply_text(text, reply_markup=matches_keyboard(matches_data))


async def open_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Open chat with a match."""
    text = update.message.text.strip()
    matches_map = context.user_data.get("matches_map", {})

    if text not in matches_map:
        return

    match_info = matches_map[text]
    match_id = uuid.UUID(match_info["match_id"])

    async with db_session.async_session_factory() as session:
        chat = await chat_service.get_or_create_chat(session, match_id)
        await session.commit()

        messages = await chat_service.get_messages(session, chat.id, limit=5)
        tg_user = update.effective_user
        user = await user_service.get_user_by_tg_id(session, tg_user.id)
        user_id = user.id

    context.user_data["active_chat_id"] = str(chat.id)
    context.user_data["chat_partner_name"] = match_info["name"]

    msg_text = f"💬 Чат с {match_info['name']}\n\n"
    if messages:
        for m in messages:
            sender = "Вы" if m.sender_id == user_id else match_info["name"]
            msg_text += f"{sender}: {m.text}\n"
        msg_text += "\nПишите сообщение:"
    else:
        msg_text += "Пока нет сообщений. Напишите первым!"

    await update.message.reply_text(msg_text, reply_markup=chat_keyboard())


async def show_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show last 20 messages in the chat."""
    chat_id = context.user_data.get("active_chat_id")
    partner_name = context.user_data.get("chat_partner_name", "")

    if not chat_id:
        await update.message.reply_text("Вы не в чате.")
        return

    tg_user = update.effective_user

    async with db_session.async_session_factory() as session:
        user = await user_service.get_user_by_tg_id(session, tg_user.id)
        messages = await chat_service.get_messages(session, uuid.UUID(chat_id), limit=20)

    if not messages:
        await update.message.reply_text(
            "История пуста.",
            reply_markup=chat_keyboard(),
        )
        return

    text = f"📜 История с {partner_name} (последние {len(messages)}):\n\n"
    for m in messages:
        sender = "Вы" if m.sender_id == user.id else partner_name
        text += f"{sender}: {m.text}\n"

    await update.message.reply_text(text, reply_markup=chat_keyboard())


async def chat_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages in an active chat. This is the catch-all handler."""
    chat_id = context.user_data.get("active_chat_id")
    if not chat_id:
        # Not in a chat — ignore (or could show help)
        return

    tg_user = update.effective_user
    text = update.message.text.strip()

    if not text:
        return

    async with db_session.async_session_factory() as session:
        user = await user_service.get_user_by_tg_id(session, tg_user.id)
        if not user:
            return

        await chat_service.send_message(session, uuid.UUID(chat_id), user.id, text)
        await session.commit()

        # Forward message to the other user
        from app.models.chat import Chat
        from app.models.match import Match
        from sqlalchemy import select

        chat_obj = (await session.execute(
            select(Chat).where(Chat.id == uuid.UUID(chat_id))
        )).scalar_one_or_none()

        if chat_obj:
            match_obj = (await session.execute(
                select(Match).where(Match.id == chat_obj.match_id)
            )).scalar_one_or_none()

            if match_obj:
                other_id = match_obj.matched_user_id if match_obj.user_id == user.id else match_obj.user_id
                other_user = await user_service.get_user(session, other_id)
                if other_user:
                    try:
                        sender_name = user.profile.name if user.profile else user.first_name
                        await context.bot.send_message(
                            chat_id=other_user.tg_id,
                            text=f"💬 {sender_name}: {text}",
                        )
                    except Exception:
                        pass


async def back_to_matches_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("active_chat_id", None)
    context.user_data.pop("chat_partner_name", None)
    await matches_handler(update, context)


async def referral_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show referral link and stats."""
    tg_user = update.effective_user

    async with db_session.async_session_factory() as session:
        user = await user_service.get_user_by_tg_id(session, tg_user.id)
        if not user:
            await update.message.reply_text("Вы не зарегистрированы.")
            return

        from app.services import referral_service
        count = await referral_service.get_referral_count(session, user.id)

    bot_me = await context.bot.get_me()
    link = f"https://t.me/{bot_me.username}?start=ref_{tg_user.id}"

    text = (
        f"🔗 Ваша реферальная ссылка:\n\n"
        f"`{link}`\n\n"
        f"Приглашено: {count} чел.\n"
        f"Бонус к рейтингу: +{min(count * 0.1, 0.5):.1f} (макс +0.5)\n\n"
        f"Отправьте ссылку друзьям — за каждого +0.1 к рейтингу!"
    )
    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=main_menu_keyboard()
    )


async def rating_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's rating."""
    tg_user = update.effective_user

    async with db_session.async_session_factory() as session:
        user = await user_service.get_user_by_tg_id(session, tg_user.id)
        if not user:
            await update.message.reply_text("Вы не зарегистрированы.")
            return

        from app.services import rating_service
        rating = await rating_service.get_rating(session, user.id)

    if not rating:
        await update.message.reply_text("Рейтинг ещё не рассчитан.")
        return

    text = (
        f"📊 Ваш рейтинг:\n\n"
        f"Первичный: {rating.primary_rating:.2f}\n"
        f"  • Возраст: {rating.age_score:.2f}\n"
        f"  • Интересы: {rating.interests_score:.2f}\n"
        f"  • География: {rating.geo_score:.2f}\n"
        f"  • Полнота: {rating.completeness_score:.2f}\n"
        f"  • Фото: {rating.photos_score:.2f}\n\n"
        f"Поведенческий: {rating.behavioral_rating:.2f}\n"
        f"  • Лайки: {rating.likes_count_score:.2f}\n"
        f"  • Соотношение: {rating.like_dislike_ratio:.2f}\n"
        f"  • Мэтчи: {rating.match_rate:.2f}\n"
        f"  • Активность: {rating.activity_time_score:.2f}\n\n"
        f"Бонусы: {rating.bonus_points:.2f}\n"
        f"Итого: {rating.final_rating:.2f}"
    )
    await update.message.reply_text(text, reply_markup=main_menu_keyboard())
