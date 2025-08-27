from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from ..models.account import AccountType


class AccountBase(BaseModel):
    name: str
    account_type: AccountType
    institution: Optional[str] = None
    account_number: Optional[str] = None
    currency: str = "USD"


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    institution: Optional[str] = None
    account_number: Optional[str] = None
    balance: Optional[Decimal] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None


class AccountInDB(AccountBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    balance: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime


class Account(AccountInDB):
    pass