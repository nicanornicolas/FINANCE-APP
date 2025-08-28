"""
Business API router for business entities, clients, invoices, and reporting
"""
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ...api.dependencies import get_db, get_current_user
from ...models.user import User
from ...models.business import BusinessEntity, Client, Invoice
from ...crud.business import (
    business_entity, client, invoice, invoice_item, invoice_payment
)
from ...services.business_service import business_service
from ...schemas.business import (
    BusinessEntity as BusinessEntitySchema,
    BusinessEntityCreate,
    BusinessEntityUpdate,
    Client as ClientSchema,
    ClientCreate,
    ClientUpdate,
    Invoice as InvoiceSchema,
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceItemCreate,
    InvoicePaymentCreate,
    BusinessSummary,
    ProfitLossReport,
    CashFlowReport,
)

router = APIRouter()


# Business Entity Endpoints
@router.post("/entities", response_model=BusinessEntitySchema)
def create_business_entity(
    entity_in: BusinessEntityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new business entity"""
    return business_entity.create(db=db, obj_in=entity_in, user_id=current_user.id)


@router.get("/entities", response_model=List[BusinessEntitySchema])
def get_business_entities(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all business entities for the current user"""
    return business_entity.get_by_user(db=db, user_id=current_user.id)


@router.get("/entities/{entity_id}", response_model=BusinessEntitySchema)
def get_business_entity(
    entity_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific business entity"""
    entity = business_entity.get(db=db, id=entity_id)
    if not entity or entity.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business entity not found"
        )
    return entity


@router.put("/entities/{entity_id}", response_model=BusinessEntitySchema)
def update_business_entity(
    entity_id: UUID,
    entity_in: BusinessEntityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a business entity"""
    entity = business_entity.get(db=db, id=entity_id)
    if not entity or entity.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business entity not found"
        )
    return business_entity.update(db=db, db_obj=entity, obj_in=entity_in)


@router.delete("/entities/{entity_id}", response_model=BusinessEntitySchema)
def delete_business_entity(
    entity_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete (deactivate) a business entity"""
    entity = business_entity.get(db=db, id=entity_id)
    if not entity or entity.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business entity not found"
        )
    return business_entity.delete(db=db, id=entity_id)


# Client Endpoints
@router.post("/entities/{entity_id}/clients", response_model=ClientSchema)
def create_client(
    entity_id: UUID,
    client_in: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new client for a business entity"""
    entity = business_entity.get(db=db, id=entity_id)
    if not entity or entity.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business entity not found"
        )
    
    client_in.business_entity_id = entity_id
    return client.create(db=db, obj_in=client_in)


@router.get("/entities/{entity_id}/clients", response_model=List[ClientSchema])
def get_clients(
    entity_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all clients for a business entity"""
    entity = business_entity.get(db=db, id=entity_id)
    if not entity or entity.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business entity not found"
        )
    return client.get_by_business(db=db, business_entity_id=entity_id)


@router.get("/clients/{client_id}", response_model=ClientSchema)
def get_client(
    client_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific client"""
    client_obj = client.get(db=db, id=client_id)
    if not client_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    # Check if user owns the business entity
    entity = business_entity.get(db=db, id=client_obj.business_entity_id)
    if not entity or entity.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    return client_obj


@router.put("/clients/{client_id}", response_model=ClientSchema)
def update_client(
    client_id: UUID,
    client_in: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a client"""
    client_obj = client.get(db=db, id=client_id)
    if not client_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    # Check if user owns the business entity
    entity = business_entity.get(db=db, id=client_obj.business_entity_id)
    if not entity or entity.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    return client.update(db=db, db_obj=client_obj, obj_in=client_in)


@router.delete("/clients/{client_id}", response_model=ClientSchema)
def delete_client(
    client_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete (deactivate) a client"""
    client_obj = client.get(db=db, id=client_id)
    if not client_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    # Check if user owns the business entity
    entity = business_entity.get(db=db, id=client_obj.business_entity_id)
    if not entity or entity.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    return client.delete(db=db, id=client_id)


# Invoice Endpoints
@router.post("/entities/{entity_id}/invoices", response_model=InvoiceSchema)
def create_invoice(
    entity_id: UUID,
    invoice_in: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new invoice"""
    entity = business_entity.get(db=db, id=entity_id)
    if not entity or entity.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business entity not found"
        )
    
    # Verify client belongs to this business entity
    client_obj = client.get(db=db, id=invoice_in.client_id)
    if not client_obj or client_obj.business_entity_id != entity_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client does not belong to this business entity"
        )
    
    invoice_in.business_entity_id = entity_id
    return invoice.create(db=db, obj_in=invoice_in)


@router.get("/entities/{entity_id}/invoices", response_model=List[InvoiceSchema])
def get_invoices(
    entity_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all invoices for a business entity"""
    entity = business_entity.get(db=db, id=entity_id)
    if not entity or entity.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business entity not found"
        )
    return invoice.get_by_business(db=db, business_entity_id=entity_id, skip=skip, limit=limit)


@router.get("/invoices/{invoice_id}", response_model=InvoiceSchema)
def get_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific invoice"""
    invoice_obj = invoice.get(db=db, id=invoice_id)
    if not invoice_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Check if user owns the business entity
    entity = business_entity.get(db=db, id=invoice_obj.business_entity_id)
    if not entity or entity.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    return invoice_obj


@router.put("/invoices/{invoice_id}", response_model=InvoiceSchema)
def update_invoice(
    invoice_id: UUID,
    invoice_in: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an invoice"""
    invoice_obj = invoice.get(db=db, id=invoice_id)
    if not invoice_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Check if user owns the business entity
    entity = business_entity.get(db=db, id=invoice_obj.business_entity_id)
    if not entity or entity.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    return invoice.update(db=db, db_obj=invoice_obj, obj_in=invoice_in)


@router.post("/invoices/{invoice_id}/send", response_model=InvoiceSchema)
def send_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark invoice as sent"""
    invoice_obj = invoice.get(db=db, id=invoice_id)
    if not invoice_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Check if user owns the business entity
    entity = business_entity.get(db=db, id=invoice_obj.business_entity_id)
    if not entity or entity.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    return invoice.mark_as_sent(db=db, invoice_id=invoice_id)


@router.post("/invoices/{invoice_id}/payments")
def add_invoice_payment(
    invoice_id: UUID,
    payment_in: InvoicePaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a payment to an invoice"""
    invoice_obj = invoice.get(db=db, id=invoice_id)
    if not invoice_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Check if user owns the business entity
    entity = business_entity.get(db=db, id=invoice_obj.business_entity_id)
    if not entity or entity.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    payment_in.invoice_id = invoice_id
    return invoice_payment.create(db=db, obj_in=payment_in)


# Business Reporting Endpoints
@router.get("/entities/{entity_id}/summary", response_model=BusinessSummary)
def get_business_summary(
    entity_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get business summary statistics"""
    entity = business_entity.get(db=db, id=entity_id)
    if not entity or entity.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business entity not found"
        )
    
    return business_service.get_business_summary(db=db, business_entity_id=entity_id)


@router.get("/entities/{entity_id}/reports/profit-loss", response_model=ProfitLossReport)
def get_profit_loss_report(
    entity_id: UUID,
    start_date: date = Query(..., description="Start date for the report"),
    end_date: date = Query(..., description="End date for the report"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate profit and loss report"""
    entity = business_entity.get(db=db, id=entity_id)
    if not entity or entity.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business entity not found"
        )
    
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before end date"
        )
    
    return business_service.generate_profit_loss_report(
        db=db, business_entity_id=entity_id, start_date=start_date, end_date=end_date
    )


@router.get("/entities/{entity_id}/reports/cash-flow", response_model=CashFlowReport)
def get_cash_flow_report(
    entity_id: UUID,
    start_date: date = Query(..., description="Start date for the report"),
    end_date: date = Query(..., description="End date for the report"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate cash flow report"""
    entity = business_entity.get(db=db, id=entity_id)
    if not entity or entity.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business entity not found"
        )
    
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before end date"
        )
    
    return business_service.generate_cash_flow_report(
        db=db, business_entity_id=entity_id, start_date=start_date, end_date=end_date
    )


@router.get("/entities/{entity_id}/analytics/invoices")
def get_invoice_analytics(
    entity_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get invoice analytics and metrics"""
    entity = business_entity.get(db=db, id=entity_id)
    if not entity or entity.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business entity not found"
        )
    
    return business_service.get_invoice_analytics(db=db, business_entity_id=entity_id)


@router.post("/entities/{entity_id}/expenses/separate")
def separate_business_expenses(
    entity_id: UUID,
    transaction_ids: List[UUID],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark transactions as business expenses for separation"""
    entity = business_entity.get(db=db, id=entity_id)
    if not entity or entity.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business entity not found"
        )
    
    return business_service.separate_business_expenses(
        db=db, business_entity_id=entity_id, transaction_ids=transaction_ids
    )