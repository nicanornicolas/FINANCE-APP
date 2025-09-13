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


class KRATaxAmendment(Base):
    """KRA Tax Amendment model"""
    __tablename__ = "kra_tax_amendments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_filing_id = Column(UUID(as_uuid=True), ForeignKey("kra_tax_filings.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    amendment_reference = Column(String(50), nullable=True, unique=True)
    reason = Column(Text, nullable=False)
    original_data = Column(JSON, nullable=False)  # Original filing data
    amended_data = Column(JSON, nullable=False)   # New filing data
    changes_summary = Column(JSON, nullable=True) # Summary of changes
    status = Column(String(20), default="draft")  # draft, submitted, accepted, rejected
    submission_date = Column(DateTime, nullable=True)
    processing_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    original_filing = relationship("KRATaxFiling", foreign_keys=[original_filing_id])
    user = relationship("User")


class KRATaxDocument(Base):
    """KRA Tax Document model"""
    __tablename__ = "kra_tax_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filing_id = Column(UUID(as_uuid=True), ForeignKey("kra_tax_filings.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    document_type = Column(String(50), nullable=False)  # tax_return, receipt, supporting_doc, etc.
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    kra_document_id = Column(String(50), nullable=True)  # KRA's document reference
    upload_date = Column(DateTime, server_default=func.now())
    verification_status = Column(String(20), default="pending")  # pending, verified, rejected
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    filing = relationship("KRATaxFiling")
    user = relationship("User")


class KRAFilingValidation(Base):
    """KRA Filing Validation model"""
    __tablename__ = "kra_filing_validations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filing_id = Column(UUID(as_uuid=True), ForeignKey("kra_tax_filings.id"), nullable=False)
    validation_id = Column(String(50), nullable=True)  # KRA validation reference
    is_valid = Column(Boolean, nullable=False)
    errors = Column(JSON, nullable=True)    # Validation errors
    warnings = Column(JSON, nullable=True)  # Validation warnings
    validation_date = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    filing = relationship("KRATaxFiling")