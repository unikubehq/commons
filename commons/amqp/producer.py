import json
import logging
import socket
from functools import cached_property

import pika as pika
from pika import BasicProperties, BlockingConnection

logger = logging.getLogger(__name__)


class _BasisBlockingAMQPProducer(object):
    exchange_type = None
    durable_exchange = False
    content_type = "text/json"
    delivery_mode = 2  # make message persistent

    def __init__(
        self,
        amqp_host: str,
        amqp_port: int,
        amqp_vhost: str = "/",
        exchange: str = "",
        routing_key: str = "",
        amqp_user: str = None,
        amqp_password: str = None,
        app_id: str = None,
    ):
        self._host = amqp_host
        self._port = amqp_port
        self._vhost = amqp_vhost
        self._username = amqp_user
        self._password = amqp_password
        self._app_id = app_id or socket.gethostname()

        self._exchange = exchange
        self._routing_key = routing_key

        if self._exchange != "":
            self._declare_exchange()

    @cached_property
    def _properties(self):
        return BasicProperties(content_type=self.content_type, delivery_mode=1, app_id=self._app_id)

    @cached_property
    def _connection(self) -> BlockingConnection:
        """This method connects to the broker, returning the connection handle."""
        logger.info(f"Connecting to {self._host}:{self._port}{self._vhost}")
        # set amqp credentials
        if self._username:
            credentials = pika.PlainCredentials(self._username, self._password)
            # set amqp connection parameters
            parameters = pika.ConnectionParameters(
                host=self._host,
                port=self._port,
                virtual_host=self._vhost,
                credentials=credentials,
            )
        else:
            parameters = pika.ConnectionParameters(
                host=self._host,
                port=self._port,
                virtual_host=self._vhost,
            )

        # connect
        return BlockingConnection(parameters=parameters)

    def _declare_exchange(self):
        channel = self._connection.channel()
        channel.exchange_declare(
            self._exchange, exchange_type=self.exchange_type, passive=False, durable=self.durable_exchange
        )

    def publish(self, message: dict):
        # get a new channel
        channel = self._connection.channel()
        channel.basic_publish(self._exchange, self._routing_key, json.dumps(message), self._properties)


class TopicProducer(_BasisBlockingAMQPProducer):
    exchange_type = "topic"
