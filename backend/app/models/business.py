"""
Business Models for multi-entity support and business features
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum, Numeric, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from ..db.database import Base


class BusinessType(str, enum.Enum):
    SOLE_PROPRIETORSHIP = "sole_proprietorship"
    PARTNERSHIP = "partnership"
    LIMITED_LIABILITY = "limited_liability"
    CORPORATION = "corporation"
    NON_PROFIT = "non_profit"


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    VIEWED = "viewed"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class PaymentTerms(str, enum.Enum):
    NET_15 = "net_15"
    NET_30 = "net_30"
    NET_60 = "net_60"
    NET_90 = "net_90"
    DUE_ON_RECEIPT = "due_on_receipt"
    CUSTOM = "custom"


class BusinessEntity(Base):
    """Business Entity model for multi-entity support"""
    __tablename__ = "business_entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    business_type = Column(Enum(BusinessType), nullable=False)
    registration_number = Column(String(100), nullable=True)
    tax_id = Column(String(50), nullable=True)  # Business tax ID/EIN
    kra_pin = Column(String(20), nullable=True)  # KRA PIN for Kenyan businesses
    
    # Contact Information
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    website = Column(String(255), nullable=True)
    
    # Address Information
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state_province = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)
    
    # Business Settings
    default_currency = Column(String(3), default="KES")
    fiscal_year_start = Column(Integer, default=1)  # Month (1-12)
    is_active = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="business_entities")
    business_accounts = relationship("BusinessAccount", back_populates="business_entity")
    clients = relationship("Client", back_populates="business_entity")
    invoices = relationship("Invoice", back_populates="business_entity")


class BusinessAccount(Base):
    """Business Account model extending the base Account for business-specific features"""
    __tablename__ = "business_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_entity_id = Column(UUID(as_uuid=True), ForeignKey("business_entities.id"), nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    
    # Business-specific account settings
    is_primary = Column(Boolean, default=False)
    account_purpose = Column(String(100), nullable=True)  # Operating, Savings, Payroll, etc.
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    business_entity = relationship("BusinessEntity", back_populates="business_accounts")
    account = relationship("Account")


class Client(Base):
    """Client management model for business entities"""
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_entity_id = Column(UUID(as_uuid=True), ForeignKey("business_entities.id"), nullable=False)
    
    # Client Information
    name = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    
    # Address Information
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state_province = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)
    
    # Business Information
    tax_id = Column(String(50), nullable=True)
    kra_pin = Column(String(20), nullable=True)
    
    # Client Settings
    default_payment_terms = Column(Enum(PaymentTerms), default=PaymentTerms.NET_30)
    default_currency = Column(String(3), default="KES")
    credit_limit = Column(Numeric(15, 2), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    business_entity = relationship("BusinessEntity", back_populates="clients")
    invoices = relationship("Invoice", back_populates="client")


class Invoice(Base):
    """Invoice model for business invoice generation and management"""
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_entity_id = Column(UUID(as_uuid=True), ForeignKey("business_entities.id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    
    # Invoice Details
    invoice_number = Column(String(50), nullable=False, unique=True)
    invoice_date = Column(DateTime, nullable=False)
    due_date = Column(DateTime, nullable=False)
    
    # Financial Information
    subtotal = Column(Numeric(15, 2), nullable=False, default=0)
    tax_rate = Column(Numeric(5, 4), nullable=False, default=0)  # e.g., 0.16 for 16% VAT
    tax_amount = Column(Numeric(15, 2), nullable=False, default=0)
    discount_amount = Column(Numeric(15, 2), nullable=False, default=0)
    total_amount = Column(Numeric(15, 2), nullable=False, default=0)
    paid_amount = Column(Numeric(15, 2), nullable=False, default=0)
    currency = Column(String(3), default="KES")
    
    # Status and Terms
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT)
    payment_terms = Column(Enum(PaymentTerms), default=PaymentTerms.NET_30)
    
    # Additional Information
    notes = Column(Text, nullable=True)
    terms_conditions = Column(Text, nullable=True)
    
    # Tracking
    sent_date = Column(DateTime, nullable=True)
    viewed_date = Column(DateTime, nullable=True)
    paid_date = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    business_entity = relationship("BusinessEntity", back_populates="invoices")
    client = relationship("Client", back_populates="invoices")
    invoice_items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("InvoicePayment", back_populates="invoice")


class InvoiceItem(Base):
    """Invoice line items model"""
    __tablename__ = "invoice_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)
    
    # Item Details
    description = Column(String(500), nullable=False)
    quantity = Column(Numeric(10, 4), nullable=False, default=1)
    unit_price = Column(Numeric(15, 2), nullable=False)
    line_total = Column(Numeric(15, 2), nullable=False)
    
    # Optional Product/Service Reference
    product_service_code = Column(String(50), nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    invoice = relationship("Invoice", back_populates="invoice_items")


class InvoicePayment(Base):
    """Invoice payment tracking model"""
    __tablename__ = "invoice_payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)
    
    # Payment Details
    payment_date = Column(DateTime, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    payment_method = Column(String(50), nullable=True)  # Cash, Check, Bank Transfer, etc.
    reference_number = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    invoice = relationship("Invoice", back_populates="payments")


class BusinessExpenseCategory(Base):
    """Business-specific expense categories for better expense tracking"""
    __tablename__ = "business_expense_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_entity_id = Column(UUID(as_uuid=True), ForeignKey("business_entities.id"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False)
    
    # Business-specific category settings
    is_tax_deductible = Column(Boolean, default=True)
    tax_form_line = Column(String(50), nullable=True)  # Reference to tax form line item
    expense_type = Column(String(100), nullable=True)  # Operating, COGS, Capital, etc.
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    business_entity = relationship("BusinessEntity")
    category = relationship("Category")