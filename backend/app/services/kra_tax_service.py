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

from app.crud.kra_tax import (
    kra_taxpayer, kra_tax_filing, kra_tax_payment, kra_tax_deduction,
    kra_tax_amendment, kra_tax_document, kra_filing_validation
)
from app.crud.transaction import transaction as transaction_crud
from app.services.kra_tax_calculator import KRATaxCalculator
from app.services.kra_api_client import KRAAPIClient, MockKRAAPIClient, KRAAPIError
from app.schemas.kra_tax import (
    KRATaxpayerCreate, KRATaxpayerResponse,
    KRATaxFilingCreate, KRATaxFilingResponse, KRATaxFilingUpdate,
    KRATaxCalculationRequest, KRATaxCalculationResponse,
    KRAPINValidationRequest, KRAPINValidationResponse,
    KRATaxDeductionCreate,
    KRATaxAmendmentCreate, KRATaxAmendmentResponse,
    KRATaxDocumentCreate, KRATaxDocumentResponse,
    KRAFilingValidationResponse,
    KRAFormValidationRequest, KRAFormValidationResponse,
    KRAFilingHistoryResponse,
    KRAPaymentInitiationRequest, KRAPaymentInitiationResponse,
    KRAPaymentConfirmationRequest, KRAPaymentMethodsResponse,
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
    
    async def validate_tax_form(self, db: Session, *, user_id: UUID, filing_id: UUID) -> KRAFormValidationResponse:
        """Validate tax form before submission"""
        filing = kra_tax_filing.get(db, id=filing_id)
        if not filing or filing.user_id != user_id:
            raise ValueError("Filing not found or not owned by user")
        
        if not filing.forms_data:
            raise ValueError("No form data to validate")
        
        try:
            # Prepare validation request
            validation_request = KRAFormValidationRequest(
                filing_type=filing.filing_type,
                form_data=filing.forms_data,
                tax_year=filing.tax_year
            )
            
            # Validate with KRA
            async with self.kra_client as client:
                validation_result = await client.validate_tax_form(validation_request.dict())
            
            # Store validation result
            kra_filing_validation.create_validation(
                db,
                filing_id=filing.id,
                validation_data=validation_result
            )
            
            return KRAFormValidationResponse(**validation_result)
            
        except KRAAPIError as e:
            logger.error(f"Form validation failed: {e.message}")
            raise ValueError(f"Form validation failed: {e.message}")
    
    async def get_filing_history(self, db: Session, *, user_id: UUID, tax_year: Optional[int] = None) -> KRAFilingHistoryResponse:
        """Get filing history from KRA"""
        taxpayer_obj = kra_taxpayer.get_by_user_id(db, user_id=user_id)
        if not taxpayer_obj:
            raise ValueError("Taxpayer not registered")
        
        try:
            async with self.kra_client as client:
                history_data = await client.get_filing_history(taxpayer_obj.kra_pin, tax_year)
            
            return KRAFilingHistoryResponse(**history_data)
            
        except KRAAPIError as e:
            logger.error(f"Failed to get filing history: {e.message}")
            raise ValueError(f"Filing history error: {e.message}")
    
    def create_amendment(self, db: Session, *, amendment_data: KRATaxAmendmentCreate, user_id: UUID) -> KRATaxAmendmentResponse:
        """Create tax filing amendment"""
        # Get original filing
        original_filing = kra_tax_filing.get(db, id=amendment_data.original_filing_id)
        if not original_filing or original_filing.user_id != user_id:
            raise ValueError("Original filing not found or not owned by user")
        
        if original_filing.status not in [KRAFilingStatus.ACCEPTED, KRAFilingStatus.PAID]:
            raise ValueError("Can only amend accepted or paid filings")
        
        # Create amendment
        amendment = kra_tax_amendment.create_with_user(
            db,
            obj_in=amendment_data,
            user_id=user_id,
            original_data=original_filing.forms_data or {}
        )
        
        return KRATaxAmendmentResponse.from_orm(amendment)
    
    async def submit_amendment(self, db: Session, *, user_id: UUID, amendment_id: UUID) -> Dict[str, Any]:
        """Submit amendment to KRA"""
        amendment = kra_tax_amendment.get(db, id=amendment_id)
        if not amendment or amendment.user_id != user_id:
            raise ValueError("Amendment not found or not owned by user")
        
        if amendment.status != "draft":
            raise ValueError("Only draft amendments can be submitted")
        
        # Get original filing
        original_filing = kra_tax_filing.get(db, id=amendment.original_filing_id)
        if not original_filing:
            raise ValueError("Original filing not found")
        
        try:
            # Prepare amendment data
            amendment_data = {
                "original_reference": original_filing.kra_reference,
                "reason": amendment.reason,
                "amended_data": amendment.amended_data,
                "changes_summary": amendment.changes_summary
            }
            
            # Submit to KRA
            async with self.kra_client as client:
                submission_response = await client.amend_tax_return(
                    original_filing.kra_reference,
                    amendment_data
                )
            
            # Update amendment status
            kra_tax_amendment.update_status(
                db,
                amendment_id=amendment.id,
                status="submitted",
                amendment_reference=submission_response.get("amendment_id")
            )
            
            return submission_response
            
        except KRAAPIError as e:
            logger.error(f"Amendment submission failed: {e.message}")
            raise ValueError(f"Amendment submission failed: {e.message}")
    
    def upload_document(self, db: Session, *, document_data: KRATaxDocumentCreate, user_id: UUID, file_content: bytes) -> KRATaxDocumentResponse:
        """Upload supporting document"""
        import os
        import uuid
        from app.core.config import settings
        
        # Create file path
        file_extension = os.path.splitext(document_data.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(getattr(settings, 'UPLOAD_DIR', '/tmp'), 'kra_documents', unique_filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Save file
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        # Create document record
        document = kra_tax_document.create_with_user(
            db,
            obj_in=document_data,
            user_id=user_id,
            file_path=file_path
        )
        
        return KRATaxDocumentResponse.from_orm(document)
    
    async def upload_document_to_kra(self, db: Session, *, user_id: UUID, document_id: UUID) -> Dict[str, Any]:
        """Upload document to KRA system"""
        document = kra_tax_document.get(db, id=document_id)
        if not document or document.user_id != user_id:
            raise ValueError("Document not found or not owned by user")
        
        if not document.filing_id:
            raise ValueError("Document must be associated with a filing")
        
        filing = kra_tax_filing.get(db, id=document.filing_id)
        if not filing or not filing.kra_reference:
            raise ValueError("Filing not found or not submitted to KRA")
        
        try:
            # Read file content
            with open(document.file_path, 'rb') as f:
                file_content = f.read()
            
            # Prepare upload data
            upload_data = {
                "filename": document.original_filename,
                "document_type": document.document_type,
                "file_content": file_content.hex(),  # Convert to hex for JSON
                "mime_type": document.mime_type
            }
            
            # Upload to KRA
            async with self.kra_client as client:
                upload_response = await client.upload_supporting_document(
                    filing.kra_reference,
                    upload_data
                )
            
            # Update document with KRA reference
            kra_tax_document.update_verification_status(
                db,
                document_id=document.id,
                status="uploaded",
                kra_document_id=upload_response.get("document_id")
            )
            
            return upload_response
            
        except KRAAPIError as e:
            logger.error(f"Document upload to KRA failed: {e.message}")
            raise ValueError(f"Document upload failed: {e.message}")
        except Exception as e:
            logger.error(f"Error uploading document: {str(e)}")
            raise ValueError(f"Document upload error: {str(e)}")
    
    async def initiate_payment(self, db: Session, *, user_id: UUID, payment_request: KRAPaymentInitiationRequest) -> KRAPaymentInitiationResponse:
        """Initiate tax payment"""
        filing = kra_tax_filing.get(db, id=payment_request.filing_id)
        if not filing or filing.user_id != user_id:
            raise ValueError("Filing not found or not owned by user")
        
        if not filing.tax_due or filing.tax_due <= 0:
            raise ValueError("No tax due for this filing")
        
        try:
            # Prepare payment data
            payment_data = {
                "kra_reference": filing.kra_reference,
                "amount": float(payment_request.amount),
                "payment_method": payment_request.payment_method,
                "return_url": payment_request.return_url,
                "taxpayer_pin": filing.taxpayer.kra_pin if filing.taxpayer else None
            }
            
            # Initiate payment with KRA
            async with self.kra_client as client:
                payment_response = await client.initiate_payment(payment_data)
            
            # Create payment record
            from app.schemas.kra_tax import KRATaxPaymentCreate
            payment_create = KRATaxPaymentCreate(
                filing_id=filing.id,
                amount=payment_request.amount,
                payment_method=payment_request.payment_method
            )
            
            kra_tax_payment.create_payment(
                db,
                obj_in=payment_create,
                payment_reference=payment_response["payment_reference"]
            )
            
            return KRAPaymentInitiationResponse(**payment_response)
            
        except KRAAPIError as e:
            logger.error(f"Payment initiation failed: {e.message}")
            raise ValueError(f"Payment initiation failed: {e.message}")
    
    async def confirm_payment(self, db: Session, *, user_id: UUID, confirmation_request: KRAPaymentConfirmationRequest) -> Dict[str, Any]:
        """Confirm payment completion"""
        payment = kra_tax_payment.get_by_reference(db, payment_reference=confirmation_request.payment_reference)
        if not payment:
            raise ValueError("Payment not found")
        
        # Verify user owns the filing
        filing = kra_tax_filing.get(db, id=payment.filing_id)
        if not filing or filing.user_id != user_id:
            raise ValueError("Payment not owned by user")
        
        try:
            # Confirm with KRA
            async with self.kra_client as client:
                confirmation_response = await client.confirm_payment(
                    confirmation_request.payment_reference,
                    confirmation_request.dict()
                )
            
            # Update payment status
            kra_tax_payment.update_payment_status(
                db,
                payment_id=payment.id,
                status="completed",
                kra_receipt=confirmation_response.get("receipt_number")
            )
            
            # Update filing status if fully paid
            total_payments = sum(p.amount for p in kra_tax_payment.get_by_filing_id(db, filing_id=filing.id) if p.status == "completed")
            if total_payments >= filing.tax_due:
                kra_tax_filing.update_status(db, filing_id=filing.id, status=KRAFilingStatus.PAID)
            
            return confirmation_response
            
        except KRAAPIError as e:
            logger.error(f"Payment confirmation failed: {e.message}")
            raise ValueError(f"Payment confirmation failed: {e.message}")
    
    async def get_payment_methods(self) -> KRAPaymentMethodsResponse:
        """Get available payment methods"""
        try:
            async with self.kra_client as client:
                methods_data = await client.get_payment_methods()
            
            return KRAPaymentMethodsResponse(**methods_data)
            
        except KRAAPIError as e:
            logger.error(f"Failed to get payment methods: {e.message}")
            raise ValueError(f"Payment methods error: {e.message}")
    
    def get_user_documents(self, db: Session, *, user_id: UUID, filing_id: Optional[UUID] = None) -> List[KRATaxDocumentResponse]:
        """Get user's tax documents"""
        if filing_id:
            documents = kra_tax_document.get_by_filing_id(db, filing_id=filing_id)
        else:
            documents = kra_tax_document.get_by_user_id(db, user_id=user_id)
        
        return [KRATaxDocumentResponse.from_orm(doc) for doc in documents]
    
    def get_user_amendments(self, db: Session, *, user_id: UUID, filing_id: Optional[UUID] = None) -> List[KRATaxAmendmentResponse]:
        """Get user's tax amendments"""
        if filing_id:
            amendments = kra_tax_amendment.get_by_filing_id(db, filing_id=filing_id)
        else:
            amendments = kra_tax_amendment.get_by_user_id(db, user_id=user_id)
        
        return [KRATaxAmendmentResponse.from_orm(amendment) for amendment in amendments]
    
    def get_filing_validations(self, db: Session, *, user_id: UUID, filing_id: UUID) -> List[KRAFilingValidationResponse]:
        """Get filing validation history"""
        filing = kra_tax_filing.get(db, id=filing_id)
        if not filing or filing.user_id != user_id:
            raise ValueError("Filing not found or not owned by user")
        
        validations = kra_filing_validation.get_by_filing_id(db, filing_id=filing_id)
        return [KRAFilingValidationResponse.from_orm(validation) for validation in validations]


# Create service instance
kra_tax_service = KRATaxService()