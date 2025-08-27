from typing import List, Optional
from sqlalchemy.orm import Session
from uuid import UUID

from .base import CRUDBase
from ..models.account import Account
from ..schemas.account import AccountCreate, AccountUpdate


class CRUDAccount(CRUDBase[Account, AccountCreate, AccountUpdate]):
    def get_by_user(self, db: Session, *, user_id: UUID, skip: int = 0, limit: int = 100) -> List[Account]:
        return (
            db.query(Account)
            .filter(Account.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_user_and_id(self, db: Session, *, user_id: UUID, account_id: UUID) -> Optional[Account]:
        return (
            db.query(Account)
            .filter(Account.user_id == user_id, Account.id == account_id)
            .first()
        )

    def create_with_user(self, db: Session, *, obj_in: AccountCreate, user_id: UUID) -> Account:
        obj_in_data = obj_in.dict()
        db_obj = Account(**obj_in_data, user_id=user_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_by_id_and_user(self, db: Session, *, id: str, user_id: UUID) -> Optional[Account]:
        """Get account by ID and verify it belongs to the user"""
        try:
            account_id = UUID(id)
        except ValueError:
            return None
        
        return (
            db.query(Account)
            .filter(Account.id == account_id, Account.user_id == user_id)
            .first()
        )


account = CRUDAccount(Account)