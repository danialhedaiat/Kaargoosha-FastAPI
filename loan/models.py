import datetime
import enum

from sqlalchemy import Integer, String, Numeric, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column

from core.database import Base


class LoanStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    duration_months: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    status: Mapped[LoanStatus] = mapped_column(Enum(LoanStatus), nullable=False, default=LoanStatus.pending)
    approved_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.now)

    user = relationship("UserModel", foreign_keys=[user_id], backref="loans")
    approver = relationship("UserModel", foreign_keys=[approved_by])


class FundPool(Base):
    __tablename__ = "fund_pool"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    balance: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)
