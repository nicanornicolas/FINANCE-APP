from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from ...db.database import get_db
from ...crud import account as crud_account
from ...schemas.account import Account, AccountCreate, AccountUpdate
from ...models.user import User as UserModel
from ..routers.auth import get_current_user

router = APIRouter()


@router.get("/", response_model=List[Account])
async def get_accounts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Get user's accounts"""
    accounts = crud_account.account.get_by_user(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    return accounts


@router.get("/{account_id}", response_model=Account)
async def get_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Get a single account"""
    account = crud_account.account.get_by_id_and_user(
        db, id=account_id, user_id=current_user.id
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.post("/", response_model=Account)
async def create_account(
    account_in: AccountCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Create a new account"""
    account = crud_account.account.create_with_user(
        db, obj_in=account_in, user_id=current_user.id
    )
    return account


@router.put("/{account_id}", response_model=Account)
async def update_account(
    account_id: str,
    account_in: AccountUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Update an account"""
    account = crud_account.account.get_by_id_and_user(
        db, id=account_id, user_id=current_user.id
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account = crud_account.account.update(db, db_obj=account, obj_in=account_in)
    return account


@router.delete("/{account_id}")
async def delete_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Delete an account"""
    account = crud_account.account.get_by_id_and_user(
        db, id=account_id, user_id=current_user.id
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    crud_account.account.remove(db, id=account_id)
    return {"message": "Account deleted successfully"}