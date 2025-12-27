import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "team_service.settings")

import django
django.setup()

import json
import pika
from django.conf import settings
from django.db import close_old_connections
from teams.models import TeamMember


def run_team_rpc():
    connection = pika.BlockingConnection(
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

    channel = connection.channel()
    channel.queue_declare(queue=settings.TEAM_RPC_QUEUE, durable=True)
    channel.basic_qos(prefetch_count=1)

    print("Team RPC Server started. Waiting for requests...")

    def on_request(ch, method, props, body):
        close_old_connections()

        try:
            payload = json.loads(body.decode())
            user_id = payload["user_id"]
            team_id = payload["team_id"]

            member = TeamMember.objects.filter(
                user_id=user_id,
                team_id=team_id
            ).first()

            if not member:
                response = {
                    "ok": True,
                    "is_member": False,
                    "role": None,
                }
            else:
                response = {
                    "ok": True,
                    "is_member": True,
                    "role": member.role,
                }

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
        ch.basic_ack(method.delivery_tag)

    channel.basic_consume(
        queue=settings.TEAM_RPC_QUEUE,
        on_message_callback=on_request,
    )

    try:
        channel.start_consuming()
    finally:
        connection.close()
        
if __name__ == "__main__":
    print("TEAM Server starting...")
    run_team_rpc()
