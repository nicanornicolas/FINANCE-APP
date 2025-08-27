from pydantic import BaseModel
from typing import Any, Dict, Optional
from datetime import datetime

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime

class ErrorResponse(BaseModel):
    error: ErrorDetail

