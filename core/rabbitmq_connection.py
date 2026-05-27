import pika

from core.settings import settings


class RabbitMQConnection:
    instance = None
    def __new(cls, *args, **kwargs):
        if cls.instance:
            return cls.instance
        cls.instance = super(RabbitMQConnection, cls).__new__(cls, *args, **kwargs)

    def __init__(self):
        if not hasattr(self, 'connection'):
            self.connection = pika.BlockingConnection(pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
                credentials=pika.PlainCredentials(settings.RABBITMQ_USERNAME, settings.RABBITMQ_PASSWORD)
            ))
            self.channel = self.connection.channel()
