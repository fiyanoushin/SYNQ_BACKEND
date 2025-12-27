import json
import pika
import uuid
import time
from django.conf import settings


class AuthRPCClient:
    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
                virtual_host=settings.RABBITMQ_VHOST,
                credentials=pika.PlainCredentials(
                    settings.RABBITMQ_USER,
                    settings.RABBITMQ_PASS,
                ),
            )
        )
        self.channel = self.connection.channel()

        result = self.channel.queue_declare(queue="", exclusive=True)
        self.callback_queue = result.method.queue

        self.response = None
        self.corr_id = None

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True,
        )

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def validate_token(self, token, timeout=3):
        self.response = None
        self.corr_id = str(uuid.uuid4())

        payload = json.dumps({"token": token})

        self.channel.basic_publish(
            exchange="",
            routing_key=settings.AUTH_VALIDATION_QUEUE,
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=payload,
        )

        start = time.time()
        while time.time() - start < timeout:
            self.connection.process_data_events(time_limit=0.1)
            if self.response:
                return json.loads(self.response.decode())

        return {"ok": False, "error": "auth_timeout"}
