import traceback

import msgpack
from pika import BasicProperties
from pika.adapters.blocking_connection import BlockingChannel

from account.service import AccountService, BankInfoService, ReceiptService
from core.rabbitmq_connection import RabbitMQConnection
from core.settings import logger


class AccountConsumer:

    def __init__(self):
        self.rabbitmq = RabbitMQConnection()
        self.channel = self.rabbitmq.channel

    def start_consuming(self):
        logger.info("running account consumer")

        self.channel.queue_declare(queue='account_queue')
        self.channel.exchange_declare(exchange='account', exchange_type='topic', durable=True)
        self.channel.queue_bind(queue='account_queue', exchange='account', routing_key='account.*')
        self.channel.basic_consume(queue='account_queue', on_message_callback=self.request_account)

        self.channel.queue_declare(queue='bank_info_queue')
        self.channel.exchange_declare(exchange='bank_info', exchange_type='topic', durable=True)
        self.channel.queue_bind(queue='bank_info_queue', exchange='bank_info', routing_key='bank_info.*')
        self.channel.basic_consume(queue='bank_info_queue', on_message_callback=self.request_bank_info)

        self.channel.queue_declare(queue='receipt_queue')
        self.channel.exchange_declare(exchange='receipt', exchange_type='topic', durable=True)
        self.channel.queue_bind(queue='receipt_queue', exchange='receipt', routing_key='receipt.*')
        self.channel.basic_consume(queue='receipt_queue', on_message_callback=self.request_receipt)

        logger.info("Waiting for messages in account_queue. To exit press CTRL+C")
        self.channel.start_consuming()

    def request_account(self, ch: BlockingChannel, method, properties: BasicProperties, body):
        try:
            data = msgpack.unpackb(body)
            service = AccountService()
            result = None

            if method.routing_key == 'account.get_balance':
                result = service.get_balance(data)
            elif method.routing_key == 'account.set_threshold':
                result = service.set_threshold(data)

            self.response(ch, method, properties, result)

        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    def request_bank_info(self, ch: BlockingChannel, method, properties: BasicProperties, body):
        try:
            data = msgpack.unpackb(body)
            service = BankInfoService()
            result = None

            if method.routing_key == 'bank_info.save':
                result = service.save(data)
            elif method.routing_key == 'bank_info.get':
                result = service.get(data)

            self.response(ch, method, properties, result)

        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    def request_receipt(self, ch: BlockingChannel, method, properties: BasicProperties, body):
        try:
            data = msgpack.unpackb(body)
            service = ReceiptService()
            result = None

            if method.routing_key == 'receipt.create':
                result = service.create(data)
            elif method.routing_key == 'receipt.approve':
                result = service.approve(data)
            elif method.routing_key == 'receipt.reject':
                result = service.reject(data)
            elif method.routing_key == 'receipt.list':
                result = service.list(data)
            elif method.routing_key == 'receipt.get_proof':
                result = service.get_proof(data)

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