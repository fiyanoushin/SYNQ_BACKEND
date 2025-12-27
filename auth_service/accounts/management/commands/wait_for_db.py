from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError
import time


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        print("Waiting for database...")

        while True:
            try:
                connections["default"].cursor()
                print("Database ready!")
                break
            except OperationalError:
                print("Database not ready, retrying...")
                time.sleep(1)
