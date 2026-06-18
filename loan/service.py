import calendar
import datetime
import json
import traceback

from core.database import get_db, SessionLocal
from core.settings import logger, settings
from loan.models import Loan, LoanStatus, FundPool, Installment, InstallmentStatus, InstallmentPaymentRequest, InstallmentPaymentStatus
from loan.schema import LoanResponseSchema
from user_management.permissions import permission, Permissions


class LoanService:

    def __init__(self):
        self.db: SessionLocal = get_db()

    def get_client_history(self, data: dict):
        try:
            user_id = data["user_id"]
            loans = (
                self.db.query(Loan)
                .filter_by(user_id=user_id)
                .order_by(Loan.created_at.desc())
                .all()
            )

            today = datetime.date.today()
            total_paid = 0
            total_installments = 0
            loan_list = []

            for loan in loans:
                installments = loan.installments
                inst_count = len(installments)
                paid_count = sum(1 for i in installments if i.status == InstallmentStatus.paid)
                overdue_count = sum(
                    1 for i in installments
                    if i.status == InstallmentStatus.pending and i.due_date < today
                )
                total_paid += paid_count
                total_installments += inst_count

                loan_list.append({
                    "id": loan.id,
                    "amount": loan.amount,
                    "duration_months": loan.duration_months,
                    "status": loan.status.value,
                    "approved_at": str(loan.approved_at) if loan.approved_at else None,
                    "rejection_reason": loan.rejection_reason,
                    "created_at": str(loan.created_at),
                    "installments_count": inst_count,
                    "paid_count": paid_count,
                    "overdue_count": overdue_count,
                })

            payment_rate = (
                round(total_paid / total_installments * 100, 1)
                if total_installments > 0
                else None
            )

            return json.dumps({
                "total_loans": len(loans),
                "payment_rate": payment_rate,
                "loans": loan_list,
            })

        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)
            return json.dumps({"error": str(e)})

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

            from account.service import AccountService
            from account.models import Account
            account_service = AccountService(db=self.db)
            threshold = account_service.get_loan_threshold()
            account = self.db.query(Account).filter_by(user_id=user_id).first()
            balance = int(account.balance) if account else 0
            if balance < threshold:
                return json.dumps({
                    "error": "insufficient_balance",
                    "balance": balance,
                    "required": threshold,
                })

            loan = Loan(
                user_id=user_id,
                duration_months=duration_months,
                member_chat_id=member_chat_id,
                status=LoanStatus.pending,
            )
            self.db.add(loan)
            self.db.commit()
            self.db.refresh(loan)

            self._notify_admins(loan)

            return LoanResponseSchema.model_validate(loan).model_dump_json()

        except Exception as e:
            self.db.rollback()
            logger.error(traceback.format_exc())
            logger.error(e)
            return json.dumps({"error": str(e)})

    def _notify_admins(self, loan):
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

            NotificationPublisher().notify_loan_request(
                loan_id=loan.id,
                user_id=loan.user_id,
                first_name=loan.user.first_name,
                last_name=loan.user.last_name,
                duration_months=loan.duration_months,
                recipients=recipients,
            )
        except Exception:
            logger.error(traceback.format_exc())

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

            from account.models import Transaction, TransactionType, TransactionDirection, TransactionStatus
            self.db.add(Transaction(
                user_id=loan.user_id,
                amount=amount,
                direction=TransactionDirection.credit,
                type=TransactionType.loan_disbursement,
                status=TransactionStatus.approved,
                reference_type="loan",
                reference_id=loan.id,
            ))

            InstallmentService(db=self.db).generate(loan.id, monthly_amount, loan.duration_months)

            self.db.commit()
            self.db.refresh(loan)

            first_installment = (
                self.db.query(Installment)
                .filter_by(loan_id=loan.id)
                .order_by(Installment.due_date)
                .first()
            )
            if loan.member_chat_id and first_installment:
                from core.notification_publisher import NotificationPublisher
                NotificationPublisher().notify_loan_approved(
                    member_chat_id=loan.member_chat_id,
                    amount=loan.amount,
                    monthly_amount=loan.monthly_amount,
                    first_due_date=first_installment.due_date,
                    duration_months=loan.duration_months,
                )

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

            if loan.member_chat_id:
                from core.notification_publisher import NotificationPublisher
                NotificationPublisher().notify_loan_rejected(
                    member_chat_id=loan.member_chat_id,
                    rejection_reason=rejection_reason or "",
                )

            return LoanResponseSchema.model_validate(loan).model_dump_json()

        except Exception as e:
            self.db.rollback()
            logger.error(traceback.format_exc())
            logger.error(e)
            return json.dumps({"error": str(e)})

    @permission(Permissions.LOAN_READ)
    def get_loans(self, data: dict):
        try:
            status_filter = data.get("status")
            days = data.get("days")

            query = self.db.query(Loan)

            if status_filter:
                query = query.filter(Loan.status == LoanStatus(status_filter))

            if days:
                from_date = datetime.datetime.now() - datetime.timedelta(days=int(days))
                query = query.filter(Loan.created_at >= from_date)

            loans = query.order_by(Loan.created_at.desc()).all()

            return json.dumps([
                {
                    "id": loan.id,
                    "user_id": loan.user_id,
                    "first_name": loan.user.first_name,
                    "last_name": loan.user.last_name,
                    "phone_number": loan.user.phone_number,
                    "member_chat_id": loan.member_chat_id,
                    "duration_months": loan.duration_months,
                    "amount": loan.amount,
                    "status": loan.status.value,
                    "created_at": str(loan.created_at),
                    "rejection_reason": loan.rejection_reason,
                }
                for loan in loans
            ])

        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)
            return json.dumps({"error": str(e)})


class InstallmentPaymentService:

    def __init__(self):
        self.db: SessionLocal = get_db()

    def get_pending(self, data: dict):
        try:
            user_id = data["user_id"]
            installments = (
                self.db.query(Installment)
                .join(Loan, Installment.loan_id == Loan.id)
                .filter(Loan.user_id == user_id, Installment.status == InstallmentStatus.pending)
                .order_by(Installment.due_date)
                .all()
            )
            return json.dumps([
                {
                    "id": i.id,
                    "amount": i.amount,
                    "due_date": str(i.due_date),
                    "loan_id": i.loan_id,
                }
                for i in installments
            ])
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)
            return json.dumps({"error": str(e)})

    def create(self, data: dict):
        try:
            user_id = data["user_id"]
            installment_id = data["installment_id"]
            proof_type = data["proof_type"]
            proof_content = data["proof_content"]

            installment = self.db.query(Installment).filter_by(id=installment_id).first()
            if not installment:
                return json.dumps({"error": "Installment not found"})
            if installment.loan.user_id != user_id:
                return json.dumps({"error": "Installment does not belong to user"})
            if installment.status != InstallmentStatus.pending:
                return json.dumps({"error": f"Installment is already {installment.status.value}"})

            request = InstallmentPaymentRequest(
                user_id=user_id,
                installment_id=installment_id,
                proof_type=proof_type,
                proof_content=proof_content,
                status=InstallmentPaymentStatus.pending,
            )
            self.db.add(request)
            self.db.flush()

            from account.models import Transaction, TransactionType, TransactionDirection, TransactionStatus
            self.db.add(Transaction(
                user_id=user_id,
                amount=installment.amount,
                direction=TransactionDirection.debit,
                type=TransactionType.installment_payment,
                status=TransactionStatus.pending,
                proof_type=proof_type,
                proof_content=proof_content,
                reference_type="installment_payment_request",
                reference_id=request.id,
            ))

            self.db.commit()
            self.db.refresh(request)

            self._notify_admins(request, installment)

            return json.dumps({"id": request.id, "status": request.status.value})

        except Exception as e:
            self.db.rollback()
            logger.error(traceback.format_exc())
            logger.error(e)
            return json.dumps({"error": str(e)})

    def _notify_admins(self, request, installment):
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

            user = self.db.query(UserModel).filter_by(id=request.user_id).first()
            NotificationPublisher().notify_installment_payment_request(
                request_id=request.id,
                user_id=request.user_id,
                first_name=user.first_name if user else "",
                last_name=user.last_name if user else "",
                installment_id=installment.id,
                amount=installment.amount,
                due_date=str(installment.due_date),
                proof_type=request.proof_type,
                proof_content=request.proof_content,
                recipients=recipients,
            )
        except Exception:
            logger.error(traceback.format_exc())

    @permission(Permissions.LOAN_APPROVE)
    def approve(self, data: dict):
        try:
            installment_payment_id = data["installment_payment_id"]

            request = self.db.query(InstallmentPaymentRequest).filter_by(id=installment_payment_id).first()
            if not request:
                return json.dumps({"error": "Installment payment request not found"})
            if request.status != InstallmentPaymentStatus.pending:
                return json.dumps({"error": f"Request is already {request.status.value}"})

            installment = self.db.query(Installment).filter_by(id=request.installment_id).first()
            if installment.status != InstallmentStatus.pending:
                return json.dumps({"error": f"Installment is already {installment.status.value}"})

            installment.status = InstallmentStatus.paid
            installment.paid_at = datetime.datetime.now()

            from account.service import AccountService
            AccountService(db=self.db).debit(request.user_id, installment.amount)

            from account.models import Transaction, TransactionType, TransactionDirection, TransactionStatus
            transaction = self.db.query(Transaction).filter_by(
                reference_type="installment_payment_request", reference_id=request.id
            ).first()
            if transaction:
                transaction.status = TransactionStatus.approved
            else:
                self.db.add(Transaction(
                    user_id=request.user_id,
                    amount=installment.amount,
                    direction=TransactionDirection.debit,
                    type=TransactionType.installment_payment,
                    status=TransactionStatus.approved,
                    reference_type="installment_payment_request",
                    reference_id=request.id,
                ))

            request.status = InstallmentPaymentStatus.approved
            request.approved_by = data["requested_by"]
            request.approved_at = datetime.datetime.now()

            self.db.commit()
            return json.dumps({"id": request.id, "status": request.status.value})

        except Exception as e:
            self.db.rollback()
            logger.error(traceback.format_exc())
            logger.error(e)
            return json.dumps({"error": str(e)})

    @permission(Permissions.LOAN_APPROVE)
    def reject(self, data: dict):
        try:
            installment_payment_id = data["installment_payment_id"]
            rejection_reason = data.get("rejection_reason")

            request = self.db.query(InstallmentPaymentRequest).filter_by(id=installment_payment_id).first()
            if not request:
                return json.dumps({"error": "Installment payment request not found"})
            if request.status != InstallmentPaymentStatus.pending:
                return json.dumps({"error": f"Request is already {request.status.value}"})

            request.status = InstallmentPaymentStatus.rejected
            request.rejection_reason = rejection_reason

            from account.models import Transaction, TransactionStatus
            transaction = self.db.query(Transaction).filter_by(
                reference_type="installment_payment_request", reference_id=request.id
            ).first()
            if transaction:
                transaction.status = TransactionStatus.rejected

            self.db.commit()
            return json.dumps({"id": request.id, "status": request.status.value})

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

