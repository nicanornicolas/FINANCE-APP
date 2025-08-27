from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class CategoryBase(BaseModel):
    name: str
    parent_id: Optional[UUID] = None
    color: str = "#6B7280"
    icon: str = "folder"
    is_tax_category: bool = False
    tax_form_line: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[UUID] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    is_tax_category: Optional[bool] = None
    tax_form_line: Optional[str] = None


class CategoryInDB(CategoryBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime


class Category(CategoryInDB):
    subcategories: Optional[List["Category"]] = []


# Enable forward references
Category.model_rebuild()