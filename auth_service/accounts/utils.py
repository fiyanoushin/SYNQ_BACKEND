import redis
from django.conf import settings
import random
import string
from django.core.mail import send_mail


redis_client = redis.StrictRedis.from_url(settings.REDIS_URL, decode_responses=True)

OTP_PREFIX = "otp:"
OTP_TTL = 600 


def generate_otp():
    return ''.join(random.choices(string.digits, k=6))


def save_otp_to_redis(email, otp):
    redis_client.setex(f"{OTP_PREFIX}{email.lower()}", OTP_TTL, otp)


def get_otp_from_redis(email):
    return redis_client.get(f"{OTP_PREFIX}{email.lower()}")


def delete_otp(email):
    redis_client.delete(f"{OTP_PREFIX}{email.lower()}")


def send_email_sync(subject, message, recipient):
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [recipient])
