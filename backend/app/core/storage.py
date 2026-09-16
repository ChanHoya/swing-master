"""
Cloudflare R2 / AWS S3 Storage Client
Provides upload, presigned URL, and delete operations.
"""
import boto3
from botocore.config import Config
from functools import lru_cache

from app.core.config import settings


@lru_cache
def get_r2_client():
    """Return a cached boto3 S3 client configured for Cloudflare R2."""
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def upload_fileobj(file_obj, key: str, content_type: str = "video/mp4") -> str:
    """
    Upload a file-like object to R2.

    Returns:
        Public URL of the uploaded object.
    """
    client = get_r2_client()
    client.upload_fileobj(
        file_obj,
        settings.R2_BUCKET_NAME,
        key,
        ExtraArgs={"ContentType": content_type},
    )
    return f"{settings.R2_PUBLIC_URL}/{key}"


def generate_presigned_url(key: str, expires_in: int = 3600) -> str:
    """
    Generate a presigned URL for direct client upload.

    Args:
        key: Object key in R2
        expires_in: URL expiration in seconds (default: 1 hour)

    Returns:
        Presigned URL string
    """
    client = get_r2_client()
    return client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.R2_BUCKET_NAME,
            "Key": key,
            "ContentType": "video/mp4",
        },
        ExpiresIn=expires_in,
    )


def delete_object(key: str) -> None:
    """Delete an object from R2."""
    client = get_r2_client()
    client.delete_object(Bucket=settings.R2_BUCKET_NAME, Key=key)
