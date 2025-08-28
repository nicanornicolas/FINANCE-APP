"""
Bank integration service for Open Banking API connections.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import httpx

from ..models.integration import Integration
from ..schemas.integration import IntegrationSyncResponse
from ..crud.transaction import transaction as transaction_crud
from ..crud.account import account as account_crud
from ..schemas.transaction import TransactionCreate
from ..schemas.account import AccountCreate

logger = logging.getLogger(__name__)


class BankIntegrationService:
    """Service for integrating with bank APIs using Open Banking standards."""
    
    def __init__(self):
        # Open Banking API endpoints (these would be configured per bank)
        self.api_endpoints = {
            "accounts": "/open-banking/v3.1/aisp/accounts",
            "transactions": "/open-banking/v3.1/aisp/accounts/{account_id}/transactions",
            "balances": "/open-banking/v3.1/aisp/accounts/{account_id}/balances",
            "direct-debits": "/open-banking/v3.1/aisp/accounts/{account_id}/direct-debits",
            "standing-orders": "/open-banking/v3.1/aisp/accounts/{account_id}/standing-orders"
        }
        
        # Bank-specific configurations
        self.bank_configs = {
            "hsbc": {
                "base_url": "https://api.hsbc.com",
                "client_id": "your_hsbc_client_id",
                "requires_customer_consent": True
            },
            "barclays": {
                "base_url": "https://api.barclays.com",
                "client_id": "your_barclays_client_id",
                "requires_customer_consent": True
            },
            "lloyds": {
                "base_url": "https://api.lloydsbank.com",
                "client_id": "your_lloyds_client_id",
                "requires_customer_consent": True
            },
            "santander": {
                "base_url": "https://api.santander.co.uk",
                "client_id": "your_santander_client_id",
                "requires_customer_consent": True
            }
        }
    
    async def sync_data(
        self, 
        db: Session, 
        integration: Integration
    ) -> IntegrationSyncResponse:
        """Sync data from bank API."""
        try:
            bank_provider = integration.provider.lower()
            config = self.bank_configs.get(bank_provider)
            
            if not config:
                return IntegrationSyncResponse(
                    success=False,
                    message=f"Unsupported bank provider: {integration.provider}"
                )
            
            if not integration.access_token:
                return IntegrationSyncResponse(
                    success=False,
                    message="No access token available for bank integration"
                )
            
            # Sync accounts first
            accounts_synced = await self._sync_accounts(db, integration, config)
            
            # Then sync transactions for each account
            transactions_synced = 0
            for account_id in accounts_synced:
                account_transactions = await self._sync_transactions(
                    db, integration, config, account_id
                )
                transactions_synced += account_transactions
            
            return IntegrationSyncResponse(
                success=True,
                message=f"Successfully synced {len(accounts_synced)} accounts and {transactions_synced} transactions",
                synced_records=len(accounts_synced) + transactions_synced
            )
            
        except Exception as e:
            logger.error(f"Failed to sync bank data for integration {integration.id}: {str(e)}")
            return IntegrationSyncResponse(
                success=False,
                message=f"Bank sync failed: {str(e)}"
            )
    
    async def _sync_accounts(
        self, 
        db: Session, 
        integration: Integration, 
        config: Dict[str, Any]
    ) -> List[str]:
        """Sync bank accounts."""
        try:
            headers = {
                "Authorization": f"Bearer {integration.access_token}",
                "Accept": "application/json",
                "x-fapi-financial-id": config["client_id"]
            }
            
            url = f"{config['base_url']}{self.api_endpoints['accounts']}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                
                accounts_data = response.json()
                accounts = accounts_data.get("Data", {}).get("Account", [])
                
                synced_account_ids = []
                
                for account_data in accounts:
                    account_id = account_data.get("AccountId")
                    if not account_id:
                        continue
                    
                    # Check if account already exists
                    existing_account = account_crud.get_by_external_id(
                        db, integration.user_id, account_id
                    )
                    
                    if not existing_account:
                        # Create new account
                        account_create = AccountCreate(
                            name=account_data.get("Nickname", account_data.get("AccountType", "Unknown")),
                            account_type=self._map_account_type(account_data.get("AccountType")),
                            institution=integration.provider,
                            account_number=account_data.get("AccountId"),  # This would be encrypted
                            balance=0.0,  # Will be updated when syncing balances
                            currency=account_data.get("Currency", "GBP"),
                            external_id=account_id,
                            integration_id=integration.id
                        )
                        
                        account_crud.create_with_user(
                            db, obj_in=account_create, user_id=integration.user_id
                        )
                    
                    synced_account_ids.append(account_id)
                
                return synced_account_ids
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error syncing accounts: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error syncing accounts: {str(e)}")
            raise
    
    async def _sync_transactions(
        self, 
        db: Session, 
        integration: Integration, 
        config: Dict[str, Any],
        account_id: str
    ) -> int:
        """Sync transactions for a specific account."""
        try:
            headers = {
                "Authorization": f"Bearer {integration.access_token}",
                "Accept": "application/json",
                "x-fapi-financial-id": config["client_id"]
            }
            
            # Get transactions from the last sync or last 30 days
            from_date = integration.last_sync_at or (datetime.utcnow() - timedelta(days=30))
            to_date = datetime.utcnow()
            
            url = f"{config['base_url']}{self.api_endpoints['transactions'].format(account_id=account_id)}"
            params = {
                "fromBookingDateTime": from_date.isoformat(),
                "toBookingDateTime": to_date.isoformat()
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, params=params, timeout=30.0)
                response.raise_for_status()
                
                transactions_data = response.json()
                transactions = transactions_data.get("Data", {}).get("Transaction", [])
                
                synced_count = 0
                
                # Get the internal account ID
                internal_account = account_crud.get_by_external_id(
                    db, integration.user_id, account_id
                )
                if not internal_account:
                    logger.warning(f"Internal account not found for external ID: {account_id}")
                    return 0
                
                for transaction_data in transactions:
                    transaction_id = transaction_data.get("TransactionId")
                    if not transaction_id:
                        continue
                    
                    # Check if transaction already exists
                    existing_transaction = transaction_crud.get_by_external_id(
                        db, transaction_id
                    )
                    
                    if not existing_transaction:
                        # Parse transaction data
                        amount_data = transaction_data.get("Amount", {})
                        amount = float(amount_data.get("Amount", 0))
                        
                        # Determine transaction type based on credit/debit indicator
                        credit_debit = transaction_data.get("CreditDebitIndicator", "Debit")
                        if credit_debit == "Debit":
                            amount = -abs(amount)  # Ensure debits are negative
                        
                        # Parse date
                        booking_date = transaction_data.get("BookingDateTime")
                        if booking_date:
                            transaction_date = datetime.fromisoformat(
                                booking_date.replace("Z", "+00:00")
                            ).date()
                        else:
                            transaction_date = datetime.utcnow().date()
                        
                        # Create transaction
                        transaction_create = TransactionCreate(
                            account_id=internal_account.id,
                            date=transaction_date,
                            description=self._clean_description(
                                transaction_data.get("TransactionInformation", "Unknown Transaction")
                            ),
                            amount=amount,
                            transaction_type="debit" if amount < 0 else "credit",
                            external_id=transaction_id,
                            raw_data=transaction_data
                        )
                        
                        transaction_crud.create(db, obj_in=transaction_create)
                        synced_count += 1
                
                return synced_count
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error syncing transactions: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error syncing transactions: {str(e)}")
            raise
    
    async def test_connection(self, integration: Integration) -> Dict[str, Any]:
        """Test connection to bank API."""
        try:
            bank_provider = integration.provider.lower()
            config = self.bank_configs.get(bank_provider)
            
            if not config:
                return {
                    "success": False,
                    "message": f"Unsupported bank provider: {integration.provider}"
                }
            
            if not integration.access_token:
                return {
                    "success": False,
                    "message": "No access token available"
                }
            
            headers = {
                "Authorization": f"Bearer {integration.access_token}",
                "Accept": "application/json",
                "x-fapi-financial-id": config["client_id"]
            }
            
            # Test with a simple accounts request
            url = f"{config['base_url']}{self.api_endpoints['accounts']}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=10.0)
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": "Connection successful",
                        "details": {
                            "status_code": response.status_code,
                            "response_time": response.elapsed.total_seconds()
                        }
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Connection failed with status {response.status_code}",
                        "details": {
                            "status_code": response.status_code,
                            "error": response.text
                        }
                    }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection test failed: {str(e)}"
            }
    
    def _map_account_type(self, open_banking_type: str) -> str:
        """Map Open Banking account type to internal account type."""
        type_mapping = {
            "Personal": "checking",
            "Business": "business",
            "Savings": "savings",
            "CurrentAccount": "checking",
            "SavingsAccount": "savings",
            "CreditCard": "credit_card",
            "Loan": "loan",
            "Mortgage": "mortgage"
        }
        return type_mapping.get(open_banking_type, "other")
    
    def _clean_description(self, description: str) -> str:
        """Clean and normalize transaction description."""
        if not description:
            return "Unknown Transaction"
        
        # Remove extra whitespace and normalize
        cleaned = " ".join(description.split())
        
        # Truncate if too long
        if len(cleaned) > 255:
            cleaned = cleaned[:252] + "..."
        
        return cleaned