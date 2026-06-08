import sys
from types import SimpleNamespace

import pytest

from app.schemas.chat import ChatMessageResponse
from app.services.storage_service import (
    PassthroughStorageService,
    S3ChatImageStorage,
    get_chat_image_storage,
    get_storage_service,
    public_url_for_storage_key,
)


def test_passthrough_storage_returns_source_url():
    service = PassthroughStorageService()

    stored = service.store_remote_image(
        source_url="https://example.com/image.jpg",
        key_hint="recipes/1/main",
        thumbnail_url="https://example.com/thumb.jpg",
    )

    assert stored.source_url == "https://example.com/image.jpg"
    assert stored.storage_url == "https://example.com/image.jpg"
    assert stored.thumbnail_url == "https://example.com/thumb.jpg"
    assert stored.storage_provider == "PASSTHROUGH"


def test_get_storage_service_rejects_unknown_backend(monkeypatch):
    monkeypatch.setattr("app.services.storage_service.STORAGE_BACKEND", "unknown")

    with pytest.raises(ValueError):
        get_storage_service()


def test_get_storage_service_keeps_remote_images_passthrough_for_s3(monkeypatch):
    monkeypatch.setattr("app.services.storage_service.STORAGE_BACKEND", "s3")

    assert isinstance(get_storage_service(), PassthroughStorageService)


class FakeS3Client:
    def __init__(self, *, bucket_exists=True):
        self.bucket_exists = bucket_exists
        self.created_buckets = []
        self.policies = []
        self.objects = []
        self.deleted_objects = []

    def head_bucket(self, **kwargs):
        bucket = kwargs["Bucket"]
        if not self.bucket_exists:
            raise RuntimeError(f"Missing bucket: {bucket}")

    def create_bucket(self, **kwargs):
        self.created_buckets.append(kwargs["Bucket"])
        self.bucket_exists = True

    def put_bucket_policy(self, **kwargs):
        self.policies.append((kwargs["Bucket"], kwargs["Policy"]))

    def put_object(self, **kwargs):
        self.objects.append(kwargs)

    def delete_object(self, **kwargs):
        self.deleted_objects.append(kwargs)


def test_s3_chat_image_storage_uses_minio_endpoint_and_static_keys(monkeypatch):
    calls = []
    fake_client = FakeS3Client(bucket_exists=False)

    def fake_boto3_client(service_name, **kwargs):
        calls.append((service_name, kwargs))
        return fake_client

    monkeypatch.setitem(
        sys.modules,
        "boto3",
        SimpleNamespace(client=fake_boto3_client),
    )

    storage = S3ChatImageStorage(
        endpoint="http://minio:9000",
        access_key="minio",
        secret_key="minio123",
        bucket="naengo-local",
        public_url="http://localhost:9000",
    )

    key = storage.upload_bytes(b"image", "user-recipes/main.jpg", "image/jpeg")

    assert calls == [
        (
            "s3",
            {
                "endpoint_url": "http://minio:9000",
                "aws_access_key_id": "minio",
                "aws_secret_access_key": "minio123",
            },
        )
    ]
    assert fake_client.created_buckets == ["naengo-local"]
    assert key == "user-recipes/main.jpg"


def test_s3_chat_image_storage_uses_default_role_credentials(monkeypatch):
    calls = []
    fake_client = FakeS3Client()

    def fake_boto3_client(service_name, **kwargs):
        calls.append((service_name, kwargs))
        return fake_client

    monkeypatch.setitem(
        sys.modules,
        "boto3",
        SimpleNamespace(client=fake_boto3_client),
    )

    storage = S3ChatImageStorage(
        endpoint=None,
        access_key=None,
        secret_key=None,
        bucket="naengo-images",
        public_url="https://d123.cloudfront.net",
    )

    key = storage.upload_bytes(b"image", "/user-recipes/main.jpg", "image/jpeg")

    assert calls == [("s3", {})]
    assert fake_client.created_buckets == []
    assert key == "user-recipes/main.jpg"


def test_s3_chat_image_storage_deletes_normalized_key(monkeypatch):
    fake_client = FakeS3Client()

    monkeypatch.setitem(
        sys.modules,
        "boto3",
        SimpleNamespace(client=lambda *_args, **_kwargs: fake_client),
    )

    storage = S3ChatImageStorage(
        endpoint=None,
        access_key=None,
        secret_key=None,
        bucket="naengo-images",
        public_url="https://d123.cloudfront.net",
    )

    storage.delete_bytes("/user-recipes/main.jpg")

    assert fake_client.deleted_objects == [
        {
            "Bucket": "naengo-images",
            "Key": "user-recipes/main.jpg",
        }
    ]


def test_public_url_for_storage_key_preserves_absolute_urls(monkeypatch):
    monkeypatch.setattr(
        "app.services.storage_service.S3_PUBLIC_URL",
        "https://d123.cloudfront.net",
    )

    assert (
        public_url_for_storage_key("https://example.com/image.jpg")
        == "https://example.com/image.jpg"
    )


def test_public_url_for_storage_key_uses_cloudfront_domain(monkeypatch):
    monkeypatch.setattr("app.services.storage_service.S3_ENDPOINT", None)
    monkeypatch.setattr("app.services.storage_service.S3_BUCKET", "naengo-images")
    monkeypatch.setattr(
        "app.services.storage_service.S3_PUBLIC_URL",
        "https://d123.cloudfront.net",
    )

    assert (
        public_url_for_storage_key("user-recipes/main.jpg")
        == "https://d123.cloudfront.net/user-recipes/main.jpg"
    )


def test_public_url_for_storage_key_uses_minio_bucket_path(monkeypatch):
    monkeypatch.setattr("app.services.storage_service.S3_ENDPOINT", "http://minio:9000")
    monkeypatch.setattr("app.services.storage_service.S3_BUCKET", "naengo-local")
    monkeypatch.setattr(
        "app.services.storage_service.S3_PUBLIC_URL",
        "http://localhost:9000",
    )

    assert (
        public_url_for_storage_key("user-recipes/main.jpg")
        == "http://localhost:9000/naengo-local/user-recipes/main.jpg"
    )


def test_chat_message_response_expands_storage_key(monkeypatch):
    monkeypatch.setattr("app.services.storage_service.S3_ENDPOINT", None)
    monkeypatch.setattr("app.services.storage_service.S3_BUCKET", "naengo-images")
    monkeypatch.setattr(
        "app.services.storage_service.S3_PUBLIC_URL",
        "https://d123.cloudfront.net",
    )

    response = ChatMessageResponse(
        message_id=1,
        role="user",
        content="냉장고 사진이에요",
        image_url="chat/1/image.jpg",
        created_at="2026-05-28T00:00:00+09:00",
    )

    assert (
        response.model_dump(mode="json")["image_url"]
        == "https://d123.cloudfront.net/chat/1/image.jpg"
    )


def test_get_chat_image_storage_allows_role_based_s3(monkeypatch):
    class FakeStorage:
        is_available = True

        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr("app.services.storage_service.STORAGE_BACKEND", "s3")
    monkeypatch.setattr("app.services.storage_service.S3_ENDPOINT", None)
    monkeypatch.setattr("app.services.storage_service.S3_ACCESS_KEY_ID", None)
    monkeypatch.setattr("app.services.storage_service.S3_SECRET_ACCESS_KEY", None)
    monkeypatch.setattr("app.services.storage_service.S3_BUCKET", "naengo-images")
    monkeypatch.setattr(
        "app.services.storage_service.S3_PUBLIC_URL",
        "https://d123.cloudfront.net",
    )
    monkeypatch.setattr("app.services.storage_service.S3ChatImageStorage", FakeStorage)

    storage = get_chat_image_storage()

    assert isinstance(storage, FakeStorage)
    assert storage.kwargs == {
        "endpoint": None,
        "access_key": None,
        "secret_key": None,
        "bucket": "naengo-images",
        "public_url": "https://d123.cloudfront.net",
    }
