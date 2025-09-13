from pydantic_settings import BaseSettings
from typing import Optional, List
import secrets


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
    
    # Security Settings
    BCRYPT_ROUNDS: int = 12
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_NUMBERS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    DEFAULT_RATE_LIMIT: int = 100  # requests per minute
    LOGIN_RATE_LIMIT: int = 5      # login attempts per minute
    
    # Session Security
    SESSION_TIMEOUT_MINUTES: int = 60
    MFA_SESSION_TIMEOUT_MINUTES: int = 5
    
    # CORS Settings
    CORS_ORIGINS: List[str] = ["*"]  # Override in production
    CORS_ALLOW_CREDENTIALS: bool = True
    
    # Security Headers
    SECURITY_HEADERS_ENABLED: bool = True
    HSTS_MAX_AGE: int = 31536000  # 1 year
    
    # Audit Logging
    AUDIT_LOG_ENABLED: bool = True
    AUDIT_LOG_RETENTION_DAYS: int = 365
    
    # File Upload Security
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_FILE_TYPES: List[str] = [".csv", ".xlsx", ".xls", ".pdf"]
    
    # API Security
    API_KEY_LENGTH: int = 32
    API_RATE_LIMIT: int = 1000  # requests per hour
    
    # MFA Settings
    MFA_ISSUER_NAME: str = "Finance App"
    MFA_BACKUP_CODES_COUNT: int = 10
    TOTP_VALID_WINDOW: int = 1  # Allow 1 window tolerance
    
    # Account Security
    MAX_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_DURATION_MINUTES: int = 30
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 15
    
    # Data Protection
    DATA_ENCRYPTION_ENABLED: bool = True
    SENSITIVE_FIELDS_ENCRYPTION: bool = True
    
    # Monitoring and Alerting
    SECURITY_MONITORING_ENABLED: bool = True
    FAILED_LOGIN_ALERT_THRESHOLD: int = 10
    SUSPICIOUS_ACTIVITY_ALERT_ENABLED: bool = True
    
    def generate_secret_key(self) -> str:
        """Generate a secure secret key."""
        return secrets.token_urlsafe(32)
    
    def generate_encryption_key(self) -> str:
        """Generate a secure encryption key."""
        from cryptography.fernet import Fernet
        return Fernet.generate_key().decode()
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

# Generate keys if not provided (development only)
if settings.ENVIRONMENT == "development":
    if settings.SECRET_KEY == "your-secret-key-change-in-production":
        print("WARNING: Using default secret key. Generate a secure key for production!")
    
    if not settings.ENCRYPTION_KEY:
        print("WARNING: No encryption key provided. Generating temporary key for development.")
        # In production, this should be set via environment variable