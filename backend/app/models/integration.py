"""
Integration models for external service connections.
"""
from sqlalchemy import Column, String, DateTime, Boolean, JSON, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from ..db.database import Base


class IntegrationType(str, enum.Enum):
    """Types of external integrations."""
    BANK_API = "bank_api"
    ACCOUNTING_SOFTWARE = "accounting_software"
    PAYMENT_PROCESSOR = "payment_processor"
    INVESTMENT_PLATFORM = "investment_platform"
    KRA_ITAX = "kra_itax"


class IntegrationStatus(str, enum.Enum):
    """Status of integration connections."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING_AUTH = "pending_auth"
    EXPIRED = "expired"


class OAuthProvider(str, enum.Enum):
    """OAuth providers for external services."""
    OPEN_BANKING = "open_banking"
    QUICKBOOKS = "quickbooks"
    XERO = "xero"
    PAYPAL = "paypal"
    STRIPE = "stripe"
    KRA_ITAX = "kra_itax"


class Integration(Base):
    """Model for external service integrations."""
    __tablename__ = "integrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    integration_type = Column(SQLEnum(IntegrationType), nullable=False)
    provider = Column(String(100), nullable=False)
    status = Column(SQLEnum(IntegrationStatus), nullable=False, default=IntegrationStatus.INACTIVE)
    
    # OAuth and authentication data
    oauth_provider = Column(SQLEnum(OAuthProvider), nullable=True)
    access_token = Column(Text, nullable=True)  # Encrypted in practice
    refresh_token = Column(Text, nullable=True)  # Encrypted in practice
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Configuration and metadata
    config = Column(JSON, nullable=True)  # Provider-specific configuration
    metadata = Column(JSON, nullable=True)  # Additional metadata
    
    # Sync information
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    next_sync_at = Column(DateTime(timezone=True), nullable=True)
    sync_frequency_minutes = Column(String(50), default="60")  # How often to sync
    
    # Error tracking
    last_error = Column(Text, nullable=True)
    error_count = Column(String(10), default="0")
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)


class WebhookEndpoint(Base):
    """Model for webhook endpoints from external services."""
    __tablename__ = "webhook_endpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    endpoint_url = Column(String(500), nullable=False)
    webhook_secret = Column(String(255), nullable=True)  # For signature verification
    event_types = Column(JSON, nullable=False)  # List of event types to handle
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class WebhookEvent(Base):
    """Model for tracking webhook events."""
    __tablename__ = "webhook_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    webhook_endpoint_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    event_data = Column(JSON, nullable=False)
    processed = Column(Boolean, default=False)
    processing_error = Column(Text, nullable=True)
    
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)


class IntegrationLog(Base):
    """Model for logging integration activities."""
    __tablename__ = "integration_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    action = Column(String(100), nullable=False)  # sync, auth, webhook, etc.
    status = Column(String(50), nullable=False)  # success, error, warning
    message = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())