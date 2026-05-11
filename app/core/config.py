from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


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
    base_url: str = Field(alias="BASE_URL")
    model_name: str = Field(alias="MODEL_NAME")
    temp_user_id: int = 1

settings = Settings()

DATABASE_URL = settings.database_url
EMBEDDING_API_KEY = settings.embedding_api_key
EMBEDDING_MODEL = settings.embedding_model

API_KEY = settings.api_key
BASE_URL = settings.base_url
MODEL_NAME = settings.model_name

TEMP_USER_ID = settings.temp_user_id
