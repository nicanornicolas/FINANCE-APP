from io import StringIO, BytesIO
from typing import List, Optional
import re

import pandas as pd

from ..models.transaction import Transaction


REQUIRED_COLUMNS = {"date", "details", "type", "amount"}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    # map common variants
    mapping = {
        "date": "date",
        "transaction date": "date",
        "details": "details",
        "description": "details",
        "narration": "details",
        "type": "type",
        "dr/cr": "type",
        "debit/credit": "type",
        "amount": "amount",
        "debit": "amount",
        "credit": "amount",
    }
    normalized = {c: mapping.get(c, c) for c in df.columns}
    df = df.rename(columns=normalized)
    return df


def infer_from_headerless(df_raw: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Attempt to parse headerless CSVs by inferring columns.
    Heuristics: date = first field parseable as date; amount = last numeric-like field; type inferred from tokens (sales=>credit, purchases=>debit).
    """
    if df_raw.empty:
        return None

    # Treat as no header
    df = df_raw.copy()
    df.columns = [str(i) for i in range(len(df.columns))]

    parsed_rows = []
    for _, row in df.iterrows():
        values = [str(v).strip() for v in row.tolist()]
        # find date
        date_val = None
        date_idx = None
        for i, v in enumerate(values):
            try:
                dt = pd.to_datetime(v, format="mixed", errors="raise")
                date_val = dt
                date_idx = i
                break
            except Exception:
                continue
        # find amount (from end)
        amount_val = None
        amount_idx = None
        for j in range(len(values) - 1, -1, -1):
            s = values[j].replace(",", "")
            s = re.sub(r"[^0-9.()-]", "", s)
            try:
                if s:
                    amt = float(s.replace("(", "-").replace(")", ""))
                    amount_val = amt
                    amount_idx = j
                    break
            except Exception:
                continue
        if date_val is None or amount_val is None:
            # cannot infer
            continue
        # details = join remaining text fields except date/amount
        detail_parts = [values[k] for k in range(len(values)) if k not in (date_idx, amount_idx) and values[k]]
        details = ", ".join([p for p in detail_parts if p])
        token_blob = " ".join(detail_parts).lower()
        tx_type = "credit" if "sales" in token_blob else ("debit" if "purchase" in token_blob or "purchases" in token_blob else "debit")
        parsed_rows.append({
            "date": date_val,
            "details": details or "",
            "type": tx_type,
            "amount": amount_val,
        })

    if not parsed_rows:
        return None
    out_df = pd.DataFrame(parsed_rows, columns=["date", "details", "type", "amount"])
    return out_df


def parse_csv_to_transactions(content: bytes, filename: Optional[str] = None) -> List[Transaction]:
    # Excel support
    if filename and filename.lower().endswith((".xls", ".xlsx")):
        try:
            df = pd.read_excel(BytesIO(content))
            df = normalize_columns(df)
        except Exception as e:
            raise ValueError(f"Failed to read Excel file: {e}")
    else:
        text = content.decode("utf-8", errors="ignore")
        # First try with header
        try:
            df = pd.read_csv(StringIO(text))
            df = normalize_columns(df)
            missing = REQUIRED_COLUMNS - set(df.columns)
            if missing:
                raise ValueError("missing columns")
        except Exception:
            # fallback: headerless inference
            df_raw = pd.read_csv(StringIO(text), header=None)
            df = infer_from_headerless(df_raw)
            if df is None:
                raise ValueError("Could not infer columns from CSV. Please provide a file with headers: date, details, type, amount")

    # Normalize
    df["date"] = pd.to_datetime(df["date"], errors="coerce", format="mixed")
    if df["date"].isna().any():
        raise ValueError("Some dates could not be parsed")

    df["type"] = df["type"].astype(str).str.lower().str.strip()
    # Map common type variants
    df["type"] = df["type"].replace({
        "dr": "debit",
        "debit": "debit",
        "cr": "credit",
        "credit": "credit",
    })

    # Amount: handle commas and parentheses
    def to_amount(x):
        s = str(x).strip()
        if s == "" or s.lower() == "nan":
            return None
        s = s.replace(",", "")
        negative = False
        if s.startswith("(") and s.endswith(")"):
            negative = True
            s = s[1:-1]
        try:
            val = float(s)
            if negative:
                val = -val
            return val
        except Exception:
            return None

    df["amount"] = df["amount"].apply(to_amount)
    if df["amount"].isna().any():
        raise ValueError("Some amounts could not be parsed")

    df["details"] = df["details"].astype(str).str.strip()

    # Build transactions
    txs: List[Transaction] = []
    for _, row in df.iterrows():
        txs.append(Transaction(
            date=row["date"].to_pydatetime(),
            details=row["details"],
            type=row["type"],
            amount=float(row["amount"]),
        ))
    return txs

