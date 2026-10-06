import os

from pydantic_settings import BaseSettings, SettingsConfigDict


def _build_database_url() -> str:
    if url := os.environ.get("DATABASE_URL"):
        return url
    if conn := os.environ.get("POSTGRES_CONNECTION_STRING"):
        return conn.replace("postgres://", "postgresql+asyncpg://", 1)
    if all(
        os.environ.get(k)
        for k in (
            "POSTGRES_USERNAME",
            "POSTGRES_PASSWORD",
            "POSTGRES_HOST",
            "POSTGRES_DATABASE_NAME",
        )
    ):
        user = os.environ["POSTGRES_USERNAME"]
        password = os.environ["POSTGRES_PASSWORD"]
        host = os.environ["POSTGRES_HOST"]
        port = os.environ.get("POSTGRES_PORT", "5432")
        db = os.environ["POSTGRES_DATABASE_NAME"]
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"
    return (
        "postgresql+asyncpg://eventprovider:secret@eventprovider-db:5432/eventprovider"
    )


def _build_events_provider_url() -> str:
    if url := os.environ.get("EVENTS_PROVIDER_URL"):
        return url
    if os.environ.get("POSTGRES_CONNECTION_STRING"):
        return (
            "http://student-system-events-provider-web"
            ".student-system-events-provider.svc:8000"
        )
    return "https://events-provider.dev-2.python-labs.ru"

def _default_capashino_url() -> str:
    if os.environ.get("CAPASHINO_URL"):
        return os.environ["CAPASHINO_URL"]
    if os.environ.get("POSTGRES_CONNECTION_STRING"):
        return "http://student-system-capashino-web.student-system-capashino.svc:8000"
    return "https://capashino.dev-2.python-labs.ru"


class Settings(BaseSettings):
    app_name: str = "LearnApp"
    database_url: str = _build_database_url()
    events_provider_url: str = _build_events_provider_url()
    events_provider_api_key: str = os.environ.get("EVENTS_PROVIDER_API_KEY", "")

    capashino_url: str = _default_capashino_url()
    capashino_api_key: str = os.environ.get("CAPASHINO_API_KEY")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
