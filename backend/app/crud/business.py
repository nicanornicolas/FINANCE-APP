"""
CRUD operations for business entities and related models
"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, extract
from datetime import datetime, date
from decimal import Decimal

from ..models.business import (
    BusinessEntity, BusinessAccount, Client, Invoice, InvoiceItem, 
    InvoicePayment, BusinessExpenseCategory, InvoiceStatus
)
from ..models.transaction import Transaction
from ..schemas.business import (
    BusinessEntityCreate, BusinessEntityUpdate, ClientCreate, ClientUpdate,
    InvoiceCreate, InvoiceUpdate, InvoiceItemCreate, InvoicePaymentCreate,
    BusinessAccountCreate, BusinessExpenseCategoryCreate
)


class CRUDBusinessEntity:
    def get(self, db: Session, id: UUID) -> Optional[BusinessEntity]:
        return db.query(BusinessEntity).filter(BusinessEntity.id == id).first()

    def get_by_user(self, db: Session, user_id: UUID) -> List[BusinessEntity]:
        return db.query(BusinessEntity).filter(
            and_(BusinessEntity.user_id == user_id, BusinessEntity.is_active == True)
        ).all()

    def create(self, db: Session, obj_in: BusinessEntityCreate, user_id: UUID) -> BusinessEntity:
        db_obj = BusinessEntity(
            user_id=user_id,
            **obj_in.dict()
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: BusinessEntity, obj_in: BusinessEntityUpdate) -> BusinessEntity:
        update_data = obj_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: UUID) -> BusinessEntity:
        obj = db.query(BusinessEntity).filter(BusinessEntity.id == id).first()
        if obj:
            obj.is_active = False
            db.commit()
            db.refresh(obj)
        return obj


class CRUDClient:
    def get(self, db: Session, id: UUID) -> Optional[Client]:
        return db.query(Client).filter(Client.id == id).first()

    def get_by_business(self, db: Session, business_entity_id: UUID) -> List[Client]:
        return db.query(Client).filter(
            and_(Client.business_entity_id == business_entity_id, Client.is_active == True)
        ).all()

    def create(self, db: Session, obj_in: ClientCreate) -> Client:
        db_obj = Client(**obj_in.dict())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: Client, obj_in: ClientUpdate) -> Client:
        update_data = obj_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: UUID) -> Client:
        obj = db.query(Client).filter(Client.id == id).first()
        if obj:
            obj.is_active = False
            db.commit()
            db.refresh(obj)
        return obj


class CRUDInvoice:
    def get(self, db: Session, id: UUID) -> Optional[Invoice]:
        return db.query(Invoice).filter(Invoice.id == id).first()

    def get_by_business(self, db: Session, business_entity_id: UUID, skip: int = 0, limit: int = 100) -> List[Invoice]:
        return db.query(Invoice).filter(
            Invoice.business_entity_id == business_entity_id
        ).offset(skip).limit(limit).all()

    def get_by_client(self, db: Session, client_id: UUID, skip: int = 0, limit: int = 100) -> List[Invoice]:
        return db.query(Invoice).filter(
            Invoice.client_id == client_id
        ).offset(skip).limit(limit).all()

    def get_by_status(self, db: Session, business_entity_id: UUID, status: InvoiceStatus) -> List[Invoice]:
        return db.query(Invoice).filter(
            and_(Invoice.business_entity_id == business_entity_id, Invoice.status == status)
        ).all()

    def get_overdue(self, db: Session, business_entity_id: UUID) -> List[Invoice]:
        today = datetime.now().date()
        return db.query(Invoice).filter(
            and_(
                Invoice.business_entity_id == business_entity_id,
                Invoice.due_date < today,
                Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.VIEWED])
            )
        ).all()

    def create(self, db: Session, obj_in: InvoiceCreate) -> Invoice:
        # Calculate totals
        subtotal = sum(item.quantity * item.unit_price for item in obj_in.items)
        tax_amount = subtotal * obj_in.tax_rate
        total_amount = subtotal + tax_amount - obj_in.discount_amount

        # Create invoice
        invoice_data = obj_in.dict(exclude={'items'})
        invoice_data.update({
            'subtotal': subtotal,
            'tax_amount': tax_amount,
            'total_amount': total_amount
        })
        
        db_obj = Invoice(**invoice_data)
        db.add(db_obj)
        db.flush()  # Get the invoice ID

        # Create invoice items
        for item_data in obj_in.items:
            line_total = item_data.quantity * item_data.unit_price
            invoice_item = InvoiceItem(
                invoice_id=db_obj.id,
                line_total=line_total,
                **item_data.dict()
            )
            db.add(invoice_item)

        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: Invoice, obj_in: InvoiceUpdate) -> Invoice:
        update_data = obj_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def recalculate_totals(self, db: Session, invoice_id: UUID) -> Invoice:
        """Recalculate invoice totals based on current items"""
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            return None

        # Get all invoice items
        items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).all()
        
        # Calculate totals
        subtotal = sum(item.line_total for item in items)
        tax_amount = subtotal * invoice.tax_rate
        total_amount = subtotal + tax_amount - invoice.discount_amount

        # Update invoice
        invoice.subtotal = subtotal
        invoice.tax_amount = tax_amount
        invoice.total_amount = total_amount

        db.commit()
        db.refresh(invoice)
        return invoice

    def mark_as_sent(self, db: Session, invoice_id: UUID) -> Invoice:
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if invoice:
            invoice.status = InvoiceStatus.SENT
            invoice.sent_date = datetime.now()
            db.commit()
            db.refresh(invoice)
        return invoice

    def mark_as_paid(self, db: Session, invoice_id: UUID) -> Invoice:
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if invoice:
            invoice.status = InvoiceStatus.PAID
            invoice.paid_date = datetime.now()
            db.commit()
            db.refresh(invoice)
        return invoice


class CRUDInvoiceItem:
    def get(self, db: Session, id: UUID) -> Optional[InvoiceItem]:
        return db.query(InvoiceItem).filter(InvoiceItem.id == id).first()

    def get_by_invoice(self, db: Session, invoice_id: UUID) -> List[InvoiceItem]:
        return db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).all()

    def create(self, db: Session, obj_in: InvoiceItemCreate, invoice_id: UUID) -> InvoiceItem:
        line_total = obj_in.quantity * obj_in.unit_price
        db_obj = InvoiceItem(
            invoice_id=invoice_id,
            line_total=line_total,
            **obj_in.dict()
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: InvoiceItem, obj_in: dict) -> InvoiceItem:
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        
        # Recalculate line total
        db_obj.line_total = db_obj.quantity * db_obj.unit_price
        
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: UUID) -> bool:
        obj = db.query(InvoiceItem).filter(InvoiceItem.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()
            return True
        return False


class CRUDInvoicePayment:
    def get(self, db: Session, id: UUID) -> Optional[InvoicePayment]:
        return db.query(InvoicePayment).filter(InvoicePayment.id == id).first()

    def get_by_invoice(self, db: Session, invoice_id: UUID) -> List[InvoicePayment]:
        return db.query(InvoicePayment).filter(InvoicePayment.invoice_id == invoice_id).all()

    def create(self, db: Session, obj_in: InvoicePaymentCreate) -> InvoicePayment:
        db_obj = InvoicePayment(**obj_in.dict())
        db.add(db_obj)
        
        # Update invoice paid amount
        invoice = db.query(Invoice).filter(Invoice.id == obj_in.invoice_id).first()
        if invoice:
            invoice.paid_amount += obj_in.amount
            
            # Check if invoice is fully paid
            if invoice.paid_amount >= invoice.total_amount:
                invoice.status = InvoiceStatus.PAID
                invoice.paid_date = datetime.now()
        
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: UUID) -> bool:
        payment = db.query(InvoicePayment).filter(InvoicePayment.id == id).first()
        if payment:
            # Update invoice paid amount
            invoice = db.query(Invoice).filter(Invoice.id == payment.invoice_id).first()
            if invoice:
                invoice.paid_amount -= payment.amount
                
                # Update invoice status if needed
                if invoice.paid_amount < invoice.total_amount and invoice.status == InvoiceStatus.PAID:
                    invoice.status = InvoiceStatus.SENT
                    invoice.paid_date = None
            
            db.delete(payment)
            db.commit()
            return True
        return False


class CRUDBusinessAccount:
    def get(self, db: Session, id: UUID) -> Optional[BusinessAccount]:
        return db.query(BusinessAccount).filter(BusinessAccount.id == id).first()

    def get_by_business(self, db: Session, business_entity_id: UUID) -> List[BusinessAccount]:
        return db.query(BusinessAccount).filter(
            BusinessAccount.business_entity_id == business_entity_id
        ).all()

    def create(self, db: Session, obj_in: BusinessAccountCreate) -> BusinessAccount:
        db_obj = BusinessAccount(**obj_in.dict())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: UUID) -> bool:
        obj = db.query(BusinessAccount).filter(BusinessAccount.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()
            return True
        return False


class CRUDBusinessExpenseCategory:
    def get(self, db: Session, id: UUID) -> Optional[BusinessExpenseCategory]:
        return db.query(BusinessExpenseCategory).filter(BusinessExpenseCategory.id == id).first()

    def get_by_business(self, db: Session, business_entity_id: UUID) -> List[BusinessExpenseCategory]:
        return db.query(BusinessExpenseCategory).filter(
            BusinessExpenseCategory.business_entity_id == business_entity_id
        ).all()

    def create(self, db: Session, obj_in: BusinessExpenseCategoryCreate) -> BusinessExpenseCategory:
        db_obj = BusinessExpenseCategory(**obj_in.dict())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: UUID) -> bool:
        obj = db.query(BusinessExpenseCategory).filter(BusinessExpenseCategory.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()
            return True
        return False


# Create instances
business_entity = CRUDBusinessEntity()
client = CRUDClient()
invoice = CRUDInvoice()
invoice_item = CRUDInvoiceItem()
invoice_payment = CRUDInvoicePayment()
business_account = CRUDBusinessAccount()
business_expense_category = CRUDBusinessExpenseCategory()