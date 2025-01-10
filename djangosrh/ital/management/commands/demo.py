from datetime import datetime, timezone

from django.core.management.base import (
    BaseCommand
)

from ...models import Event, Item, Reservation
from ...tests.test_models import fill_db

class Command(BaseCommand):
    def make_db_empty(self):
        for evt in Event.objects.all():
            evt.delete()
        for it in Item.objects.all():
            it.delete()
        for res in Reservation.objects.all():
            res.delete()

    def handle(self, *args, **options):
        self.make_db_empty()
        fill_db()
