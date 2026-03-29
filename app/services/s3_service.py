import uuid
from io import BytesIO

import aioboto3

from app.config import settings

_session = aioboto3.Session()


async def _get_client():
    return _session.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name="us-east-1",
    )


async def ensure_bucket():
    async with await _get_client() as s3:
        try:
            await s3.head_bucket(Bucket=settings.S3_BUCKET)
        except Exception:
            await s3.create_bucket(Bucket=settings.S3_BUCKET)


async def upload_photo(file_bytes: bytes, content_type: str = "image/jpeg") -> str:
    """Upload photo to S3, return the object key."""
    key = f"photos/{uuid.uuid4()}.jpg"
    async with await _get_client() as s3:
        await s3.upload_fileobj(
            BytesIO(file_bytes),
            settings.S3_BUCKET,
            key,
            ExtraArgs={"ContentType": content_type},
        )
    return key


async def get_photo_url(key: str) -> str:
    """Get a presigned URL for a photo."""
    async with await _get_client() as s3:
        url = await s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET, "Key": key},
            ExpiresIn=3600,
        )
    return url


async def download_photo(key: str) -> bytes:
    """Download photo bytes from S3."""
    buf = BytesIO()
    async with await _get_client() as s3:
        await s3.download_fileobj(settings.S3_BUCKET, key, buf)
    return buf.getvalue()


async def delete_photo(key: str) -> None:
    async with await _get_client() as s3:
        await s3.delete_object(Bucket=settings.S3_BUCKET, Key=key)
