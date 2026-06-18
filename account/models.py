import datetime
import enum

from sqlalchemy import Integer, Numeric, DateTime, ForeignKey, String, Enum, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column

from core.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    balance: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    user = relationship("UserModel", backref="account")


class TransactionType(str, enum.Enum):
    deposit = "deposit"
    loan_disbursement = "loan_disbursement"
    installment_payment = "installment_payment"


class TransactionDirection(str, enum.Enum):
    credit = "credit"
    debit = "debit"


class TransactionStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    direction: Mapped[TransactionDirection] = mapped_column(Enum(TransactionDirection), nullable=False)
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    status: Mapped[TransactionStatus] = mapped_column(Enum(TransactionStatus), nullable=False, default=TransactionStatus.pending)
    proof_type: Mapped[str] = mapped_column(String(10), nullable=True)
    proof_content: Mapped[str] = mapped_column(String(500), nullable=True)
    reference_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.now)

    user = relationship("UserModel", foreign_keys=[user_id])


class DepositStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class DepositRequest(Base):
    __tablename__ = "deposit_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    proof_type: Mapped[str] = mapped_column(String(10), nullable=False)
    proof_content: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[DepositStatus] = mapped_column(Enum(DepositStatus), nullable=False, default=DepositStatus.pending)
    approved_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.now)

    user = relationship("UserModel", foreign_keys=[user_id])
    approver = relationship("UserModel", foreign_keys=[approved_by])


class AccountSetting(Base):
    __tablename__ = "account_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    loan_balance_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ReceiptType(str, enum.Enum):
    deposit = "deposit"
    installment_payment = "installment_payment"


class ReceiptStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class Receipt(Base):
    """Mutable request/slip a client submits (with proof) for an admin to review.

    On approval an immutable Transaction (ledger) row is posted from it.
    Replaces the per-type deposit_requests / installment_payment_requests tables.
    """
    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    type: Mapped[ReceiptType] = mapped_column(Enum(ReceiptType), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    proof_type: Mapped[str] = mapped_column(String(10), nullable=False)  # "photo" | "text"
    proof_path: Mapped[str] = mapped_column(String(500), nullable=True)  # media-relative path for photo proofs
    proof_text: Mapped[str] = mapped_column(String(500), nullable=True)  # inline text proofs
    status: Mapped[ReceiptStatus] = mapped_column(Enum(ReceiptStatus), nullable=False, default=ReceiptStatus.pending)
    reviewed_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[str] = mapped_column(String(500), nullable=True)
    reference_type: Mapped[str] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.now)

    user = relationship("UserModel", foreign_keys=[user_id])
    reviewer = relationship("UserModel", foreign_keys=[reviewed_by])

    __table_args__ = (
        Index("ix_receipts_type_status_created", "type", "status", "created_at"),
    )