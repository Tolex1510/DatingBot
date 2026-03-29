import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import chat_repo, like_repo, match_repo
from app.models.match import Match


async def process_like(
    session: AsyncSession, liker_id: uuid.UUID, liked_id: uuid.UUID
) -> Match | None:
    """Process a like. Returns a Match if mutual, None otherwise."""
    if await like_repo.exists(session, liker_id, liked_id):
        return None

    await like_repo.create(session, liker_id, liked_id, is_like=True)

    if await like_repo.check_mutual(session, liker_id, liked_id):
        if not await match_repo.exists(session, liker_id, liked_id):
            match = await match_repo.create(session, liker_id, liked_id)
            # Create chat for the match
            chat = await chat_repo.create(session, match.id)
            match.chat_id = chat.id
            return match

    return None


async def process_skip(
    session: AsyncSession, liker_id: uuid.UUID, liked_id: uuid.UUID
) -> None:
    """Record a skip so this profile won't be shown again."""
    if not await like_repo.exists(session, liker_id, liked_id):
        await like_repo.create(session, liker_id, liked_id, is_like=False)


async def get_matches(
    session: AsyncSession, user_id: uuid.UUID
) -> list[Match]:
    return await match_repo.get_user_matches(session, user_id)
