from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Event Provider API"
    database_url: str = "postgresql+asyncpg://eventprovider:secret@eventprovider-db:5432/eventprovider"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

settings = Settings()