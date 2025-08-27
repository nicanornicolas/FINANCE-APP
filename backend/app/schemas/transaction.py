from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

from ..models.transaction import TransactionType


class TransactionBase(BaseModel):
    date: date
    description: str
    amount: Decimal
    transaction_type: TransactionType
    category_id: Optional[UUID] = None
    subcategory_id: Optional[UUID] = None
    tags: List[str] = []
    is_tax_deductible: bool = False
    notes: Optional[str] = None
    reference_number: Optional[str] = None


class TransactionCreate(TransactionBase):
    account_id: UUID


class TransactionUpdate(BaseModel):
    date: Optional[date] = None
    description: Optional[str] = None
    amount: Optional[Decimal] = None
    transaction_type: Optional[TransactionType] = None
    category_id: Optional[UUID] = None
    subcategory_id: Optional[UUID] = None
    tags: Optional[List[str]] = None
    is_tax_deductible: Optional[bool] = None
    notes: Optional[str] = None
    reference_number: Optional[str] = None
    confidence_score: Optional[float] = None


class TransactionInDB(TransactionBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    account_id: UUID
    confidence_score: float
    created_at: datetime
    updated_at: datetime


class Transaction(TransactionInDB):
    pass


class TransactionListResponse(BaseModel):
    transactions: List[Transaction]
    total: int
    page: int
    size: int
    pages: int