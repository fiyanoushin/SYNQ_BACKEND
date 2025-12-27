import json
import pika
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "task_service.settings")
django.setup()

from tasks.models import Task

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
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
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST)
    )
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=on_request)

    print(" Task RPC Worker started")
    channel.start_consuming()


if __name__ == "__main__":
    main()
