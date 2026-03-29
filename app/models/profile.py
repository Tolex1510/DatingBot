import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class Profile(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tg_users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(String(255))
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str] = mapped_column(String(20), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str | None] = mapped_column(String(100))
    bio: Mapped[str | None] = mapped_column(Text)
    interests: Mapped[list | None] = mapped_column(JSONB)
    preferences: Mapped[dict | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    user: Mapped["TgUser"] = relationship("TgUser", back_populates="profile")
    photos: Mapped[list["Photo"]] = relationship(
        "Photo", back_populates="profile", cascade="all, delete-orphan"
    )
