from typing import Iterable, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from ..db.models import TransactionORM
from ..models.transaction import Transaction


def _fingerprint(t: Transaction) -> Tuple:
    return (t.date.replace(microsecond=0), t.details.lower().strip(), t.type, round(float(t.amount), 2))


def create_many(db: Session, txs: Iterable[Transaction]) -> List[Transaction]:
    # simple dedupe: avoid inserting duplicates by (date, details, type, amount)
    fps: Set[Tuple] = set()
    for t in txs:
        fps.add(_fingerprint(t))

    existing = db.query(TransactionORM).all()
    existing_fps = {
        (e.date.replace(microsecond=0), e.details.lower().strip(), e.type, round(float(e.amount), 2)) for e in existing
    }

    objs = []
    for t in txs:
        if _fingerprint(t) in existing_fps:
            continue
        obj = TransactionORM(
            date=t.date,
            details=t.details,
            type=t.type,
            amount=t.amount,
            category=t.category,
        )
        objs.append(obj)
    if objs:
        db.add_all(objs)
        db.commit()
        for obj in objs:
            db.refresh(obj)
    return [Transaction(
        id=o.id, date=o.date, details=o.details, type=o.type, amount=float(o.amount), category=o.category
    ) for o in objs]


def list_all(db: Session, q: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Transaction]:
    query = db.query(TransactionORM)
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(TransactionORM.details.ilike(like))
    results = query.order_by(TransactionORM.date.desc()).limit(limit).offset(offset).all()
    return [Transaction(
        id=o.id, date=o.date, details=o.details, type=o.type, amount=float(o.amount), category=o.category
    ) for o in results]


def update_one(db: Session, tx_id: int, payload: Transaction) -> Optional[Transaction]:
    obj = db.get(TransactionORM, tx_id)
    if not obj:
        return None
    obj.date = payload.date
    obj.details = payload.details
    obj.type = payload.type
    obj.amount = payload.amount
    obj.category = payload.category
    db.commit()
    db.refresh(obj)
    return Transaction(
        id=obj.id, date=obj.date, details=obj.details, type=obj.type, amount=float(obj.amount), category=obj.category
    )


def delete_one(db: Session, tx_id: int) -> bool:
    obj = db.get(TransactionORM, tx_id)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True

