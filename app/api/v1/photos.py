import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.photo import Photo
from app.services import s3_service, rating_service

router = APIRouter(prefix="/photos", tags=["photos"])


@router.post("/upload")
async def upload_photo(
    profile_id: uuid.UUID,
    file: UploadFile,
    session: AsyncSession = Depends(get_db),
):
    from app.db.repositories import profile_repo

    profile = await profile_repo.get_by_id(session, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    file_bytes = await file.read()
    content_type = file.content_type or "image/jpeg"
    s3_key = await s3_service.upload_photo(file_bytes, content_type)

    db_photo = Photo(profile_id=profile.id, url=s3_key, is_primary=False)
    session.add(db_photo)

    await rating_service.calculate_primary_rating(session, profile.user_id)
    await rating_service.calculate_combined_rating(session, profile.user_id)

    await session.flush()

    return {
        "id": str(db_photo.id),
        "url": s3_key,
        "created_at": str(db_photo.created_at),
    }


@router.delete("/{photo_id}", status_code=204)
async def delete_photo(
    photo_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select, delete as sa_delete

    photo = (await session.execute(
        select(Photo).where(Photo.id == photo_id)
    )).scalar_one_or_none()

    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    try:
        await s3_service.delete_photo(photo.url)
    except Exception:
        pass

    await session.execute(sa_delete(Photo).where(Photo.id == photo_id))
