import uuid

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.helpers import format_profile_text, get_profile_photos, send_profile_with_photos
from app.bot.keyboards import main_menu_keyboard
from app.db import session as db_session
from app.db.repositories import profile_repo, rating_repo, user_repo
from app.events.publisher import publish
from app.services import cache_service, match_service, user_service


def browse_keyboard():
    from telegram import ReplyKeyboardMarkup

    return ReplyKeyboardMarkup(
        [["❤️ Лайк", "⭐ Суперлайк", "👎 Пропуск"], ["Назад"]],
        resize_keyboard=True,
    )


async def _fetch_and_show(update, context, user_id: uuid.UUID) -> None:
    """Fetch next profile from Redis cache or DB, and display it."""
    # Try Redis cache first
    cached_id = await cache_service.pop_next_profile(user_id)

    if cached_id:
        profile_user_id = uuid.UUID(cached_id)
        async with db_session.async_session_factory() as session:
            profile = await profile_repo.get_by_user_id(session, profile_user_id)
            photos = await get_profile_photos(session, profile.id) if profile else []
        if profile:
            context.user_data["browsing"] = True
            context.user_data["viewing_user_id"] = str(profile.user_id)
            await _display_profile(update, profile, photos)
            return

    # Cache miss — fetch batch from DB ordered by rating
    async with db_session.async_session_factory() as session:
        ranked_ids = await rating_repo.get_top_rated_profiles(session, user_id, limit=20)

    if not ranked_ids:
        await update.message.reply_text(
            "Анкеты закончились! Попробуйте позже.",
            reply_markup=main_menu_keyboard(),
        )
        context.user_data.pop("browsing", None)
        context.user_data.pop("viewing_user_id", None)
        return

    # Cache the rest, show the first
    first_id = ranked_ids[0]
    if len(ranked_ids) > 1:
        await cache_service.cache_profiles(user_id, [str(uid) for uid in ranked_ids[1:]])

    async with db_session.async_session_factory() as session:
        profile = await profile_repo.get_by_user_id(session, first_id)
        photos = await get_profile_photos(session, profile.id) if profile else []

    if profile:
        context.user_data["browsing"] = True
        context.user_data["viewing_user_id"] = str(profile.user_id)
        await _display_profile(update, profile, photos)
    else:
        await update.message.reply_text("Анкеты закончились!", reply_markup=main_menu_keyboard())


async def _display_profile(update, profile, photos: list | None = None) -> None:
    text = format_profile_text(profile)
    await send_profile_with_photos(
        update, profile, photos or [], text,
        reply_markup=browse_keyboard(),
    )


async def show_next_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user

    async with db_session.async_session_factory() as session:
        user = await user_service.get_user_by_tg_id(session, tg_user.id)
        if not user:
            await update.message.reply_text("Вы не зарегистрированы. Используйте /start.")
            return
        await user_repo.update_last_seen(session, user.id)
        await session.commit()
        user_id = user.id

    await _fetch_and_show(update, context, user_id)


async def handle_like(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    viewing_user_id = context.user_data.get("viewing_user_id")

    if not viewing_user_id:
        await update.message.reply_text("Нет анкеты для оценки.", reply_markup=main_menu_keyboard())
        return

    async with db_session.async_session_factory() as session:
        user = await user_service.get_user_by_tg_id(session, tg_user.id)
        liked_uid = uuid.UUID(viewing_user_id)

        match = await match_service.process_like(session, user.id, liked_uid)
        await user_repo.update_last_seen(session, user.id)
        await session.commit()

        # Publish event → consumer recalculates rating asynchronously
        await publish("profile.liked", {
            "liker_id": str(user.id),
            "target_user_id": str(liked_uid),
        })

        if match:
            liked_user = await user_service.get_user(session, liked_uid)
            liked_name = liked_user.profile.name if liked_user and liked_user.profile else "Кто-то"

            await update.message.reply_text(f"🎉 Это мэтч! Вы понравились друг другу с {liked_name}!")

            await publish("match.created", {
                "user_id": str(user.id),
                "matched_user_id": str(liked_uid),
            })

            try:
                our_name = user.profile.name if user.profile else user.first_name
                await context.bot.send_message(
                    chat_id=liked_user.tg_id,
                    text=f"🎉 Мэтч! Вы понравились {our_name}!",
                )
            except Exception:
                pass

        user_id = user.id

    await _fetch_and_show(update, context, user_id)


async def handle_superlike(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    viewing_user_id = context.user_data.get("viewing_user_id")

    if not viewing_user_id:
        await update.message.reply_text("Нет анкеты для оценки.", reply_markup=main_menu_keyboard())
        return

    async with db_session.async_session_factory() as session:
        user = await user_service.get_user_by_tg_id(session, tg_user.id)
        liked_uid = uuid.UUID(viewing_user_id)

        match = await match_service.process_like(session, user.id, liked_uid)
        await user_repo.update_last_seen(session, user.id)
        await session.commit()

        await publish("profile.liked", {
            "liker_id": str(user.id),
            "target_user_id": str(liked_uid),
            "is_superlike": True,
        })

        # Notify target about superlike
        liked_user = await user_service.get_user(session, liked_uid)
        if liked_user:
            try:
                our_name = user.profile.name if user.profile else user.first_name
                await context.bot.send_message(
                    chat_id=liked_user.tg_id,
                    text=f"⭐ {our_name} поставил(а) вам суперлайк!",
                )
            except Exception:
                pass

        if match:
            liked_name = liked_user.profile.name if liked_user and liked_user.profile else "Кто-то"
            await update.message.reply_text(f"🎉 Это мэтч! Вы понравились друг другу с {liked_name}!")

            await publish("match.created", {
                "user_id": str(user.id),
                "matched_user_id": str(liked_uid),
            })

        user_id = user.id

    await _fetch_and_show(update, context, user_id)


async def handle_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    viewing_user_id = context.user_data.get("viewing_user_id")

    if not viewing_user_id:
        await update.message.reply_text("Нет анкеты для оценки.", reply_markup=main_menu_keyboard())
        return

    async with db_session.async_session_factory() as session:
        user = await user_service.get_user_by_tg_id(session, tg_user.id)
        skipped_uid = uuid.UUID(viewing_user_id)

        await match_service.process_skip(session, user.id, skipped_uid)
        await user_repo.update_last_seen(session, user.id)
        await session.commit()
        user_id = user.id

    # Publish event → consumer recalculates rating asynchronously
    await publish("profile.skipped", {
        "liker_id": str(user_id),
        "target_user_id": viewing_user_id,
    })

    await _fetch_and_show(update, context, user_id)


async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("browsing", None)
    context.user_data.pop("viewing_user_id", None)
    await update.message.reply_text("Главное меню", reply_markup=main_menu_keyboard())
