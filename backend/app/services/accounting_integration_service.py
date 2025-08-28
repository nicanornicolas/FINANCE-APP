"""
Accounting software integration service for QuickBooks, Xero, etc.
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


class AccountingIntegrationService:
    """Service for integrating with accounting software APIs."""
    
    def __init__(self):
        # Accounting software configurations
        self.software_configs = {
            "quickbooks": {
                "base_url": "https://sandbox-quickbooks.api.intuit.com",
                "api_version": "v3",
                "endpoints": {
                    "company_info": "/v3/company/{company_id}/companyinfo/{company_id}",
                    "accounts": "/v3/company/{company_id}/accounts",
                    "items": "/v3/company/{company_id}/items",
                    "customers": "/v3/company/{company_id}/customers",
                    "vendors": "/v3/company/{company_id}/vendors",
                    "transactions": "/v3/company/{company_id}/reports/TransactionList",
                    "profit_loss": "/v3/company/{company_id}/reports/ProfitAndLoss"
                }
            },
            "xero": {
                "base_url": "https://api.xero.com",
                "api_version": "2.0",
                "endpoints": {
                    "organisation": "/api.xro/2.0/Organisation",
                    "accounts": "/api.xro/2.0/Accounts",
                    "contacts": "/api.xro/2.0/Contacts",
                    "invoices": "/api.xro/2.0/Invoices",
                    "bank_transactions": "/api.xro/2.0/BankTransactions",
                    "reports": "/api.xro/2.0/Reports"
                }
            }
        }
    
    async def sync_data(
        self, 
        db: Session, 
        integration: Integration
    ) -> IntegrationSyncResponse:
        """Sync data from accounting software."""
        try:
            software = integration.provider.lower()
            config = self.software_configs.get(software)
            
            if not config:
                return IntegrationSyncResponse(
                    success=False,
                    message=f"Unsupported accounting software: {integration.provider}"
                )
            
            if not integration.access_token:
                return IntegrationSyncResponse(
                    success=False,
                    message="No access token available for accounting integration"
                )
            
            # Get company/organisation ID from metadata
            company_id = integration.metadata.get("company_id") if integration.metadata else None
            if not company_id:
                # Try to get company info first
                company_id = await self._get_company_id(integration, config)
                if not company_id:
                    return IntegrationSyncResponse(
                        success=False,
                        message="Could not determine company/organisation ID"
                    )
            
            total_synced = 0
            
            # Sync chart of accounts
            accounts_synced = await self._sync_chart_of_accounts(db, integration, config, company_id)
            total_synced += accounts_synced
            
            # Sync transactions/bank transactions
            transactions_synced = await self._sync_transactions(db, integration, config, company_id)
            total_synced += transactions_synced
            
            return IntegrationSyncResponse(
                success=True,
                message=f"Successfully synced {accounts_synced} accounts and {transactions_synced} transactions",
                synced_records=total_synced
            )
            
        except Exception as e:
            logger.error(f"Failed to sync accounting data for integration {integration.id}: {str(e)}")
            return IntegrationSyncResponse(
                success=False,
                message=f"Accounting sync failed: {str(e)}"
            )
    
    async def _get_company_id(
        self, 
        integration: Integration, 
        config: Dict[str, Any]
    ) -> Optional[str]:
        """Get company/organisation ID from accounting software."""
        try:
            headers = self._get_headers(integration, config)
            
            if integration.provider.lower() == "quickbooks":
                # For QuickBooks, company ID is usually in the token response or metadata
                # This is a simplified approach - in reality, you'd get this during OAuth
                return integration.metadata.get("realmId") if integration.metadata else None
                
            elif integration.provider.lower() == "xero":
                url = f"{config['base_url']}{config['endpoints']['organisation']}"
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, headers=headers, timeout=30.0)
                    response.raise_for_status()
                    
                    data = response.json()
                    organisations = data.get("Organisations", [])
                    if organisations:
                        return organisations[0].get("OrganisationID")
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get company ID: {str(e)}")
            return None
    
    async def _sync_chart_of_accounts(
        self, 
        db: Session, 
        integration: Integration, 
        config: Dict[str, Any],
        company_id: str
    ) -> int:
        """Sync chart of accounts from accounting software."""
        try:
            headers = self._get_headers(integration, config)
            
            if integration.provider.lower() == "quickbooks":
                url = f"{config['base_url']}{config['endpoints']['accounts'].format(company_id=company_id)}"
            elif integration.provider.lower() == "xero":
                url = f"{config['base_url']}{config['endpoints']['accounts']}"
            else:
                return 0
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                
                data = response.json()
                
                # Parse accounts based on software
                accounts = []
                if integration.provider.lower() == "quickbooks":
                    query_response = data.get("QueryResponse", {})
                    accounts = query_response.get("Account", [])
                elif integration.provider.lower() == "xero":
                    accounts = data.get("Accounts", [])
                
                synced_count = 0
                
                for account_data in accounts:
                    account_id = account_data.get("Id") or account_data.get("AccountID")
                    if not account_id:
                        continue
                    
                    # Check if account already exists
                    existing_account = account_crud.get_by_external_id(
                        db, integration.user_id, account_id
                    )
                    
                    if not existing_account:
                        # Map account data
                        account_name = account_data.get("Name") or account_data.get("AccountName", "Unknown")
                        account_type = self._map_account_type(
                            account_data.get("AccountType") or account_data.get("Type"),
                            integration.provider.lower()
                        )
                        
                        # Get balance if available
                        balance = 0.0
                        if "CurrentBalance" in account_data:
                            balance = float(account_data["CurrentBalance"])
                        elif "Balance" in account_data:
                            balance = float(account_data["Balance"])
                        
                        account_create = AccountCreate(
                            name=account_name,
                            account_type=account_type,
                            institution=integration.provider,
                            account_number=account_id,
                            balance=balance,
                            currency="USD",  # Default, could be configured
                            external_id=account_id,
                            integration_id=integration.id
                        )
                        
                        account_crud.create_with_user(
                            db, obj_in=account_create, user_id=integration.user_id
                        )
                        synced_count += 1
                
                return synced_count
                
        except Exception as e:
            logger.error(f"Error syncing chart of accounts: {str(e)}")
            raise
    
    async def _sync_transactions(
        self, 
        db: Session, 
        integration: Integration, 
        config: Dict[str, Any],
        company_id: str
    ) -> int:
        """Sync transactions from accounting software."""
        try:
            headers = self._get_headers(integration, config)
            
            # Get transactions from the last sync or last 30 days
            from_date = integration.last_sync_at or (datetime.utcnow() - timedelta(days=30))
            to_date = datetime.utcnow()
            
            synced_count = 0
            
            if integration.provider.lower() == "quickbooks":
                # QuickBooks uses reports for transaction data
                url = f"{config['base_url']}{config['endpoints']['transactions'].format(company_id=company_id)}"
                params = {
                    "start_date": from_date.strftime("%Y-%m-%d"),
                    "end_date": to_date.strftime("%Y-%m-%d")
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, headers=headers, params=params, timeout=30.0)
                    response.raise_for_status()
                    
                    # QuickBooks report parsing would be complex - simplified here
                    data = response.json()
                    # Process report data...
                    
            elif integration.provider.lower() == "xero":
                # Xero has bank transactions endpoint
                url = f"{config['base_url']}{config['endpoints']['bank_transactions']}"
                params = {
                    "where": f"Date >= DateTime({from_date.strftime('%Y,%m,%d')}) AND Date <= DateTime({to_date.strftime('%Y,%m,%d')})"
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, headers=headers, params=params, timeout=30.0)
                    response.raise_for_status()
                    
                    data = response.json()
                    bank_transactions = data.get("BankTransactions", [])
                    
                    for transaction_data in bank_transactions:
                        transaction_id = transaction_data.get("BankTransactionID")
                        if not transaction_id:
                            continue
                        
                        # Check if transaction already exists
                        existing_transaction = transaction_crud.get_by_external_id(
                            db, transaction_id
                        )
                        
                        if not existing_transaction:
                            # Find corresponding internal account
                            bank_account_id = transaction_data.get("BankAccount", {}).get("AccountID")
                            internal_account = account_crud.get_by_external_id(
                                db, integration.user_id, bank_account_id
                            )
                            
                            if internal_account:
                                # Parse transaction
                                amount = float(transaction_data.get("Total", 0))
                                transaction_type = transaction_data.get("Type", "SPEND")
                                
                                if transaction_type == "SPEND":
                                    amount = -abs(amount)
                                
                                transaction_date = datetime.fromisoformat(
                                    transaction_data.get("Date", datetime.utcnow().isoformat())
                                ).date()
                                
                                transaction_create = TransactionCreate(
                                    account_id=internal_account.id,
                                    date=transaction_date,
                                    description=transaction_data.get("Reference", "Accounting Transaction"),
                                    amount=amount,
                                    transaction_type="debit" if amount < 0 else "credit",
                                    external_id=transaction_id,
                                    raw_data=transaction_data
                                )
                                
                                transaction_crud.create(db, obj_in=transaction_create)
                                synced_count += 1
            
            return synced_count
            
        except Exception as e:
            logger.error(f"Error syncing transactions: {str(e)}")
            raise
    
    async def test_connection(self, integration: Integration) -> Dict[str, Any]:
        """Test connection to accounting software API."""
        try:
            software = integration.provider.lower()
            config = self.software_configs.get(software)
            
            if not config:
                return {
                    "success": False,
                    "message": f"Unsupported accounting software: {integration.provider}"
                }
            
            if not integration.access_token:
                return {
                    "success": False,
                    "message": "No access token available"
                }
            
            headers = self._get_headers(integration, config)
            
            # Test with appropriate endpoint
            if software == "quickbooks":
                company_id = integration.metadata.get("realmId") if integration.metadata else "1"
                url = f"{config['base_url']}{config['endpoints']['company_info'].format(company_id=company_id)}"
            elif software == "xero":
                url = f"{config['base_url']}{config['endpoints']['organisation']}"
            else:
                return {"success": False, "message": "Unknown software"}
            
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
        headers = {
            "Authorization": f"Bearer {integration.access_token}",
            "Accept": "application/json"
        }
        
        if integration.provider.lower() == "xero":
            headers["Xero-tenant-id"] = integration.metadata.get("tenant_id", "") if integration.metadata else ""
        
        return headers
    
    def _map_account_type(self, accounting_type: str, software: str) -> str:
        """Map accounting software account type to internal account type."""
        if software == "quickbooks":
            type_mapping = {
                "Bank": "checking",
                "Other Current Asset": "checking",
                "Accounts Receivable": "receivable",
                "Accounts Payable": "payable",
                "Credit Card": "credit_card",
                "Expense": "expense",
                "Income": "income",
                "Other Income": "income",
                "Cost of Goods Sold": "expense"
            }
        elif software == "xero":
            type_mapping = {
                "BANK": "checking",
                "CURRENT": "checking",
                "CURRLIAB": "payable",
                "EQUITY": "equity",
                "EXPENSE": "expense",
                "FIXED": "asset",
                "INVENTORY": "asset",
                "LIABILITY": "liability",
                "PREPAYMENT": "asset",
                "REVENUE": "income"
            }
        else:
            type_mapping = {}
        
        return type_mapping.get(accounting_type, "other")