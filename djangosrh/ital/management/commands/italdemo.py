from datetime import datetime, timezone

from django.core.management.base import (
    BaseCommand
)
from django.urls import reverse

from ...models import Event, Item, Reservation
from core.models import Payment, ReservationPayment
from ...tests.test_models import fill_db

class Command(BaseCommand):
    def make_db_empty(self):
        for res_pay in ReservationPayment.objects.all():
            res_pay.delete()
        for pmnt in Payment.objects.all():
            pmnt.delete()
        for evt in Event.objects.all():
            evt.delete()
        for it in Item.objects.all():
            it.delete()
        for res in Reservation.objects.all():
            res.delete()

    def handle(self, *args, **options):
        self.make_db_empty()
        event, *_ = fill_db()
        print("http://localhost:8000" + reverse("ital:reservation_form", kwargs={"event_id": event.id}))
