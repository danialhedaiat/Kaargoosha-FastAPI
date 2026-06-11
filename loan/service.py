import calendar
import datetime
import json
import traceback

from core.database import get_db, SessionLocal
from core.settings import logger, settings
from loan.models import Loan, LoanStatus, FundPool, Installment, InstallmentStatus
from loan.schema import LoanResponseSchema
from user_management.permissions import permission, Permissions


class LoanService:

    def __init__(self):
        self.db: SessionLocal = get_db()

    def create(self, data: dict):
        try:
            user_id = data["user_id"]
            duration_months = data["duration_months"]
            member_chat_id = data.get("member_chat_id")

            active_loan = self.db.query(Loan).filter(
                Loan.user_id == user_id,
                Loan.status.in_([LoanStatus.pending, LoanStatus.approved])
            ).first()
            if active_loan:
                return json.dumps({"error": "User already has an active or pending loan"})

            loan = Loan(
                user_id=user_id,
                duration_months=duration_months,
                member_chat_id=member_chat_id,
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


class InstallmentService:

    def __init__(self, db: SessionLocal = None):
        self.db: SessionLocal = db or get_db()

    def generate(self, loan_id: int, monthly_amount: float, duration_months: int):
        today = datetime.date.today()
        for i in range(1, duration_months + 1):
            month = today.month - 1 + i
            year = today.year + month // 12
            month = month % 12 + 1
            day = min(today.day, calendar.monthrange(year, month)[1])
            due_date = datetime.date(year, month, day)

            self.db.add(Installment(
                loan_id=loan_id,
                amount=monthly_amount,
                due_date=due_date,
                status=InstallmentStatus.pending,
            ))


class LoanRequestService:

    def __init__(self):
        self.db: SessionLocal = get_db()

    @permission(Permissions.LOAN_APPROVE)
    def approve(self, data: dict):
        try:
            loan_id = data["loan_id"]
            approver_id = data["requested_by"]
            amount = int(data["amount"])

            loan = self.db.query(Loan).filter_by(id=loan_id).first()
            if not loan:
                return json.dumps({"error": "Loan not found"})

            if loan.status != LoanStatus.pending:
                return json.dumps({"error": f"Loan is already {loan.status.value}"})

            if amount > settings.LOAN_MAX_AMOUNT:
                return json.dumps({"error": f"Amount exceeds maximum allowed limit of {settings.LOAN_MAX_AMOUNT}"})

            fund_pool = self.db.query(FundPool).first()
            if not fund_pool or int(fund_pool.balance) < amount:
                return json.dumps({"error": "Insufficient fund pool balance"})

            monthly_amount = amount // loan.duration_months

            loan.amount = amount
            loan.monthly_amount = monthly_amount
            loan.status = LoanStatus.approved
            loan.approved_by = approver_id
            loan.approved_at = datetime.datetime.now()
            fund_pool.balance = int(fund_pool.balance) - amount

            self.db.flush()

            from account.service import AccountService
            AccountService(db=self.db).credit(loan.user_id, amount)

            InstallmentService(db=self.db).generate(loan.id, monthly_amount, loan.duration_months)

            self.db.commit()
            self.db.refresh(loan)

            return LoanResponseSchema.model_validate(loan).model_dump_json()

        except Exception as e:
            self.db.rollback()
            logger.error(traceback.format_exc())
            logger.error(e)
            return json.dumps({"error": str(e)})

    @permission(Permissions.LOAN_REJECT)
    def reject(self, data: dict):
        try:
            loan_id = data["loan_id"]
            rejection_reason = data.get("rejection_reason")

            loan = self.db.query(Loan).filter_by(id=loan_id).first()
            if not loan:
                return json.dumps({"error": "Loan not found"})

            if loan.status != LoanStatus.pending:
                return json.dumps({"error": f"Loan is already {loan.status.value}"})

            loan.status = LoanStatus.rejected
            loan.rejection_reason = rejection_reason

            self.db.commit()
            self.db.refresh(loan)

            return LoanResponseSchema.model_validate(loan).model_dump_json()

        except Exception as e:
            self.db.rollback()
            logger.error(traceback.format_exc())
            logger.error(e)
            return json.dumps({"error": str(e)})