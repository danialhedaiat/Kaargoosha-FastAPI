import traceback

import msgpack
from pika import BasicProperties
from pika.adapters.blocking_connection import BlockingChannel

from account.service import AccountService
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

        logger.info("Waiting for messages in account_queue. To exit press CTRL+C")
        self.channel.start_consuming()

    def request_account(self, ch: BlockingChannel, method, properties: BasicProperties, body):
        try:
            data = msgpack.unpackb(body)
            service = AccountService()
            result = None

            if method.routing_key == 'account.get_balance':
                result = service.get_balance(data)

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