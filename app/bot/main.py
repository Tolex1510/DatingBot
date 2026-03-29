from telegram.ext import Application, ApplicationBuilder, CommandHandler, MessageHandler, filters
from telegram.request import HTTPXRequest

from app.bot.handlers.browse import handle_back, handle_like, handle_skip, handle_superlike, show_next_profile
from app.bot.handlers.edit_profile import edit_profile_handler
from app.bot.handlers.matches import (
    back_to_matches_handler,
    chat_message_handler,
    matches_handler,
    open_chat_handler,
    rating_handler,
    referral_handler,
    show_history_handler,
)
from app.bot.handlers.photo import (
    add_photo_prompt_handler,
    back_to_photos_handler,
    delete_photo_handler,
    photo_upload_handler,
    select_photo_handler,
    show_photos_handler,
    swap_photo_handler,
)
from app.bot.handlers.profile import (
    cancel_delete_handler,
    confirm_delete_handler,
    delete_profile_handler,
    profile_back_handler,
    profile_handler,
    toggle_active_handler,
)
from app.bot.handlers.registration import registration_handler


def create_bot_app(bot_token: str) -> Application:
    request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
    )
    app = (
        ApplicationBuilder()
        .token(bot_token)
        .request(request)
        .build()
    )

    # ConversationHandlers
    app.add_handler(registration_handler)
    app.add_handler(edit_profile_handler)

    # Commands
    app.add_handler(CommandHandler("profile", profile_handler))
    app.add_handler(CommandHandler("matches", matches_handler))
    app.add_handler(CommandHandler("rating", rating_handler))
    app.add_handler(CommandHandler("ref", referral_handler))

    # Profile menu actions
    app.add_handler(MessageHandler(filters.Regex("^Да, удалить$"), confirm_delete_handler))
    app.add_handler(MessageHandler(filters.Regex("^Отмена$"), cancel_delete_handler))

    # Photo management
    app.add_handler(MessageHandler(filters.Regex("^🔄 Поменять местами$"), swap_photo_handler))
    app.add_handler(MessageHandler(filters.Regex("^🗑 Удалить фото$"), delete_photo_handler))
    app.add_handler(MessageHandler(filters.Regex("^◀️ К списку фото$"), back_to_photos_handler))
    app.add_handler(MessageHandler(filters.Regex("^📷 Добавить фото$"), add_photo_prompt_handler))

    # Profile actions
    app.add_handler(MessageHandler(filters.Regex("^🗑 Удалить$"), delete_profile_handler))
    app.add_handler(MessageHandler(filters.Regex("^⏸ Деактивировать$"), toggle_active_handler))
    app.add_handler(MessageHandler(filters.Regex("^▶️ Активировать$"), toggle_active_handler))
    app.add_handler(MessageHandler(filters.Regex("^◀️ Назад$"), profile_back_handler))

    # Chat
    app.add_handler(MessageHandler(filters.Regex("^📜 История$"), show_history_handler))
    app.add_handler(MessageHandler(filters.Regex("^◀️ К мэтчам$"), back_to_matches_handler))

    # Main menu buttons (must be before generic "^💬 " catch)
    app.add_handler(MessageHandler(filters.Regex("^Моя анкета$"), profile_handler))
    app.add_handler(MessageHandler(filters.Regex("^Смотреть анкеты$"), show_next_profile))
    app.add_handler(MessageHandler(filters.Regex("^💬 Мэтчи$"), matches_handler))
    app.add_handler(MessageHandler(filters.Regex("^📊 Рейтинг$"), rating_handler))
    app.add_handler(MessageHandler(filters.Regex("^🔗 Реферал$"), referral_handler))

    # Open chat with specific match (after "💬 Мэтчи" to avoid conflict)
    app.add_handler(MessageHandler(filters.Regex("^💬 "), open_chat_handler))

    # Browse actions
    app.add_handler(MessageHandler(filters.Regex("^❤️ Лайк$"), handle_like))
    app.add_handler(MessageHandler(filters.Regex("^⭐ Суперлайк$"), handle_superlike))
    app.add_handler(MessageHandler(filters.Regex("^👎 Пропуск$"), handle_skip))
    app.add_handler(MessageHandler(filters.Regex("^Назад$"), handle_back))

    # Number selection (photo picker)
    app.add_handler(MessageHandler(filters.Regex(r"^\d+$"), select_photo_handler))

    # Photo uploads
    app.add_handler(MessageHandler(filters.PHOTO, photo_upload_handler))

    # Catch-all for chat messages (must be last text handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_message_handler))

    return app
