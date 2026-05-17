import pytest

from app.services.storage_service import (
    PassthroughStorageService,
    get_storage_service,
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
