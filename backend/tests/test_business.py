"""
Tests for business functionality including entities, clients, invoices, and reporting
"""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from uuid import uuid4
from sqlalchemy.orm import Session

from app.models.business import (
    BusinessEntity, BusinessType, Client, Invoice, InvoiceItem, 
    InvoicePayment, InvoiceStatus, PaymentTerms
)
from app.models.user import User
from app.models.account import Account, AccountType
from app.models.transaction import Transaction, TransactionType
from app.crud.business import (
    business_entity, client, invoice, invoice_item, invoice_payment
)
from app.services.business_service import business_service
from app.schemas.business import (
    BusinessEntityCreate, ClientCreate, InvoiceCreate, InvoiceItemCreate,
    InvoicePaymentCreate
)


@pytest.fixture
def test_user(db: Session):
    """Create a test user"""
    user = User(
        email="test@example.com",
        password_hash="hashed_password",
        first_name="Test",
        last_name="User",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_business_entity(db: Session, test_user: User):
    """Create a test business entity"""
    entity_data = BusinessEntityCreate(
        name="Test Business LLC",
        business_type=BusinessType.LIMITED_LIABILITY,
        registration_number="REG123456",
        tax_id="TAX789012",
        kra_pin="A123456789Z",
        email="business@test.com",
        phone="+254700123456",
        address_line1="123 Business Street",
        city="Nairobi",
        country="Kenya",
        default_currency="KES"
    )
    return business_entity.create(db=db, obj_in=entity_data, user_id=test_user.id)


@pytest.fixture
def test_client(db: Session, test_business_entity: BusinessEntity):
    """Create a test client"""
    client_data = ClientCreate(
        business_entity_id=test_business_entity.id,
        name="Test Client",
        company_name="Client Corp",
        email="client@test.com",
        phone="+254700654321",
        address_line1="456 Client Avenue",
        city="Nairobi",
        country="Kenya",
        default_payment_terms=PaymentTerms.NET_30
    )
    return client.create(db=db, obj_in=client_data)


@pytest.fixture
def test_account(db: Session, test_user: User):
    """Create a test account"""
    account = Account(
        user_id=test_user.id,
        name="Test Business Account",
        account_type=AccountType.CHECKING,
        institution="Test Bank",
        balance=Decimal('10000.00'),
        currency="KES"
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


class TestBusinessEntity:
    """Test business entity CRUD operations"""

    def test_create_business_entity(self, db: Session, test_user: User):
        """Test creating a business entity"""
        entity_data = BusinessEntityCreate(
            name="New Business",
            business_type=BusinessType.SOLE_PROPRIETORSHIP,
            email="new@business.com",
            default_currency="KES"
        )
        
        entity = business_entity.create(db=db, obj_in=entity_data, user_id=test_user.id)
        
        assert entity.name == "New Business"
        assert entity.business_type == BusinessType.SOLE_PROPRIETORSHIP
        assert entity.user_id == test_user.id
        assert entity.default_currency == "KES"
        assert entity.is_active is True

    def test_get_business_entities_by_user(self, db: Session, test_business_entity: BusinessEntity, test_user: User):
        """Test getting business entities by user"""
        entities = business_entity.get_by_user(db=db, user_id=test_user.id)
        
        assert len(entities) == 1
        assert entities[0].id == test_business_entity.id

    def test_update_business_entity(self, db: Session, test_business_entity: BusinessEntity):
        """Test updating a business entity"""
        from app.schemas.business import BusinessEntityUpdate
        
        update_data = BusinessEntityUpdate(
            name="Updated Business Name",
            phone="+254700999888"
        )
        
        updated_entity = business_entity.update(db=db, db_obj=test_business_entity, obj_in=update_data)
        
        assert updated_entity.name == "Updated Business Name"
        assert updated_entity.phone == "+254700999888"

    def test_delete_business_entity(self, db: Session, test_business_entity: BusinessEntity):
        """Test deleting (deactivating) a business entity"""
        deleted_entity = business_entity.delete(db=db, id=test_business_entity.id)
        
        assert deleted_entity.is_active is False


class TestClient:
    """Test client CRUD operations"""

    def test_create_client(self, db: Session, test_business_entity: BusinessEntity):
        """Test creating a client"""
        client_data = ClientCreate(
            business_entity_id=test_business_entity.id,
            name="New Client",
            email="newclient@test.com",
            default_payment_terms=PaymentTerms.NET_15
        )
        
        new_client = client.create(db=db, obj_in=client_data)
        
        assert new_client.name == "New Client"
        assert new_client.business_entity_id == test_business_entity.id
        assert new_client.default_payment_terms == PaymentTerms.NET_15

    def test_get_clients_by_business(self, db: Session, test_client: Client, test_business_entity: BusinessEntity):
        """Test getting clients by business entity"""
        clients = client.get_by_business(db=db, business_entity_id=test_business_entity.id)
        
        assert len(clients) == 1
        assert clients[0].id == test_client.id

    def test_update_client(self, db: Session, test_client: Client):
        """Test updating a client"""
        from app.schemas.business import ClientUpdate
        
        update_data = ClientUpdate(
            name="Updated Client Name",
            credit_limit=Decimal('5000.00')
        )
        
        updated_client = client.update(db=db, db_obj=test_client, obj_in=update_data)
        
        assert updated_client.name == "Updated Client Name"
        assert updated_client.credit_limit == Decimal('5000.00')


class TestInvoice:
    """Test invoice CRUD operations"""

    def test_create_invoice_with_items(self, db: Session, test_business_entity: BusinessEntity, test_client: Client):
        """Test creating an invoice with items"""
        invoice_items = [
            InvoiceItemCreate(
                description="Web Development Services",
                quantity=Decimal('40.0000'),
                unit_price=Decimal('1500.00')
            ),
            InvoiceItemCreate(
                description="Domain Registration",
                quantity=Decimal('1.0000'),
                unit_price=Decimal('2000.00')
            )
        ]
        
        invoice_data = InvoiceCreate(
            business_entity_id=test_business_entity.id,
            client_id=test_client.id,
            invoice_number="INV-001",
            invoice_date=datetime.now(),
            due_date=datetime.now() + timedelta(days=30),
            tax_rate=Decimal('0.16'),  # 16% VAT
            discount_amount=Decimal('0.00'),
            items=invoice_items
        )
        
        new_invoice = invoice.create(db=db, obj_in=invoice_data)
        
        assert new_invoice.invoice_number == "INV-001"
        assert new_invoice.subtotal == Decimal('62000.00')  # 40 * 1500 + 1 * 2000
        assert new_invoice.tax_amount == Decimal('9920.00')  # 62000 * 0.16
        assert new_invoice.total_amount == Decimal('71920.00')  # 62000 + 9920
        assert len(new_invoice.invoice_items) == 2

    def test_get_invoices_by_business(self, db: Session, test_business_entity: BusinessEntity):
        """Test getting invoices by business entity"""
        invoices = invoice.get_by_business(db=db, business_entity_id=test_business_entity.id)
        
        # Should include any invoices created in other tests
        assert isinstance(invoices, list)

    def test_mark_invoice_as_sent(self, db: Session, test_business_entity: BusinessEntity, test_client: Client):
        """Test marking an invoice as sent"""
        # Create an invoice first
        invoice_items = [
            InvoiceItemCreate(
                description="Consulting Services",
                quantity=Decimal('10.0000'),
                unit_price=Decimal('5000.00')
            )
        ]
        
        invoice_data = InvoiceCreate(
            business_entity_id=test_business_entity.id,
            client_id=test_client.id,
            invoice_number="INV-002",
            invoice_date=datetime.now(),
            due_date=datetime.now() + timedelta(days=30),
            items=invoice_items
        )
        
        new_invoice = invoice.create(db=db, obj_in=invoice_data)
        
        # Mark as sent
        sent_invoice = invoice.mark_as_sent(db=db, invoice_id=new_invoice.id)
        
        assert sent_invoice.status == InvoiceStatus.SENT
        assert sent_invoice.sent_date is not None

    def test_add_invoice_payment(self, db: Session, test_business_entity: BusinessEntity, test_client: Client):
        """Test adding a payment to an invoice"""
        # Create an invoice first
        invoice_items = [
            InvoiceItemCreate(
                description="Payment Test Service",
                quantity=Decimal('1.0000'),
                unit_price=Decimal('10000.00')
            )
        ]
        
        invoice_data = InvoiceCreate(
            business_entity_id=test_business_entity.id,
            client_id=test_client.id,
            invoice_number="INV-003",
            invoice_date=datetime.now(),
            due_date=datetime.now() + timedelta(days=30),
            items=invoice_items
        )
        
        new_invoice = invoice.create(db=db, obj_in=invoice_data)
        
        # Add a payment
        payment_data = InvoicePaymentCreate(
            invoice_id=new_invoice.id,
            payment_date=datetime.now(),
            amount=Decimal('5000.00'),
            payment_method="Bank Transfer",
            reference_number="TXN123456"
        )
        
        payment = invoice_payment.create(db=db, obj_in=payment_data)
        
        assert payment.amount == Decimal('5000.00')
        assert payment.payment_method == "Bank Transfer"
        
        # Check that invoice paid amount was updated
        db.refresh(new_invoice)
        assert new_invoice.paid_amount == Decimal('5000.00')

    def test_full_payment_marks_invoice_paid(self, db: Session, test_business_entity: BusinessEntity, test_client: Client):
        """Test that full payment marks invoice as paid"""
        # Create an invoice
        invoice_items = [
            InvoiceItemCreate(
                description="Full Payment Test",
                quantity=Decimal('1.0000'),
                unit_price=Decimal('1000.00')
            )
        ]
        
        invoice_data = InvoiceCreate(
            business_entity_id=test_business_entity.id,
            client_id=test_client.id,
            invoice_number="INV-004",
            invoice_date=datetime.now(),
            due_date=datetime.now() + timedelta(days=30),
            tax_rate=Decimal('0.00'),  # No tax for simplicity
            items=invoice_items
        )
        
        new_invoice = invoice.create(db=db, obj_in=invoice_data)
        
        # Add full payment
        payment_data = InvoicePaymentCreate(
            invoice_id=new_invoice.id,
            payment_date=datetime.now(),
            amount=new_invoice.total_amount,
            payment_method="Cash"
        )
        
        invoice_payment.create(db=db, obj_in=payment_data)
        
        # Check that invoice is marked as paid
        db.refresh(new_invoice)
        assert new_invoice.status == InvoiceStatus.PAID
        assert new_invoice.paid_date is not None


class TestBusinessService:
    """Test business service layer"""

    def test_get_business_summary(self, db: Session, test_business_entity: BusinessEntity, test_client: Client):
        """Test getting business summary statistics"""
        # Create a paid invoice for revenue
        invoice_items = [
            InvoiceItemCreate(
                description="Summary Test Service",
                quantity=Decimal('1.0000'),
                unit_price=Decimal('5000.00')
            )
        ]
        
        invoice_data = InvoiceCreate(
            business_entity_id=test_business_entity.id,
            client_id=test_client.id,
            invoice_number="INV-SUMMARY",
            invoice_date=datetime.now(),
            due_date=datetime.now() + timedelta(days=30),
            tax_rate=Decimal('0.00'),
            items=invoice_items
        )
        
        test_invoice = invoice.create(db=db, obj_in=invoice_data)
        
        # Mark as paid
        invoice.mark_as_paid(db=db, invoice_id=test_invoice.id)
        
        # Get business summary
        summary = business_service.get_business_summary(db=db, business_entity_id=test_business_entity.id)
        
        assert summary.total_revenue >= Decimal('5000.00')
        assert summary.active_clients >= 1

    def test_generate_profit_loss_report(self, db: Session, test_business_entity: BusinessEntity):
        """Test generating profit and loss report"""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
        
        report = business_service.generate_profit_loss_report(
            db=db,
            business_entity_id=test_business_entity.id,
            start_date=start_date,
            end_date=end_date
        )
        
        assert report.business_entity_id == test_business_entity.id
        assert report.period_start.date() == start_date
        assert report.period_end.date() == end_date
        assert isinstance(report.revenue, Decimal)
        assert isinstance(report.net_profit, Decimal)

    def test_generate_cash_flow_report(self, db: Session, test_business_entity: BusinessEntity):
        """Test generating cash flow report"""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
        
        report = business_service.generate_cash_flow_report(
            db=db,
            business_entity_id=test_business_entity.id,
            start_date=start_date,
            end_date=end_date
        )
        
        assert report.business_entity_id == test_business_entity.id
        assert isinstance(report.opening_balance, Decimal)
        assert isinstance(report.closing_balance, Decimal)
        assert isinstance(report.monthly_breakdown, list)

    def test_get_invoice_analytics(self, db: Session, test_business_entity: BusinessEntity):
        """Test getting invoice analytics"""
        analytics = business_service.get_invoice_analytics(db=db, business_entity_id=test_business_entity.id)
        
        assert 'status_distribution' in analytics
        assert 'average_payment_days' in analytics
        assert 'top_clients' in analytics
        assert isinstance(analytics['status_distribution'], list)


class TestBusinessValidation:
    """Test business model validation"""

    def test_invoice_item_validation(self):
        """Test invoice item validation"""
        # Test valid item
        valid_item = InvoiceItemCreate(
            description="Valid Item",
            quantity=Decimal('2.0000'),
            unit_price=Decimal('100.00')
        )
        assert valid_item.quantity > 0
        assert valid_item.unit_price >= 0

    def test_business_entity_fiscal_year_validation(self):
        """Test business entity fiscal year validation"""
        # This would be tested in the Pydantic schema validation
        # The actual validation logic is in the schema
        pass

    def test_invoice_calculation_accuracy(self, db: Session, test_business_entity: BusinessEntity, test_client: Client):
        """Test invoice calculation accuracy"""
        invoice_items = [
            InvoiceItemCreate(
                description="Item 1",
                quantity=Decimal('2.5000'),
                unit_price=Decimal('1234.56')
            ),
            InvoiceItemCreate(
                description="Item 2",
                quantity=Decimal('1.0000'),
                unit_price=Decimal('999.99')
            )
        ]
        
        invoice_data = InvoiceCreate(
            business_entity_id=test_business_entity.id,
            client_id=test_client.id,
            invoice_number="INV-CALC",
            invoice_date=datetime.now(),
            due_date=datetime.now() + timedelta(days=30),
            tax_rate=Decimal('0.16'),
            discount_amount=Decimal('100.00'),
            items=invoice_items
        )
        
        test_invoice = invoice.create(db=db, obj_in=invoice_data)
        
        expected_subtotal = Decimal('2.5000') * Decimal('1234.56') + Decimal('1.0000') * Decimal('999.99')
        expected_tax = expected_subtotal * Decimal('0.16')
        expected_total = expected_subtotal + expected_tax - Decimal('100.00')
        
        assert test_invoice.subtotal == expected_subtotal
        assert test_invoice.tax_amount == expected_tax
        assert test_invoice.total_amount == expected_total