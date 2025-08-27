from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from ...db.database import get_db
from ...crud import transaction as crud_transaction
from ...schemas.transaction import (
    Transaction, 
    TransactionCreate, 
    TransactionUpdate,
    TransactionListResponse
)
from ...models.user import User as UserModel
from ..routers.auth import get_current_user

router = APIRouter()


@router.get("/", response_model=TransactionListResponse)
async def get_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    account_id: Optional[str] = None,
    category_id: Optional[str] = None,
    transaction_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    search: Optional[str] = None,
    is_tax_deductible: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Get transactions with filtering and pagination"""
    filters = {}
    if account_id:
        filters['account_id'] = account_id
    if category_id:
        filters['category_id'] = category_id
    if transaction_type:
        filters['transaction_type'] = transaction_type
    if start_date:
        filters['start_date'] = start_date
    if end_date:
        filters['end_date'] = end_date
    if min_amount is not None:
        filters['min_amount'] = min_amount
    if max_amount is not None:
        filters['max_amount'] = max_amount
    if search:
        filters['search'] = search
    if is_tax_deductible is not None:
        filters['is_tax_deductible'] = is_tax_deductible

    transactions, total = crud_transaction.transaction.get_multi_with_filters(
        db, skip=skip, limit=limit, user_id=current_user.id, filters=filters
    )
    
    pages = (total + limit - 1) // limit
    page = (skip // limit) + 1
    
    return TransactionListResponse(
        transactions=transactions,
        total=total,
        page=page,
        size=limit,
        pages=pages
    )


@router.get("/{transaction_id}", response_model=Transaction)
async def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Get a single transaction"""
    transaction = crud_transaction.transaction.get_by_id_and_user(
        db, id=transaction_id, user_id=current_user.id
    )
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


@router.post("/", response_model=Transaction)
async def create_transaction(
    transaction_in: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Create a new transaction"""
    # Verify account belongs to user
    # TODO: Add account ownership verification
    transaction = crud_transaction.transaction.create_with_user(
        db, obj_in=transaction_in, user_id=current_user.id
    )
    return transaction


@router.put("/{transaction_id}", response_model=Transaction)
async def update_transaction(
    transaction_id: str,
    transaction_in: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Update a transaction"""
    transaction = crud_transaction.transaction.get_by_id_and_user(
        db, id=transaction_id, user_id=current_user.id
    )
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    transaction = crud_transaction.transaction.update(
        db, db_obj=transaction, obj_in=transaction_in
    )
    return transaction


@router.delete("/{transaction_id}")
async def delete_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Delete a transaction"""
    transaction = crud_transaction.transaction.get_by_id_and_user(
        db, id=transaction_id, user_id=current_user.id
    )
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    crud_transaction.transaction.remove(db, id=transaction_id)
    return {"message": "Transaction deleted successfully"}


@router.put("/bulk", response_model=List[Transaction])
async def bulk_update_transactions(
    bulk_data: dict,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Bulk update transactions"""
    transaction_ids = bulk_data.get("transaction_ids", [])
    updates = bulk_data.get("updates", {})
    
    if not transaction_ids:
        raise HTTPException(status_code=400, detail="No transaction IDs provided")
    
    updated_transactions = []
    for transaction_id in transaction_ids:
        transaction = crud_transaction.transaction.get_by_id_and_user(
            db, id=transaction_id, user_id=current_user.id
        )
        if transaction:
            updated_transaction = crud_transaction.transaction.update(
                db, db_obj=transaction, obj_in=updates
            )
            updated_transactions.append(updated_transaction)
    
    return updated_transactions


@router.delete("/bulk")
async def bulk_delete_transactions(
    bulk_data: dict,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Bulk delete transactions"""
    transaction_ids = bulk_data.get("transaction_ids", [])
    
    if not transaction_ids:
        raise HTTPException(status_code=400, detail="No transaction IDs provided")
    
    deleted_count = 0
    for transaction_id in transaction_ids:
        transaction = crud_transaction.transaction.get_by_id_and_user(
            db, id=transaction_id, user_id=current_user.id
        )
        if transaction:
            crud_transaction.transaction.remove(db, id=transaction_id)
            deleted_count += 1
    
    return {"message": f"Deleted {deleted_count} transactions"}


@router.post("/import")
async def import_transactions(
    file: UploadFile = File(...),
    account_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Import transactions from CSV file"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    
    # TODO: Verify account belongs to user
    # TODO: Implement CSV parsing and transaction creation
    # For now, return a mock response
    
    return {
        "imported": 0,
        "duplicates": 0,
        "errors": ["Import functionality not yet implemented"]
    }


@router.get("/search", response_model=TransactionListResponse)
async def search_transactions(
    q: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Search transactions"""
    transactions, total = crud_transaction.transaction.search(
        db, query=q, skip=skip, limit=limit, user_id=current_user.id
    )
    
    pages = (total + limit - 1) // limit
    page = (skip // limit) + 1
    
    return TransactionListResponse(
        transactions=transactions,
        total=total,
        page=page,
        size=limit,
        pages=pages
    )

