import traceback

import msgpack
from pika.adapters.blocking_connection import BlockingChannel

from pika import BasicProperties
from core.rabbitmq_connection import RabbitMQConnection
from core.settings import logger
from user_management.service import UserService, RoleService, PermissionService


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

        self.channel.queue_declare(queue='role_queue')
        self.channel.exchange_declare(exchange='role', exchange_type='topic', durable=True)
        self.channel.queue_bind(queue='role_queue', exchange="role", routing_key="role.*")
        self.channel.basic_consume(queue='role_queue', on_message_callback=self.request_role)

        self.channel.queue_declare(queue='permission_queue')
        self.channel.exchange_declare(exchange='permission', exchange_type='topic', durable=True)
        self.channel.queue_bind(queue='permission_queue', exchange="permission", routing_key="permission.*")
        self.channel.basic_consume(queue='permission_queue', on_message_callback=self.request_permission)

        logger.info("Waiting for messages in user_queue. To exit press CTRL+C")
        self.channel.start_consuming()

    def request_user(self, ch: BlockingChannel, method, properties: BasicProperties, body):
        try:
            data = msgpack.unpackb(body)
            service = UserService()
            result = None

            if method.routing_key == "user.create":
                result = service.create_user(data)

            elif method.routing_key == "user.check_phone_number":
                result = service.check_phone_number_exist(data)

            elif method.routing_key == "user.join":
                result = service.join_user(data)

            elif method.routing_key == "user.get_user_by_username":
                result = service.get_user_by_username(data)

            elif method.routing_key == "user.check_admin_menu_permission":
                result = service.check_admin_menu_permission(data)

            self.response(ch, method, properties, result)

        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    def request_role(self, ch: BlockingChannel, method, properties: BasicProperties, body):
        try:
            data = msgpack.unpackb(body)
            service = RoleService()
            result = None

            if method.routing_key == "role.create":
                result = service.create_role(data)

            elif method.routing_key == "role.get":
                result = service.get_role(data)

            elif method.routing_key == "role.get_all":
                result = service.get_all_roles(data)

            elif method.routing_key == "role.assign":
                result = service.assign_role(data)

            elif method.routing_key == "role.get_user_roles":
                result = service.get_user_roles(data)

            elif method.routing_key == "role.revoke":
                result = service.revoke_role(data)

            elif method.routing_key == "role.delete":
                result = service.delete_role(data)

            self.response(ch, method, properties, result)

        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    def request_permission(self, ch: BlockingChannel, method, properties: BasicProperties, body):
        try:
            data = msgpack.unpackb(body)
            service = PermissionService()
            result = None

            if method.routing_key == "permission.create":
                result = service.create_permission(data)

            elif method.routing_key == "permission.get_all":
                result = service.get_all_permissions(data)

            elif method.routing_key == "permission.get_role_permission":
                result = service.get_role_permissions(data)

            elif method.routing_key == "permission.revoke":
                result = service.revoke_permission_from_role(data)

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