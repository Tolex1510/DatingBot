from telegram import Update
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.bot.keyboards import REMOVE_KEYBOARD, gender_keyboard, main_menu_keyboard
from app.db import session as db_session
from app.services import profile_service, user_service

CHOOSE_FIELD, EDIT_VALUE = range(2)

FIELD_MAP = {
    "Имя": "name",
    "Возраст": "age",
    "Пол": "gender",
    "Город": "city",
    "О себе": "bio",
    "Интересы": "interests",
}

GENDER_MAP = {"мужской": "male", "женский": "female"}


def field_keyboard():
    from telegram import ReplyKeyboardMarkup

    return ReplyKeyboardMarkup(
        [["Имя", "Возраст"], ["Пол", "Город"], ["О себе", "Интересы"], ["📷 Фото", "Отмена"]],
        one_time_keyboard=True,
        resize_keyboard=True,
    )


async def edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    tg_user = update.effective_user
    async with db_session.async_session_factory() as session:
        user = await user_service.get_user_by_tg_id(session, tg_user.id)
        if not user:
            await update.message.reply_text("Вы не зарегистрированы. Используйте /start.")
            return ConversationHandler.END

        profile = await profile_service.get_profile(session, user.id)

    if not profile:
        await update.message.reply_text("У вас нет анкеты. Используйте /start для создания.")
        return ConversationHandler.END

    context.user_data["edit_user_id"] = str(user.id)
    context.user_data["edit_profile_id"] = str(profile.id)

    await update.message.reply_text(
        "Какое поле хотите изменить?",
        reply_markup=field_keyboard(),
    )
    return CHOOSE_FIELD


async def choose_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()

    if text == "Отмена":
        await update.message.reply_text("Редактирование отменено.", reply_markup=main_menu_keyboard())
        return ConversationHandler.END

    if text.startswith("📷"):
        from app.bot.handlers.photo import show_photos_handler
        await show_photos_handler(update, context)
        return ConversationHandler.END

    if text not in FIELD_MAP:
        await update.message.reply_text("Выберите поле из списка:", reply_markup=field_keyboard())
        return CHOOSE_FIELD

    context.user_data["edit_field"] = text
    field = FIELD_MAP[text]

    if field == "gender":
        await update.message.reply_text("Выберите пол:", reply_markup=gender_keyboard())
    elif field == "interests":
        await update.message.reply_text(
            "Введите интересы через запятую:\nНапример: музыка, спорт, путешествия",
            reply_markup=REMOVE_KEYBOARD,
        )
    elif field == "age":
        await update.message.reply_text("Введите новый возраст (18-100):", reply_markup=REMOVE_KEYBOARD)
    else:
        await update.message.reply_text(f"Введите новое значение для «{text}»:", reply_markup=REMOVE_KEYBOARD)

    return EDIT_VALUE


async def edit_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    import uuid

    text = update.message.text.strip()
    field_name = context.user_data["edit_field"]
    field = FIELD_MAP[field_name]
    profile_id = uuid.UUID(context.user_data["edit_profile_id"])

    # Validate
    if field == "age":
        try:
            value = int(text)
        except ValueError:
            await update.message.reply_text("Введите число. Попробуйте ещё раз:")
            return EDIT_VALUE
        if value < 18 or value > 100:
            await update.message.reply_text("Возраст должен быть от 18 до 100:")
            return EDIT_VALUE
    elif field == "gender":
        if text.lower() not in GENDER_MAP:
            await update.message.reply_text("Выберите один из вариантов:", reply_markup=gender_keyboard())
            return EDIT_VALUE
        value = GENDER_MAP[text.lower()]
    elif field == "interests":
        value = [i.strip() for i in text.split(",") if i.strip()]
    elif field == "name" and len(text) > 255:
        await update.message.reply_text("Имя слишком длинное. Попробуйте ещё раз:")
        return EDIT_VALUE
    elif field == "city" and len(text) > 100:
        await update.message.reply_text("Название слишком длинное. Попробуйте ещё раз:")
        return EDIT_VALUE
    else:
        value = text

    async with db_session.async_session_factory() as session:
        await profile_service.update_profile(session, profile_id, **{field: value})
        await session.commit()

    await update.message.reply_text(
        f"«{field_name}» обновлено!",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


async def edit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Редактирование отменено.", reply_markup=main_menu_keyboard())
    return ConversationHandler.END


edit_profile_handler = ConversationHandler(
    entry_points=[
        CommandHandler("edit", edit_start),
        MessageHandler(filters.Regex("^✏️ Изменить$"), edit_start),
    ],
    states={
        CHOOSE_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_field)],
        EDIT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_value)],
    },
    fallbacks=[CommandHandler("cancel", edit_cancel)],
)
