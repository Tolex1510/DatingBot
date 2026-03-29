from telegram import Update
from telegram.ext import ContextTypes

from app.bot.helpers import format_profile_text, get_profile_photos, send_profile_with_photos
from app.bot.keyboards import main_menu_keyboard
from app.db import session as db_session
from app.services import profile_service, user_service


def profile_actions_keyboard(is_active: bool):
    from telegram import ReplyKeyboardMarkup

    toggle_text = "⏸ Деактивировать" if is_active else "▶️ Активировать"
    return ReplyKeyboardMarkup(
        [[toggle_text, "✏️ Изменить"], ["🗑 Удалить", "◀️ Назад"]],
        resize_keyboard=True,
    )


async def profile_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    tg_user = update.effective_user

    async with db_session.async_session_factory() as session:
        user = await user_service.get_user_by_tg_id(session, tg_user.id)
        if not user:
            await update.message.reply_text(
                "Вы не зарегистрированы. Используйте /start."
            )
            return

        profile = await profile_service.get_profile(session, user.id)

        photos = []
        if profile:
            photos = await get_profile_photos(session, profile.id)

    if not profile:
        await update.message.reply_text(
            "У вас нет анкеты. Используйте /start для создания."
        )
        return

    text = format_profile_text(profile, show_status=True, photo_count=len(photos))
    context.user_data["in_profile_menu"] = True
    await send_profile_with_photos(
        update, profile, photos, text,
        reply_markup=profile_actions_keyboard(profile.is_active),
    )


async def toggle_active_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    tg_user = update.effective_user

    async with db_session.async_session_factory() as session:
        user = await user_service.get_user_by_tg_id(session, tg_user.id)
        if not user:
            return

        profile = await profile_service.get_profile(session, user.id)
        if not profile:
            return

        new_status = not profile.is_active
        await profile_service.update_profile(session, profile.id, is_active=new_status)
        await session.commit()

    status_text = "активирована ✅" if new_status else "деактивирована ⏸"
    await update.message.reply_text(
        f"Анкета {status_text}",
        reply_markup=profile_actions_keyboard(new_status),
    )


async def delete_profile_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not context.user_data.get("confirm_delete"):
        context.user_data["confirm_delete"] = True
        from telegram import ReplyKeyboardMarkup

        confirm_kb = ReplyKeyboardMarkup(
            [["Да, удалить", "Отмена"]],
            one_time_keyboard=True,
            resize_keyboard=True,
        )
        await update.message.reply_text(
            "⚠️ Вы уверены? Анкета будет удалена безвозвратно.",
            reply_markup=confirm_kb,
        )
        return

    # Should not reach here — handled by confirm/cancel handlers


async def confirm_delete_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    context.user_data.pop("confirm_delete", None)
    context.user_data.pop("in_profile_menu", None)
    tg_user = update.effective_user

    async with db_session.async_session_factory() as session:
        user = await user_service.get_user_by_tg_id(session, tg_user.id)
        if user:
            profile = await profile_service.get_profile(session, user.id)
            if profile:
                await profile_service.delete_profile(session, profile.id)
                await session.commit()

    await update.message.reply_text(
        "Анкета удалена. Используйте /start чтобы создать новую.",
        reply_markup=main_menu_keyboard(),
    )


async def cancel_delete_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    context.user_data.pop("confirm_delete", None)

    tg_user = update.effective_user
    async with db_session.async_session_factory() as session:
        user = await user_service.get_user_by_tg_id(session, tg_user.id)
        profile = await profile_service.get_profile(session, user.id) if user else None

    is_active = profile.is_active if profile else True
    await update.message.reply_text(
        "Удаление отменено.",
        reply_markup=profile_actions_keyboard(is_active),
    )


async def profile_back_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    context.user_data.pop("in_profile_menu", None)
    context.user_data.pop("confirm_delete", None)
    await update.message.reply_text("Главное меню", reply_markup=main_menu_keyboard())
