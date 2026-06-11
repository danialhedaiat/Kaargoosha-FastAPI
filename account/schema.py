from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class AccountResponseSchema(BaseModel):
    id: int
    user_id: int
    balance: Decimal
    updated_at: datetime

    class Config:
        from_attributes = True