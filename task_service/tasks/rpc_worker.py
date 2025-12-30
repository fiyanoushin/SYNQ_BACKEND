import os
import sys
import json
import pika
import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "task_service.settings")
django.setup()

from tasks.models import Task


QUEUE_NAME = "task_rpc_queue"


def handle_request(payload):
    action = payload.get("action")

    if action == "get_user_tasks":
        user_id = payload["user_id"]
        tasks = Task.objects.filter(assigned_to_id=user_id)
        return [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "team_id": t.team_id,
            }
            for t in tasks
        ]

    if action == "get_team_tasks":
        team_id = payload["team_id"]
        tasks = Task.objects.filter(team_id=team_id)
        return [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "assigned_to": t.assigned_to_id,
            }
            for t in tasks
        ]

    return {"error": "Unknown action"}


def on_request(ch, method, props, body):
    payload = json.loads(body)

    try:
        data = handle_request(payload)
        response = {"ok": True, "data": data}
    except Exception as e:
        response = {"ok": False, "error": str(e)}

    ch.basic_publish(
        exchange="",
        routing_key=props.reply_to,
        properties=pika.BasicProperties(
            correlation_id=props.correlation_id
        ),
        body=json.dumps(response),
    )
    ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    credentials = pika.PlainCredentials(
        os.getenv("RABBITMQ_USER", "user"),
        os.getenv("RABBITMQ_PASS", "password"),
    )

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=os.getenv("RABBITMQ_HOST", "rabbitmq"),
            port=int(os.getenv("RABBITMQ_PORT", 5672)),
            virtual_host=os.getenv("RABBITMQ_VHOST", "/"),
            credentials=credentials,
            heartbeat=60,
            blocked_connection_timeout=30,
        )
    )

    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=on_request)

    print("Task RPC Worker started")
    channel.start_consuming()


if __name__ == "__main__":
    main()
