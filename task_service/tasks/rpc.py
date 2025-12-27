
import json
import uuid
import time
import pika
from django.conf import settings


class AuthRPCClient:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.callback_queue = None
        self.response = None
        self.corr_id = None

    def _connect(self):
        params = pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            virtual_host=settings.RABBITMQ_VHOST,
            credentials=pika.PlainCredentials(
                settings.RABBITMQ_USER,
                settings.RABBITMQ_PASS,
            ),
            heartbeat=30,
            blocked_connection_timeout=10,
        )

        self.connection = pika.BlockingConnection(params)
        self.channel = self.connection.channel()

        result = self.channel.queue_declare(queue="", exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self._on_response,
            auto_ack=True,
        )

    def _on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def validate_token(self, token, timeout=3):
        try:
            self._connect()
        except Exception:
            return {"ok": False, "error": "auth_rpc_unavailable"}

        self.response = None
        self.corr_id = str(uuid.uuid4())

        try:
            self.channel.basic_publish(
                exchange="",
                routing_key=settings.AUTH_VALIDATION_QUEUE,
                properties=pika.BasicProperties(
                    reply_to=self.callback_queue,
                    correlation_id=self.corr_id,
                ),
                body=json.dumps({"token": token}),
            )
        except Exception:
            return {"ok": False, "error": "publish_failed"}

        start = time.time()
        while time.time() - start < timeout:
            try:
                self.connection.process_data_events(time_limit=0.1)
                if self.response:
                    return json.loads(self.response.decode())
            except Exception:
                break

        return {"ok": False, "error": "timeout"}
