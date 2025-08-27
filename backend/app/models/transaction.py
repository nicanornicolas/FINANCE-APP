from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum, Numeric, Date, Float, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from ..db.database import Base


class TransactionType(enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    description = Column(String, nullable=False)
    amount = Column(Numeric(precision=12, scale=2), nullable=False, index=True)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True, index=True)
    subcategory_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    tags = Column(ARRAY(String), default=[])  # Array of tags
    is_tax_deductible = Column(Boolean, default=False)
    confidence_score = Column(Float, default=0.0)  # For ML categorization confidence
    notes = Column(String)  # Additional notes
    reference_number = Column(String)  # Check number, transaction ID, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", foreign_keys=[category_id], back_populates="transactions")
    subcategory = relationship("Category", foreign_keys=[subcategory_id])

    def __repr__(self):
        return f"<Transaction(id={self.id}, amount={self.amount}, description={self.description})>"