import os
from urllib.parse import urlparse, urlunparse

from pydantic_settings import BaseSettings, SettingsConfigDict


def _to_asyncpg_url(url: str) -> str:
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

    return (
        "postgresql+asyncpg://eventprovider:secret@eventprovider-db:5432/eventprovider"
    )


class Settings(BaseSettings):
    app_name: str = "LearnApp"
    database_url: str = _build_database_url()

    events_provider_url: str = "https://events-provider.dev-2.python-labs.ru"
    events_provider_api_key: str = os.environ.get("EVENTS_PROVIDER_API_KEY", "")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
