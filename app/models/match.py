import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class Match(UUIDMixin, Base):
    __tablename__ = "matches"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tg_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    matched_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tg_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    chat_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    chat: Mapped["Chat | None"] = relationship(
        "Chat", foreign_keys="Chat.match_id", uselist=False
    )
