"""
KRA Tax Models for Kenya Revenue Authority integration
"""
from sqlalchemy import Column, String, Integer, Decimal, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.db.base_class import Base


class KRAFilingType(str, enum.Enum):
    INDIVIDUAL = "individual"
    CORPORATE = "corporate"
    VAT = "vat"
    WITHHOLDING = "withholding"
    TURNOVER = "turnover"
    RENTAL = "rental"
    CAPITAL_GAINS = "capital_gains"


class KRAFilingStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PAID = "paid"
    OVERDUE = "overdue"


class KRATaxpayerType(str, enum.Enum):
    INDIVIDUAL = "individual"
    CORPORATE = "corporate"
    PARTNERSHIP = "partnership"
    TRUST = "trust"


class KRATaxpayer(Base):
    """KRA Taxpayer information model"""
    __tablename__ = "kra_taxpayers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    kra_pin = Column(String(20), nullable=False, index=True)  # Encrypted in service layer
    taxpayer_name = Column(String(255), nullable=False)
    taxpayer_type = Column(Enum(KRATaxpayerType), nullable=False)
    registration_date = Column(DateTime, nullable=True)
    tax_office = Column(String(100), nullable=True)
    is_verified = Column(Boolean, default=False)
    last_sync = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="kra_taxpayer")
    tax_filings = relationship("KRATaxFiling", back_populates="taxpayer")


class KRATaxFiling(Base):
    """KRA Tax Filing model"""
    __tablename__ = "kra_tax_filings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    taxpayer_id = Column(UUID(as_uuid=True), ForeignKey("kra_taxpayers.id"), nullable=False)
    tax_year = Column(Integer, nullable=False)
    filing_type = Column(Enum(KRAFilingType), nullable=False)
    forms_data = Column(JSON, nullable=True)  # Structured tax form data
    calculated_tax = Column(Decimal(15, 2), nullable=True)
    tax_due = Column(Decimal(15, 2), nullable=True)
    payments_made = Column(Decimal(15, 2), default=0)
    filing_date = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    kra_reference = Column(String(50), nullable=True, unique=True)
    status = Column(Enum(KRAFilingStatus), default=KRAFilingStatus.DRAFT)
    submission_receipt = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User")
    taxpayer = relationship("KRATaxpayer", back_populates="tax_filings")
    payments = relationship("KRATaxPayment", back_populates="filing")


class KRATaxPayment(Base):
    """KRA Tax Payment tracking model"""
    __tablename__ = "kra_tax_payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filing_id = Column(UUID(as_uuid=True), ForeignKey("kra_tax_filings.id"), nullable=False)
    payment_reference = Column(String(50), nullable=False, unique=True)
    amount = Column(Decimal(15, 2), nullable=False)
    payment_date = Column(DateTime, nullable=False)
    payment_method = Column(String(50), nullable=True)  # Bank, Mobile Money, etc.
    kra_receipt = Column(String(100), nullable=True)
    status = Column(String(20), default="pending")  # pending, completed, failed
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    filing = relationship("KRATaxFiling", back_populates="payments")


class KRATaxDeduction(Base):
    """KRA Tax Deductions model"""
    __tablename__ = "kra_tax_deductions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    tax_year = Column(Integer, nullable=False)
    deduction_type = Column(String(100), nullable=False)  # Insurance, Mortgage, etc.
    description = Column(String(255), nullable=False)
    amount = Column(Decimal(15, 2), nullable=False)
    supporting_documents = Column(JSON, nullable=True)  # File references
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User")