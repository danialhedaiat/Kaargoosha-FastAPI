import logging

import msgpack
from pika.adapters.blocking_connection import BlockingChannel

from pika import BasicProperties
from core.rabbitmq_connection import RabbitMQConnection
from core.settings import logger
from user_management.service import UserService




class UserConsumer:
    def __init__(self):
        logger.info("Init consumer")

        self.rabbitmq = RabbitMQConnection()
        self.channel = self.rabbitmq.channel

    def start_consuming(self):
        logger.info("running consumer")

        self.channel.queue_declare(queue='user_queue')
        self.channel.exchange_declare(exchange='user', exchange_type='topic', durable=True)
        self.channel.queue_bind(queue='user_queue', exchange="user", routing_key="user.*")
        self.channel.basic_consume(queue='user_queue', on_message_callback=self.request_user)

        logger.info("Waiting for messages in user_queue. To exit press CTRL+C")
        self.channel.start_consuming()

    @staticmethod
    def request_user(ch: BlockingChannel, method, properties: BasicProperties, body):
        try:
            data = msgpack.unpackb(body)

            if method.routing_key == "user.create":
                logger.info("create")
            elif method.routing_key == "user.update":
                logger.info("update")
            elif method.routing_key == "user.get":
                logger.info("get")
            elif method.routing_key == "user.delete":
                UserService().delete()


        except Exception as e:
            import traceback
            logger.error(traceback.format_exc())
            logger.error(e)
