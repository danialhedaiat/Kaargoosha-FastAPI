import json

from core.database import SessionLocal, get_db
from account.models import Account
from account.schema import AccountResponseSchema


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