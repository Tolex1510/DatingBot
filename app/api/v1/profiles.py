import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.schemas import (
    ProfileCreateRequest,
    ProfileResponse,
    ProfileUpdateRequest,
)
from app.db.repositories import rating_repo
from app.events.publisher import publish
from app.services import match_service, profile_service

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.post("", response_model=ProfileResponse, status_code=201)
async def create_profile(
    body: ProfileCreateRequest,
    session: AsyncSession = Depends(get_db),
):
    try:
        profile = await profile_service.create_profile(
            session,
            user_id=body.user_id,
            name=body.name,
            age=body.age,
            gender=body.gender,
            city=body.city,
            country=body.country,
            bio=body.bio,
            interests=body.interests,
            preferences=body.preferences,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ProfileResponse.model_validate(profile)


@router.get("", response_model=list[ProfileResponse])
async def list_profiles(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    gender: str | None = None,
    city: str | None = None,
    session: AsyncSession = Depends(get_db),
):
    profiles = await profile_service.list_profiles(
        session, limit=limit, offset=offset, gender=gender, city=city
    )
    return [ProfileResponse.model_validate(p) for p in profiles]


@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    profile = await profile_service.get_profile_by_id(session, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileResponse.model_validate(profile)


@router.put("/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: uuid.UUID,
    body: ProfileUpdateRequest,
    session: AsyncSession = Depends(get_db),
):
    data = body.model_dump(exclude_unset=True)
    profile = await profile_service.update_profile(session, profile_id, **data)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileResponse.model_validate(profile)


@router.delete("/{profile_id}", status_code=204)
async def delete_profile(
    profile_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await profile_service.delete_profile(session, profile_id)


@router.get("/next", response_model=ProfileResponse)
async def get_next_profile(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    """Get next ranked profile for user to view."""
    ranked_ids = await rating_repo.get_top_rated_profiles(session, user_id, limit=1)
    if not ranked_ids:
        raise HTTPException(status_code=404, detail="No profiles available")
    from app.db.repositories import profile_repo
    profile = await profile_repo.get_by_user_id(session, ranked_ids[0])
    if not profile:
        raise HTTPException(status_code=404, detail="No profiles available")
    return ProfileResponse.model_validate(profile)


@router.post("/{profile_id}/like")
async def like_profile(
    profile_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    """Like a profile. Returns match info if mutual."""
    from app.db.repositories import profile_repo
    profile = await profile_repo.get_by_id(session, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    match = await match_service.process_like(session, user_id, profile.user_id)

    await publish("profile.liked", {
        "liker_id": str(user_id),
        "target_user_id": str(profile.user_id),
    })

    if match:
        await publish("match.created", {
            "user_id": str(user_id),
            "matched_user_id": str(profile.user_id),
        })
        return {"match": True, "chat_id": str(match.chat_id)}

    return {"match": False, "chat_id": None}


@router.post("/{profile_id}/skip")
async def skip_profile(
    profile_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    """Skip a profile."""
    from app.db.repositories import profile_repo
    profile = await profile_repo.get_by_id(session, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    await match_service.process_skip(session, user_id, profile.user_id)

    await publish("profile.skipped", {
        "liker_id": str(user_id),
        "target_user_id": str(profile.user_id),
    })

    return {"status": "skipped"}


@router.post("/{profile_id}/superlike")
async def superlike_profile(
    profile_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    """Superlike a profile. Like + notification to the target user."""
    from app.db.repositories import profile_repo
    profile = await profile_repo.get_by_id(session, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    match = await match_service.process_like(session, user_id, profile.user_id)

    await publish("profile.liked", {
        "liker_id": str(user_id),
        "target_user_id": str(profile.user_id),
        "is_superlike": True,
    })

    if match:
        await publish("match.created", {
            "user_id": str(user_id),
            "matched_user_id": str(profile.user_id),
        })
        return {"match": True, "chat_id": str(match.chat_id), "superlike": True}

    return {"match": False, "chat_id": None, "superlike": True}
