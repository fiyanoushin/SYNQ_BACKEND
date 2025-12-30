import json
import uuid
import time
import pika
from django.conf import settings


class AuthRPCClient:
    def __init__(self):
        credentials = pika.PlainCredentials(
            settings.RABBITMQ_USER,
            settings.RABBITMQ_PASS,
        )

        params = pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            virtual_host=settings.RABBITMQ_VHOST,
            credentials=credentials,
            heartbeat=60,
            blocked_connection_timeout=30,
        )

        self.connection = pika.BlockingConnection(params)
        self.channel = self.connection.channel()

        result = self.channel.queue_declare(queue="", exclusive=True)
        self.callback_queue = result.method.queue

        self.response = None
        self.corr_id = None

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self._on_response,
            auto_ack=True,
        )

    def _on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = json.loads(body)

    def verify_token(self, token, timeout=5):
        self.response = None
        self.corr_id = str(uuid.uuid4())

        self.channel.basic_publish(
            exchange="",
            routing_key=settings.AUTH_VALIDATION_QUEUE,
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=json.dumps({"token": token}),
        )

        start = time.time()
        while self.response is None:
            if time.time() - start > timeout:
                raise TimeoutError("Auth RPC timeout")
            self.connection.process_data_events(time_limit=0.2)

        return self.response

    def close(self):
        try:
            self.channel.close()
            self.connection.close()
        except Exception:
            pass
