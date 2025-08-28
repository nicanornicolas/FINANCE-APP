"""
KRA Tax Service
Main service for KRA tax preparation, calculation, and filing
"""
import logging
from typing import Dict, List, Any, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime, date
from sqlalchemy.orm import Session

from app.crud.kra_tax import kra_taxpayer, kra_tax_filing, kra_tax_payment, kra_tax_deduction
from app.crud.transaction import transaction as transaction_crud
from app.services.kra_tax_calculator import KRATaxCalculator
from app.services.kra_api_client import KRAAPIClient, MockKRAAPIClient, KRAAPIError
from app.schemas.kra_tax import (
    KRATaxpayerCreate, KRATaxpayerResponse,
    KRATaxFilingCreate, KRATaxFilingResponse, KRATaxFilingUpdate,
    KRATaxCalculationRequest, KRATaxCalculationResponse,
    KRAPINValidationRequest, KRAPINValidationResponse,
    KRATaxDeductionCreate,
    KRAFilingType, KRAFilingStatus
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class KRATaxService:
    """Service for managing KRA tax operations"""
    
    def __init__(self):
        self.calculator = KRATaxCalculator()
        # Use mock client for development
        self.kra_client = MockKRAAPIClient() if getattr(settings, 'USE_MOCK_KRA', True) else KRAAPIClient()
    
    async def validate_kra_pin(self, kra_pin: str) -> KRAPINValidationResponse:
        """Validate KRA PIN with KRA iTax system"""
        try:
            async with self.kra_client as client:
                return await client.validate_pin(kra_pin)
        except KRAAPIError as e:
            logger.error(f"KRA PIN validation failed: {e.message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error validating KRA PIN: {str(e)}")
            raise KRAAPIError(f"PIN validation error: {str(e)}")
    
    def register_taxpayer(self, db: Session, *, taxpayer_data: KRATaxpayerCreate, user_id: UUID) -> KRATaxpayerResponse:
        """Register new taxpayer"""
        # Check if taxpayer already exists for this user
        existing = kra_taxpayer.get_by_user_id(db, user_id=user_id)
        if existing:
            raise ValueError("Taxpayer already registered for this user")
        
        # Check if KRA PIN is already registered
        existing_pin = kra_taxpayer.get_by_kra_pin(db, kra_pin=taxpayer_data.kra_pin)
        if existing_pin:
            raise ValueError("KRA PIN already registered")
        
        # Create taxpayer
        taxpayer = kra_taxpayer.create_with_user(db, obj_in=taxpayer_data, user_id=user_id)
        return KRATaxpayerResponse.from_orm(taxpayer)
    
    async def verify_taxpayer(self, db: Session, *, taxpayer_id: UUID) -> KRATaxpayerResponse:
        """Verify taxpayer with KRA"""
        taxpayer_obj = kra_taxpayer.get(db, id=taxpayer_id)
        if not taxpayer_obj:
            raise ValueError("Taxpayer not found")
        
        try:
            # Validate with KRA
            validation = await self.validate_kra_pin(taxpayer_obj.kra_pin)
            
            if validation.is_valid:
                # Update taxpayer info from KRA
                update_data = {
                    "taxpayer_name": validation.taxpayer_name or taxpayer_obj.taxpayer_name,
                    "tax_office": validation.tax_office or taxpayer_obj.tax_office,
                    "registration_date": validation.registration_date,
                    "is_verified": True,
                    "last_sync": datetime.now()
                }
                
                updated_taxpayer = kra_taxpayer.update(db, db_obj=taxpayer_obj, obj_in=update_data)
                return KRATaxpayerResponse.from_orm(updated_taxpayer)
            else:
                raise ValueError("KRA PIN validation failed")
                
        except KRAAPIError as e:
            logger.error(f"KRA verification failed: {e.message}")
            raise ValueError(f"KRA verification failed: {e.message}")
    
    def get_user_taxpayer(self, db: Session, *, user_id: UUID) -> Optional[KRATaxpayerResponse]:
        """Get taxpayer for user"""
        taxpayer_obj = kra_taxpayer.get_by_user_id(db, user_id=user_id)
        return KRATaxpayerResponse.from_orm(taxpayer_obj) if taxpayer_obj else None
    
    def create_tax_filing(self, db: Session, *, filing_data: KRATaxFilingCreate, user_id: UUID) -> KRATaxFilingResponse:
        """Create new tax filing"""
        # Verify taxpayer exists and is verified
        taxpayer_obj = kra_taxpayer.get(db, id=filing_data.taxpayer_id)
        if not taxpayer_obj or taxpayer_obj.user_id != user_id:
            raise ValueError("Taxpayer not found or not owned by user")
        
        if not taxpayer_obj.is_verified:
            raise ValueError("Taxpayer must be verified before filing")
        
        # Check for existing filing for same year and type
        existing_filings = kra_tax_filing.get_by_tax_year(db, user_id=user_id, tax_year=filing_data.tax_year)
        for filing in existing_filings:
            if filing.filing_type == filing_data.filing_type and filing.status not in [KRAFilingStatus.REJECTED]:
                raise ValueError(f"Filing for {filing_data.filing_type} {filing_data.tax_year} already exists")
        
        # Create filing
        filing = kra_tax_filing.create_with_user(db, obj_in=filing_data, user_id=user_id)
        return KRATaxFilingResponse.from_orm(filing)
    
    async def calculate_tax(self, db: Session, *, user_id: UUID, filing_id: UUID) -> KRATaxCalculationResponse:
        """Calculate tax for filing"""
        # Get filing
        filing = kra_tax_filing.get(db, id=filing_id)
        if not filing or filing.user_id != user_id:
            raise ValueError("Filing not found or not owned by user")
        
        # Get user's financial data for the tax year
        income_data = await self._get_user_income_data(db, user_id=user_id, tax_year=filing.tax_year)
        deductions = await self._get_user_deductions(db, user_id=user_id, tax_year=filing.tax_year)
        
        # Create calculation request
        calc_request = KRATaxCalculationRequest(
            tax_year=filing.tax_year,
            filing_type=filing.filing_type,
            income_data=income_data,
            deductions=deductions
        )
        
        # Calculate tax
        calculation = await self.calculator.calculate_tax(calc_request)
        
        # Update filing with calculation results
        update_data = KRATaxFilingUpdate(
            calculated_tax=calculation.calculated_tax,
            tax_due=calculation.calculated_tax,
            forms_data={
                "calculation": calculation.dict(),
                "income_data": income_data,
                "deductions": deductions
            }
        )
        
        kra_tax_filing.update(db, db_obj=filing, obj_in=update_data)
        
        return calculation
    
    async def submit_tax_filing(self, db: Session, *, user_id: UUID, filing_id: UUID) -> Dict[str, Any]:
        """Submit tax filing to KRA"""
        # Get filing
        filing = kra_tax_filing.get(db, id=filing_id)
        if not filing or filing.user_id != user_id:
            raise ValueError("Filing not found or not owned by user")
        
        if filing.status != KRAFilingStatus.DRAFT:
            raise ValueError("Only draft filings can be submitted")
        
        if not filing.calculated_tax:
            raise ValueError("Tax must be calculated before submission")
        
        # Get taxpayer info
        taxpayer_obj = kra_taxpayer.get(db, id=filing.taxpayer_id)
        if not taxpayer_obj:
            raise ValueError("Taxpayer not found")
        
        try:
            # Prepare submission data
            submission_data = {
                "taxpayer_pin": taxpayer_obj.kra_pin,
                "tax_year": filing.tax_year,
                "filing_type": filing.filing_type.value,
                "forms_data": filing.forms_data,
                "calculated_tax": float(filing.calculated_tax),
                "submission_date": datetime.now().isoformat()
            }
            
            # Submit to KRA
            async with self.kra_client as client:
                submission_response = await client.submit_tax_return(submission_data)
            
            # Update filing status
            kra_tax_filing.update_status(
                db,
                filing_id=filing.id,
                status=KRAFilingStatus.SUBMITTED,
                kra_reference=submission_response.kra_reference
            )
            
            return {
                "success": True,
                "kra_reference": submission_response.kra_reference,
                "submission_date": submission_response.submission_date,
                "status": submission_response.status,
                "next_steps": submission_response.next_steps
            }
            
        except KRAAPIError as e:
            logger.error(f"KRA submission failed: {e.message}")
            raise ValueError(f"Tax filing submission failed: {e.message}")
    
    async def get_filing_status(self, db: Session, *, user_id: UUID, filing_id: UUID) -> Dict[str, Any]:
        """Get filing status from KRA"""
        filing = kra_tax_filing.get(db, id=filing_id)
        if not filing or filing.user_id != user_id:
            raise ValueError("Filing not found or not owned by user")
        
        if not filing.kra_reference:
            return {"status": filing.status.value, "message": "Not yet submitted to KRA"}
        
        try:
            async with self.kra_client as client:
                status_data = await client.get_filing_status(filing.kra_reference)
            
            # Update local status if changed
            if status_data.get("status") != filing.status.value:
                kra_tax_filing.update_status(db, filing_id=filing.id, status=status_data["status"])
            
            return status_data
            
        except KRAAPIError as e:
            logger.error(f"Failed to get filing status: {e.message}")
            return {"status": filing.status.value, "error": e.message}
    
    def get_user_filings(self, db: Session, *, user_id: UUID, skip: int = 0, limit: int = 100) -> List[KRATaxFilingResponse]:
        """Get user's tax filings"""
        filings = kra_tax_filing.get_by_user_id(db, user_id=user_id, skip=skip, limit=limit)
        return [KRATaxFilingResponse.from_orm(filing) for filing in filings]
    
    def add_tax_deduction(self, db: Session, *, deduction_data: KRATaxDeductionCreate, user_id: UUID):
        """Add tax deduction for user"""
        return kra_tax_deduction.create_with_user(db, obj_in=deduction_data, user_id=user_id)
    
    def get_user_deductions(self, db: Session, *, user_id: UUID, tax_year: int):
        """Get user's tax deductions for year"""
        return kra_tax_deduction.get_by_user_and_year(db, user_id=user_id, tax_year=tax_year)
    
    async def _get_user_income_data(self, db: Session, *, user_id: UUID, tax_year: int) -> Dict[str, Decimal]:
        """Get user's income data for tax year from transactions"""
        # This would analyze user's transactions to categorize income
        # For now, return basic structure
        
        # Get transactions for the tax year
        from datetime import date
        start_date = date(tax_year, 1, 1)
        end_date = date(tax_year, 12, 31)
        
        # This is a simplified implementation
        # In reality, you'd analyze transactions by category to determine income types
        
        return {
            "employment": Decimal("0"),
            "business": Decimal("0"),
            "rental": Decimal("0"),
            "investment": Decimal("0"),
            "other": Decimal("0")
        }
    
    async def _get_user_deductions(self, db: Session, *, user_id: UUID, tax_year: int) -> List[Dict[str, Any]]:
        """Get user's deductions for tax year"""
        deductions_data = kra_tax_deduction.get_by_user_and_year(db, user_id=user_id, tax_year=tax_year)
        
        return [
            {
                "type": deduction.deduction_type,
                "amount": float(deduction.amount),
                "description": deduction.description,
                "verified": deduction.is_verified
            }
            for deduction in deductions_data
        ]


# Create service instance
kra_tax_service = KRATaxService()