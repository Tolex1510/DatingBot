import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import chat_repo, match_repo
from app.models.chat import Chat
from app.models.message import Message


async def get_or_create_chat(session: AsyncSession, match_id: uuid.UUID) -> Chat:
    chat = await chat_repo.get_by_match_id(session, match_id)
    if not chat:
        chat = await chat_repo.create(session, match_id)
    return chat


async def send_message(
    session: AsyncSession, chat_id: uuid.UUID, sender_id: uuid.UUID, text: str
) -> Message:
    return await chat_repo.add_message(session, chat_id, sender_id, text)


async def get_messages(
    session: AsyncSession, chat_id: uuid.UUID, limit: int = 50, offset: int = 0
) -> list[Message]:
    return await chat_repo.get_messages(session, chat_id, limit, offset)


async def get_chat_by_match(session: AsyncSession, match_id: uuid.UUID) -> Chat | None:
    return await chat_repo.get_by_match_id(session, match_id)
