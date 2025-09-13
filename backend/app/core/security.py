"""
Security utilities for data encryption, hashing, and other security operations.
"""
import hashlib
import secrets
import base64
from typing import Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from passlib.context import CryptContext
import bcrypt

from .config import settings


class EncryptionManager:
    """Handles encryption and decryption of sensitive data."""
    
    def __init__(self):
        self._fernet = None
        self._init_encryption()
    
    def _init_encryption(self):
        """Initialize encryption with key from settings or generate new one."""
        if settings.ENCRYPTION_KEY:
            # Use existing key from settings
            key = settings.ENCRYPTION_KEY.encode()
        else:
            # Generate a new key (should be stored securely in production)
            key = Fernet.generate_key()
            # In production, this should be stored in a secure key management service
            print(f"Generated encryption key: {key.decode()}")
            print("Store this key securely and set ENCRYPTION_KEY environment variable")
        
        self._fernet = Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data."""
        if not data:
            return data
        
        encrypted_data = self._fernet.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        if not encrypted_data:
            return encrypted_data
        
        try:
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self._fernet.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception:
            # Return empty string if decryption fails
            return ""


class PasswordManager:
    """Handles password hashing and verification."""
    
    def __init__(self):
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=12  # Higher rounds for better security
        )
    
    def hash_password(self, password: str) -> str:
        """Hash a password."""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(length)


class SecurityUtils:
    """General security utilities."""
    
    @staticmethod
    def generate_salt() -> str:
        """Generate a random salt for hashing."""
        return secrets.token_hex(16)
    
    @staticmethod
    def hash_with_salt(data: str, salt: str) -> str:
        """Hash data with salt using SHA-256."""
        return hashlib.sha256((data + salt).encode()).hexdigest()
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key."""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
        """Mask sensitive data showing only last few characters."""
        if not data or len(data) <= visible_chars:
            return "*" * len(data) if data else ""
        
        return "*" * (len(data) - visible_chars) + data[-visible_chars:]


# Global instances
encryption_manager = EncryptionManager()
password_manager = PasswordManager()
security_utils = SecurityUtils()