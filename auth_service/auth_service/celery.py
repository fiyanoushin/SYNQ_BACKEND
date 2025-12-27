import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth_service.settings")

from django.conf import settings

app = Celery("auth_service", broker=settings.CELERY_BROKER_URL)
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
