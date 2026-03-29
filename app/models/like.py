import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class Like(UUIDMixin, Base):
    __tablename__ = "likes"

    liker_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tg_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    liked_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tg_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_like: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
