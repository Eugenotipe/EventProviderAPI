from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LearnApp"

    database_url: str = "postgresql+asyncpg://..."

    # Events Provider API
    events_provider_url: str = "http://events-provider.dev-2.python-labs.ru"
    events_provider_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
