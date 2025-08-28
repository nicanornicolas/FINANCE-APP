"""
Tests for integration framework.
"""
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.integration import Integration, IntegrationType, IntegrationStatus, OAuthProvider
from app.schemas.integration import IntegrationCreate, IntegrationUpdate
from app.services.integration_service import integration_service
from app.services.oauth_service import OAuthService
from app.services.webhook_service import webhook_service
from app.crud.integration import integration as integration_crud

client = TestClient(app)


class TestIntegrationModels:
    """Test integration models."""
    
    def test_integration_model_creation(self, db: Session, test_user):
        """Test creating an integration model."""
        integration_data = {
            "user_id": test_user.id,
            "name": "Test Bank Integration",
            "integration_type": IntegrationType.BANK_API,
            "provider": "test_bank",
            "status": IntegrationStatus.INACTIVE
        }
        
        integration = integration_crud.create(db, obj_in=integration_data)
        
        assert integration.id is not None
        assert integration.user_id == test_user.id
        assert integration.name == "Test Bank Integration"
        assert integration.integration_type == IntegrationType.BANK_API
        assert integration.provider == "test_bank"
        assert integration.status == IntegrationStatus.INACTIVE
        assert integration.is_active is True
    
    def test_integration_model_relationships(self, db: Session, test_user):
        """Test integration model relationships."""
        integration_data = {
            "user_id": test_user.id,
            "name": "Test Integration",
            "integration_type": IntegrationType.PAYMENT_PROCESSOR,
            "provider": "stripe"
        }
        
        integration = integration_crud.create(db, obj_in=integration_data)
        
        # Test querying by user
        user_integrations = integration_crud.get_by_user(db, test_user.id)
        assert len(user_integrations) == 1
        assert user_integrations[0].id == integration.id


class TestIntegrationCRUD:
    """Test integration CRUD operations."""
    
    def test_create_integration(self, db: Session, test_user):
        """Test creating an integration."""
        integration_data = IntegrationCreate(
            name="PayPal Integration",
            integration_type=IntegrationType.PAYMENT_PROCESSOR,
            provider="paypal",
            oauth_provider=OAuthProvider.PAYPAL
        )
        
        integration = integration_crud.create(
            db, 
            obj_in={
                **integration_data.model_dump(),
                "user_id": test_user.id
            }
        )
        
        assert integration.name == "PayPal Integration"
        assert integration.integration_type == IntegrationType.PAYMENT_PROCESSOR
        assert integration.provider == "paypal"
        assert integration.oauth_provider == OAuthProvider.PAYPAL
    
    def test_get_by_user_and_provider(self, db: Session, test_user):
        """Test getting integration by user and provider."""
        integration_data = {
            "user_id": test_user.id,
            "name": "QuickBooks Integration",
            "integration_type": IntegrationType.ACCOUNTING_SOFTWARE,
            "provider": "quickbooks"
        }
        
        created_integration = integration_crud.create(db, obj_in=integration_data)
        
        found_integration = integration_crud.get_by_user_and_provider(
            db, test_user.id, "quickbooks"
        )
        
        assert found_integration is not None
        assert found_integration.id == created_integration.id
    
    def test_get_integrations_due_for_sync(self, db: Session, test_user):
        """Test getting integrations due for sync."""
        # Create integration that's due for sync
        past_time = datetime.utcnow() - timedelta(minutes=30)
        integration_data = {
            "user_id": test_user.id,
            "name": "Due Integration",
            "integration_type": IntegrationType.BANK_API,
            "provider": "test_bank",
            "status": IntegrationStatus.ACTIVE,
            "next_sync_at": past_time
        }
        
        integration_crud.create(db, obj_in=integration_data)
        
        due_integrations = integration_crud.get_integrations_due_for_sync(db)
        assert len(due_integrations) >= 1
    
    def test_update_sync_status(self, db: Session, test_user):
        """Test updating integration sync status."""
        integration_data = {
            "user_id": test_user.id,
            "name": "Test Integration",
            "integration_type": IntegrationType.BANK_API,
            "provider": "test_bank"
        }
        
        integration = integration_crud.create(db, obj_in=integration_data)
        
        # Update sync status - success
        updated_integration = integration_crud.update_sync_status(
            db, integration.id, success=True, next_sync_minutes=120
        )
        
        assert updated_integration.status == IntegrationStatus.ACTIVE
        assert updated_integration.error_count == "0"
        assert updated_integration.last_sync_at is not None
        assert updated_integration.next_sync_at is not None
        
        # Update sync status - failure
        updated_integration = integration_crud.update_sync_status(
            db, integration.id, success=False, error_message="Test error"
        )
        
        assert updated_integration.error_count == "1"
        assert updated_integration.last_error == "Test error"


class TestOAuthService:
    """Test OAuth service."""
    
    @pytest.fixture
    def oauth_service(self):
        return OAuthService()
    
    def test_get_authorization_url(self, oauth_service):
        """Test generating OAuth authorization URL."""
        auth_response = oauth_service.get_authorization_url(
            OAuthProvider.STRIPE,
            "https://example.com/callback",
            ["read_write"]
        )
        
        assert "authorization_url" in auth_response
        assert "state" in auth_response
        assert "connect.stripe.com" in auth_response["authorization_url"]
    
    @patch('httpx.AsyncClient.post')
    async def test_exchange_code_for_tokens(self, mock_post, oauth_service):
        """Test exchanging authorization code for tokens."""
        # Mock successful token response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer"
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value.__aenter__.return_value = mock_response
        
        token_response = await oauth_service.exchange_code_for_tokens(
            OAuthProvider.STRIPE,
            "test_auth_code",
            "https://example.com/callback",
            "test_state"
        )
        
        assert token_response.access_token == "test_access_token"
        assert token_response.refresh_token == "test_refresh_token"
        assert token_response.expires_in == 3600
    
    @patch('httpx.AsyncClient.post')
    async def test_refresh_token(self, mock_post, oauth_service):
        """Test refreshing OAuth token."""
        # Mock successful refresh response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value.__aenter__.return_value = mock_response
        
        token_response = await oauth_service.refresh_token(
            OAuthProvider.STRIPE,
            "old_refresh_token"
        )
        
        assert token_response.access_token == "new_access_token"
        assert token_response.refresh_token == "new_refresh_token"


class TestIntegrationService:
    """Test integration service."""
    
    @pytest.mark.asyncio
    async def test_create_integration(self, db: Session, test_user):
        """Test creating integration through service."""
        integration_data = IntegrationCreate(
            name="Test Service Integration",
            integration_type=IntegrationType.BANK_API,
            provider="test_bank"
        )
        
        integration = await integration_service.create_integration(
            db, test_user.id, integration_data
        )
        
        assert integration.name == "Test Service Integration"
        assert integration.user_id == test_user.id
        assert integration.status == IntegrationStatus.INACTIVE
    
    @pytest.mark.asyncio
    async def test_create_duplicate_integration(self, db: Session, test_user):
        """Test creating duplicate integration raises error."""
        integration_data = IntegrationCreate(
            name="Duplicate Integration",
            integration_type=IntegrationType.BANK_API,
            provider="duplicate_bank"
        )
        
        # Create first integration
        await integration_service.create_integration(
            db, test_user.id, integration_data
        )
        
        # Try to create duplicate
        with pytest.raises(ValueError, match="already exists"):
            await integration_service.create_integration(
                db, test_user.id, integration_data
            )
    
    @pytest.mark.asyncio
    async def test_update_integration(self, db: Session, test_user):
        """Test updating integration through service."""
        # Create integration
        integration_data = IntegrationCreate(
            name="Original Name",
            integration_type=IntegrationType.BANK_API,
            provider="test_bank"
        )
        
        integration = await integration_service.create_integration(
            db, test_user.id, integration_data
        )
        
        # Update integration
        update_data = IntegrationUpdate(name="Updated Name")
        updated_integration = await integration_service.update_integration(
            db, integration.id, update_data
        )
        
        assert updated_integration.name == "Updated Name"
    
    @pytest.mark.asyncio
    async def test_delete_integration(self, db: Session, test_user):
        """Test deleting integration through service."""
        integration_data = IntegrationCreate(
            name="To Delete",
            integration_type=IntegrationType.BANK_API,
            provider="test_bank"
        )
        
        integration = await integration_service.create_integration(
            db, test_user.id, integration_data
        )
        
        # Delete integration
        success = await integration_service.delete_integration(db, integration.id)
        assert success is True
        
        # Verify soft delete
        deleted_integration = integration_crud.get(db, integration.id)
        assert deleted_integration.is_active is False


class TestWebhookService:
    """Test webhook service."""
    
    @pytest.fixture
    def webhook_service_instance(self):
        return webhook_service
    
    def test_verify_stripe_signature(self, webhook_service_instance):
        """Test Stripe webhook signature verification."""
        webhook_secret = "test_secret"
        timestamp = "1234567890"
        payload = b'{"test": "data"}'
        
        # Create valid signature
        import hmac
        import hashlib
        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        signature = hmac.new(
            webhook_secret.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            "stripe-signature": f"t={timestamp},v1={signature}"
        }
        
        is_valid = webhook_service_instance._verify_stripe_signature(
            webhook_secret, headers, payload
        )
        
        assert is_valid is True
    
    def test_extract_event_type(self, webhook_service_instance):
        """Test extracting event type from webhook payload."""
        # Test Stripe event
        stripe_payload = {"type": "payment_intent.succeeded"}
        event_type = webhook_service_instance._extract_event_type("stripe", stripe_payload)
        assert event_type == "payment_intent.succeeded"
        
        # Test PayPal event
        paypal_payload = {"event_type": "PAYMENT.CAPTURE.COMPLETED"}
        event_type = webhook_service_instance._extract_event_type("paypal", paypal_payload)
        assert event_type == "PAYMENT.CAPTURE.COMPLETED"


class TestIntegrationAPI:
    """Test integration API endpoints."""
    
    def test_get_integrations_unauthorized(self):
        """Test getting integrations without authentication."""
        response = client.get("/api/integrations/")
        assert response.status_code == 401
    
    @patch('app.api.dependencies.get_current_user')
    def test_get_integrations_authorized(self, mock_get_user, test_user):
        """Test getting integrations with authentication."""
        mock_get_user.return_value = test_user
        
        response = client.get("/api/integrations/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    @patch('app.api.dependencies.get_current_user')
    @patch('app.services.integration_service.integration_service.create_integration')
    async def test_create_integration_api(self, mock_create, mock_get_user, test_user):
        """Test creating integration via API."""
        mock_get_user.return_value = test_user
        mock_integration = Mock()
        mock_integration.id = uuid4()
        mock_integration.name = "Test Integration"
        mock_integration.integration_type = IntegrationType.BANK_API
        mock_integration.provider = "test_bank"
        mock_integration.status = IntegrationStatus.INACTIVE
        mock_create.return_value = mock_integration
        
        integration_data = {
            "name": "Test Integration",
            "integration_type": "bank_api",
            "provider": "test_bank"
        }
        
        response = client.post("/api/integrations/", json=integration_data)
        assert response.status_code == 200
    
    @patch('app.api.dependencies.get_current_user')
    def test_oauth_authorization_url(self, mock_get_user, test_user):
        """Test getting OAuth authorization URL."""
        mock_get_user.return_value = test_user
        
        auth_request = {
            "provider": "stripe",
            "redirect_uri": "https://example.com/callback"
        }
        
        response = client.post("/api/integrations/oauth/authorize", json=auth_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data


class TestIntegrationSyncScenarios:
    """Test integration sync scenarios."""
    
    @pytest.mark.asyncio
    @patch('app.services.bank_integration_service.BankIntegrationService.sync_data')
    async def test_bank_integration_sync(self, mock_sync, db: Session, test_user):
        """Test bank integration sync."""
        # Create bank integration
        integration_data = {
            "user_id": test_user.id,
            "name": "Bank Integration",
            "integration_type": IntegrationType.BANK_API,
            "provider": "test_bank",
            "status": IntegrationStatus.ACTIVE,
            "access_token": "test_token"
        }
        
        integration = integration_crud.create(db, obj_in=integration_data)
        
        # Mock successful sync
        from app.schemas.integration import IntegrationSyncResponse
        mock_sync.return_value = IntegrationSyncResponse(
            success=True,
            message="Sync successful",
            synced_records=10
        )
        
        # Perform sync
        result = await integration_service.sync_integration(db, integration.id)
        
        assert result.success is True
        assert result.synced_records == 10
        mock_sync.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_sync_inactive_integration(self, db: Session, test_user):
        """Test syncing inactive integration."""
        integration_data = {
            "user_id": test_user.id,
            "name": "Inactive Integration",
            "integration_type": IntegrationType.BANK_API,
            "provider": "test_bank",
            "status": IntegrationStatus.INACTIVE
        }
        
        integration = integration_crud.create(db, obj_in=integration_data)
        
        result = await integration_service.sync_integration(db, integration.id)
        
        assert result.success is False
        assert "not active" in result.message


class TestIntegrationErrorHandling:
    """Test integration error handling."""
    
    @pytest.mark.asyncio
    async def test_sync_with_network_error(self, db: Session, test_user):
        """Test sync with network error."""
        integration_data = {
            "user_id": test_user.id,
            "name": "Error Integration",
            "integration_type": IntegrationType.BANK_API,
            "provider": "error_bank",
            "status": IntegrationStatus.ACTIVE,
            "access_token": "test_token"
        }
        
        integration = integration_crud.create(db, obj_in=integration_data)
        
        # Mock network error
        with patch('app.services.bank_integration_service.BankIntegrationService.sync_data') as mock_sync:
            mock_sync.side_effect = Exception("Network error")
            
            result = await integration_service.sync_integration(db, integration.id)
            
            assert result.success is False
            assert "Network error" in result.message
    
    @pytest.mark.asyncio
    async def test_oauth_token_refresh_failure(self, db: Session, test_user):
        """Test OAuth token refresh failure."""
        integration_data = {
            "user_id": test_user.id,
            "name": "Token Integration",
            "integration_type": IntegrationType.PAYMENT_PROCESSOR,
            "provider": "stripe",
            "oauth_provider": OAuthProvider.STRIPE,
            "access_token": "expired_token",
            "refresh_token": "refresh_token",
            "token_expires_at": datetime.utcnow() - timedelta(hours=1)
        }
        
        integration = integration_crud.create(db, obj_in=integration_data)
        
        # Mock refresh failure
        with patch('app.services.oauth_service.OAuthService.refresh_token') as mock_refresh:
            mock_refresh.side_effect = Exception("Refresh failed")
            
            result = await integration_service.refresh_expired_tokens(db)
            
            assert result["failed"] >= 1
            assert len(result["errors"]) >= 1


# Fixtures for testing
@pytest.fixture
def test_user(db: Session):
    """Create a test user."""
    from app.models.user import User
    from app.crud.user import user as user_crud
    from app.schemas.user import UserCreate
    
    user_data = UserCreate(
        email="test@example.com",
        password="testpassword",
        first_name="Test",
        last_name="User"
    )
    
    return user_crud.create(db, obj_in=user_data)


@pytest.fixture
def db():
    """Create a test database session."""
    # This would typically use a test database
    # For now, return a mock session
    return Mock(spec=Session)