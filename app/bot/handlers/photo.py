import uuid
from io import BytesIO

from telegram import InputMediaPhoto, Update
from telegram.ext import ContextTypes

from app.bot.helpers import get_profile_photos
from app.bot.keyboards import main_menu_keyboard
from app.db import session as db_session
from app.models.photo import Photo
from app.services import s3_service, user_service, profile_service, rating_service

MAX_PHOTOS = 10


def photo_menu_keyboard(photo_count: int):
    from telegram import ReplyKeyboardMarkup

    rows = []
    if photo_count > 0:
        # Number buttons for each photo
        nums = [str(i + 1) for i in range(photo_count)]
        # Split into rows of 5
        for i in range(0, len(nums), 5):
            rows.append(nums[i:i + 5])

    rows.append(["📷 Добавить фото", "◀️ Назад"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def photo_action_keyboard():
    from telegram import ReplyKeyboardMarkup

    return ReplyKeyboardMarkup(
        [["🔄 Поменять местами", "🗑 Удалить фото"], ["◀️ К списку фото"]],
        resize_keyboard=True,
    )


def swap_target_keyboard(photo_count: int, exclude: int):
    from telegram import ReplyKeyboardMarkup

    nums = [str(i + 1) for i in range(photo_count) if (i + 1) != exclude]
    rows = []
    for i in range(0, len(nums), 5):
        rows.append(nums[i:i + 5])
    rows.append(["◀️ К списку фото"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


async def _get_user_profile(tg_user):
    """Helper to get user and profile."""
    async with db_session.async_session_factory() as session:
        user = await user_service.get_user_by_tg_id(session, tg_user.id)
        if not user:
            return None, None, []
        profile = await profile_service.get_profile(session, user.id)
        if not profile:
            return user, None, []
        photos = await get_profile_photos(session, profile.id)
        return user, profile, photos


async def show_photos_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all photos as album with numbered list."""
    tg_user = update.effective_user
    user, profile, photos = await _get_user_profile(tg_user)

    if not profile:
        await update.message.reply_text("У вас нет анкеты.")
        return

    context.user_data.pop("selected_photo_idx", None)
    context.user_data.pop("swap_mode", None)

    if not photos:
        await update.message.reply_text(
            f"У вас нет фото (0/{MAX_PHOTOS}).\n"
            "Отправьте фото, чтобы добавить.",
            reply_markup=photo_menu_keyboard(0),
        )
        return

    # Send photos as album with numbers
    media = []
    for i, photo in enumerate(photos):
        try:
            photo_bytes = await s3_service.download_photo(photo.url)
            buf = BytesIO(photo_bytes)
            buf.name = f"photo_{i}.jpg"
            caption = f"Фото {i + 1}" if i == 0 else None
            media.append(InputMediaPhoto(media=buf, caption=caption))
        except Exception:
            continue

    if media:
        await update.message.reply_media_group(media=media)

    await update.message.reply_text(
        f"У вас {len(photos)}/{MAX_PHOTOS} фото.\n"
        "Выберите номер фото для действий или отправьте новое.",
        reply_markup=photo_menu_keyboard(len(photos)),
    )


async def select_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """User selected a photo number."""
    text = update.message.text.strip()

    # Check if we're in swap mode
    if context.user_data.get("swap_mode"):
        await _do_swap(update, context, int(text))
        return

    tg_user = update.effective_user
    user, profile, photos = await _get_user_profile(tg_user)

    if not profile or not photos:
        return

    try:
        idx = int(text) - 1
    except ValueError:
        return

    if idx < 0 or idx >= len(photos):
        await update.message.reply_text("Неверный номер фото.")
        return

    context.user_data["selected_photo_idx"] = idx
    context.user_data["photo_count"] = len(photos)

    # Send the selected photo
    try:
        photo_bytes = await s3_service.download_photo(photos[idx].url)
        buf = BytesIO(photo_bytes)
        buf.name = "selected.jpg"
        await update.message.reply_photo(
            photo=buf,
            caption=f"Фото {idx + 1} из {len(photos)}",
            reply_markup=photo_action_keyboard(),
        )
    except Exception:
        await update.message.reply_text(
            f"Фото {idx + 1} выбрано.",
            reply_markup=photo_action_keyboard(),
        )


async def swap_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start swap mode — ask which photo to swap with."""
    idx = context.user_data.get("selected_photo_idx")
    photo_count = context.user_data.get("photo_count", 0)

    if idx is None:
        await update.message.reply_text("Сначала выберите фото.")
        return

    if photo_count < 2:
        await update.message.reply_text("Нужно минимум 2 фото для обмена.")
        return

    context.user_data["swap_mode"] = True

    await update.message.reply_text(
        f"Выберите номер фото для обмена с фото {idx + 1}:",
        reply_markup=swap_target_keyboard(photo_count, idx + 1),
    )


async def _do_swap(update: Update, context: ContextTypes.DEFAULT_TYPE, target_num: int) -> None:
    """Perform the swap between two photos."""
    idx_a = context.user_data.get("selected_photo_idx")
    context.user_data.pop("swap_mode", None)

    if idx_a is None:
        return

    idx_b = target_num - 1
    tg_user = update.effective_user

    async with db_session.async_session_factory() as session:
        user = await user_service.get_user_by_tg_id(session, tg_user.id)
        if not user:
            return
        profile = await profile_service.get_profile(session, user.id)
        if not profile:
            return

        photos = await get_profile_photos(session, profile.id)

        if idx_a >= len(photos) or idx_b >= len(photos) or idx_a == idx_b:
            await update.message.reply_text("Неверный выбор.")
            return

        # Swap the S3 URLs between the two photo records
        photo_a = photos[idx_a]
        photo_b = photos[idx_b]
        photo_a.url, photo_b.url = photo_b.url, photo_a.url
        photo_a.is_primary, photo_b.is_primary = photo_b.is_primary, photo_a.is_primary
        await session.commit()

    context.user_data.pop("selected_photo_idx", None)

    await update.message.reply_text(
        f"Фото {idx_a + 1} и {target_num} поменялись местами!",
    )

    # Show updated photo list
    await show_photos_handler(update, context)


async def delete_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete the selected photo."""
    idx = context.user_data.get("selected_photo_idx")
    if idx is None:
        await update.message.reply_text("Сначала выберите фото.")
        return

    tg_user = update.effective_user

    async with db_session.async_session_factory() as session:
        user = await user_service.get_user_by_tg_id(session, tg_user.id)
        if not user:
            return
        profile = await profile_service.get_profile(session, user.id)
        if not profile:
            return

        photos = await get_profile_photos(session, profile.id)

        if idx >= len(photos):
            await update.message.reply_text("Фото не найдено.")
            return

        photo = photos[idx]

        # Delete from S3
        try:
            await s3_service.delete_photo(photo.url)
        except Exception:
            pass

        # Delete from DB
        from sqlalchemy import delete as sa_delete
        await session.execute(sa_delete(Photo).where(Photo.id == photo.id))

        # Recalculate rating
        await rating_service.calculate_primary_rating(session, user.id)
        await rating_service.calculate_combined_rating(session, user.id)

        await session.commit()

    context.user_data.pop("selected_photo_idx", None)

    await update.message.reply_text(f"Фото {idx + 1} удалено!")

    # Show updated list
    await show_photos_handler(update, context)


async def back_to_photos_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return to photo list from photo actions."""
    context.user_data.pop("selected_photo_idx", None)
    context.user_data.pop("swap_mode", None)
    await show_photos_handler(update, context)


async def add_photo_prompt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prompt to send a photo."""
    await update.message.reply_text("Отправьте фото для добавления в анкету.")


async def photo_upload_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo uploads from users."""
    tg_user = update.effective_user

    if not update.message.photo:
        return

    async with db_session.async_session_factory() as session:
        user = await user_service.get_user_by_tg_id(session, tg_user.id)
        if not user:
            await update.message.reply_text("Вы не зарегистрированы. Используйте /start.")
            return

        profile = await profile_service.get_profile(session, user.id)
        if not profile:
            await update.message.reply_text("Сначала создайте анкету через /start.")
            return

        from sqlalchemy import func, select
        photo_count = (await session.execute(
            select(func.count()).select_from(Photo).where(Photo.profile_id == profile.id)
        )).scalar_one()

        if photo_count >= MAX_PHOTOS:
            await update.message.reply_text(
                f"Максимум {MAX_PHOTOS} фото. Удалите старые.",
                reply_markup=photo_menu_keyboard(photo_count),
            )
            return

        photo_file = await update.message.photo[-1].get_file()
        file_bytes = await photo_file.download_as_bytearray()

        try:
            s3_key = await s3_service.upload_photo(bytes(file_bytes))
        except Exception as e:
            await update.message.reply_text(f"Ошибка загрузки: {e}")
            return

        is_primary = photo_count == 0
        db_photo = Photo(
            profile_id=profile.id,
            url=s3_key,
            is_primary=is_primary,
        )
        session.add(db_photo)

        await rating_service.calculate_primary_rating(session, user.id)
        await rating_service.calculate_combined_rating(session, user.id)

        await session.commit()

        new_count = photo_count + 1

    await update.message.reply_text(f"Фото загружено! 📸 ({new_count}/{MAX_PHOTOS})")

    # Show updated list
    await show_photos_handler(update, context)
