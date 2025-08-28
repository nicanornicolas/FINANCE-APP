"""
CRUD operations for KRA Tax models
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from app.crud.base import CRUDBase
from app.models.kra_tax import KRATaxpayer, KRATaxFiling, KRATaxPayment, KRATaxDeduction
from app.schemas.kra_tax import (
    KRATaxpayerCreate, KRATaxpayerUpdate,
    KRATaxFilingCreate, KRATaxFilingUpdate,
    KRATaxPaymentCreate,
    KRATaxDeductionCreate, KRATaxDeductionUpdate
)


class CRUDKRATaxpayer(CRUDBase[KRATaxpayer, KRATaxpayerCreate, KRATaxpayerUpdate]):
    """CRUD operations for KRA Taxpayer"""
    
    def get_by_user_id(self, db: Session, *, user_id: UUID) -> Optional[KRATaxpayer]:
        """Get taxpayer by user ID"""
        return db.query(KRATaxpayer).filter(KRATaxpayer.user_id == user_id).first()
    
    def get_by_kra_pin(self, db: Session, *, kra_pin: str) -> Optional[KRATaxpayer]:
        """Get taxpayer by KRA PIN"""
        return db.query(KRATaxpayer).filter(KRATaxpayer.kra_pin == kra_pin).first()
    
    def create_with_user(self, db: Session, *, obj_in: KRATaxpayerCreate, user_id: UUID) -> KRATaxpayer:
        """Create taxpayer with user ID"""
        obj_in_data = obj_in.dict()
        obj_in_data["user_id"] = user_id
        db_obj = KRATaxpayer(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def verify_taxpayer(self, db: Session, *, taxpayer_id: UUID) -> Optional[KRATaxpayer]:
        """Mark taxpayer as verified"""
        db_obj = db.query(KRATaxpayer).filter(KRATaxpayer.id == taxpayer_id).first()
        if db_obj:
            db_obj.is_verified = True
            db.commit()
            db.refresh(db_obj)
        return db_obj


class CRUDKRATaxFiling(CRUDBase[KRATaxFiling, KRATaxFilingCreate, KRATaxFilingUpdate]):
    """CRUD operations for KRA Tax Filing"""
    
    def get_by_user_id(self, db: Session, *, user_id: UUID, skip: int = 0, limit: int = 100) -> List[KRATaxFiling]:
        """Get tax filings by user ID"""
        return (
            db.query(KRATaxFiling)
            .filter(KRATaxFiling.user_id == user_id)
            .order_by(desc(KRATaxFiling.tax_year), desc(KRATaxFiling.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_tax_year(self, db: Session, *, user_id: UUID, tax_year: int) -> List[KRATaxFiling]:
        """Get tax filings by user and tax year"""
        return (
            db.query(KRATaxFiling)
            .filter(and_(KRATaxFiling.user_id == user_id, KRATaxFiling.tax_year == tax_year))
            .all()
        )
    
    def get_by_kra_reference(self, db: Session, *, kra_reference: str) -> Optional[KRATaxFiling]:
        """Get tax filing by KRA reference"""
        return db.query(KRATaxFiling).filter(KRATaxFiling.kra_reference == kra_reference).first()
    
    def create_with_user(self, db: Session, *, obj_in: KRATaxFilingCreate, user_id: UUID) -> KRATaxFiling:
        """Create tax filing with user ID"""
        obj_in_data = obj_in.dict()
        obj_in_data["user_id"] = user_id
        db_obj = KRATaxFiling(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get_pending_filings(self, db: Session, *, user_id: UUID) -> List[KRATaxFiling]:
        """Get pending tax filings for user"""
        from app.models.kra_tax import KRAFilingStatus
        return (
            db.query(KRATaxFiling)
            .filter(
                and_(
                    KRATaxFiling.user_id == user_id,
                    or_(
                        KRATaxFiling.status == KRAFilingStatus.DRAFT,
                        KRATaxFiling.status == KRAFilingStatus.SUBMITTED
                    )
                )
            )
            .all()
        )
    
    def get_overdue_filings(self, db: Session, *, user_id: UUID) -> List[KRATaxFiling]:
        """Get overdue tax filings for user"""
        from datetime import datetime
        from app.models.kra_tax import KRAFilingStatus
        
        return (
            db.query(KRATaxFiling)
            .filter(
                and_(
                    KRATaxFiling.user_id == user_id,
                    KRATaxFiling.due_date < datetime.now(),
                    KRATaxFiling.status != KRAFilingStatus.PAID
                )
            )
            .all()
        )
    
    def update_status(self, db: Session, *, filing_id: UUID, status: str, kra_reference: Optional[str] = None) -> Optional[KRATaxFiling]:
        """Update filing status and KRA reference"""
        db_obj = db.query(KRATaxFiling).filter(KRATaxFiling.id == filing_id).first()
        if db_obj:
            db_obj.status = status
            if kra_reference:
                db_obj.kra_reference = kra_reference
            db.commit()
            db.refresh(db_obj)
        return db_obj


class CRUDKRATaxPayment(CRUDBase[KRATaxPayment, KRATaxPaymentCreate, KRATaxPaymentCreate]):
    """CRUD operations for KRA Tax Payment"""
    
    def get_by_filing_id(self, db: Session, *, filing_id: UUID) -> List[KRATaxPayment]:
        """Get payments by filing ID"""
        return (
            db.query(KRATaxPayment)
            .filter(KRATaxPayment.filing_id == filing_id)
            .order_by(desc(KRATaxPayment.payment_date))
            .all()
        )
    
    def get_by_reference(self, db: Session, *, payment_reference: str) -> Optional[KRATaxPayment]:
        """Get payment by reference"""
        return db.query(KRATaxPayment).filter(KRATaxPayment.payment_reference == payment_reference).first()
    
    def create_payment(self, db: Session, *, obj_in: KRATaxPaymentCreate, payment_reference: str) -> KRATaxPayment:
        """Create payment with generated reference"""
        from datetime import datetime
        
        obj_in_data = obj_in.dict()
        obj_in_data["payment_reference"] = payment_reference
        obj_in_data["payment_date"] = datetime.now()
        
        db_obj = KRATaxPayment(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update_payment_status(self, db: Session, *, payment_id: UUID, status: str, kra_receipt: Optional[str] = None) -> Optional[KRATaxPayment]:
        """Update payment status"""
        db_obj = db.query(KRATaxPayment).filter(KRATaxPayment.id == payment_id).first()
        if db_obj:
            db_obj.status = status
            if kra_receipt:
                db_obj.kra_receipt = kra_receipt
            db.commit()
            db.refresh(db_obj)
        return db_obj


class CRUDKRATaxDeduction(CRUDBase[KRATaxDeduction, KRATaxDeductionCreate, KRATaxDeductionUpdate]):
    """CRUD operations for KRA Tax Deduction"""
    
    def get_by_user_and_year(self, db: Session, *, user_id: UUID, tax_year: int) -> List[KRATaxDeduction]:
        """Get deductions by user and tax year"""
        return (
            db.query(KRATaxDeduction)
            .filter(and_(KRATaxDeduction.user_id == user_id, KRATaxDeduction.tax_year == tax_year))
            .all()
        )
    
    def get_by_type(self, db: Session, *, user_id: UUID, tax_year: int, deduction_type: str) -> List[KRATaxDeduction]:
        """Get deductions by type"""
        return (
            db.query(KRATaxDeduction)
            .filter(
                and_(
                    KRATaxDeduction.user_id == user_id,
                    KRATaxDeduction.tax_year == tax_year,
                    KRATaxDeduction.deduction_type == deduction_type
                )
            )
            .all()
        )
    
    def create_with_user(self, db: Session, *, obj_in: KRATaxDeductionCreate, user_id: UUID) -> KRATaxDeduction:
        """Create deduction with user ID"""
        obj_in_data = obj_in.dict()
        obj_in_data["user_id"] = user_id
        db_obj = KRATaxDeduction(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get_total_deductions(self, db: Session, *, user_id: UUID, tax_year: int) -> Dict[str, Any]:
        """Get total deductions by type for user and year"""
        from sqlalchemy import func
        
        result = (
            db.query(
                KRATaxDeduction.deduction_type,
                func.sum(KRATaxDeduction.amount).label('total_amount'),
                func.count(KRATaxDeduction.id).label('count')
            )
            .filter(and_(KRATaxDeduction.user_id == user_id, KRATaxDeduction.tax_year == tax_year))
            .group_by(KRATaxDeduction.deduction_type)
            .all()
        )
        
        return {
            row.deduction_type: {
                'total_amount': float(row.total_amount),
                'count': row.count
            }
            for row in result
        }
    
    def verify_deduction(self, db: Session, *, deduction_id: UUID) -> Optional[KRATaxDeduction]:
        """Mark deduction as verified"""
        db_obj = db.query(KRATaxDeduction).filter(KRATaxDeduction.id == deduction_id).first()
        if db_obj:
            db_obj.is_verified = True
            db.commit()
            db.refresh(db_obj)
        return db_obj


# Create instances
kra_taxpayer = CRUDKRATaxpayer(KRATaxpayer)
kra_tax_filing = CRUDKRATaxFiling(KRATaxFiling)
kra_tax_payment = CRUDKRATaxPayment(KRATaxPayment)
kra_tax_deduction = CRUDKRATaxDeduction(KRATaxDeduction)