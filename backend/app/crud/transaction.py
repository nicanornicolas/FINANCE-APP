from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from uuid import UUID
from datetime import date

from .base import CRUDBase
from ..models.transaction import Transaction
from ..schemas.transaction import TransactionCreate, TransactionUpdate


class CRUDTransaction(CRUDBase[Transaction, TransactionCreate, TransactionUpdate]):
    def get_by_account(
        self, 
        db: Session, 
        *, 
        account_id: UUID, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Transaction]:
        return (
            db.query(Transaction)
            .filter(Transaction.account_id == account_id)
            .order_by(desc(Transaction.date))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_user(
        self, 
        db: Session, 
        *, 
        user_id: UUID, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Transaction]:
        return (
            db.query(Transaction)
            .join(Transaction.account)
            .filter(Transaction.account.has(user_id=user_id))
            .order_by(desc(Transaction.date))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_date_range(
        self,
        db: Session,
        *,
        user_id: UUID,
        start_date: date,
        end_date: date,
        skip: int = 0,
        limit: int = 100
    ) -> List[Transaction]:
        return (
            db.query(Transaction)
            .join(Transaction.account)
            .filter(
                and_(
                    Transaction.account.has(user_id=user_id),
                    Transaction.date >= start_date,
                    Transaction.date <= end_date
                )
            )
            .order_by(desc(Transaction.date))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_category(
        self,
        db: Session,
        *,
        user_id: UUID,
        category_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Transaction]:
        return (
            db.query(Transaction)
            .join(Transaction.account)
            .filter(
                and_(
                    Transaction.account.has(user_id=user_id),
                    or_(
                        Transaction.category_id == category_id,
                        Transaction.subcategory_id == category_id
                    )
                )
            )
            .order_by(desc(Transaction.date))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def search_transactions(
        self,
        db: Session,
        *,
        user_id: UUID,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Transaction]:
        return (
            db.query(Transaction)
            .join(Transaction.account)
            .filter(
                and_(
                    Transaction.account.has(user_id=user_id),
                    or_(
                        Transaction.description.ilike(f"%{search_term}%"),
                        Transaction.notes.ilike(f"%{search_term}%"),
                        Transaction.reference_number.ilike(f"%{search_term}%")
                    )
                )
            )
            .order_by(desc(Transaction.date))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_multi_with_filters(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        user_id: UUID,
        filters: dict = None
    ) -> tuple[List[Transaction], int]:
        """Get transactions with filters and return total count"""
        from ..models.account import Account
        
        query = db.query(Transaction).join(Account).filter(Account.user_id == user_id)
        
        if filters:
            if filters.get('account_id'):
                query = query.filter(Transaction.account_id == UUID(filters['account_id']))
            if filters.get('category_id'):
                category_id = UUID(filters['category_id'])
                query = query.filter(
                    or_(
                        Transaction.category_id == category_id,
                        Transaction.subcategory_id == category_id
                    )
                )
            if filters.get('transaction_type'):
                query = query.filter(Transaction.transaction_type == filters['transaction_type'])
            if filters.get('start_date'):
                query = query.filter(Transaction.date >= filters['start_date'])
            if filters.get('end_date'):
                query = query.filter(Transaction.date <= filters['end_date'])
            if filters.get('min_amount') is not None:
                query = query.filter(Transaction.amount >= filters['min_amount'])
            if filters.get('max_amount') is not None:
                query = query.filter(Transaction.amount <= filters['max_amount'])
            if filters.get('search'):
                search_term = filters['search']
                query = query.filter(
                    or_(
                        Transaction.description.ilike(f"%{search_term}%"),
                        Transaction.notes.ilike(f"%{search_term}%"),
                        Transaction.reference_number.ilike(f"%{search_term}%")
                    )
                )
            if filters.get('is_tax_deductible') is not None:
                query = query.filter(Transaction.is_tax_deductible == filters['is_tax_deductible'])
        
        total = query.count()
        transactions = query.order_by(desc(Transaction.date)).offset(skip).limit(limit).all()
        
        return transactions, total

    def get_by_id_and_user(
        self,
        db: Session,
        *,
        id: str,
        user_id: UUID
    ) -> Optional[Transaction]:
        """Get transaction by ID and verify it belongs to the user"""
        from ..models.account import Account
        
        return (
            db.query(Transaction)
            .join(Account)
            .filter(
                and_(
                    Transaction.id == UUID(id),
                    Account.user_id == user_id
                )
            )
            .first()
        )

    def create_with_user(
        self,
        db: Session,
        *,
        obj_in: TransactionCreate,
        user_id: UUID
    ) -> Transaction:
        """Create transaction and verify account belongs to user"""
        # TODO: Add account ownership verification
        return self.create(db, obj_in=obj_in)

    def search(
        self,
        db: Session,
        *,
        query: str,
        skip: int = 0,
        limit: int = 100,
        user_id: UUID
    ) -> tuple[List[Transaction], int]:
        """Search transactions and return total count"""
        from ..models.account import Account
        
        db_query = (
            db.query(Transaction)
            .join(Account)
            .filter(
                and_(
                    Account.user_id == user_id,
                    or_(
                        Transaction.description.ilike(f"%{query}%"),
                        Transaction.notes.ilike(f"%{query}%"),
                        Transaction.reference_number.ilike(f"%{query}%")
                    )
                )
            )
        )
        
        total = db_query.count()
        transactions = db_query.order_by(desc(Transaction.date)).offset(skip).limit(limit).all()
        
        return transactions, total


transaction = CRUDTransaction(Transaction)