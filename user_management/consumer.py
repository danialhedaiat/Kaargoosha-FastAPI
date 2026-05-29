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

    def request_user(self, ch: BlockingChannel, method, properties: BasicProperties, body):
        try:
            data = msgpack.unpackb(body)
            service = UserService()

            if method.routing_key == "user.create":
                result = service.create_user(data)
                self.response(ch, method, properties, result)

            elif method.routing_key == "user.check_phone_number":
                result = service.check_phone_number_exist(data)
                self.response(ch, method, properties, result)

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

    @staticmethod
    def response(ch, method, properties, response):
        response = msgpack.packb(response)
        ch.basic_publish(
            exchange='',
            routing_key=properties.reply_to,
            properties=BasicProperties(correlation_id=properties.correlation_id),
            body=response
        )

        ch.basic_ack(delivery_tag=method.delivery_tag)