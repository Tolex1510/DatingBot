from telegram import Update
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.bot.keyboards import (
    REMOVE_KEYBOARD,
    confirm_keyboard,
    gender_keyboard,
    main_menu_keyboard,
    skip_keyboard,
)
from app.db import session as db_session
from app.services import profile_service, referral_service, user_service

NAME, AGE, GENDER, CITY, BIO, INTERESTS, CONFIRMATION = range(7)

GENDER_MAP = {"мужской": "male", "женский": "female"}


async def start_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    tg_user = update.effective_user
    async with db_session.async_session_factory() as session:
        # Check if user already exists (for referral tracking)
        existing_user = await user_service.get_user_by_tg_id(session, tg_user.id)
        is_new = existing_user is None

        user = await user_service.register_user(
            session,
            tg_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
            last_name=tg_user.last_name,
        )
        await session.commit()

        # Process referral link: /start ref_<tg_id>
        if is_new and context.args:
            ref_arg = context.args[0] if context.args else ""
            if ref_arg.startswith("ref_"):
                try:
                    referrer_tg_id = int(ref_arg[4:])
                    referrer = await user_service.get_user_by_tg_id(session, referrer_tg_id)
                    if referrer:
                        await referral_service.create_referral(session, referrer.id, user.id)
                        await session.commit()
                except (ValueError, Exception):
                    pass

        profile = await profile_service.get_profile(session, user.id)

    context.user_data["user_id"] = str(user.id)

    if profile:
        await update.message.reply_text(
            f"С возвращением, {profile.name}! 👋\n"
            "Используйте /profile для просмотра анкеты.",
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "Добро пожаловать! Давайте создадим вашу анкету.\n\n"
        "Как вас зовут?",
        reply_markup=REMOVE_KEYBOARD,
    )
    return NAME


async def ask_name(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    name = update.message.text.strip()
    if len(name) > 255:
        await update.message.reply_text("Имя слишком длинное. Попробуйте ещё раз:")
        return NAME

    context.user_data["name"] = name
    await update.message.reply_text("Сколько вам лет?")
    return AGE


async def ask_age(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    text = update.message.text.strip()
    try:
        age = int(text)
    except ValueError:
        await update.message.reply_text("Введите число. Сколько вам лет?")
        return AGE

    if age < 18 or age > 100:
        await update.message.reply_text("Возраст должен быть от 18 до 100. Попробуйте ещё раз:")
        return AGE

    context.user_data["age"] = age
    await update.message.reply_text(
        "Укажите ваш пол:",
        reply_markup=gender_keyboard(),
    )
    return GENDER


async def ask_gender(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    text = update.message.text.strip().lower()
    if text not in GENDER_MAP:
        await update.message.reply_text(
            "Выберите один из вариантов:",
            reply_markup=gender_keyboard(),
        )
        return GENDER

    context.user_data["gender"] = GENDER_MAP[text]
    await update.message.reply_text(
        "В каком городе вы находитесь?",
        reply_markup=REMOVE_KEYBOARD,
    )
    return CITY


async def ask_city(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    city = update.message.text.strip()
    if len(city) > 100:
        await update.message.reply_text("Название города слишком длинное. Попробуйте ещё раз:")
        return CITY

    context.user_data["city"] = city
    await update.message.reply_text(
        "Расскажите о себе (или нажмите «Пропустить»):",
        reply_markup=skip_keyboard(),
    )
    return BIO


async def ask_bio(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    text = update.message.text.strip()
    if text.lower() == "пропустить":
        context.user_data["bio"] = None
    else:
        context.user_data["bio"] = text

    await update.message.reply_text(
        "Укажите ваши интересы через запятую (или нажмите «Пропустить»):\n"
        "Например: музыка, спорт, путешествия",
        reply_markup=skip_keyboard(),
    )
    return INTERESTS


async def ask_interests(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    text = update.message.text.strip()
    if text.lower() == "пропустить":
        context.user_data["interests"] = None
    else:
        interests = [i.strip() for i in text.split(",") if i.strip()]
        context.user_data["interests"] = interests

    data = context.user_data
    gender_display = "Мужской" if data["gender"] == "male" else "Женский"
    bio_display = data.get("bio") or "—"
    interests_display = ", ".join(data["interests"]) if data.get("interests") else "—"

    summary = (
        f"📋 Ваша анкета:\n\n"
        f"Имя: {data['name']}\n"
        f"Возраст: {data['age']}\n"
        f"Пол: {gender_display}\n"
        f"Город: {data['city']}\n"
        f"О себе: {bio_display}\n"
        f"Интересы: {interests_display}\n\n"
        f"Всё верно?"
    )
    await update.message.reply_text(summary, reply_markup=confirm_keyboard())
    return CONFIRMATION


async def confirm(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    text = update.message.text.strip().lower()

    if text == "заново":
        await update.message.reply_text(
            "Давайте начнём заново.\n\nКак вас зовут?",
            reply_markup=REMOVE_KEYBOARD,
        )
        return NAME

    if text != "подтвердить":
        await update.message.reply_text(
            "Выберите один из вариантов:",
            reply_markup=confirm_keyboard(),
        )
        return CONFIRMATION

    import uuid
    data = context.user_data
    user_id = uuid.UUID(data["user_id"])

    async with db_session.async_session_factory() as session:
        try:
            await profile_service.create_profile(
                session,
                user_id=user_id,
                name=data["name"],
                age=data["age"],
                gender=data["gender"],
                city=data["city"],
                bio=data.get("bio"),
                interests=data.get("interests"),
            )
            await session.commit()
        except ValueError as e:
            await update.message.reply_text(
                f"Ошибка: {e}",
                reply_markup=REMOVE_KEYBOARD,
            )
            return ConversationHandler.END

    await update.message.reply_text(
        "Анкета создана! 🎉\n"
        "Используйте /profile для просмотра.",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


async def cancel(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    await update.message.reply_text(
        "Создание анкеты отменено.",
        reply_markup=REMOVE_KEYBOARD,
    )
    return ConversationHandler.END


registration_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start_handler)],
    states={
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
        AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_age)],
        GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_gender)],
        CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_city)],
        BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_bio)],
        INTERESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_interests)],
        CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
