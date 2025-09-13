"""
Audit log model for tracking user actions and system events.
"""
from sqlalchemy import Column, String, DateTime, Text, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
import uuid
import enum

from ..db.database import Base


class AuditAction(str, enum.Enum):
    """Enumeration of audit actions."""
    # Authentication actions
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    
    # User management
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_ACTIVATED = "user_activated"
    USER_DEACTIVATED = "user_deactivated"
    
    # Transaction actions
    TRANSACTION_CREATED = "transaction_created"
    TRANSACTION_UPDATED = "transaction_updated"
    TRANSACTION_DELETED = "transaction_deleted"
    TRANSACTION_IMPORTED = "transaction_imported"
    TRANSACTION_CATEGORIZED = "transaction_categorized"
    
    # Account actions
    ACCOUNT_CREATED = "account_created"
    ACCOUNT_UPDATED = "account_updated"
    ACCOUNT_DELETED = "account_deleted"
    
    # Category actions
    CATEGORY_CREATED = "category_created"
    CATEGORY_UPDATED = "category_updated"
    CATEGORY_DELETED = "category_deleted"
    
    # Tax actions
    TAX_FILING_CREATED = "tax_filing_created"
    TAX_FILING_SUBMITTED = "tax_filing_submitted"
    TAX_FILING_UPDATED = "tax_filing_updated"
    KRA_API_CALL = "kra_api_call"
    TAX_PAYMENT = "tax_payment"
    
    # Business actions
    BUSINESS_ENTITY_CREATED = "business_entity_created"
    BUSINESS_ENTITY_UPDATED = "business_entity_updated"
    INVOICE_CREATED = "invoice_created"
    INVOICE_SENT = "invoice_sent"
    
    # Report actions
    REPORT_GENERATED = "report_generated"
    REPORT_EXPORTED = "report_exported"
    DASHBOARD_VIEWED = "dashboard_viewed"
    
    # Integration actions
    INTEGRATION_CONNECTED = "integration_connected"
    INTEGRATION_DISCONNECTED = "integration_disconnected"
    BANK_SYNC = "bank_sync"
    
    # Security actions
    SECURITY_VIOLATION = "security_violation"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    
    # System actions
    SYSTEM_ERROR = "system_error"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"
    BACKUP_CREATED = "backup_created"


class AuditSeverity(str, enum.Enum):
    """Audit log severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditLog(Base):
    """Audit log model for tracking user actions and system events."""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # User information
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    user_email = Column(String, nullable=True)  # Store email for deleted users
    
    # Action details
    action = Column(SQLEnum(AuditAction), nullable=False, index=True)
    resource_type = Column(String, nullable=True)  # e.g., "transaction", "account"
    resource_id = Column(String, nullable=True)  # ID of the affected resource
    
    # Request details
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    endpoint = Column(String, nullable=True)
    http_method = Column(String, nullable=True)
    
    # Event details
    severity = Column(SQLEnum(AuditSeverity), default=AuditSeverity.LOW, nullable=False)
    description = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)  # Additional structured data
    
    # Outcome
    success = Column(String, nullable=True)  # "success", "failure", "partial"
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    user = relationship("User", backref="audit_logs")

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, user_id={self.user_id})>"


class SecurityEvent(Base):
    """Security-specific events that require special attention."""
    __tablename__ = "security_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Event details
    event_type = Column(String, nullable=False, index=True)
    severity = Column(SQLEnum(AuditSeverity), nullable=False, index=True)
    description = Column(Text, nullable=False)
    
    # Source information
    ip_address = Column(String, nullable=True, index=True)
    user_agent = Column(Text, nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    
    # Additional data
    metadata = Column(JSON, nullable=True)
    
    # Status
    resolved = Column(String, default=False, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="security_events")
    resolver = relationship("User", foreign_keys=[resolved_by])

    def __repr__(self):
        return f"<SecurityEvent(id={self.id}, event_type={self.event_type}, severity={self.severity})>"