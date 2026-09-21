from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import urlparse, urlunparse

import os

def _to_asyncpg_url(url: str) -> str:
    """postgres://... → postgresql+asyncpg://... для SQLAlchemy."""
    if url.startswith("postgresql+asyncpg://"):
        return url
    parsed = urlparse(url)
    return urlunparse(parsed._replace(scheme="postgresql+asyncpg"))


def _build_database_url() -> str:
    if url := os.environ.get("DATABASE_URL"):
        return _to_asyncpg_url(url)

    if conn := os.environ.get("POSTGRES_CONNECTION_STRING"):
        return _to_asyncpg_url(conn)

    user = os.environ.get("POSTGRES_USERNAME")
    password = os.environ.get("POSTGRES_PASSWORD")
    host = os.environ.get("POSTGRES_HOST")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DATABASE_NAME")
    if all([user, password, host, db]):
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"

    return "postgresql+asyncpg://eventprovider:secret@eventprovider-db:5432/eventprovider"

class Settings(BaseSettings):
    app_name: str = "Event Provider API"
    database_url: str = _build_database_url()

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

settings = Settings()