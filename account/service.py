import datetime
import json
import os
import traceback

from core.database import SessionLocal, get_db
from core.settings import logger, settings
from core.utilities import since_from_range, save_receipt_proof
from account.models import (
    Account, AccountSetting, Transaction,
    TransactionDirection, TransactionType, Receipt, ReceiptType, ReceiptStatus,
)
from account.schema import AccountResponseSchema
from user_management.models import UserBankInfo
from user_management.permissions import permission, Permissions


class AccountService:

    def __init__(self, db: SessionLocal = None):
        self.db: SessionLocal = db or get_db()

    def credit(self, user_id: int, amount: int):
        account = self.db.query(Account).filter_by(user_id=user_id).first()
        if not account:
            account = Account(user_id=user_id, balance=0)
            self.db.add(account)
            self.db.flush()
        account.balance = int(account.balance) + amount

    def debit(self, user_id: int, amount: int):
        account = self.db.query(Account).filter_by(user_id=user_id).first()
        if not account:
            raise ValueError(f"Account not found for user_id={user_id}")
        account.balance = int(account.balance) - amount

    def get_loan_threshold(self) -> int:
        setting = self.db.query(AccountSetting).first()
        return setting.loan_balance_threshold if setting else 0

    def set_threshold(self, data: dict):
        try:
            threshold = int(data["threshold"])
            setting = self.db.query(AccountSetting).first()
            if setting:
                setting.loan_balance_threshold = threshold
            else:
                self.db.add(AccountSetting(loan_balance_threshold=threshold))
            self.db.commit()
            return json.dumps({"threshold": threshold})
        except Exception as e:
            self.db.rollback()
            logger.error(traceback.format_exc())
            logger.error(e)
            return json.dumps({"error": str(e)})

    def get_balance(self, data: dict):
        account = self.db.query(Account).filter_by(user_id=data["user_id"]).first()
        if not account:
            return json.dumps({"error": "Account not found"})
        return AccountResponseSchema.model_validate(account).model_dump_json()

    @permission(Permissions.ACCOUNT_CLOSE)
    def close(self, data: dict):
        """Admin-initiated account closure. Settles outstanding installment debt
        from the wallet, pays out the remaining balance out-of-band (book entry
        only), decreases the fund pool by the net payout, and soft-closes the
        account. All movements happen atomically in one transaction."""
        try:
            user_id = data["user_id"]
            admin_id = data["requested_by"]

            account = self.db.query(Account).filter_by(user_id=user_id).first()
            if not account:
                return json.dumps({"error": "Account not found"})
            if not account.is_active:
                return json.dumps({"error": "Account is already closed"})

            from loan.models import Loan, LoanStatus, Installment, InstallmentStatus, FundPool

            # A pending loan request must be resolved before closing.
            pending_loan = self.db.query(Loan).filter(
                Loan.user_id == user_id,
                Loan.status == LoanStatus.pending,
            ).first()
            if pending_loan:
                return json.dumps({"error": "pending loan request must be resolved before closing"})

            balance = int(account.balance)

            unpaid = (
                self.db.query(Installment)
                .join(Loan, Installment.loan_id == Loan.id)
                .filter(Loan.user_id == user_id, Installment.status == InstallmentStatus.pending)
                .all()
            )
            debt = sum(i.amount for i in unpaid)

            # Not enough in the wallet to cover the outstanding debt.
            if debt > balance:
                return json.dumps({"error": "must settle remaining debt before closing"})

            fund_pool = self.db.query(FundPool).first()
            if not fund_pool:
                fund_pool = FundPool(balance=0)
                self.db.add(fund_pool)
                self.db.flush()

            # Settle outstanding installments from the wallet (repayment in -> pool up).
            for installment in unpaid:
                installment.status = InstallmentStatus.paid
                installment.paid_at = datetime.datetime.now()
                self.db.add(Transaction(
                    user_id=user_id,
                    amount=installment.amount,
                    direction=TransactionDirection.debit,
                    type=TransactionType.installment_payment,
                    reference_type="installment",
                    reference_id=installment.id,
                ))
            fund_pool.balance = int(fund_pool.balance) + debt

            # Any loan whose installments are now all paid is marked paid.
            for loan_id in {i.loan_id for i in unpaid}:
                remaining = self.db.query(Installment).filter(
                    Installment.loan_id == loan_id,
                    Installment.status == InstallmentStatus.pending,
                ).count()
                if remaining == 0:
                    loan = self.db.query(Loan).filter_by(id=loan_id).first()
                    if loan:
                        loan.status = LoanStatus.paid

            # Pay out the remainder out-of-band; fund pool must cover it.
            remainder = balance - debt
            if remainder > 0:
                if int(fund_pool.balance) < remainder:
                    self.db.rollback()
                    return json.dumps({"error": "insufficient fund pool"})
                fund_pool.balance = int(fund_pool.balance) - remainder
                self.db.add(Transaction(
                    user_id=user_id,
                    amount=remainder,
                    direction=TransactionDirection.debit,
                    type=TransactionType.account_close,
                    reference_type="account_close",
                    reference_id=account.id,
                ))

            account.balance = 0
            account.is_active = False
            account.closed_at = datetime.datetime.now()
            account.closed_by = admin_id

            self.db.commit()
            return json.dumps({
                "user_id": user_id,
                "is_active": account.is_active,
                "settled_debt": debt,
                "paid_out": remainder,
            })

        except Exception as e:
            self.db.rollback()
            logger.error(traceback.format_exc())
            logger.error(e)
            return json.dumps({"error": str(e)})


class BankInfoService:

    def __init__(self):
        self.db: SessionLocal = get_db()

    def save(self, data: dict):
        try:
            user_id = data["user_id"]
            field = data["field"]
            value = data["value"]

            if field not in ("card_number", "iban_number"):
                return json.dumps({"error": "Invalid field"})

            row = self.db.query(UserBankInfo).filter_by(user_id=user_id).first()
            if row:
                setattr(row, field, value)
            else:
                row = UserBankInfo(user_id=user_id, **{field: value})
                self.db.add(row)

            self.db.commit()
            return json.dumps({"status": True})

        except Exception as e:
            self.db.rollback()
            logger.error(traceback.format_exc())
            logger.error(e)
            return json.dumps({"error": str(e)})

    def get(self, data: dict):
        try:
            row = self.db.query(UserBankInfo).filter_by(user_id=data["user_id"]).first()
            if not row:
                return json.dumps({"error": "not found"})
            return json.dumps({
                "card_number": row.card_number,
                "iban_number": row.iban_number,
            })
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)
            return json.dumps({"error": str(e)})


class ReceiptService:
    """Unified service for client receipts (deposit / installment payment / future types).

    A receipt is the mutable request/slip. On approval the money effect is applied and a
    single immutable ledger Transaction is posted referencing the receipt.
    """

    def __init__(self):
        self.db: SessionLocal = get_db()

    def create(self, data: dict):
        try:
            user_id = data["user_id"]
            receipt_type = data["type"]
            proof_type = data["proof_type"]

            account = self.db.query(Account).filter_by(user_id=user_id).first()
            if account and not account.is_active:
                return json.dumps({"error": "account is closed"})

            if proof_type == "photo":
                proof_bytes = data.get("proof_bytes")
                if not proof_bytes:
                    return json.dumps({"error": "proof_bytes required for photo proof"})
                proof_path = save_receipt_proof(proof_bytes, data.get("proof_ext", "jpg"))
                proof_text = None
            else:
                proof_text = data.get("proof_text")
                proof_path = None

            reference_type = reference_id = None

            if receipt_type == ReceiptType.installment_payment.value:
                from loan.models import Installment, InstallmentStatus
                installment = self.db.query(Installment).filter_by(id=data["installment_id"]).first()
                if not installment:
                    return json.dumps({"error": "Installment not found"})
                if installment.loan.user_id != user_id:
                    return json.dumps({"error": "Installment does not belong to user"})
                if installment.status != InstallmentStatus.pending:
                    return json.dumps({"error": f"Installment is already {installment.status.value}"})
                amount = installment.amount
                reference_type, reference_id = "installment", installment.id
            else:
                amount = int(data["amount"])

            receipt = Receipt(
                user_id=user_id,
                type=ReceiptType(receipt_type),
                amount=amount,
                proof_type=proof_type,
                proof_path=proof_path,
                proof_text=proof_text,
                status=ReceiptStatus.pending,
                reference_type=reference_type,
                reference_id=reference_id,
            )
            self.db.add(receipt)
            self.db.commit()
            self.db.refresh(receipt)
            return json.dumps({"id": receipt.id, "status": receipt.status.value})

        except Exception as e:
            self.db.rollback()
            logger.error(traceback.format_exc())
            logger.error(e)
            return json.dumps({"error": str(e)})

    @permission(Permissions.LOAN_APPROVE)
    def approve(self, data: dict):
        try:
            receipt = self.db.query(Receipt).filter_by(id=data["receipt_id"]).first()
            if not receipt:
                return json.dumps({"error": "Receipt not found"})
            if receipt.status != ReceiptStatus.pending:
                return json.dumps({"error": f"Receipt is already {receipt.status.value}"})

            if receipt.type == ReceiptType.deposit:
                AccountService(db=self.db).credit(receipt.user_id, receipt.amount)
                direction = TransactionDirection.credit
                tx_type = TransactionType.deposit
            else:  # installment_payment
                from loan.models import Installment, InstallmentStatus
                installment = self.db.query(Installment).filter_by(id=receipt.reference_id).first()
                if not installment:
                    return json.dumps({"error": "Installment not found"})
                if installment.status != InstallmentStatus.pending:
                    return json.dumps({"error": f"Installment is already {installment.status.value}"})
                installment.status = InstallmentStatus.paid
                installment.paid_at = datetime.datetime.now()
                AccountService(db=self.db).debit(receipt.user_id, receipt.amount)
                direction = TransactionDirection.debit
                tx_type = TransactionType.installment_payment

            # Money in (deposit or installment payment) tops up the shared fund pool.
            from loan.models import FundPool
            fund_pool = self.db.query(FundPool).first()
            if not fund_pool:
                fund_pool = FundPool(balance=0)
                self.db.add(fund_pool)
                self.db.flush()
            fund_pool.balance = int(fund_pool.balance) + receipt.amount

            self.db.add(Transaction(
                user_id=receipt.user_id,
                amount=receipt.amount,
                direction=direction,
                type=tx_type,
                reference_type="receipt",
                reference_id=receipt.id,
            ))

            receipt.status = ReceiptStatus.approved
            receipt.reviewed_by = data["requested_by"]
            receipt.reviewed_at = datetime.datetime.now()

            self.db.commit()
            return json.dumps({"id": receipt.id, "status": receipt.status.value})

        except Exception as e:
            self.db.rollback()
            logger.error(traceback.format_exc())
            logger.error(e)
            return json.dumps({"error": str(e)})

    @permission(Permissions.LOAN_APPROVE)
    def reject(self, data: dict):
        try:
            receipt = self.db.query(Receipt).filter_by(id=data["receipt_id"]).first()
            if not receipt:
                return json.dumps({"error": "Receipt not found"})
            if receipt.status != ReceiptStatus.pending:
                return json.dumps({"error": f"Receipt is already {receipt.status.value}"})

            receipt.status = ReceiptStatus.rejected
            receipt.rejection_reason = data.get("rejection_reason")
            receipt.reviewed_by = data["requested_by"]
            receipt.reviewed_at = datetime.datetime.now()

            self.db.commit()
            return json.dumps({"id": receipt.id, "status": receipt.status.value})

        except Exception as e:
            self.db.rollback()
            logger.error(traceback.format_exc())
            logger.error(e)
            return json.dumps({"error": str(e)})

    @permission(Permissions.TRANSACTION_READ)
    def list(self, data: dict):
        try:
            r_type = data.get("type")
            status = data.get("status", "all")
            since = since_from_range(data.get("range"))

            query = self.db.query(Receipt)
            if r_type and r_type != "all":
                query = query.filter(Receipt.type == ReceiptType(r_type))
            if status and status != "all":
                query = query.filter(Receipt.status == ReceiptStatus(status))
            if since is not None:
                query = query.filter(Receipt.created_at >= since)

            rows = query.order_by(Receipt.created_at.desc()).limit(50).all()
            return json.dumps([
                {
                    "id": r.id,
                    "user_id": r.user_id,
                    "first_name": r.user.first_name if r.user else "",
                    "last_name": r.user.last_name if r.user else "",
                    "type": r.type.value,
                    "amount": r.amount,
                    "status": r.status.value,
                    "proof_type": r.proof_type,
                    "proof_path": r.proof_path,
                    "proof_text": r.proof_text,
                    "reference_type": r.reference_type,
                    "reference_id": r.reference_id,
                    "created_at": str(r.created_at),
                }
                for r in rows
            ])

        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)
            return json.dumps({"error": str(e)})

    def list_mine(self, data: dict):
        """Ownership-scoped receipt list for the client self-service menu.

        No permission gate: returns only the caller's own receipts (the bot derives
        user_id from the authenticated member, never from client input)."""
        try:
            user_id = data["user_id"]
            rows = (
                self.db.query(Receipt)
                .filter(Receipt.user_id == user_id)
                .order_by(Receipt.created_at.desc())
                .limit(50)
                .all()
            )
            return json.dumps([
                {
                    "id": r.id,
                    "type": r.type.value,
                    "amount": r.amount,
                    "status": r.status.value,
                    "proof_type": r.proof_type,
                    "proof_text": r.proof_text,
                    "reference_type": r.reference_type,
                    "reference_id": r.reference_id,
                    "rejection_reason": r.rejection_reason,
                    "created_at": str(r.created_at),
                }
                for r in rows
            ])

        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)
            return json.dumps({"error": str(e)})

    @permission(Permissions.TRANSACTION_READ)
    def get_proof(self, data: dict):
        """Return a receipt's proof for the admin to view: raw image bytes for photo
        proofs (read from the media dir) or the inline text. Bytes travel over RabbitMQ
        (msgpack) so the bot can re-send the actual photo to Bale."""
        try:
            receipt = self.db.query(Receipt).filter_by(id=data["receipt_id"]).first()
            if not receipt:
                return {"error": "Receipt not found"}

            if receipt.proof_type == "photo" and receipt.proof_path:
                path = os.path.join(settings.MEDIA_ROOT, receipt.proof_path)
                if not os.path.exists(path):
                    return {"error": "Proof file not found"}
                with open(path, "rb") as f:
                    content = f.read()
                ext = receipt.proof_path.rsplit(".", 1)[-1] if "." in receipt.proof_path else "jpg"
                return {"proof_type": "photo", "proof_bytes": content, "ext": ext}

            return {"proof_type": receipt.proof_type, "proof_text": receipt.proof_text}

        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)
            return {"error": str(e)}


class TransactionService:
    """Read access to the immutable ledger for the client self-service menu."""

    def __init__(self):
        self.db: SessionLocal = get_db()

    def list_mine(self, data: dict):
        """Ownership-scoped ledger list. No permission gate: returns only the
        caller's own transactions (the bot derives user_id from the authenticated
        member, never from client input)."""
        try:
            user_id = data["user_id"]
            rows = (
                self.db.query(Transaction)
                .filter(Transaction.user_id == user_id)
                .order_by(Transaction.created_at.desc())
                .limit(50)
                .all()
            )
            return json.dumps([
                {
                    "id": t.id,
                    "amount": t.amount,
                    "direction": t.direction.value,
                    "type": t.type.value,
                    "reference_type": t.reference_type,
                    "reference_id": t.reference_id,
                    "created_at": str(t.created_at),
                }
                for t in rows
            ])

        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)
            return json.dumps({"error": str(e)})