import pika

from core.settings import settings


class RabbitMQConnection:

    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            credentials=pika.PlainCredentials(settings.RABBITMQ_USERNAME, settings.RABBITMQ_PASSWORD)
        ))
        self.channel = self.connection.channel()
