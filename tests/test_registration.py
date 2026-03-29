import uuid

import pytest
import pytest_asyncio

from app.services import user_service, profile_service


@pytest.mark.asyncio
async def test_register_user(db_session):
    user = await user_service.register_user(
        db_session,
        tg_id=123456789,
        username="testuser",
        first_name="Test",
        last_name="User",
    )
    await db_session.commit()

    assert user.tg_id == 123456789
    assert user.username == "testuser"
    assert user.first_name == "Test"


@pytest.mark.asyncio
async def test_register_user_idempotent(db_session):
    user1 = await user_service.register_user(
        db_session,
        tg_id=111222333,
        username="same_user",
        first_name="Same",
    )
    await db_session.commit()

    user2 = await user_service.register_user(
        db_session,
        tg_id=111222333,
        username="same_user",
        first_name="Same",
    )

    assert user1.id == user2.id


@pytest.mark.asyncio
async def test_create_profile(db_session):
    user = await user_service.register_user(
        db_session,
        tg_id=987654321,
        username="profile_user",
        first_name="Profile",
    )
    await db_session.commit()

    profile = await profile_service.create_profile(
        db_session,
        user_id=user.id,
        name="Profile User",
        age=25,
        gender="male",
        city="Moscow",
        bio="Test bio",
        interests=["music", "sports"],
    )
    await db_session.commit()

    assert profile.user_id == user.id
    assert profile.age == 25
    assert profile.city == "Moscow"


@pytest.mark.asyncio
async def test_create_profile_user_not_found(db_session):
    with pytest.raises(ValueError, match="User not found"):
        await profile_service.create_profile(
            db_session,
            user_id=uuid.uuid4(),
            name="Nobody",
            age=25,
            gender="male",
            city="Moscow",
        )


@pytest.mark.asyncio
async def test_api_register_user(client):
    response = await client.post(
        "/api/v1/users/register",
        json={
            "telegram_id": 555666777,
            "username": "api_user",
            "first_name": "API",
            "last_name": "User",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["telegram_id"] == 555666777
    assert data["first_name"] == "API"


@pytest.mark.asyncio
async def test_api_create_profile(client):
    reg_response = await client.post(
        "/api/v1/users/register",
        json={
            "telegram_id": 888999000,
            "first_name": "ProfileAPI",
        },
    )
    user_id = reg_response.json()["id"]

    response = await client.post(
        "/api/v1/profiles",
        json={
            "user_id": user_id,
            "name": "ProfileAPI",
            "age": 30,
            "gender": "female",
            "city": "Saint Petersburg",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["age"] == 30
    assert data["city"] == "Saint Petersburg"


@pytest.mark.asyncio
async def test_api_get_user_not_found(client):
    response = await client.get(f"/api/v1/users/{uuid.uuid4()}")
    assert response.status_code == 404
