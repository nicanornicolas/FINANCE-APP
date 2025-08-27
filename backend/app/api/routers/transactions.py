from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from ...models.transaction import Transaction
from ...db.database import get_db
from ...services.importer import parse_csv_to_transactions
from ...crud.transactions import create_many, list_all, update_one, delete_one
from ...schemas.error import ErrorResponse, ErrorDetail
from datetime import datetime, timezone

router = APIRouter()


def err(code: str, message: str, details: dict | None = None):
    return ErrorResponse(error=ErrorDetail(code=code, message=message, details=details, timestamp=datetime.now(timezone.utc)))


@router.get("/", response_model=List[Transaction])
async def list_transactions(q: Optional[str] = None, limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    return list_all(db, q=q, limit=limit, offset=offset)


@router.post("/import", response_model=List[Transaction], responses={400: {"model": ErrorResponse}})
async def import_transactions(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    try:
        txs = parse_csv_to_transactions(content, filename=file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=err("VALIDATION_ERROR", str(e)).model_dump())
    created = create_many(db, txs)
    return created


@router.put("/{tx_id}", response_model=Transaction, responses={404: {"model": ErrorResponse}})
async def update_transaction(tx_id: int, payload: Transaction, db: Session = Depends(get_db)):
    updated = update_one(db, tx_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail=err("NOT_FOUND", "Transaction not found").model_dump())
    return updated


@router.delete("/{tx_id}", responses={404: {"model": ErrorResponse}})
async def delete_transaction(tx_id: int, db: Session = Depends(get_db)):
    ok = delete_one(db, tx_id)
    if not ok:
        raise HTTPException(status_code=404, detail=err("NOT_FOUND", "Transaction not found").model_dump())
    return {"deleted": True, "id": tx_id}


@router.post("/bulk-update")
async def bulk_update(transactions: List[Transaction], db: Session = Depends(get_db)):
    updated = 0
    for t in transactions:
        if t.id is None:
            continue
        if update_one(db, t.id, t):
            updated += 1
    return {"updated": updated}

