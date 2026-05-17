import json
import logging
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
    def upload_bytes(self, data: bytes, key: str, content_type: str) -> str | None:
        ...


class PassthroughChatImageStorage:
    def upload_bytes(self, data: bytes, key: str, content_type: str) -> str | None:
        return None


class S3ChatImageStorage:
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        public_url: str,
    ) -> None:
        import boto3

        self._bucket = bucket
        self._public_url = public_url.rstrip("/")
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except Exception:
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
        return f"{self._public_url}/{self._bucket}/{key}"


def get_storage_service() -> StorageService:
    if STORAGE_BACKEND == "passthrough":
        return PassthroughStorageService()
    raise ValueError(f"지원하지 않는 STORAGE_BACKEND입니다: {STORAGE_BACKEND}")


def get_chat_image_storage() -> ChatImageStorage:
    if (
        STORAGE_BACKEND == "s3"
        and S3_ENDPOINT
        and S3_ACCESS_KEY_ID
        and S3_SECRET_ACCESS_KEY
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
            logger.warning("S3 채팅 이미지 스토리지 초기화 실패, passthrough 사용: %s", exc)
    return PassthroughChatImageStorage()


storage_service = get_storage_service()
chat_image_storage = get_chat_image_storage()
