from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Finance Backend"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://postgres:postgres@db:5432/finance"
    redis_url: str = "redis://redis:6379/0"

    class Config:
        env_file = ".env"

settings = Settings()
