import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import rating_repo, referral_repo
from app.models.like import Like
from app.models.match import Match
from app.models.message import Message
from app.models.photo import Photo
from app.models.profile import Profile
from app.models.rating import Rating
from app.models.user import TgUser

# Level 1 weights
W_AGE = 0.2
W_GENDER = 0.1
W_INTERESTS = 0.3
W_GEO = 0.2
W_COMPLETENESS = 0.1
W_PHOTOS = 0.1

# Level 2 weights
W_LIKES_COUNT = 0.25
W_LIKE_RATIO = 0.25
W_MATCH_RATE = 0.25
W_MESSAGE_RATE = 0.15
W_ACTIVITY = 0.1

# Level 3 weights
W_PRIMARY = 0.4
W_BEHAVIORAL = 0.4


async def ensure_rating_exists(session: AsyncSession, user_id: uuid.UUID) -> Rating:
    rating = await rating_repo.get_by_user_id(session, user_id)
    if not rating:
        rating = await rating_repo.create(session, user_id)
    return rating


async def calculate_primary_rating(session: AsyncSession, user_id: uuid.UUID) -> float:
    rating = await ensure_rating_exists(session, user_id)

    profile = (await session.execute(
        select(Profile).where(Profile.user_id == user_id)
    )).scalar_one_or_none()
    if not profile:
        return 0.0

    # Age score: peak at 30, min 0.1
    age_score = max(0.1, min(1.0, 1.0 - abs(profile.age - 30) / 40))

    # Gender score: neutral
    gender_score = 1.0

    # Interests score: 10+ interests = max
    interests = profile.interests or []
    interests_score = min(len(interests) / 10, 1.0)

    # Geo score: based on city population in the app
    city_count = (await session.execute(
        select(func.count()).select_from(Profile).where(
            Profile.city == profile.city, Profile.is_active == True
        )
    )).scalar_one()
    geo_score = min(city_count / 50, 1.0)

    # Completeness: optional fields filled
    optional_fields = [profile.name, profile.bio, profile.country, profile.interests, profile.preferences]
    filled = sum(1 for f in optional_fields if f)
    completeness_score = filled / len(optional_fields)

    # Photos score
    photo_count = (await session.execute(
        select(func.count()).select_from(Photo).where(Photo.profile_id == profile.id)
    )).scalar_one()
    photos_score = min(photo_count / 3, 1.0)

    primary = (
        age_score * W_AGE +
        gender_score * W_GENDER +
        interests_score * W_INTERESTS +
        geo_score * W_GEO +
        completeness_score * W_COMPLETENESS +
        photos_score * W_PHOTOS
    )

    await rating_repo.update(session, rating, {
        "age_score": round(age_score, 4),
        "gender_score": round(gender_score, 4),
        "interests_score": round(interests_score, 4),
        "geo_score": round(geo_score, 4),
        "completeness_score": round(completeness_score, 4),
        "photos_score": round(photos_score, 4),
        "primary_rating": round(primary, 4),
    })
    return primary


async def calculate_behavioral_rating(session: AsyncSession, user_id: uuid.UUID) -> float:
    rating = await ensure_rating_exists(session, user_id)

    # Likes received (is_like=True)
    likes_received = (await session.execute(
        select(func.count()).select_from(Like).where(
            and_(Like.liked_id == user_id, Like.is_like == True)
        )
    )).scalar_one()

    # Skips received (is_like=False)
    skips_received = (await session.execute(
        select(func.count()).select_from(Like).where(
            and_(Like.liked_id == user_id, Like.is_like == False)
        )
    )).scalar_one()

    # Matches count
    matches_count = (await session.execute(
        select(func.count()).select_from(Match).where(
            (Match.user_id == user_id) | (Match.matched_user_id == user_id)
        )
    )).scalar_one()

    # Likes count score
    likes_count_score = min(likes_received / 100, 1.0)

    # Like/dislike ratio
    total_interactions = likes_received + skips_received
    like_dislike_ratio = likes_received / total_interactions if total_interactions > 0 else 0.5

    # Match rate
    match_rate = min(matches_count / max(likes_received, 1), 1.0)

    # Message rate: messages sent / matches (how actively user chats)
    messages_sent = (await session.execute(
        select(func.count()).select_from(Message).where(Message.sender_id == user_id)
    )).scalar_one()
    message_rate = min(messages_sent / max(matches_count, 1) / 10, 1.0)

    # Activity time score based on last_seen
    user = (await session.execute(
        select(TgUser).where(TgUser.id == user_id)
    )).scalar_one_or_none()

    activity_time_score = 0.1
    if user and user.last_seen:
        now = datetime.now(timezone.utc)
        last_seen = user.last_seen.replace(tzinfo=timezone.utc) if user.last_seen.tzinfo is None else user.last_seen
        hours_ago = (now - last_seen).total_seconds() / 3600
        if hours_ago < 1:
            activity_time_score = 1.0
        elif hours_ago < 24:
            activity_time_score = 0.7
        elif hours_ago < 168:  # 1 week
            activity_time_score = 0.4
        else:
            activity_time_score = 0.1

    behavioral = (
        likes_count_score * W_LIKES_COUNT +
        like_dislike_ratio * W_LIKE_RATIO +
        match_rate * W_MATCH_RATE +
        message_rate * W_MESSAGE_RATE +
        activity_time_score * W_ACTIVITY
    )

    await rating_repo.update(session, rating, {
        "likes_count_score": round(likes_count_score, 4),
        "like_dislike_ratio": round(like_dislike_ratio, 4),
        "match_rate": round(match_rate, 4),
        "message_rate": round(message_rate, 4),
        "activity_time_score": round(activity_time_score, 4),
        "behavioral_rating": round(behavioral, 4),
    })
    return behavioral


async def calculate_combined_rating(session: AsyncSession, user_id: uuid.UUID) -> float:
    rating = await ensure_rating_exists(session, user_id)

    user = (await session.execute(
        select(TgUser).where(TgUser.id == user_id)
    )).scalar_one_or_none()

    # Referral bonus
    referral_count = await referral_repo.count_by_referrer(session, user_id)
    referral_bonus = min(referral_count * 0.1, 0.5)

    premium_bonus = 0.2 if (user and user.is_premium) else 0.0
    verified_bonus = 0.15 if (user and user.is_verified) else 0.0
    total_bonus = min(referral_bonus + premium_bonus + verified_bonus, 1.0)

    final = (
        rating.primary_rating * W_PRIMARY +
        rating.behavioral_rating * W_BEHAVIORAL +
        total_bonus
    )

    await rating_repo.update(session, rating, {
        "bonus_points": round(total_bonus, 4),
        "final_rating": round(final, 4),
    })
    return final


async def recalculate_full(session: AsyncSession, user_id: uuid.UUID) -> float:
    await calculate_primary_rating(session, user_id)
    await calculate_behavioral_rating(session, user_id)
    return await calculate_combined_rating(session, user_id)


async def get_rating(session: AsyncSession, user_id: uuid.UUID) -> Rating | None:
    return await rating_repo.get_by_user_id(session, user_id)
