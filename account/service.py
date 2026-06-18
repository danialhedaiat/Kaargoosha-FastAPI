import datetime
import json
import traceback

from core.database import SessionLocal, get_db
from core.settings import logger
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