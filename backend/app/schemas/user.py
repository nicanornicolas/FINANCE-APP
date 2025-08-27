from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None
    settings: Optional[str] = None


class UserInDB(UserBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    settings: Optional[str] = None


class User(UserInDB):
    pass


class UserLogin(BaseModel):
    email: EmailStr
    password: str