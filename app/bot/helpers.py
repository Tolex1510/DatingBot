"""Shared helpers for sending profile cards with photos."""
import uuid
from io import BytesIO

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import InputMediaPhoto, Update

from app.models.photo import Photo
from app.services import s3_service


async def get_profile_photos(session: AsyncSession, profile_id: uuid.UUID) -> list[Photo]:
    stmt = (
        select(Photo)
        .where(Photo.profile_id == profile_id)
        .order_by(Photo.is_primary.desc(), Photo.created_at)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


def format_profile_text(profile, show_status: bool = False, photo_count: int = 0) -> str:
    gender_display = "Мужской" if profile.gender == "male" else "Женский"
    bio_display = profile.bio or "—"
    interests_display = ", ".join(profile.interests) if profile.interests else "—"

    text = (
        f"{'📋 Ваша анкета' if show_status else profile.name}:\n\n"
        f"Имя: {profile.name}\n"
        f"Возраст: {profile.age}\n"
        f"Пол: {gender_display}\n"
        f"Город: {profile.city}\n"
        f"О себе: {bio_display}\n"
        f"Интересы: {interests_display}"
    )

    if show_status:
        status_display = "✅ Активна" if profile.is_active else "⏸ Неактивна"
        text += f"\nФото: {photo_count}/10\n\nСтатус: {status_display}"

    return text


async def send_profile_with_photos(
    update: Update,
    profile,
    photos: list[Photo],
    text: str,
    reply_markup=None,
) -> None:
    """Send profile card: photos as album + text with keyboard."""
    if photos:
        media = []
        for i, photo in enumerate(photos[:10]):
            try:
                photo_bytes = await s3_service.download_photo(photo.url)
                buf = BytesIO(photo_bytes)
                buf.name = f"photo_{i}.jpg"
                if i == 0:
                    media.append(InputMediaPhoto(media=buf, caption=text))
                else:
                    media.append(InputMediaPhoto(media=buf))
            except Exception:
                continue

        if media:
            await update.message.reply_media_group(media=media)
            if reply_markup:
                await update.message.reply_text("⬇️", reply_markup=reply_markup)
            return

    # No photos or all failed — just send text
    await update.message.reply_text(text, reply_markup=reply_markup)
