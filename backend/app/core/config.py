from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/finance"
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Redis
    REDIS_URL: str = "redis://redis:6379"
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # KRA API Configuration
    KRA_API_BASE_URL: str = "https://itax.kra.go.ke/api/v1"
    KRA_CLIENT_ID: str = ""
    KRA_CLIENT_SECRET: str = ""
    USE_MOCK_KRA: bool = True  # Set to False in production
    
    # Encryption key for sensitive data (KRA PINs, etc.)
    ENCRYPTION_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()