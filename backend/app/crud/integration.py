"""
CRUD operations for integration models.
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
from datetime import datetime, timedelta

from .base import CRUDBase
from ..models.integration import (
    Integration, WebhookEndpoint, WebhookEvent, IntegrationLog,
    IntegrationStatus, IntegrationType
)
from ..schemas.integration import (
    IntegrationCreate, IntegrationUpdate,
    WebhookEndpointCreate, WebhookEndpointUpdate,
    WebhookEventCreate, IntegrationLogCreate
)


class CRUDIntegration(CRUDBase[Integration, IntegrationCreate, IntegrationUpdate]):
    """CRUD operations for Integration model."""
    
    def get_by_user(
        self, 
        db: Session, 
        user_id: UUID, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Integration]:
        """Get integrations by user ID."""
        return (
            db.query(self.model)
            .filter(self.model.user_id == user_id)
            .filter(self.model.is_active == True)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_user_and_type(
        self, 
        db: Session, 
        user_id: UUID, 
        integration_type: IntegrationType
    ) -> List[Integration]:
        """Get integrations by user ID and type."""
        return (
            db.query(self.model)
            .filter(
                and_(
                    self.model.user_id == user_id,
                    self.model.integration_type == integration_type,
                    self.model.is_active == True
                )
            )
            .all()
        )
    
    def get_by_user_and_provider(
        self, 
        db: Session, 
        user_id: UUID, 
        provider: str
    ) -> Optional[Integration]:
        """Get integration by user ID and provider."""
        return (
            db.query(self.model)
            .filter(
                and_(
                    self.model.user_id == user_id,
                    self.model.provider == provider,
                    self.model.is_active == True
                )
            )
            .first()
        )
    
    def get_active_integrations(self, db: Session) -> List[Integration]:
        """Get all active integrations."""
        return (
            db.query(self.model)
            .filter(
                and_(
                    self.model.status == IntegrationStatus.ACTIVE,
                    self.model.is_active == True
                )
            )
            .all()
        )
    
    def get_integrations_due_for_sync(self, db: Session) -> List[Integration]:
        """Get integrations that are due for synchronization."""
        now = datetime.utcnow()
        return (
            db.query(self.model)
            .filter(
                and_(
                    self.model.status == IntegrationStatus.ACTIVE,
                    self.model.is_active == True,
                    self.model.next_sync_at <= now
                )
            )
            .all()
        )
    
    def get_expired_tokens(self, db: Session) -> List[Integration]:
        """Get integrations with expired tokens."""
        now = datetime.utcnow()
        return (
            db.query(self.model)
            .filter(
                and_(
                    self.model.token_expires_at <= now,
                    self.model.access_token.isnot(None),
                    self.model.is_active == True
                )
            )
            .all()
        )
    
    def update_sync_status(
        self, 
        db: Session, 
        integration_id: UUID, 
        success: bool,
        next_sync_minutes: int = 60,
        error_message: Optional[str] = None
    ) -> Optional[Integration]:
        """Update integration sync status."""
        integration = self.get(db, integration_id)
        if not integration:
            return None
        
        now = datetime.utcnow()
        next_sync = now + timedelta(minutes=next_sync_minutes)
        
        update_data = {
            "last_sync_at": now,
            "next_sync_at": next_sync,
            "updated_at": now
        }
        
        if success:
            update_data["status"] = IntegrationStatus.ACTIVE
            update_data["error_count"] = "0"
            update_data["last_error"] = None
        else:
            current_error_count = int(integration.error_count or "0")
            update_data["error_count"] = str(current_error_count + 1)
            update_data["last_error"] = error_message
            
            # Mark as error if too many failures
            if current_error_count >= 5:
                update_data["status"] = IntegrationStatus.ERROR
        
        return self.update(db, db_obj=integration, obj_in=update_data)
    
    def update_tokens(
        self, 
        db: Session, 
        integration_id: UUID,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: Optional[int] = None
    ) -> Optional[Integration]:
        """Update OAuth tokens for integration."""
        integration = self.get(db, integration_id)
        if not integration:
            return None
        
        update_data = {
            "access_token": access_token,
            "updated_at": datetime.utcnow()
        }
        
        if refresh_token:
            update_data["refresh_token"] = refresh_token
        
        if expires_in:
            update_data["token_expires_at"] = datetime.utcnow() + timedelta(seconds=expires_in)
        
        return self.update(db, db_obj=integration, obj_in=update_data)


class CRUDWebhookEndpoint(CRUDBase[WebhookEndpoint, WebhookEndpointCreate, WebhookEndpointUpdate]):
    """CRUD operations for WebhookEndpoint model."""
    
    def get_by_integration(
        self, 
        db: Session, 
        integration_id: UUID
    ) -> List[WebhookEndpoint]:
        """Get webhook endpoints by integration ID."""
        return (
            db.query(self.model)
            .filter(
                and_(
                    self.model.integration_id == integration_id,
                    self.model.is_active == True
                )
            )
            .all()
        )
    
    def get_by_url(
        self, 
        db: Session, 
        endpoint_url: str
    ) -> Optional[WebhookEndpoint]:
        """Get webhook endpoint by URL."""
        return (
            db.query(self.model)
            .filter(self.model.endpoint_url == endpoint_url)
            .first()
        )


class CRUDWebhookEvent(CRUDBase[WebhookEvent, WebhookEventCreate, WebhookEventCreate]):
    """CRUD operations for WebhookEvent model."""
    
    def get_unprocessed(
        self, 
        db: Session, 
        limit: int = 100
    ) -> List[WebhookEvent]:
        """Get unprocessed webhook events."""
        return (
            db.query(self.model)
            .filter(self.model.processed == False)
            .order_by(self.model.received_at)
            .limit(limit)
            .all()
        )
    
    def get_by_endpoint(
        self, 
        db: Session, 
        webhook_endpoint_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[WebhookEvent]:
        """Get webhook events by endpoint ID."""
        return (
            db.query(self.model)
            .filter(self.model.webhook_endpoint_id == webhook_endpoint_id)
            .order_by(desc(self.model.received_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def mark_processed(
        self, 
        db: Session, 
        event_id: UUID,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> Optional[WebhookEvent]:
        """Mark webhook event as processed."""
        event = self.get(db, event_id)
        if not event:
            return None
        
        update_data = {
            "processed": True,
            "processed_at": datetime.utcnow()
        }
        
        if not success and error_message:
            update_data["processing_error"] = error_message
        
        return self.update(db, db_obj=event, obj_in=update_data)


class CRUDIntegrationLog(CRUDBase[IntegrationLog, IntegrationLogCreate, IntegrationLogCreate]):
    """CRUD operations for IntegrationLog model."""
    
    def get_by_integration(
        self, 
        db: Session, 
        integration_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[IntegrationLog]:
        """Get logs by integration ID."""
        return (
            db.query(self.model)
            .filter(self.model.integration_id == integration_id)
            .order_by(desc(self.model.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_recent_errors(
        self, 
        db: Session, 
        integration_id: UUID,
        hours: int = 24
    ) -> List[IntegrationLog]:
        """Get recent error logs for an integration."""
        since = datetime.utcnow() - timedelta(hours=hours)
        return (
            db.query(self.model)
            .filter(
                and_(
                    self.model.integration_id == integration_id,
                    self.model.status == "error",
                    self.model.created_at >= since
                )
            )
            .order_by(desc(self.model.created_at))
            .all()
        )
    
    def get_success_rate(
        self, 
        db: Session, 
        integration_id: UUID,
        hours: int = 24
    ) -> float:
        """Calculate success rate for an integration."""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        total_count = (
            db.query(func.count(self.model.id))
            .filter(
                and_(
                    self.model.integration_id == integration_id,
                    self.model.created_at >= since
                )
            )
            .scalar()
        )
        
        if total_count == 0:
            return 1.0
        
        success_count = (
            db.query(func.count(self.model.id))
            .filter(
                and_(
                    self.model.integration_id == integration_id,
                    self.model.status == "success",
                    self.model.created_at >= since
                )
            )
            .scalar()
        )
        
        return success_count / total_count


# Create instances
integration = CRUDIntegration(Integration)
webhook_endpoint = CRUDWebhookEndpoint(WebhookEndpoint)
webhook_event = CRUDWebhookEvent(WebhookEvent)
integration_log = CRUDIntegrationLog(IntegrationLog)