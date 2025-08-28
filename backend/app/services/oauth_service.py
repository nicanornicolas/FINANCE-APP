"""
OAuth service for handling external service authentication.
"""
import secrets
import logging
from typing import Dict, Optional, List
from urllib.parse import urlencode, parse_qs, urlparse
import httpx

from ..models.integration import OAuthProvider
from ..schemas.integration import (
    OAuthAuthorizationResponse, OAuthTokenResponse
)

logger = logging.getLogger(__name__)


class OAuthService:
    """Service for handling OAuth flows with external services."""
    
    def __init__(self):
        # OAuth provider configurations
        self.provider_configs = {
            OAuthProvider.OPEN_BANKING: {
                "authorization_url": "https://auth.openbanking.org.uk/oauth2/authorize",
                "token_url": "https://auth.openbanking.org.uk/oauth2/token",
                "revoke_url": "https://auth.openbanking.org.uk/oauth2/revoke",
                "scopes": ["accounts", "transactions", "balances"],
                "client_id": "your_open_banking_client_id",  # From environment
                "client_secret": "your_open_banking_client_secret"  # From environment
            },
            OAuthProvider.QUICKBOOKS: {
                "authorization_url": "https://appcenter.intuit.com/connect/oauth2",
                "token_url": "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer",
                "revoke_url": "https://developer.api.intuit.com/v2/oauth2/tokens/revoke",
                "scopes": ["com.intuit.quickbooks.accounting"],
                "client_id": "your_quickbooks_client_id",
                "client_secret": "your_quickbooks_client_secret"
            },
            OAuthProvider.XERO: {
                "authorization_url": "https://login.xero.com/identity/connect/authorize",
                "token_url": "https://identity.xero.com/connect/token",
                "revoke_url": "https://identity.xero.com/connect/revocation",
                "scopes": ["accounting.transactions", "accounting.contacts"],
                "client_id": "your_xero_client_id",
                "client_secret": "your_xero_client_secret"
            },
            OAuthProvider.PAYPAL: {
                "authorization_url": "https://www.paypal.com/signin/authorize",
                "token_url": "https://api.paypal.com/v1/oauth2/token",
                "revoke_url": "https://api.paypal.com/v1/oauth2/token/revoke",
                "scopes": ["https://uri.paypal.com/services/payments/payment"],
                "client_id": "your_paypal_client_id",
                "client_secret": "your_paypal_client_secret"
            },
            OAuthProvider.STRIPE: {
                "authorization_url": "https://connect.stripe.com/oauth/authorize",
                "token_url": "https://connect.stripe.com/oauth/token",
                "revoke_url": "https://connect.stripe.com/oauth/deauthorize",
                "scopes": ["read_write"],
                "client_id": "your_stripe_client_id",
                "client_secret": "your_stripe_client_secret"
            },
            OAuthProvider.KRA_ITAX: {
                "authorization_url": "https://itax.kra.go.ke/oauth2/authorize",
                "token_url": "https://itax.kra.go.ke/oauth2/token",
                "revoke_url": "https://itax.kra.go.ke/oauth2/revoke",
                "scopes": ["tax_filing", "taxpayer_info"],
                "client_id": "your_kra_client_id",
                "client_secret": "your_kra_client_secret"
            }
        }
    
    async def get_authorization_url(
        self,
        provider: OAuthProvider,
        redirect_uri: str,
        scopes: Optional[List[str]] = None,
        state: Optional[str] = None
    ) -> OAuthAuthorizationResponse:
        """Generate OAuth authorization URL."""
        try:
            config = self.provider_configs.get(provider)
            if not config:
                raise ValueError(f"Unsupported OAuth provider: {provider}")
            
            # Generate state if not provided
            if not state:
                state = secrets.token_urlsafe(32)
            
            # Use default scopes if not provided
            if not scopes:
                scopes = config["scopes"]
            
            # Build authorization URL
            params = {
                "response_type": "code",
                "client_id": config["client_id"],
                "redirect_uri": redirect_uri,
                "scope": " ".join(scopes),
                "state": state
            }
            
            # Add provider-specific parameters
            if provider == OAuthProvider.QUICKBOOKS:
                params["access_type"] = "offline"
            elif provider == OAuthProvider.XERO:
                params["code_challenge_method"] = "S256"
                # In a real implementation, you'd generate and store the code_challenge
            
            authorization_url = f"{config['authorization_url']}?{urlencode(params)}"
            
            return OAuthAuthorizationResponse(
                authorization_url=authorization_url,
                state=state
            )
            
        except Exception as e:
            logger.error(f"Failed to generate authorization URL for {provider}: {str(e)}")
            raise
    
    async def exchange_code_for_tokens(
        self,
        provider: OAuthProvider,
        authorization_code: str,
        redirect_uri: str,
        state: str
    ) -> OAuthTokenResponse:
        """Exchange authorization code for access tokens."""
        try:
            config = self.provider_configs.get(provider)
            if not config:
                raise ValueError(f"Unsupported OAuth provider: {provider}")
            
            # Prepare token request
            token_data = {
                "grant_type": "authorization_code",
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "code": authorization_code,
                "redirect_uri": redirect_uri
            }
            
            # Add provider-specific parameters
            if provider == OAuthProvider.XERO:
                # In a real implementation, you'd include the code_verifier
                token_data["code_verifier"] = "your_code_verifier"
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            }
            
            # Make token request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    config["token_url"],
                    data=token_data,
                    headers=headers,
                    timeout=30.0
                )
                response.raise_for_status()
                token_data = response.json()
            
            # Parse response based on provider
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in")
            token_type = token_data.get("token_type", "Bearer")
            
            if not access_token:
                raise ValueError("No access token received from provider")
            
            return OAuthTokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=expires_in,
                token_type=token_type
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during token exchange for {provider}: {e.response.status_code} - {e.response.text}")
            raise ValueError(f"Token exchange failed: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Failed to exchange code for tokens for {provider}: {str(e)}")
            raise
    
    async def refresh_token(
        self,
        provider: OAuthProvider,
        refresh_token: str
    ) -> OAuthTokenResponse:
        """Refresh an expired access token."""
        try:
            config = self.provider_configs.get(provider)
            if not config:
                raise ValueError(f"Unsupported OAuth provider: {provider}")
            
            # Prepare refresh request
            refresh_data = {
                "grant_type": "refresh_token",
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "refresh_token": refresh_token
            }
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            }
            
            # Make refresh request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    config["token_url"],
                    data=refresh_data,
                    headers=headers,
                    timeout=30.0
                )
                response.raise_for_status()
                token_data = response.json()
            
            # Parse response
            access_token = token_data.get("access_token")
            new_refresh_token = token_data.get("refresh_token", refresh_token)
            expires_in = token_data.get("expires_in")
            token_type = token_data.get("token_type", "Bearer")
            
            if not access_token:
                raise ValueError("No access token received from refresh")
            
            return OAuthTokenResponse(
                access_token=access_token,
                refresh_token=new_refresh_token,
                expires_in=expires_in,
                token_type=token_type
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during token refresh for {provider}: {e.response.status_code} - {e.response.text}")
            raise ValueError(f"Token refresh failed: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Failed to refresh token for {provider}: {str(e)}")
            raise
    
    async def revoke_token(
        self,
        provider: OAuthProvider,
        token: str,
        token_type: str = "access_token"
    ) -> bool:
        """Revoke an access or refresh token."""
        try:
            config = self.provider_configs.get(provider)
            if not config or not config.get("revoke_url"):
                logger.warning(f"No revoke URL configured for provider {provider}")
                return True  # Assume success if no revoke endpoint
            
            # Prepare revoke request
            revoke_data = {
                "token": token,
                "token_type_hint": token_type,
                "client_id": config["client_id"],
                "client_secret": config["client_secret"]
            }
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            }
            
            # Make revoke request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    config["revoke_url"],
                    data=revoke_data,
                    headers=headers,
                    timeout=30.0
                )
                
                # Some providers return 200, others return 204
                if response.status_code in [200, 204]:
                    return True
                else:
                    logger.warning(f"Unexpected status code during token revocation: {response.status_code}")
                    return False
            
        except Exception as e:
            logger.error(f"Failed to revoke token for {provider}: {str(e)}")
            return False
    
    async def validate_token(
        self,
        provider: OAuthProvider,
        access_token: str
    ) -> Dict[str, any]:
        """Validate an access token and get user info."""
        try:
            # This would vary by provider - each has different validation endpoints
            validation_urls = {
                OAuthProvider.OPEN_BANKING: "https://api.openbanking.org.uk/user/info",
                OAuthProvider.QUICKBOOKS: "https://sandbox-quickbooks.api.intuit.com/v3/company/companyinfo",
                OAuthProvider.XERO: "https://api.xero.com/connections",
                OAuthProvider.PAYPAL: "https://api.paypal.com/v1/identity/oauth2/userinfo",
                OAuthProvider.STRIPE: "https://api.stripe.com/v1/account",
                OAuthProvider.KRA_ITAX: "https://itax.kra.go.ke/api/v1/taxpayer/info"
            }
            
            validation_url = validation_urls.get(provider)
            if not validation_url:
                return {"valid": False, "error": "No validation endpoint configured"}
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    validation_url,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    user_info = response.json()
                    return {
                        "valid": True,
                        "user_info": user_info
                    }
                else:
                    return {
                        "valid": False,
                        "error": f"Token validation failed: {response.status_code}"
                    }
            
        except Exception as e:
            logger.error(f"Failed to validate token for {provider}: {str(e)}")
            return {"valid": False, "error": str(e)}