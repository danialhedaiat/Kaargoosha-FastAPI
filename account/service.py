import datetime
import json
import traceback

from core.database import SessionLocal, get_db
from core.settings import logger
from account.models import Account, DepositRequest, DepositStatus, Transaction, TransactionDirection, TransactionType
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


class DepositService:

    def __init__(self):
        self.db: SessionLocal = get_db()

    def create(self, data: dict):
        try:
            user_id = data["user_id"]
            amount = int(data["amount"])
            proof_type = data["proof_type"]
            proof_content = data["proof_content"]

            deposit = DepositRequest(
                user_id=user_id,
                amount=amount,
                proof_type=proof_type,
                proof_content=proof_content,
                status=DepositStatus.pending,
            )
            self.db.add(deposit)
            self.db.commit()
            self.db.refresh(deposit)

            self._notify_admins(deposit)

            return json.dumps({"id": deposit.id, "status": deposit.status.value})

        except Exception as e:
            self.db.rollback()
            logger.error(traceback.format_exc())
            logger.error(e)
            return json.dumps({"error": str(e)})

    def _notify_admins(self, deposit):
        try:
            from user_management.models import UserModel, UserSocialMediaID, UserRole, RolePermission
            from core.notification_publisher import NotificationPublisher

            rows = (
                self.db.query(UserSocialMediaID.chat_id, UserSocialMediaID.social_media)
                .join(UserModel, UserSocialMediaID.user_id == UserModel.id)
                .join(UserRole, UserModel.id == UserRole.user_id)
                .join(RolePermission, UserRole.role_id == RolePermission.role_id)
                .filter(
                    RolePermission.codename == Permissions.LOAN_APPROVE,
                    UserSocialMediaID.chat_id.isnot(None),
                )
                .distinct()
                .all()
            )

            recipients = [{"chat_id": row[0], "social_media": row[1]} for row in rows]
            if not recipients:
                return

            user = self.db.query(UserModel).filter_by(id=deposit.user_id).first()
            NotificationPublisher().notify_deposit_request(
                deposit_id=deposit.id,
                user_id=deposit.user_id,
                first_name=user.first_name if user else "",
                last_name=user.last_name if user else "",
                amount=deposit.amount,
                proof_type=deposit.proof_type,
                proof_content=deposit.proof_content,
                recipients=recipients,
            )
        except Exception:
            logger.error(traceback.format_exc())

    @permission(Permissions.LOAN_APPROVE)
    def approve(self, data: dict):
        try:
            deposit_id = data["deposit_id"]

            deposit = self.db.query(DepositRequest).filter_by(id=deposit_id).first()
            if not deposit:
                return json.dumps({"error": "Deposit request not found"})

            if deposit.status != DepositStatus.pending:
                return json.dumps({"error": f"Deposit is already {deposit.status.value}"})

            AccountService(db=self.db).credit(deposit.user_id, deposit.amount)

            self.db.add(Transaction(
                user_id=deposit.user_id,
                amount=deposit.amount,
                direction=TransactionDirection.credit,
                type=TransactionType.deposit,
                reference_type="deposit",
                reference_id=deposit.id,
            ))

            deposit.status = DepositStatus.approved
            deposit.approved_by = data["requested_by"]
            deposit.approved_at = datetime.datetime.now()

            self.db.commit()
            return json.dumps({"id": deposit.id, "status": deposit.status.value})

        except Exception as e:
            self.db.rollback()
            logger.error(traceback.format_exc())
            logger.error(e)
            return json.dumps({"error": str(e)})

    @permission(Permissions.LOAN_APPROVE)
    def reject(self, data: dict):
        try:
            deposit_id = data["deposit_id"]
            rejection_reason = data.get("rejection_reason")

            deposit = self.db.query(DepositRequest).filter_by(id=deposit_id).first()
            if not deposit:
                return json.dumps({"error": "Deposit request not found"})

            if deposit.status != DepositStatus.pending:
                return json.dumps({"error": f"Deposit is already {deposit.status.value}"})

            deposit.status = DepositStatus.rejected
            deposit.rejection_reason = rejection_reason

            self.db.commit()
            return json.dumps({"id": deposit.id, "status": deposit.status.value})

        except Exception as e:
            self.db.rollback()
            logger.error(traceback.format_exc())
            logger.error(e)
            return json.dumps({"error": str(e)})