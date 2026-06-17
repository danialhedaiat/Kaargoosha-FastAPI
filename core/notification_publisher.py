import traceback

import msgpack

from core.rabbitmq_connection import RabbitMQConnection
from core.settings import logger


class NotificationPublisher:
    EXCHANGE = "notify"

    def __init__(self):
        self.rabbitmq = RabbitMQConnection()
        self.channel = self.rabbitmq.channel
        self.channel.exchange_declare(exchange=self.EXCHANGE, exchange_type="topic", durable=True)

    def notify_loan_request(self, loan_id: int, user_id: int, first_name: str, last_name: str, duration_months: int, recipients: list):
        try:
            message = {
                "loan_id": loan_id,
                "user_id": user_id,
                "first_name": first_name,
                "last_name": last_name,
                "duration_months": duration_months,
                "recipients": recipients,
            }
            self.channel.basic_publish(
                exchange=self.EXCHANGE,
                routing_key="notify.loan_request",
                body=msgpack.packb(message),
            )
            logger.info(f"Sent loan request notification for loan_id={loan_id} to {len(recipients)} recipient(s)")
        except Exception:
            logger.error(traceback.format_exc())

    def notify_loan_approved(self, member_chat_id: int, amount: int, monthly_amount: int, first_due_date, duration_months: int):
        try:
            message = {
                "member_chat_id": member_chat_id,
                "amount": amount,
                "monthly_amount": monthly_amount,
                "first_due_date": str(first_due_date),
                "duration_months": duration_months,
            }
            self.channel.basic_publish(
                exchange=self.EXCHANGE,
                routing_key="notify.loan_approved",
                body=msgpack.packb(message),
            )
            logger.info(f"Sent loan approved notification to member_chat_id={member_chat_id}")
        except Exception:
            logger.error(traceback.format_exc())

    def notify_loan_rejected(self, member_chat_id: int, rejection_reason: str):
        try:
            message = {
                "member_chat_id": member_chat_id,
                "rejection_reason": rejection_reason,
            }
            self.channel.basic_publish(
                exchange=self.EXCHANGE,
                routing_key="notify.loan_rejected",
                body=msgpack.packb(message),
            )
            logger.info(f"Sent loan rejected notification to member_chat_id={member_chat_id}")
        except Exception:
            logger.error(traceback.format_exc())

    def notify_deposit_request(self, deposit_id: int, user_id: int, first_name: str, last_name: str, amount: int, proof_type: str, proof_content: str, recipients: list):
        try:
            message = {
                "deposit_id": deposit_id,
                "user_id": user_id,
                "first_name": first_name,
                "last_name": last_name,
                "amount": amount,
                "proof_type": proof_type,
                "proof_content": proof_content,
                "recipients": recipients,
            }
            self.channel.basic_publish(
                exchange=self.EXCHANGE,
                routing_key="notify.deposit_request",
                body=msgpack.packb(message),
            )
            logger.info(f"Sent deposit request notification for deposit_id={deposit_id} to {len(recipients)} recipient(s)")
        except Exception:
            logger.error(traceback.format_exc())