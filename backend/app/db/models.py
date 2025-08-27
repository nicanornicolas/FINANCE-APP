from sqlalchemy import Column, Integer, String, Numeric, DateTime, Index
from sqlalchemy.sql import func

from .database import Base


class TransactionORM(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    details = Column(String(512), nullable=False, index=True)
    type = Column(String(16), nullable=False, index=True)  # debit|credit
    amount = Column(Numeric(14, 2), nullable=False, index=True)
    category = Column(String(128), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_tx_user_date", "date"),
        Index("ix_tx_category", "category"),
        Index("ix_tx_amount", "amount"),
    )

