"""
Multi-Factor Authentication models.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
import uuid
from datetime import datetime, timedelta

from ..db.database import Base


class MFAMethod(Base):
    """Multi-Factor Authentication methods for users."""
    __tablename__ = "mfa_methods"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Method details
    method_type = Column(String, nullable=False)  # "totp", "sms", "email", "backup_codes"
    method_name = Column(String, nullable=True)  # User-friendly name
    
    # TOTP-specific fields
    secret_key = Column(String, nullable=True)  # Encrypted TOTP secret
    
    # SMS/Email-specific fields
    phone_number = Column(String, nullable=True)  # Encrypted phone number
    email_address = Column(String, nullable=True)  # Email for MFA
    
    # Backup codes
    backup_codes = Column(Text, nullable=True)  # Encrypted JSON array of backup codes
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Usage tracking
    last_used = Column(DateTime(timezone=True), nullable=True)
    use_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="mfa_methods")

    def __repr__(self):
        return f"<MFAMethod(id={self.id}, user_id={self.user_id}, method_type={self.method_type})>"


class MFAAttempt(Base):
    """MFA verification attempts for security monitoring."""
    __tablename__ = "mfa_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    mfa_method_id = Column(UUID(as_uuid=True), ForeignKey("mfa_methods.id"), nullable=True, index=True)
    
    # Attempt details
    method_type = Column(String, nullable=False)
    code_provided = Column(String, nullable=True)  # Hashed version of provided code
    success = Column(Boolean, nullable=False)
    
    # Request details
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Timestamps
    attempted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    user = relationship("User")
    mfa_method = relationship("MFAMethod")

    def __repr__(self):
        return f"<MFAAttempt(id={self.id}, user_id={self.user_id}, success={self.success})>"


class MFASession(Base):
    """Temporary MFA sessions for multi-step authentication."""
    __tablename__ = "mfa_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Session details
    session_token = Column(String, nullable=False, unique=True, index=True)
    challenge_type = Column(String, nullable=False)  # "login", "sensitive_operation"
    
    # Status
    is_verified = Column(Boolean, default=False, nullable=False)
    is_expired = Column(Boolean, default=False, nullable=False)
    
    # Expiry
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Request details
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<MFASession(id={self.id}, user_id={self.user_id}, is_verified={self.is_verified})>"

    @property
    def is_valid(self) -> bool:
        """Check if the MFA session is still valid."""
        return (
            not self.is_expired and 
            datetime.utcnow() < self.expires_at and
            not self.is_verified
        )

    def mark_expired(self):
        """Mark the session as expired."""
        self.is_expired = True

    def mark_verified(self):
        """Mark the session as verified."""
        self.is_verified = True
        self.verified_at = datetime.utcnow()