"""
Pydantic schemas for integration models.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from ..models.integration import IntegrationType, IntegrationStatus, OAuthProvider


class IntegrationBase(BaseModel):
    """Base schema for integration."""
    name: str = Field(..., min_length=1, max_length=255)
    integration_type: IntegrationType
    provider: str = Field(..., min_length=1, max_length=100)
    oauth_provider: Optional[OAuthProvider] = None
    config: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    sync_frequency_minutes: str = "60"


class IntegrationCreate(IntegrationBase):
    """Schema for creating an integration."""
    pass


class IntegrationUpdate(BaseModel):
    """Schema for updating an integration."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[IntegrationStatus] = None
    config: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    sync_frequency_minutes: Optional[str] = None
    is_active: Optional[bool] = None


class Integration(IntegrationBase):
    """Schema for integration response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    status: IntegrationStatus
    token_expires_at: Optional[datetime] = None
    last_sync_at: Optional[datetime] = None
    next_sync_at: Optional[datetime] = None
    last_error: Optional[str] = None
    error_count: str
    created_at: datetime
    updated_at: datetime
    is_active: bool


class IntegrationWithTokens(Integration):
    """Schema for integration with sensitive token data (admin only)."""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None


class WebhookEndpointBase(BaseModel):
    """Base schema for webhook endpoint."""
    endpoint_url: str = Field(..., min_length=1, max_length=500)
    webhook_secret: Optional[str] = Field(None, max_length=255)
    event_types: List[str] = Field(..., min_items=1)


class WebhookEndpointCreate(WebhookEndpointBase):
    """Schema for creating a webhook endpoint."""
    integration_id: UUID


class WebhookEndpointUpdate(BaseModel):
    """Schema for updating a webhook endpoint."""
    endpoint_url: Optional[str] = Field(None, min_length=1, max_length=500)
    webhook_secret: Optional[str] = Field(None, max_length=255)
    event_types: Optional[List[str]] = Field(None, min_items=1)
    is_active: Optional[bool] = None


class WebhookEndpoint(WebhookEndpointBase):
    """Schema for webhook endpoint response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    integration_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class WebhookEventBase(BaseModel):
    """Base schema for webhook event."""
    event_type: str = Field(..., min_length=1, max_length=100)
    event_data: Dict[str, Any]


class WebhookEventCreate(WebhookEventBase):
    """Schema for creating a webhook event."""
    webhook_endpoint_id: UUID


class WebhookEvent(WebhookEventBase):
    """Schema for webhook event response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    webhook_endpoint_id: UUID
    processed: bool
    processing_error: Optional[str] = None
    received_at: datetime
    processed_at: Optional[datetime] = None


class IntegrationLogBase(BaseModel):
    """Base schema for integration log."""
    action: str = Field(..., min_length=1, max_length=100)
    status: str = Field(..., min_length=1, max_length=50)
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class IntegrationLogCreate(IntegrationLogBase):
    """Schema for creating an integration log."""
    integration_id: UUID


class IntegrationLog(IntegrationLogBase):
    """Schema for integration log response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    integration_id: UUID
    created_at: datetime


class OAuthAuthorizationRequest(BaseModel):
    """Schema for OAuth authorization request."""
    provider: OAuthProvider
    redirect_uri: str
    state: Optional[str] = None
    scopes: Optional[List[str]] = None


class OAuthAuthorizationResponse(BaseModel):
    """Schema for OAuth authorization response."""
    authorization_url: str
    state: str


class OAuthTokenRequest(BaseModel):
    """Schema for OAuth token exchange."""
    provider: OAuthProvider
    authorization_code: str
    state: str
    redirect_uri: str


class OAuthTokenResponse(BaseModel):
    """Schema for OAuth token response."""
    access_token: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    token_type: str = "Bearer"


class IntegrationSyncRequest(BaseModel):
    """Schema for manual integration sync request."""
    force: bool = False


class IntegrationSyncResponse(BaseModel):
    """Schema for integration sync response."""
    success: bool
    message: str
    synced_records: Optional[int] = None
    errors: Optional[List[str]] = None


class IntegrationStatusResponse(BaseModel):
    """Schema for integration status response."""
    integration_id: UUID
    status: IntegrationStatus
    last_sync_at: Optional[datetime] = None
    next_sync_at: Optional[datetime] = None
    error_count: int
    last_error: Optional[str] = None
    health_score: float  # 0.0 to 1.0 based on recent success rate