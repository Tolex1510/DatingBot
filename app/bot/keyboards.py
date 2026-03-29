from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove

REMOVE_KEYBOARD = ReplyKeyboardRemove()


def gender_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["Мужской", "Женский"]],
        one_time_keyboard=True,
        resize_keyboard=True,
    )


def confirm_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["Подтвердить", "Заново"]],
        one_time_keyboard=True,
        resize_keyboard=True,
    )


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["Смотреть анкеты", "Моя анкета"], ["💬 Мэтчи", "📊 Рейтинг"], ["🔗 Реферал"]],
        resize_keyboard=True,
    )


def skip_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["Пропустить"]],
        one_time_keyboard=True,
        resize_keyboard=True,
    )
