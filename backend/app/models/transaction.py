from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class Transaction(BaseModel):
    id: Optional[int] = None
    date: datetime
    details: str
    type: str = Field(pattern="^(debit|credit)$")
    amount: float
    category: Optional[str] = None

