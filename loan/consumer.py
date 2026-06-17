import traceback

import msgpack
from pika import BasicProperties
from pika.adapters.blocking_connection import BlockingChannel

from core.rabbitmq_connection import RabbitMQConnection
from core.settings import logger
from loan.service import LoanService, InstallmentPaymentService


class LoanConsumer:

    def __init__(self):
        self.rabbitmq = RabbitMQConnection()
        self.channel = self.rabbitmq.channel

    def start_consuming(self):
        logger.info("running loan consumer")

        self.channel.queue_declare(queue='loan_queue')
        self.channel.exchange_declare(exchange='loan', exchange_type='topic', durable=True)
        self.channel.queue_bind(queue='loan_queue', exchange='loan', routing_key='loan.*')
        self.channel.basic_consume(queue='loan_queue', on_message_callback=self.request_loan)

        self.channel.queue_declare(queue='installment_payment_queue')
        self.channel.exchange_declare(exchange='installment_payment', exchange_type='topic', durable=True)
        self.channel.queue_bind(queue='installment_payment_queue', exchange='installment_payment', routing_key='installment_payment.*')
        self.channel.basic_consume(queue='installment_payment_queue', on_message_callback=self.request_installment_payment)

        logger.info("Waiting for messages in loan_queue. To exit press CTRL+C")
        self.channel.start_consuming()

    def request_loan(self, ch: BlockingChannel, method, properties: BasicProperties, body):
        try:
            data = msgpack.unpackb(body)
            result = None

            if method.routing_key == 'loan.create':
                result = LoanService().create(data)

            elif method.routing_key == 'loan.approve':
                result = LoanService().approve(data)

            elif method.routing_key == 'loan.reject':
                result = LoanService().reject(data)

            elif method.routing_key == 'loan.get_client_history':
                result = LoanService().get_client_history(data)

            elif method.routing_key == 'loan.get_loans':
                result = LoanService().get_loans(data)

            self.response(ch, method, properties, result)

        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    def request_installment_payment(self, ch: BlockingChannel, method, properties: BasicProperties, body):
        try:
            data = msgpack.unpackb(body)
            service = InstallmentPaymentService()
            result = None

            if method.routing_key == 'installment_payment.get_pending':
                result = service.get_pending(data)
            elif method.routing_key == 'installment_payment.create':
                result = service.create(data)
            elif method.routing_key == 'installment_payment.approve':
                result = service.approve(data)
            elif method.routing_key == 'installment_payment.reject':
                result = service.reject(data)

            self.response(ch, method, properties, result)

        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    @staticmethod
    def response(ch, method, properties, response):
        try:
            response = msgpack.packb(response)
            ch.basic_publish(
                exchange='',
                routing_key=properties.reply_to,
                properties=BasicProperties(correlation_id=properties.correlation_id),
                body=response
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.info(traceback.format_exc())
            logger.info(e)