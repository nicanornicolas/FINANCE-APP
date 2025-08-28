"""
Core integration service for managing external service connections.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from ..crud.integration import integration as integration_crud, integration_log as log_crud
from ..models.integration import Integration, IntegrationType, IntegrationStatus
from ..schemas.integration import (
    IntegrationCreate, IntegrationUpdate, IntegrationSyncResponse,
    IntegrationStatusResponse, IntegrationLogCreate
)
from .oauth_service import OAuthService
from .bank_integration_service import BankIntegrationService
from .accounting_integration_service import AccountingIntegrationService
from .payment_integration_service import PaymentIntegrationService

logger = logging.getLogger(__name__)


class IntegrationService:
    """Service for managing external integrations."""
    
    def __init__(self):
        self.oauth_service = OAuthService()
        self.bank_service = BankIntegrationService()
        self.accounting_service = AccountingIntegrationService()
        self.payment_service = PaymentIntegrationService()
        
        # Map integration types to their respective services
        self.service_map = {
            IntegrationType.BANK_API: self.bank_service,
            IntegrationType.ACCOUNTING_SOFTWARE: self.accounting_service,
            IntegrationType.PAYMENT_PROCESSOR: self.payment_service,
        }
    
    async def create_integration(
        self, 
        db: Session, 
        user_id: UUID, 
        integration_data: IntegrationCreate
    ) -> Integration:
        """Create a new integration."""
        try:
            # Check if integration already exists for this user and provider
            existing = integration_crud.get_by_user_and_provider(
                db, user_id, integration_data.provider
            )
            if existing:
                raise ValueError(f"Integration with provider {integration_data.provider} already exists")
            
            # Create integration record
            integration_obj = integration_crud.create(
                db, 
                obj_in={
                    **integration_data.model_dump(),
                    "user_id": user_id,
                    "status": IntegrationStatus.INACTIVE
                }
            )
            
            # Log creation
            await self._log_action(
                db, 
                integration_obj.id, 
                "create", 
                "success", 
                f"Integration created for provider {integration_data.provider}"
            )
            
            return integration_obj
            
        except Exception as e:
            logger.error(f"Failed to create integration: {str(e)}")
            raise
    
    async def update_integration(
        self, 
        db: Session, 
        integration_id: UUID, 
        update_data: IntegrationUpdate
    ) -> Optional[Integration]:
        """Update an existing integration."""
        try:
            integration_obj = integration_crud.get(db, integration_id)
            if not integration_obj:
                return None
            
            updated_integration = integration_crud.update(
                db, 
                db_obj=integration_obj, 
                obj_in=update_data
            )
            
            await self._log_action(
                db, 
                integration_id, 
                "update", 
                "success", 
                "Integration updated successfully"
            )
            
            return updated_integration
            
        except Exception as e:
            logger.error(f"Failed to update integration {integration_id}: {str(e)}")
            await self._log_action(
                db, 
                integration_id, 
                "update", 
                "error", 
                f"Failed to update integration: {str(e)}"
            )
            raise
    
    async def delete_integration(
        self, 
        db: Session, 
        integration_id: UUID
    ) -> bool:
        """Soft delete an integration."""
        try:
            integration_obj = integration_crud.get(db, integration_id)
            if not integration_obj:
                return False
            
            # Revoke OAuth tokens if they exist
            if integration_obj.access_token:
                await self.oauth_service.revoke_token(
                    integration_obj.oauth_provider,
                    integration_obj.access_token
                )
            
            # Soft delete
            integration_crud.update(
                db, 
                db_obj=integration_obj, 
                obj_in={"is_active": False}
            )
            
            await self._log_action(
                db, 
                integration_id, 
                "delete", 
                "success", 
                "Integration deleted successfully"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete integration {integration_id}: {str(e)}")
            await self._log_action(
                db, 
                integration_id, 
                "delete", 
                "error", 
                f"Failed to delete integration: {str(e)}"
            )
            return False
    
    async def sync_integration(
        self, 
        db: Session, 
        integration_id: UUID, 
        force: bool = False
    ) -> IntegrationSyncResponse:
        """Sync data from an external integration."""
        try:
            integration_obj = integration_crud.get(db, integration_id)
            if not integration_obj:
                return IntegrationSyncResponse(
                    success=False,
                    message="Integration not found"
                )
            
            if integration_obj.status != IntegrationStatus.ACTIVE and not force:
                return IntegrationSyncResponse(
                    success=False,
                    message="Integration is not active"
                )
            
            # Get the appropriate service for this integration type
            service = self.service_map.get(integration_obj.integration_type)
            if not service:
                return IntegrationSyncResponse(
                    success=False,
                    message=f"No service available for integration type {integration_obj.integration_type}"
                )
            
            # Perform the sync
            sync_result = await service.sync_data(db, integration_obj)
            
            # Update integration sync status
            integration_crud.update_sync_status(
                db,
                integration_id,
                sync_result.success,
                error_message=sync_result.message if not sync_result.success else None
            )
            
            # Log the sync attempt
            await self._log_action(
                db,
                integration_id,
                "sync",
                "success" if sync_result.success else "error",
                sync_result.message,
                {"synced_records": sync_result.synced_records}
            )
            
            return sync_result
            
        except Exception as e:
            logger.error(f"Failed to sync integration {integration_id}: {str(e)}")
            
            # Update integration with error
            integration_crud.update_sync_status(
                db,
                integration_id,
                False,
                error_message=str(e)
            )
            
            await self._log_action(
                db,
                integration_id,
                "sync",
                "error",
                f"Sync failed: {str(e)}"
            )
            
            return IntegrationSyncResponse(
                success=False,
                message=str(e)
            )
    
    async def sync_all_due_integrations(self, db: Session) -> Dict[str, Any]:
        """Sync all integrations that are due for synchronization."""
        due_integrations = integration_crud.get_integrations_due_for_sync(db)
        results = {
            "total": len(due_integrations),
            "successful": 0,
            "failed": 0,
            "errors": []
        }
        
        for integration_obj in due_integrations:
            try:
                sync_result = await self.sync_integration(db, integration_obj.id)
                if sync_result.success:
                    results["successful"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append({
                        "integration_id": str(integration_obj.id),
                        "provider": integration_obj.provider,
                        "error": sync_result.message
                    })
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "integration_id": str(integration_obj.id),
                    "provider": integration_obj.provider,
                    "error": str(e)
                })
        
        logger.info(f"Sync completed: {results['successful']} successful, {results['failed']} failed")
        return results
    
    async def refresh_expired_tokens(self, db: Session) -> Dict[str, Any]:
        """Refresh expired OAuth tokens."""
        expired_integrations = integration_crud.get_expired_tokens(db)
        results = {
            "total": len(expired_integrations),
            "successful": 0,
            "failed": 0,
            "errors": []
        }
        
        for integration_obj in expired_integrations:
            try:
                if integration_obj.refresh_token:
                    token_response = await self.oauth_service.refresh_token(
                        integration_obj.oauth_provider,
                        integration_obj.refresh_token
                    )
                    
                    integration_crud.update_tokens(
                        db,
                        integration_obj.id,
                        token_response.access_token,
                        token_response.refresh_token,
                        token_response.expires_in
                    )
                    
                    results["successful"] += 1
                    
                    await self._log_action(
                        db,
                        integration_obj.id,
                        "token_refresh",
                        "success",
                        "OAuth token refreshed successfully"
                    )
                else:
                    # Mark as expired if no refresh token
                    integration_crud.update(
                        db,
                        db_obj=integration_obj,
                        obj_in={"status": IntegrationStatus.EXPIRED}
                    )
                    results["failed"] += 1
                    
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "integration_id": str(integration_obj.id),
                    "provider": integration_obj.provider,
                    "error": str(e)
                })
                
                await self._log_action(
                    db,
                    integration_obj.id,
                    "token_refresh",
                    "error",
                    f"Failed to refresh token: {str(e)}"
                )
        
        return results
    
    async def get_integration_status(
        self, 
        db: Session, 
        integration_id: UUID
    ) -> Optional[IntegrationStatusResponse]:
        """Get detailed status information for an integration."""
        integration_obj = integration_crud.get(db, integration_id)
        if not integration_obj:
            return None
        
        # Calculate health score based on recent success rate
        success_rate = log_crud.get_success_rate(db, integration_id, hours=24)
        
        return IntegrationStatusResponse(
            integration_id=integration_id,
            status=integration_obj.status,
            last_sync_at=integration_obj.last_sync_at,
            next_sync_at=integration_obj.next_sync_at,
            error_count=int(integration_obj.error_count or "0"),
            last_error=integration_obj.last_error,
            health_score=success_rate
        )
    
    async def test_connection(
        self, 
        db: Session, 
        integration_id: UUID
    ) -> Dict[str, Any]:
        """Test the connection to an external service."""
        try:
            integration_obj = integration_crud.get(db, integration_id)
            if not integration_obj:
                return {"success": False, "message": "Integration not found"}
            
            service = self.service_map.get(integration_obj.integration_type)
            if not service:
                return {
                    "success": False, 
                    "message": f"No service available for integration type {integration_obj.integration_type}"
                }
            
            # Test the connection
            test_result = await service.test_connection(integration_obj)
            
            await self._log_action(
                db,
                integration_id,
                "test_connection",
                "success" if test_result["success"] else "error",
                test_result["message"]
            )
            
            return test_result
            
        except Exception as e:
            logger.error(f"Failed to test connection for integration {integration_id}: {str(e)}")
            
            await self._log_action(
                db,
                integration_id,
                "test_connection",
                "error",
                f"Connection test failed: {str(e)}"
            )
            
            return {"success": False, "message": str(e)}
    
    async def _log_action(
        self,
        db: Session,
        integration_id: UUID,
        action: str,
        status: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log an integration action."""
        try:
            log_crud.create(
                db,
                obj_in=IntegrationLogCreate(
                    integration_id=integration_id,
                    action=action,
                    status=status,
                    message=message,
                    details=details
                )
            )
        except Exception as e:
            logger.error(f"Failed to log integration action: {str(e)}")


# Create service instance
integration_service = IntegrationService()