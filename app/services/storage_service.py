import json
import logging
import re
from dataclasses import dataclass
from typing import Protocol

from app.core.config import (
    S3_ACCESS_KEY_ID,
    S3_BUCKET,
    S3_ENDPOINT,
    S3_PUBLIC_URL,
    S3_SECRET_ACCESS_KEY,
    STORAGE_BACKEND,
)

logger = logging.getLogger(__name__)
_URL_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)


@dataclass(frozen=True)
class StoredFile:
    storage_url: str
    source_url: str | None = None
    thumbnail_url: str | None = None
    storage_provider: str = "PASSTHROUGH"
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None
    file_size_bytes: int | None = None


class StorageService(Protocol):
    def store_remote_image(
        self,
        source_url: str,
        key_hint: str,
        thumbnail_url: str | None = None,
    ) -> StoredFile:
        pass

    def store_remote_video(
        self,
        source_url: str,
        key_hint: str,
    ) -> StoredFile:
        pass


class PassthroughStorageService:
    def store_remote_image(
        self,
        source_url: str,
        key_hint: str,
        thumbnail_url: str | None = None,
    ) -> StoredFile:
        return StoredFile(
            source_url=source_url,
            storage_url=source_url,
            thumbnail_url=thumbnail_url,
            storage_provider="PASSTHROUGH",
        )

    def store_remote_video(
        self,
        source_url: str,
        key_hint: str,
    ) -> StoredFile:
        return StoredFile(
            source_url=source_url,
            storage_url=source_url,
            storage_provider="PASSTHROUGH",
        )


class ChatImageStorage(Protocol):
    is_available: bool

    def upload_bytes(self, data: bytes, key: str, content_type: str) -> str | None:
        ...


class PassthroughChatImageStorage:
    is_available = False

    def upload_bytes(self, data: bytes, key: str, content_type: str) -> str | None:
        return None


class S3ChatImageStorage:
    is_available = True

    def __init__(
        self,
        endpoint: str | None,
        access_key: str | None,
        secret_key: str | None,
        bucket: str,
        public_url: str,
    ) -> None:
        import boto3

        self._bucket = bucket
        self._public_url = public_url.rstrip("/")
        client_kwargs = {}
        if endpoint:
            client_kwargs["endpoint_url"] = endpoint
        if access_key and secret_key:
            client_kwargs["aws_access_key_id"] = access_key
            client_kwargs["aws_secret_access_key"] = secret_key
        self._client = boto3.client("s3", **client_kwargs)
        self._ensure_bucket(create_if_missing=endpoint is not None)

    def _ensure_bucket(self, *, create_if_missing: bool) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except Exception:
            if not create_if_missing:
                raise
            self._client.create_bucket(Bucket=self._bucket)
            self._client.put_bucket_policy(
                Bucket=self._bucket,
                Policy=json.dumps({
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{self._bucket}/*"],
                    }],
                }),
            )

    def upload_bytes(self, data: bytes, key: str, content_type: str) -> str | None:
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        key = key.lstrip("/")
        return key


def public_url_for_storage_key(key: str | None) -> str | None:
    if key is None:
        return None
    value = key.strip()
    if not value or _URL_SCHEME_RE.match(value) or value.startswith("data:"):
        return value
    if not S3_PUBLIC_URL:
        return value

    normalized_key = value.lstrip("/")
    public_url = S3_PUBLIC_URL.rstrip("/")
    if S3_ENDPOINT and S3_BUCKET:
        return f"{public_url}/{S3_BUCKET}/{normalized_key}"
    return f"{public_url}/{normalized_key}"


def get_storage_service() -> StorageService:
    if STORAGE_BACKEND in {"passthrough", "s3"}:
        return PassthroughStorageService()
    raise ValueError(f"지원하지 않는 STORAGE_BACKEND입니다: {STORAGE_BACKEND}")


def get_chat_image_storage() -> ChatImageStorage:
    if (
        STORAGE_BACKEND == "s3"
        and S3_BUCKET
        and S3_PUBLIC_URL
    ):
        try:
            return S3ChatImageStorage(
                endpoint=S3_ENDPOINT,
                access_key=S3_ACCESS_KEY_ID,
                secret_key=S3_SECRET_ACCESS_KEY,
                bucket=S3_BUCKET,
                public_url=S3_PUBLIC_URL,
            )
        except Exception as exc:
            logger.warning(
                "S3 채팅 이미지 스토리지 초기화 실패, passthrough 사용: %s",
                exc,
            )
    return PassthroughChatImageStorage()


storage_service = get_storage_service()
chat_image_storage = get_chat_image_storage()
user_recipe_image_storage = chat_image_storage
