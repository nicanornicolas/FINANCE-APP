from typing import List, Optional
from sqlalchemy.orm import Session
from uuid import UUID

from .base import CRUDBase
from ..models.category import Category
from ..schemas.category import CategoryCreate, CategoryUpdate


class CRUDCategory(CRUDBase[Category, CategoryCreate, CategoryUpdate]):
    def get_by_user(self, db: Session, *, user_id: UUID, skip: int = 0, limit: int = 100) -> List[Category]:
        return (
            db.query(Category)
            .filter(Category.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_user_and_id(self, db: Session, *, user_id: UUID, category_id: UUID) -> Optional[Category]:
        return (
            db.query(Category)
            .filter(Category.user_id == user_id, Category.id == category_id)
            .first()
        )

    def get_root_categories(self, db: Session, *, user_id: UUID) -> List[Category]:
        return (
            db.query(Category)
            .filter(Category.user_id == user_id, Category.parent_id.is_(None))
            .all()
        )

    def get_subcategories(self, db: Session, *, user_id: UUID, parent_id: UUID) -> List[Category]:
        return (
            db.query(Category)
            .filter(Category.user_id == user_id, Category.parent_id == parent_id)
            .all()
        )

    def create_with_user(self, db: Session, *, obj_in: CategoryCreate, user_id: UUID) -> Category:
        obj_in_data = obj_in.dict()
        db_obj = Category(**obj_in_data, user_id=user_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


category = CRUDCategory(Category)