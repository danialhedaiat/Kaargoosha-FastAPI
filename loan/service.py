import json
import traceback

from core.database import get_db, SessionLocal
from core.settings import logger, settings
from loan.models import Loan, LoanStatus, FundPool
from loan.schema import LoanResponseSchema


class LoanService:

    def __init__(self):
        self.db: SessionLocal = get_db()

    def create(self, data: dict):
        try:
            user_id = data["user_id"]
            amount = data["amount"]
            duration_months = data["duration_months"]
            monthly_amount = data["monthly_amount"]

            active_loan = self.db.query(Loan).filter(
                Loan.user_id == user_id,
                Loan.status.in_([LoanStatus.pending, LoanStatus.approved])
            ).first()
            if active_loan:
                return json.dumps({"error": "User already has an active or pending loan"})

            if float(amount) > settings.LOAN_MAX_AMOUNT:
                return json.dumps({"error": f"Amount exceeds maximum allowed limit of {settings.LOAN_MAX_AMOUNT}"})

            fund_pool = self.db.query(FundPool).first()
            if not fund_pool or float(fund_pool.balance) < float(amount):
                return json.dumps({"error": "Requested amount exceeds available fund pool balance"})

            loan = Loan(
                user_id=user_id,
                amount=amount,
                duration_months=duration_months,
                monthly_amount=monthly_amount,
                status=LoanStatus.pending,
            )
            self.db.add(loan)
            self.db.commit()
            self.db.refresh(loan)

            return LoanResponseSchema.model_validate(loan).model_dump_json()

        except Exception as e:
            self.db.rollback()
            logger.error(traceback.format_exc())
            logger.error(e)
            return json.dumps({"error": str(e)})