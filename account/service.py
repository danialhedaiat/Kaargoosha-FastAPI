import json
import traceback

from core.database import SessionLocal, get_db
from core.settings import logger
from account.models import Account
from account.schema import AccountResponseSchema
from user_management.models import UserBankInfo


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