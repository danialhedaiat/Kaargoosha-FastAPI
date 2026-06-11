from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from loan.models import LoanStatus


class LoanCreateSchema(BaseModel):
    user_id: int
    duration_months: int = Field(..., gt=0)
    member_chat_id: Optional[int] = None


class LoanResponseSchema(BaseModel):
    id: int
    user_id: int
    amount: Optional[int] = None
    duration_months: int
    monthly_amount: Optional[int] = None
    member_chat_id: Optional[int] = None
    status: LoanStatus
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True