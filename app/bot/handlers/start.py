# Start handler is part of the ConversationHandler in registration.py
# This module re-exports the registration_handler for convenience.

from app.bot.handlers.registration import registration_handler

__all__ = ["registration_handler"]
