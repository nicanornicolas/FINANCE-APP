"""
API router for external integrations.
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.orm import Session

from ...api.dependencies import get_db, get_current_user
from ...crud.integration import integration as integration_crud
from ...models.user import User
from ...schemas.integration import (
    Integration, IntegrationCreate, IntegrationUpdate, IntegrationWithTokens,
    WebhookEndpoint, WebhookEndpointCreate, WebhookEndpointUpdate,
    WebhookEvent, IntegrationLog,
    OAuthAuthorizationRequest, OAuthAuthorizationResponse,
    OAuthTokenRequest, OAuthTokenResponse,
    IntegrationSyncRequest, IntegrationSyncResponse,
    IntegrationStatusResponse
)
from ...services.integration_service import integration_service
from ...services.oauth_service import OAuthService
from ...services.webhook_service import webhook_service

router = APIRouter()
oauth_service = OAuthService()


@router.get("/", response_model=List[Integration])
async def get_integrations(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's integrations."""
    integrations = integration_crud.get_by_user(db, current_user.id, skip, limit)
    return integrations


@router.post("/", response_model=Integration)
async def create_integration(
    integration_data: IntegrationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new integration."""
    try:
        integration = await integration_service.create_integration(
            db, current_user.id, integration_data
        )
        return integration
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create integration")


@router.get("/{integration_id}", response_model=Integration)
async def get_integration(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific integration."""
    integration = integration_crud.get(db, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if integration.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this integration")
    
    return integration


@router.put("/{integration_id}", response_model=Integration)
async def update_integration(
    integration_id: UUID,
    update_data: IntegrationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an integration."""
    integration = integration_crud.get(db, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if integration.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this integration")
    
    try:
        updated_integration = await integration_service.update_integration(
            db, integration_id, update_data
        )
        return updated_integration
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update integration")


@router.delete("/{integration_id}")
async def delete_integration(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an integration."""
    integration = integration_crud.get(db, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if integration.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this integration")
    
    success = await integration_service.delete_integration(db, integration_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete integration")
    
    return {"message": "Integration deleted successfully"}


@router.get("/{integration_id}/status", response_model=IntegrationStatusResponse)
async def get_integration_status(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed status for an integration."""
    integration = integration_crud.get(db, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if integration.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this integration")
    
    status_info = await integration_service.get_integration_status(db, integration_id)
    if not status_info:
        raise HTTPException(status_code=404, detail="Status information not available")
    
    return status_info


@router.post("/{integration_id}/sync", response_model=IntegrationSyncResponse)
async def sync_integration(
    integration_id: UUID,
    sync_request: IntegrationSyncRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually sync an integration."""
    integration = integration_crud.get(db, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if integration.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to sync this integration")
    
    # Run sync in background for long-running operations
    if sync_request.force:
        background_tasks.add_task(
            integration_service.sync_integration, db, integration_id, sync_request.force
        )
        return IntegrationSyncResponse(
            success=True,
            message="Sync started in background"
        )
    else:
        return await integration_service.sync_integration(db, integration_id, sync_request.force)


@router.post("/{integration_id}/test", response_model=Dict[str, Any])
async def test_integration_connection(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test connection to an integration."""
    integration = integration_crud.get(db, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if integration.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to test this integration")
    
    return await integration_service.test_connection(db, integration_id)


# OAuth endpoints
@router.post("/oauth/authorize", response_model=OAuthAuthorizationResponse)
async def get_oauth_authorization_url(
    auth_request: OAuthAuthorizationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get OAuth authorization URL for external service."""
    try:
        return await oauth_service.get_authorization_url(
            auth_request.provider,
            auth_request.redirect_uri,
            auth_request.scopes,
            auth_request.state
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to generate authorization URL")


@router.post("/oauth/token", response_model=OAuthTokenResponse)
async def exchange_oauth_token(
    token_request: OAuthTokenRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Exchange OAuth authorization code for access token."""
    try:
        return await oauth_service.exchange_code_for_tokens(
            token_request.provider,
            token_request.authorization_code,
            token_request.redirect_uri,
            token_request.state
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to exchange token")


@router.post("/{integration_id}/oauth/refresh", response_model=OAuthTokenResponse)
async def refresh_oauth_token(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Refresh OAuth token for an integration."""
    integration = integration_crud.get(db, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if integration.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to refresh this integration")
    
    if not integration.refresh_token:
        raise HTTPException(status_code=400, detail="No refresh token available")
    
    try:
        token_response = await oauth_service.refresh_token(
            integration.oauth_provider,
            integration.refresh_token
        )
        
        # Update integration with new tokens
        integration_crud.update_tokens(
            db,
            integration_id,
            token_response.access_token,
            token_response.refresh_token,
            token_response.expires_in
        )
        
        return token_response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to refresh token")


# Webhook endpoints
@router.post("/webhooks/{provider}")
async def handle_webhook(
    provider: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Handle incoming webhook from external service."""
    try:
        # Get request details
        headers = dict(request.headers)
        payload = await request.body()
        endpoint_url = str(request.url)
        
        # Process webhook in background
        background_tasks.add_task(
            webhook_service.handle_webhook,
            db, provider, endpoint_url, headers, payload
        )
        
        return {"status": "received"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to process webhook")


@router.get("/{integration_id}/logs", response_model=List[IntegrationLog])
async def get_integration_logs(
    integration_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get logs for an integration."""
    integration = integration_crud.get(db, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if integration.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access these logs")
    
    from ...crud.integration import integration_log
    logs = integration_log.get_by_integration(db, integration_id, skip, limit)
    return logs


# Admin endpoints (would require admin role check)
@router.post("/sync-all")
async def sync_all_integrations(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Sync all due integrations (admin only)."""
    # In a real implementation, you'd check for admin role here
    background_tasks.add_task(integration_service.sync_all_due_integrations, db)
    return {"message": "Sync started for all due integrations"}


@router.post("/refresh-expired-tokens")
async def refresh_all_expired_tokens(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Refresh all expired tokens (admin only)."""
    # In a real implementation, you'd check for admin role here
    background_tasks.add_task(integration_service.refresh_expired_tokens, db)
    return {"message": "Token refresh started for expired integrations"}