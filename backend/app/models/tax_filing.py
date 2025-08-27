from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Numeric, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from ..db.database import Base


class FilingStatus(enum.Enum):
    SINGLE = "single"
    MARRIED_FILING_JOINTLY = "married_filing_jointly"
    MARRIED_FILING_SEPARATELY = "married_filing_separately"
    HEAD_OF_HOUSEHOLD = "head_of_household"
    QUALIFYING_WIDOW = "qualifying_widow"


class TaxFilingStatus(enum.Enum):
    DRAFT = "draft"
    PREPARED = "prepared"
    FILED = "filed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    AMENDED = "amended"


class TaxFiling(Base):
    __tablename__ = "tax_filings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    tax_year = Column(Integer, nullable=False, index=True)
    filing_status = Column(Enum(FilingStatus), nullable=False)
    forms_data = Column(JSON)  # Store tax form data as JSON
    calculated_tax = Column(Numeric(precision=12, scale=2), default=0.00)
    refund_amount = Column(Numeric(precision=12, scale=2), default=0.00)
    filing_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(TaxFilingStatus), default=TaxFilingStatus.DRAFT, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="tax_filings")

    def __repr__(self):
        return f"<TaxFiling(id={self.id}, tax_year={self.tax_year}, status={self.status})>"