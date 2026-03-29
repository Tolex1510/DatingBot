import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class Rating(UUIDMixin, Base):
    __tablename__ = "ratings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tg_users.id", ondelete="CASCADE"),
        unique=True, nullable=False, index=True,
    )
    # Level 1: Primary
    age_score: Mapped[float] = mapped_column(Float, default=0.0)
    gender_score: Mapped[float] = mapped_column(Float, default=0.0)
    interests_score: Mapped[float] = mapped_column(Float, default=0.0)
    geo_score: Mapped[float] = mapped_column(Float, default=0.0)
    completeness_score: Mapped[float] = mapped_column(Float, default=0.0)
    photos_score: Mapped[float] = mapped_column(Float, default=0.0)
    primary_rating: Mapped[float] = mapped_column(Float, default=0.0, index=True)

    # Level 2: Behavioral
    likes_count_score: Mapped[float] = mapped_column(Float, default=0.0)
    like_dislike_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    match_rate: Mapped[float] = mapped_column(Float, default=0.0)
    message_rate: Mapped[float] = mapped_column(Float, default=0.0)
    activity_time_score: Mapped[float] = mapped_column(Float, default=0.0)
    behavioral_rating: Mapped[float] = mapped_column(Float, default=0.0, index=True)

    # Level 3: Combined
    bonus_points: Mapped[float] = mapped_column(Float, default=0.0)
    final_rating: Mapped[float] = mapped_column(Float, default=0.0, index=True)

    updated_at: Mapped[datetime | None] = mapped_column(onupdate=func.now(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
