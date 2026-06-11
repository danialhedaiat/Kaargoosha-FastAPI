from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from loan.models import LoanStatus


class LoanCreateSchema(BaseModel):
    user_id: int
    amount: Decimal = Field(..., gt=0)
    duration_months: int = Field(..., gt=0)
    monthly_amount: Decimal = Field(..., gt=0)


class LoanResponseSchema(BaseModel):
    id: int
    user_id: int
    amount: Decimal
    duration_months: int
    monthly_amount: Decimal
    status: LoanStatus
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True