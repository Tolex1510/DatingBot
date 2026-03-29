import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.chat import Chat
from app.models.message import Message


async def create(session: AsyncSession, match_id: uuid.UUID) -> Chat:
    chat = Chat(match_id=match_id)
    session.add(chat)
    await session.flush()
    return chat


async def get_by_match_id(session: AsyncSession, match_id: uuid.UUID) -> Chat | None:
    stmt = select(Chat).where(Chat.match_id == match_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_id(session: AsyncSession, chat_id: uuid.UUID) -> Chat | None:
    stmt = select(Chat).where(Chat.id == chat_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def add_message(
    session: AsyncSession, chat_id: uuid.UUID, sender_id: uuid.UUID, text: str
) -> Message:
    msg = Message(chat_id=chat_id, sender_id=sender_id, text=text)
    session.add(msg)
    await session.flush()

    # Update last_message_id on chat
    chat = await get_by_id(session, chat_id)
    if chat:
        chat.last_message_id = msg.id

    return msg


async def get_messages(
    session: AsyncSession, chat_id: uuid.UUID, limit: int = 50, offset: int = 0
) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return list(reversed(result.scalars().all()))
