from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_STORAGE_BACKEND = "passthrough"
DEFAULT_LIVE_SEARCH_PROVIDER = "disabled"
DEFAULT_BRAVE_SEARCH_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"


def normalize_optional_url(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped or stripped.lower() in {"none", "null"}:
        return None
    return stripped


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(alias="DATABASE_URL")
    embedding_api_key: str = Field(alias="EMBEDDING_API_KEY")
    embedding_model: str = Field(
        default=DEFAULT_EMBEDDING_MODEL,
        alias="EMBEDDING_MODEL",
    )
    api_key: str = Field(alias="API_KEY")
    base_url: str | None = Field(default=None, alias="BASE_URL")
    model_name: str = Field(alias="MODEL_NAME")
    temp_user_id: int = 1
    internal_api_secret: str | None = Field(
        default=None,
        alias="INTERNAL_API_SECRET",
    )
    storage_backend: str = Field(
        default=DEFAULT_STORAGE_BACKEND,
        alias="STORAGE_BACKEND",
    )
    s3_endpoint: str | None = Field(default=None, alias="S3_ENDPOINT")
    s3_access_key_id: str | None = Field(default=None, alias="S3_ACCESS_KEY_ID")
    s3_secret_access_key: str | None = Field(default=None, alias="S3_SECRET_ACCESS_KEY")
    s3_bucket: str | None = Field(default=None, alias="S3_BUCKET")
    s3_public_url: str | None = Field(default=None, alias="S3_PUBLIC_URL")
    live_search_provider: str = Field(
        default=DEFAULT_LIVE_SEARCH_PROVIDER,
        alias="LIVE_SEARCH_PROVIDER",
    )
    brave_search_api_key: str | None = Field(
        default=None,
        alias="BRAVE_SEARCH_API_KEY",
    )
    brave_search_endpoint: str = Field(
        default=DEFAULT_BRAVE_SEARCH_ENDPOINT,
        alias="BRAVE_SEARCH_ENDPOINT",
    )
    live_search_timeout_seconds: float = Field(
        default=5.0,
        alias="LIVE_SEARCH_TIMEOUT_SECONDS",
    )
    recipe_import_rewrite_enabled: bool = Field(
        default=True,
        alias="RECIPE_IMPORT_REWRITE_ENABLED",
    )
    recipe_import_ai_timeout_seconds: float = Field(
        default=90.0,
        alias="RECIPE_IMPORT_AI_TIMEOUT_SECONDS",
    )

settings = Settings()

DATABASE_URL = settings.database_url
EMBEDDING_API_KEY = settings.embedding_api_key
EMBEDDING_MODEL = settings.embedding_model

API_KEY = settings.api_key
BASE_URL = normalize_optional_url(settings.base_url)
MODEL_NAME = settings.model_name

TEMP_USER_ID = settings.temp_user_id
INTERNAL_API_SECRET = settings.internal_api_secret
STORAGE_BACKEND = settings.storage_backend
S3_ENDPOINT = settings.s3_endpoint
S3_ACCESS_KEY_ID = settings.s3_access_key_id
S3_SECRET_ACCESS_KEY = settings.s3_secret_access_key
S3_BUCKET = settings.s3_bucket
S3_PUBLIC_URL = normalize_optional_url(settings.s3_public_url)
LIVE_SEARCH_PROVIDER = settings.live_search_provider
BRAVE_SEARCH_API_KEY = settings.brave_search_api_key
BRAVE_SEARCH_ENDPOINT = settings.brave_search_endpoint
LIVE_SEARCH_TIMEOUT_SECONDS = settings.live_search_timeout_seconds
RECIPE_IMPORT_REWRITE_ENABLED = settings.recipe_import_rewrite_enabled
RECIPE_IMPORT_AI_TIMEOUT_SECONDS = settings.recipe_import_ai_timeout_seconds
