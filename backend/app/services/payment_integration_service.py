"""
Payment processor integration service for PayPal, Stripe, etc.
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


class PaymentIntegrationService:
    """Service for integrating with payment processor APIs."""
    
    def __init__(self):
        # Payment processor configurations
        self.processor_configs = {
            "paypal": {
                "base_url": "https://api.paypal.com",
                "sandbox_url": "https://api.sandbox.paypal.com",
                "endpoints": {
                    "transactions": "/v1/reporting/transactions",
                    "balances": "/v1/reporting/balances",
                    "disputes": "/v1/customer/disputes",
                    "webhooks": "/v1/notifications/webhooks"
                }
            },
            "stripe": {
                "base_url": "https://api.stripe.com",
                "api_version": "2023-10-16",
                "endpoints": {
                    "charges": "/v1/charges",
                    "payment_intents": "/v1/payment_intents",
                    "transfers": "/v1/transfers",
                    "balance": "/v1/balance",
                    "balance_transactions": "/v1/balance_transactions",
                    "payouts": "/v1/payouts"
                }
            },
            "square": {
                "base_url": "https://connect.squareup.com",
                "sandbox_url": "https://connect.squareupsandbox.com",
                "endpoints": {
                    "payments": "/v2/payments",
                    "orders": "/v2/orders",
                    "settlements": "/v2/settlements",
                    "locations": "/v2/locations"
                }
            }
        }
    
    async def sync_data(
        self, 
        db: Session, 
        integration: Integration
    ) -> IntegrationSyncResponse:
        """Sync data from payment processor."""
        try:
            processor = integration.provider.lower()
            config = self.processor_configs.get(processor)
            
            if not config:
                return IntegrationSyncResponse(
                    success=False,
                    message=f"Unsupported payment processor: {integration.provider}"
                )
            
            if not integration.access_token:
                return IntegrationSyncResponse(
                    success=False,
                    message="No access token available for payment integration"
                )
            
            total_synced = 0
            
            # Sync payment accounts/balances
            accounts_synced = await self._sync_payment_accounts(db, integration, config)
            total_synced += accounts_synced
            
            # Sync transactions
            transactions_synced = await self._sync_payment_transactions(db, integration, config)
            total_synced += transactions_synced
            
            return IntegrationSyncResponse(
                success=True,
                message=f"Successfully synced {accounts_synced} accounts and {transactions_synced} transactions",
                synced_records=total_synced
            )
            
        except Exception as e:
            logger.error(f"Failed to sync payment data for integration {integration.id}: {str(e)}")
            return IntegrationSyncResponse(
                success=False,
                message=f"Payment sync failed: {str(e)}"
            )
    
    async def _sync_payment_accounts(
        self, 
        db: Session, 
        integration: Integration, 
        config: Dict[str, Any]
    ) -> int:
        """Sync payment processor accounts/balances."""
        try:
            headers = self._get_headers(integration, config)
            processor = integration.provider.lower()
            
            if processor == "paypal":
                # PayPal doesn't have traditional accounts, but we can create one for the balance
                account_id = f"paypal_{integration.user_id}"
                existing_account = account_crud.get_by_external_id(
                    db, integration.user_id, account_id
                )
                
                if not existing_account:
                    account_create = AccountCreate(
                        name="PayPal Account",
                        account_type="payment_processor",
                        institution="PayPal",
                        account_number=account_id,
                        balance=0.0,  # Will be updated with actual balance
                        currency="USD",
                        external_id=account_id,
                        integration_id=integration.id
                    )
                    
                    account_crud.create_with_user(
                        db, obj_in=account_create, user_id=integration.user_id
                    )
                    return 1
                    
            elif processor == "stripe":
                # Get Stripe balance
                url = f"{config['base_url']}{config['endpoints']['balance']}"
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, headers=headers, timeout=30.0)
                    response.raise_for_status()
                    
                    balance_data = response.json()
                    
                    # Stripe can have multiple balances (available, pending, etc.)
                    for balance_type, balances in balance_data.items():
                        if isinstance(balances, list):
                            for balance in balances:
                                currency = balance.get("currency", "usd").upper()
                                amount = balance.get("amount", 0) / 100  # Stripe amounts are in cents
                                
                                account_id = f"stripe_{balance_type}_{currency}"
                                existing_account = account_crud.get_by_external_id(
                                    db, integration.user_id, account_id
                                )
                                
                                if not existing_account:
                                    account_create = AccountCreate(
                                        name=f"Stripe {balance_type.title()} ({currency})",
                                        account_type="payment_processor",
                                        institution="Stripe",
                                        account_number=account_id,
                                        balance=amount,
                                        currency=currency,
                                        external_id=account_id,
                                        integration_id=integration.id
                                    )
                                    
                                    account_crud.create_with_user(
                                        db, obj_in=account_create, user_id=integration.user_id
                                    )
                                else:
                                    # Update balance
                                    account_crud.update(
                                        db, 
                                        db_obj=existing_account, 
                                        obj_in={"balance": amount}
                                    )
                    
                    return len(balance_data.get("available", [])) + len(balance_data.get("pending", []))
            
            return 0
            
        except Exception as e:
            logger.error(f"Error syncing payment accounts: {str(e)}")
            raise
    
    async def _sync_payment_transactions(
        self, 
        db: Session, 
        integration: Integration, 
        config: Dict[str, Any]
    ) -> int:
        """Sync transactions from payment processor."""
        try:
            headers = self._get_headers(integration, config)
            processor = integration.provider.lower()
            
            # Get transactions from the last sync or last 30 days
            from_date = integration.last_sync_at or (datetime.utcnow() - timedelta(days=30))
            to_date = datetime.utcnow()
            
            synced_count = 0
            
            if processor == "paypal":
                url = f"{config['base_url']}{config['endpoints']['transactions']}"
                params = {
                    "start_date": from_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "end_date": to_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "fields": "all"
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, headers=headers, params=params, timeout=30.0)
                    response.raise_for_status()
                    
                    data = response.json()
                    transactions = data.get("transaction_details", [])
                    
                    # Get PayPal account
                    paypal_account = account_crud.get_by_external_id(
                        db, integration.user_id, f"paypal_{integration.user_id}"
                    )
                    
                    if paypal_account:
                        for transaction_data in transactions:
                            transaction_id = transaction_data.get("transaction_info", {}).get("transaction_id")
                            if not transaction_id:
                                continue
                            
                            # Check if transaction already exists
                            existing_transaction = transaction_crud.get_by_external_id(
                                db, transaction_id
                            )
                            
                            if not existing_transaction:
                                # Parse PayPal transaction
                                transaction_info = transaction_data.get("transaction_info", {})
                                amount_info = transaction_data.get("transaction_amount", {})
                                
                                amount = float(amount_info.get("value", 0))
                                transaction_status = transaction_info.get("transaction_status")
                                
                                # Skip pending or failed transactions
                                if transaction_status not in ["S", "P"]:  # S=Success, P=Pending
                                    continue
                                
                                transaction_date = datetime.fromisoformat(
                                    transaction_info.get("transaction_initiation_date", datetime.utcnow().isoformat())
                                ).date()
                                
                                transaction_create = TransactionCreate(
                                    account_id=paypal_account.id,
                                    date=transaction_date,
                                    description=transaction_info.get("transaction_subject", "PayPal Transaction"),
                                    amount=amount,
                                    transaction_type="credit" if amount > 0 else "debit",
                                    external_id=transaction_id,
                                    raw_data=transaction_data
                                )
                                
                                transaction_crud.create(db, obj_in=transaction_create)
                                synced_count += 1
                                
            elif processor == "stripe":
                # Sync balance transactions (most comprehensive view)
                url = f"{config['base_url']}{config['endpoints']['balance_transactions']}"
                params = {
                    "created[gte]": int(from_date.timestamp()),
                    "created[lte]": int(to_date.timestamp()),
                    "limit": 100
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, headers=headers, params=params, timeout=30.0)
                    response.raise_for_status()
                    
                    data = response.json()
                    transactions = data.get("data", [])
                    
                    for transaction_data in transactions:
                        transaction_id = transaction_data.get("id")
                        if not transaction_id:
                            continue
                        
                        # Check if transaction already exists
                        existing_transaction = transaction_crud.get_by_external_id(
                            db, transaction_id
                        )
                        
                        if not existing_transaction:
                            # Find appropriate Stripe account
                            currency = transaction_data.get("currency", "usd").upper()
                            account_id = f"stripe_available_{currency}"
                            stripe_account = account_crud.get_by_external_id(
                                db, integration.user_id, account_id
                            )
                            
                            if stripe_account:
                                amount = transaction_data.get("amount", 0) / 100  # Convert from cents
                                net_amount = transaction_data.get("net", 0) / 100
                                
                                transaction_date = datetime.fromtimestamp(
                                    transaction_data.get("created", datetime.utcnow().timestamp())
                                ).date()
                                
                                # Use net amount for the actual impact on balance
                                transaction_create = TransactionCreate(
                                    account_id=stripe_account.id,
                                    date=transaction_date,
                                    description=transaction_data.get("description", "Stripe Transaction"),
                                    amount=net_amount,
                                    transaction_type="credit" if net_amount > 0 else "debit",
                                    external_id=transaction_id,
                                    raw_data=transaction_data
                                )
                                
                                transaction_crud.create(db, obj_in=transaction_create)
                                synced_count += 1
            
            return synced_count
            
        except Exception as e:
            logger.error(f"Error syncing payment transactions: {str(e)}")
            raise
    
    async def test_connection(self, integration: Integration) -> Dict[str, Any]:
        """Test connection to payment processor API."""
        try:
            processor = integration.provider.lower()
            config = self.processor_configs.get(processor)
            
            if not config:
                return {
                    "success": False,
                    "message": f"Unsupported payment processor: {integration.provider}"
                }
            
            if not integration.access_token:
                return {
                    "success": False,
                    "message": "No access token available"
                }
            
            headers = self._get_headers(integration, config)
            
            # Test with appropriate endpoint
            if processor == "paypal":
                # Test with a simple balance request
                url = f"{config['base_url']}/v1/reporting/balances"
            elif processor == "stripe":
                # Test with balance endpoint
                url = f"{config['base_url']}{config['endpoints']['balance']}"
            else:
                return {"success": False, "message": "Unknown processor"}
            
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
    
    def _get_headers(self, integration: Integration, config: Dict[str, Any]) -> Dict[str, str]:
        """Get headers for API requests."""
        processor = integration.provider.lower()
        
        if processor == "paypal":
            return {
                "Authorization": f"Bearer {integration.access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
        elif processor == "stripe":
            return {
                "Authorization": f"Bearer {integration.access_token}",
                "Stripe-Version": config.get("api_version", "2023-10-16")
            }
        else:
            return {
                "Authorization": f"Bearer {integration.access_token}",
                "Accept": "application/json"
            }