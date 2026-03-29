import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class Referral(UUIDMixin, Base):
    __tablename__ = "referrals"

    referrer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tg_users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    referred_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tg_users.id", ondelete="CASCADE"),
        unique=True, nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
