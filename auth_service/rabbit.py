# import os
# import json
# import time
# import django
# import pika
# import logging

# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth_service.settings")
# django.setup()

# from django.conf import settings
# from rest_framework_simplejwt.authentication import JWTAuthentication
# from django.contrib.auth import get_user_model

# User = get_user_model()
# auth_handler = JWTAuthentication()

# logger = logging.getLogger("auth_rpc")
# logger.setLevel(logging.INFO)
# handler = logging.StreamHandler()
# handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
# logger.addHandler(handler)



# def validate_token(access_token: str):
#     try:
#         validated_token = auth_handler.get_validated_token(access_token)
#         user = auth_handler.get_user(validated_token)

#         return {
#             "ok": True,
#             "user": {
#                 "id": user.id,
#                 "email": user.email,
#                 "full_name": user.full_name,
#                 "role": user.role,                     
#                 "email_verified": user.email_verified,
#             },
#         }
#     except Exception as e:
#         logger.warning(f"Token validation failed: {e}")
#         return {"ok": False, "detail": "invalid_or_expired_token"}



# def update_user_role(payload):
#     try:
#         user_id = payload.get("user_id")
#         new_role = payload.get("role")

#         logger.info(f"Updating user {user_id} role to: {new_role}")

#         user = User.objects.get(id=user_id)
#         user.role = new_role
#         user.save()

#         return {"ok": True, "detail": "role_updated"}
#     except Exception as e:
#         logger.error(f"Role update failed: {e}")
#         return {"ok": False, "error": str(e)}



# def create_rabbit_connection():
#     credentials = pika.PlainCredentials(
#         settings.RABBITMQ_USER, settings.RABBITMQ_PASS
#     )

#     params = pika.ConnectionParameters(
#         host=settings.RABBITMQ_HOST,
#         port=settings.RABBITMQ_PORT,
#         virtual_host=settings.RABBITMQ_VHOST,
#         credentials=credentials,
#         heartbeat=60,
#         blocked_connection_timeout=30,
#     )

#     return pika.BlockingConnection(params)



# def run_rpc_server():
#     queue_name = settings.AUTH_VALIDATION_QUEUE   
#     command_queue = getattr(settings, "AUTH_COMMAND_QUEUE", "auth_commands")

#     backoff = 1

#     while True:
#         try:
#             logger.info("Connecting to RabbitMQ...")

#             connection = create_rabbit_connection()
#             channel = connection.channel()

#             channel.queue_declare(queue=queue_name, durable=True)

#             channel.queue_declare(queue=command_queue, durable=True)

#             logger.info(f"RPC server running: {queue_name} & {command_queue}")

#             def on_request(ch, method, props, body):
#                 try:
#                     payload = json.loads(body.decode())
#                 except Exception:
#                     logger.error("Invalid JSON payload")
#                     ch.basic_ack(method.delivery_tag)
#                     return

#                 action = payload.get("action")
#                 response = None

#                 if action == "update_role":
#                     response = update_user_role(payload)
#                 else:
#                     token = payload.get("token")
#                     response = validate_token(token)

                
#                 try:
#                     ch.basic_publish(
#                         exchange="",
#                         routing_key=props.reply_to,
#                         properties=pika.BasicProperties(
#                             correlation_id=props.correlation_id
#                         ),
#                         body=json.dumps(response),
#                     )
#                 except Exception as e:
#                     logger.error(f"Error sending RPC response: {e}")

#                 ch.basic_ack(method.delivery_tag)

            
#             channel.basic_consume(queue=queue_name, on_message_callback=on_request)
#             channel.basic_consume(queue=command_queue, on_message_callback=on_request)

#             backoff = 1
#             channel.start_consuming()

#         except Exception as e:
#             logger.error(f"RPC server error: {e}. Retrying...")
#             time.sleep(backoff)
#             backoff = min(backoff * 2, 30)


# if __name__ == "__main__":
#     run_rpc_server()



import os
import json
import time
import django
import pika
import logging

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth_service.settings")
django.setup()

from django.conf import settings
from django.db import close_old_connections
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import get_user_model

User = get_user_model()
auth_handler = JWTAuthentication()

logger = logging.getLogger("auth_rpc")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(handler)


def validate_token(access_token: str):
    try:
        validated_token = auth_handler.get_validated_token(access_token)
        user = auth_handler.get_user(validated_token)

        return {
            "ok": True,
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "email_verified": user.email_verified,
            },
        }
    except Exception as e:
        logger.warning(f"Token validation failed: {e}")
        return {"ok": False, "detail": "invalid_or_expired_token"}


def create_rabbit_connection():
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

    return pika.BlockingConnection(params)


def run_rpc_server():
    queue_name = settings.AUTH_VALIDATION_QUEUE
    backoff = 1

    while True:
        try:
            logger.info("Connecting to RabbitMQ...")

            connection = create_rabbit_connection()
            channel = connection.channel()

            channel.queue_declare(queue=queue_name, durable=True)
            logger.info(f"Auth RPC server listening on {queue_name}")

            def on_request(ch, method, props, body):
                close_old_connections()

                try:
                    payload = json.loads(body.decode())
                    token = payload.get("token")
                except Exception:
                    response = {"ok": False, "detail": "invalid_payload"}
                else:
                    response = validate_token(token)

                ch.basic_publish(
                    exchange="",
                    routing_key=props.reply_to,
                    properties=pika.BasicProperties(
                        correlation_id=props.correlation_id
                    ),
                    body=json.dumps(response),
                )

                ch.basic_ack(method.delivery_tag)

            channel.basic_consume(queue=queue_name, on_message_callback=on_request)
            backoff = 1
            channel.start_consuming()

        except Exception as e:
            logger.error(f"RPC server error: {e}. Retrying...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)


if __name__ == "__main__":
    run_rpc_server()

