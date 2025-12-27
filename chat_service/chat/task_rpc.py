import json
import uuid
import pika
import os
import threading
import time


RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")


class TaskRPCClient:
    def __init__(self, timeout=5):
        self.timeout = timeout
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST)
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
            self.response = json.loads(body)

    def call(self, payload):
        self.response = None
        self.corr_id = str(uuid.uuid4())

        self.channel.basic_publish(
            exchange="",
            routing_key="task_rpc_queue",
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=json.dumps(payload),
        )

        start = time.time()
        while self.response is None:
            self.connection.process_data_events()
            if time.time() - start > self.timeout:
                return {"ok": False, "error": "Task service timeout"}

        return self.response

    def get_user_tasks(self, user_id):
        return self.call({
            "action": "get_user_tasks",
            "user_id": user_id,
        })

    def get_team_tasks(self, team_id):
        return self.call({
            "action": "get_team_tasks",
            "team_id": team_id,
        })

    def close(self):
        try:
            self.connection.close()
        except Exception:
            pass
