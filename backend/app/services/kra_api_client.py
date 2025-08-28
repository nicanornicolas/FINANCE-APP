"""
KRA API Client for integrating with Kenya Revenue Authority iTax system
"""
import httpx
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from app.core.config import settings
from app.schemas.kra_tax import (
    KRAPINValidationResponse, 
    KRAAPIResponse,
    KRAFilingSubmissionResponse
)

logger = logging.getLogger(__name__)


class KRAAPIError(Exception):
    """Custom exception for KRA API errors"""
    def __init__(self, message: str, error_code: Optional[str] = None, status_code: Optional[int] = None):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)


class KRAAPIClient:
    """Client for interacting with KRA iTax APIs"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'KRA_API_BASE_URL', 'https://itax.kra.go.ke/api/v1')
        self.client_id = getattr(settings, 'KRA_CLIENT_ID', '')
        self.client_secret = getattr(settings, 'KRA_CLIENT_SECRET', '')
        self.access_token = None
        self.token_expires_at = None
        
        # HTTP client with timeout and retry configuration
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def _get_access_token(self) -> str:
        """Get or refresh OAuth access token"""
        if self.access_token and self.token_expires_at and datetime.now() < self.token_expires_at:
            return self.access_token
        
        try:
            response = await self.client.post(
                f"{self.base_url}/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": "tax_filing pin_validation payment_processing"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)  # 5 min buffer
            
            logger.info("Successfully obtained KRA API access token")
            return self.access_token
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get KRA API token: {e.response.status_code} - {e.response.text}")
            raise KRAAPIError(f"Authentication failed: {e.response.text}", status_code=e.response.status_code)
        except Exception as e:
            logger.error(f"Unexpected error getting KRA API token: {str(e)}")
            raise KRAAPIError(f"Authentication error: {str(e)}")
    
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to KRA API"""
        token = await self._get_access_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            if method.upper() == "GET":
                response = await self.client.get(url, headers=headers, params=data)
            elif method.upper() == "POST":
                response = await self.client.post(url, headers=headers, json=data)
            elif method.upper() == "PUT":
                response = await self.client.put(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = await self.client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            error_msg = f"KRA API request failed: {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_msg += f" - {error_data.get('message', e.response.text)}"
                error_code = error_data.get('error_code')
            except:
                error_msg += f" - {e.response.text}"
                error_code = None
            
            logger.error(error_msg)
            raise KRAAPIError(error_msg, error_code=error_code, status_code=e.response.status_code)
        
        except Exception as e:
            logger.error(f"Unexpected error in KRA API request: {str(e)}")
            raise KRAAPIError(f"Request error: {str(e)}")
    
    async def validate_pin(self, kra_pin: str) -> KRAPINValidationResponse:
        """Validate KRA PIN and get taxpayer information"""
        try:
            response_data = await self._make_request(
                "POST", 
                "/taxpayer/validate-pin",
                {"kra_pin": kra_pin}
            )
            
            return KRAPINValidationResponse(
                kra_pin=kra_pin,
                is_valid=response_data.get("is_valid", False),
                taxpayer_name=response_data.get("taxpayer_name"),
                taxpayer_type=response_data.get("taxpayer_type"),
                tax_office=response_data.get("tax_office"),
                registration_date=response_data.get("registration_date"),
                status=response_data.get("status", "unknown")
            )
            
        except KRAAPIError:
            raise
        except Exception as e:
            logger.error(f"Error validating KRA PIN {kra_pin}: {str(e)}")
            raise KRAAPIError(f"PIN validation error: {str(e)}")
    
    async def get_taxpayer_info(self, kra_pin: str) -> Dict[str, Any]:
        """Get detailed taxpayer information"""
        try:
            return await self._make_request(
                "GET",
                f"/taxpayer/{kra_pin}/info"
            )
        except KRAAPIError:
            raise
        except Exception as e:
            logger.error(f"Error getting taxpayer info for {kra_pin}: {str(e)}")
            raise KRAAPIError(f"Taxpayer info error: {str(e)}")
    
    async def submit_tax_return(self, filing_data: Dict[str, Any]) -> KRAFilingSubmissionResponse:
        """Submit tax return to KRA iTax system"""
        try:
            response_data = await self._make_request(
                "POST",
                "/tax-returns/submit",
                filing_data
            )
            
            return KRAFilingSubmissionResponse(
                filing_id=response_data["filing_id"],
                kra_reference=response_data["kra_reference"],
                submission_date=datetime.fromisoformat(response_data["submission_date"]),
                status=response_data["status"],
                receipt_url=response_data.get("receipt_url"),
                next_steps=response_data.get("next_steps", [])
            )
            
        except KRAAPIError:
            raise
        except Exception as e:
            logger.error(f"Error submitting tax return: {str(e)}")
            raise KRAAPIError(f"Tax return submission error: {str(e)}")
    
    async def get_filing_status(self, kra_reference: str) -> Dict[str, Any]:
        """Get status of submitted tax filing"""
        try:
            return await self._make_request(
                "GET",
                f"/tax-returns/{kra_reference}/status"
            )
        except KRAAPIError:
            raise
        except Exception as e:
            logger.error(f"Error getting filing status for {kra_reference}: {str(e)}")
            raise KRAAPIError(f"Filing status error: {str(e)}")
    
    async def make_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process tax payment through KRA payment gateway"""
        try:
            return await self._make_request(
                "POST",
                "/payments/process",
                payment_data
            )
        except KRAAPIError:
            raise
        except Exception as e:
            logger.error(f"Error processing payment: {str(e)}")
            raise KRAAPIError(f"Payment processing error: {str(e)}")
    
    async def get_payment_status(self, payment_reference: str) -> Dict[str, Any]:
        """Get payment status"""
        try:
            return await self._make_request(
                "GET",
                f"/payments/{payment_reference}/status"
            )
        except KRAAPIError:
            raise
        except Exception as e:
            logger.error(f"Error getting payment status for {payment_reference}: {str(e)}")
            raise KRAAPIError(f"Payment status error: {str(e)}")
    
    async def get_tax_rates(self, tax_year: int) -> Dict[str, Any]:
        """Get current tax rates and brackets for given year"""
        try:
            return await self._make_request(
                "GET",
                f"/tax-rates/{tax_year}"
            )
        except KRAAPIError:
            raise
        except Exception as e:
            logger.error(f"Error getting tax rates for {tax_year}: {str(e)}")
            raise KRAAPIError(f"Tax rates error: {str(e)}")


# Mock KRA API Client for development/testing
class MockKRAAPIClient(KRAAPIClient):
    """Mock implementation for development and testing"""
    
    async def validate_pin(self, kra_pin: str) -> KRAPINValidationResponse:
        """Mock PIN validation"""
        # Simulate validation logic
        is_valid = kra_pin.startswith('P') and len(kra_pin) == 11
        
        return KRAPINValidationResponse(
            kra_pin=kra_pin,
            is_valid=is_valid,
            taxpayer_name="John Doe" if is_valid else None,
            taxpayer_type="individual" if is_valid else None,
            tax_office="Nairobi South" if is_valid else None,
            registration_date="2020-01-15" if is_valid else None,
            status="active" if is_valid else "invalid"
        )
    
    async def submit_tax_return(self, filing_data: Dict[str, Any]) -> KRAFilingSubmissionResponse:
        """Mock tax return submission"""
        import uuid
        
        return KRAFilingSubmissionResponse(
            filing_id=uuid.uuid4(),
            kra_reference=f"KRA{datetime.now().strftime('%Y%m%d%H%M%S')}",
            submission_date=datetime.now(),
            status="submitted",
            receipt_url="https://itax.kra.go.ke/receipts/mock-receipt.pdf",
            next_steps=["Wait for processing", "Check status in 24 hours"]
        )
    
    async def get_tax_rates(self, tax_year: int) -> Dict[str, Any]:
        """Mock tax rates"""
        return {
            "tax_year": tax_year,
            "individual_rates": [
                {"min_income": 0, "max_income": 288000, "rate": 0.10},
                {"min_income": 288001, "max_income": 388000, "rate": 0.25},
                {"min_income": 388001, "max_income": 6000000, "rate": 0.30},
                {"min_income": 6000001, "max_income": 9600000, "rate": 0.325},
                {"min_income": 9600001, "max_income": None, "rate": 0.35}
            ],
            "reliefs": {
                "personal_relief": 28800,
                "insurance_relief_limit": 60000,
                "mortgage_interest_limit": 300000
            }
        }