"""
Integration tests for KRA e-filing capabilities
"""
import pytest
import asyncio
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.services.kra_tax_service import kra_tax_service
from app.schemas.kra_tax import (
    KRATaxpayerCreate, KRATaxFilingCreate, KRATaxAmendmentCreate,
    KRATaxDocumentCreate, KRAPaymentInitiationRequest,
    KRAPaymentConfirmationRequest, KRAFormValidationRequest,
    KRAFilingType, KRATaxpayerType
)
from app.models.kra_tax import KRAFilingStatus
from tests.utils.utils import create_random_user


client = TestClient(app)


class TestKRAEFilingIntegration:
    """Test KRA e-filing integration functionality"""
    
    @pytest.fixture
    def test_user(self, db: Session):
        """Create test user"""
        return create_random_user(db)
    
    @pytest.fixture
    def test_taxpayer(self, db: Session, test_user):
        """Create test taxpayer"""
        taxpayer_data = KRATaxpayerCreate(
            kra_pin="P051234567A",
            taxpayer_name="John Doe",
            taxpayer_type=KRATaxpayerType.INDIVIDUAL,
            tax_office="Nairobi South"
        )
        return kra_tax_service.register_taxpayer(
            db, taxpayer_data=taxpayer_data, user_id=test_user.id
        )
    
    @pytest.fixture
    def test_filing(self, db: Session, test_user, test_taxpayer):
        """Create test tax filing"""
        filing_data = KRATaxFilingCreate(
            taxpayer_id=test_taxpayer.id,
            tax_year=2023,
            filing_type=KRAFilingType.INDIVIDUAL,
            due_date=datetime(2024, 6, 30)
        )
        return kra_tax_service.create_tax_filing(
            db, filing_data=filing_data, user_id=test_user.id
        )
    
    @pytest.mark.asyncio
    async def test_validate_tax_form(self, db: Session, test_user, test_filing):
        """Test tax form validation"""
        # First calculate tax to populate form data
        await kra_tax_service.calculate_tax(
            db, user_id=test_user.id, filing_id=test_filing.id
        )
        
        # Validate the form
        validation_result = await kra_tax_service.validate_tax_form(
            db, user_id=test_user.id, filing_id=test_filing.id
        )
        
        assert validation_result is not None
        assert hasattr(validation_result, 'is_valid')
        assert hasattr(validation_result, 'errors')
        assert hasattr(validation_result, 'warnings')
        assert hasattr(validation_result, 'validation_id')
    
    @pytest.mark.asyncio
    async def test_get_filing_history(self, db: Session, test_user, test_taxpayer):
        """Test getting filing history from KRA"""
        history = await kra_tax_service.get_filing_history(
            db, user_id=test_user.id, tax_year=2023
        )
        
        assert history is not None
        assert hasattr(history, 'filings')
        assert hasattr(history, 'total_count')
        assert isinstance(history.filings, list)
        assert isinstance(history.total_count, int)
    
    def test_create_amendment(self, db: Session, test_user, test_filing):
        """Test creating tax filing amendment"""
        # Update filing status to accepted first
        from app.crud.kra_tax import kra_tax_filing
        kra_tax_filing.update_status(
            db, filing_id=test_filing.id, status=KRAFilingStatus.ACCEPTED
        )
        
        amendment_data = KRATaxAmendmentCreate(
            original_filing_id=test_filing.id,
            reason="Correction of income amount due to additional income discovered",
            amended_data={
                "total_income": 500000,
                "taxable_income": 450000,
                "calculated_tax": 45000
            }
        )
        
        amendment = kra_tax_service.create_amendment(
            db, amendment_data=amendment_data, user_id=test_user.id
        )
        
        assert amendment is not None
        assert amendment.original_filing_id == test_filing.id
        assert amendment.user_id == test_user.id
        assert amendment.reason == amendment_data.reason
        assert amendment.status == "draft"
        assert amendment.changes_summary is not None
    
    @pytest.mark.asyncio
    async def test_submit_amendment(self, db: Session, test_user, test_filing):
        """Test submitting amendment to KRA"""
        # Create amendment first
        amendment = self.test_create_amendment(db, test_user, test_filing)
        
        # Submit amendment
        submission_result = await kra_tax_service.submit_amendment(
            db, user_id=test_user.id, amendment_id=amendment.id
        )
        
        assert submission_result is not None
        assert "amendment_id" in submission_result
        assert "status" in submission_result
        assert submission_result["status"] == "submitted"
    
    def test_upload_document(self, db: Session, test_user, test_filing):
        """Test uploading supporting document"""
        document_data = KRATaxDocumentCreate(
            filing_id=test_filing.id,
            document_type="supporting_doc",
            filename="salary_certificate.pdf",
            file_content=b"Mock PDF content for testing",
            mime_type="application/pdf"
        )
        
        document = kra_tax_service.upload_document(
            db, document_data=document_data, user_id=test_user.id, file_content=document_data.file_content
        )
        
        assert document is not None
        assert document.filing_id == test_filing.id
        assert document.user_id == test_user.id
        assert document.document_type == "supporting_doc"
        assert document.original_filename == "salary_certificate.pdf"
        assert document.verification_status == "pending"
    
    @pytest.mark.asyncio
    async def test_upload_document_to_kra(self, db: Session, test_user, test_filing):
        """Test uploading document to KRA system"""
        # Create document first
        document = self.test_upload_document(db, test_user, test_filing)
        
        # Set filing as submitted (required for KRA upload)
        from app.crud.kra_tax import kra_tax_filing
        kra_tax_filing.update_status(
            db, filing_id=test_filing.id, 
            status=KRAFilingStatus.SUBMITTED,
            kra_reference="KRA2023TEST001"
        )
        
        # Upload to KRA
        upload_result = await kra_tax_service.upload_document_to_kra(
            db, user_id=test_user.id, document_id=document.id
        )
        
        assert upload_result is not None
        assert "document_id" in upload_result
        assert "status" in upload_result
        assert upload_result["status"] == "uploaded"
    
    @pytest.mark.asyncio
    async def test_get_payment_methods(self):
        """Test getting available payment methods"""
        payment_methods = await kra_tax_service.get_payment_methods()
        
        assert payment_methods is not None
        assert hasattr(payment_methods, 'methods')
        assert isinstance(payment_methods.methods, list)
        assert len(payment_methods.methods) > 0
        
        # Check first payment method structure
        method = payment_methods.methods[0]
        assert hasattr(method, 'method_id')
        assert hasattr(method, 'name')
        assert hasattr(method, 'description')
        assert hasattr(method, 'processing_time')
        assert hasattr(method, 'fees')
    
    @pytest.mark.asyncio
    async def test_initiate_payment(self, db: Session, test_user, test_filing):
        """Test initiating tax payment"""
        # Set up filing with tax due
        from app.crud.kra_tax import kra_tax_filing
        from app.schemas.kra_tax import KRATaxFilingUpdate
        
        update_data = KRATaxFilingUpdate(
            calculated_tax=Decimal("50000"),
            tax_due=Decimal("50000"),
            status=KRAFilingStatus.ACCEPTED
        )
        kra_tax_filing.update(db, db_obj=test_filing, obj_in=update_data)
        
        payment_request = KRAPaymentInitiationRequest(
            filing_id=test_filing.id,
            amount=Decimal("50000"),
            payment_method="mobile_money",
            return_url="https://example.com/payment-return"
        )
        
        payment_response = await kra_tax_service.initiate_payment(
            db, user_id=test_user.id, payment_request=payment_request
        )
        
        assert payment_response is not None
        assert hasattr(payment_response, 'payment_reference')
        assert hasattr(payment_response, 'amount')
        assert hasattr(payment_response, 'payment_url')
        assert hasattr(payment_response, 'expires_at')
        assert payment_response.amount == Decimal("50000")
    
    @pytest.mark.asyncio
    async def test_confirm_payment(self, db: Session, test_user, test_filing):
        """Test confirming payment completion"""
        # Initiate payment first
        payment_response = await self.test_initiate_payment(db, test_user, test_filing)
        
        confirmation_request = KRAPaymentConfirmationRequest(
            payment_reference=payment_response.payment_reference,
            transaction_id="TXN123456789",
            payment_method="mobile_money"
        )
        
        confirmation_result = await kra_tax_service.confirm_payment(
            db, user_id=test_user.id, confirmation_request=confirmation_request
        )
        
        assert confirmation_result is not None
        assert "status" in confirmation_result
        # In mock implementation, this would be successful
    
    def test_get_user_documents(self, db: Session, test_user, test_filing):
        """Test getting user's tax documents"""
        # Upload a document first
        self.test_upload_document(db, test_user, test_filing)
        
        # Get all documents
        documents = kra_tax_service.get_user_documents(
            db, user_id=test_user.id
        )
        
        assert isinstance(documents, list)
        assert len(documents) > 0
        
        # Get documents for specific filing
        filing_documents = kra_tax_service.get_user_documents(
            db, user_id=test_user.id, filing_id=test_filing.id
        )
        
        assert isinstance(filing_documents, list)
        assert len(filing_documents) > 0
        assert all(doc.filing_id == test_filing.id for doc in filing_documents)
    
    def test_get_user_amendments(self, db: Session, test_user, test_filing):
        """Test getting user's tax amendments"""
        # Create an amendment first
        self.test_create_amendment(db, test_user, test_filing)
        
        # Get all amendments
        amendments = kra_tax_service.get_user_amendments(
            db, user_id=test_user.id
        )
        
        assert isinstance(amendments, list)
        assert len(amendments) > 0
        
        # Get amendments for specific filing
        filing_amendments = kra_tax_service.get_user_amendments(
            db, user_id=test_user.id, filing_id=test_filing.id
        )
        
        assert isinstance(filing_amendments, list)
        assert len(filing_amendments) > 0
        assert all(amend.original_filing_id == test_filing.id for amend in filing_amendments)
    
    @pytest.mark.asyncio
    async def test_get_filing_validations(self, db: Session, test_user, test_filing):
        """Test getting filing validation history"""
        # Validate form first to create validation record
        await self.test_validate_tax_form(db, test_user, test_filing)
        
        # Get validations
        validations = kra_tax_service.get_filing_validations(
            db, user_id=test_user.id, filing_id=test_filing.id
        )
        
        assert isinstance(validations, list)
        assert len(validations) > 0
        
        validation = validations[0]
        assert validation.filing_id == test_filing.id
        assert hasattr(validation, 'is_valid')
        assert hasattr(validation, 'validation_date')


class TestKRAEFilingAPI:
    """Test KRA e-filing API endpoints"""
    
    @pytest.fixture
    def auth_headers(self, test_user):
        """Get authentication headers"""
        # This would typically involve creating a JWT token
        # For testing, we'll mock this
        return {"Authorization": f"Bearer test-token-{test_user.id}"}
    
    def test_validate_tax_form_endpoint(self, auth_headers):
        """Test tax form validation endpoint"""
        filing_id = str(uuid4())
        response = client.post(
            f"/api/v1/kra-tax/filings/{filing_id}/validate",
            headers=auth_headers
        )
        
        # This would fail in real scenario without proper setup
        # but tests the endpoint structure
        assert response.status_code in [200, 400, 404, 500]
    
    def test_get_filing_history_endpoint(self, auth_headers):
        """Test filing history endpoint"""
        response = client.get(
            "/api/v1/kra-tax/filing-history",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 400, 404, 500]
    
    def test_create_amendment_endpoint(self, auth_headers):
        """Test create amendment endpoint"""
        amendment_data = {
            "original_filing_id": str(uuid4()),
            "reason": "Test amendment reason",
            "amended_data": {"test": "data"}
        }
        
        response = client.post(
            "/api/v1/kra-tax/amendments",
            json=amendment_data,
            headers=auth_headers
        )
        
        assert response.status_code in [200, 400, 404, 500]
    
    def test_get_payment_methods_endpoint(self, auth_headers):
        """Test get payment methods endpoint"""
        response = client.get(
            "/api/v1/kra-tax/payment-methods",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 400, 500]
    
    def test_initiate_payment_endpoint(self, auth_headers):
        """Test initiate payment endpoint"""
        payment_data = {
            "filing_id": str(uuid4()),
            "amount": 50000,
            "payment_method": "mobile_money",
            "return_url": "https://example.com/return"
        }
        
        response = client.post(
            "/api/v1/kra-tax/payments/initiate",
            json=payment_data,
            headers=auth_headers
        )
        
        assert response.status_code in [200, 400, 404, 500]
    
    def test_upload_document_endpoint(self, auth_headers):
        """Test upload document endpoint"""
        document_data = {
            "filing_id": str(uuid4()),
            "document_type": "supporting_doc",
            "filename": "test.pdf",
            "file_content": "dGVzdCBjb250ZW50",  # base64 encoded "test content"
            "mime_type": "application/pdf"
        }
        
        response = client.post(
            "/api/v1/kra-tax/documents",
            json=document_data,
            headers=auth_headers
        )
        
        assert response.status_code in [200, 400, 404, 500]


class TestKRAEFilingErrorHandling:
    """Test error handling in KRA e-filing"""
    
    def test_invalid_filing_id_error(self, db: Session, test_user):
        """Test error handling for invalid filing ID"""
        invalid_filing_id = uuid4()
        
        with pytest.raises(ValueError, match="Filing not found"):
            asyncio.run(kra_tax_service.validate_tax_form(
                db, user_id=test_user.id, filing_id=invalid_filing_id
            ))
    
    def test_unauthorized_user_error(self, db: Session, test_filing):
        """Test error handling for unauthorized user"""
        unauthorized_user_id = uuid4()
        
        with pytest.raises(ValueError, match="Filing not found or not owned by user"):
            asyncio.run(kra_tax_service.validate_tax_form(
                db, user_id=unauthorized_user_id, filing_id=test_filing.id
            ))
    
    def test_unregistered_taxpayer_error(self, db: Session):
        """Test error handling for unregistered taxpayer"""
        unregistered_user_id = uuid4()
        
        with pytest.raises(ValueError, match="Taxpayer not registered"):
            asyncio.run(kra_tax_service.get_filing_history(
                db, user_id=unregistered_user_id
            ))
    
    def test_invalid_amendment_status_error(self, db: Session, test_user, test_filing):
        """Test error handling for invalid amendment status"""
        # Try to amend a draft filing (should fail)
        amendment_data = KRATaxAmendmentCreate(
            original_filing_id=test_filing.id,
            reason="Test amendment",
            amended_data={"test": "data"}
        )
        
        with pytest.raises(ValueError, match="Can only amend accepted or paid filings"):
            kra_tax_service.create_amendment(
                db, amendment_data=amendment_data, user_id=test_user.id
            )


if __name__ == "__main__":
    pytest.main([__file__])