from collections import namedtuple
from collections.abc import Iterator
from random import choices
import uuid

from django.db import models

from core.models import BaseReservation, BaseEvent


class Event(BaseEvent):
    class Meta:
        # because I want Choice to link to "concert" Events, not to BaseEvents where they could also be "ital" Events:
        proxy = False
    base_event_ptr = models.OneToOneField(BaseEvent,
                                          on_delete=models.CASCADE,
                                          parent_link=True,
                                          primary_key=True,
                                          related_name="%(class)s_set",
                                          related_query_name="%(app_label)s_%(class)ss")

    def occupied_seats(self) -> int:
        return (
            ReservationChoiceCount.objects
            .filter(reservation__event=self)
            .aggregate(total=models.Sum("count"))["total"] or 0
        )

    ChoiceSummary = namedtuple("ChoiceSummary", "id,display_text,display_text_plural,column_header,total_count")
    def reservation_choices(self) -> list[ChoiceSummary]:
        return list(
            self.ChoiceSummary(
                id=itm["choice__id"],
                display_text=itm["choice__display_text"],
                display_text_plural=itm["choice__display_text_plural"],
                column_header=itm["choice__column_header"],
                total_count=itm["total_count"]
            ) for itm in
        ReservationChoiceCount.objects
        .filter(reservation__event_id=self.id)
        .values("choice__display_text", "choice__id", "choice__display_text", "choice__display_text_plural", "choice__column_header")
        .annotate(total_count=models.Sum("count", default=0))
        .order_by("choice__id")
    )


class Choice(models.Model):
    "What a customer chooses"
    price_in_cents = models.PositiveIntegerField()
    available_in = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="%(class)s_set",
        related_query_name="%(app_label)s_%(class)ss")
    display_text = models.CharField(max_length=200, blank=False)
    display_text_plural = models.CharField(max_length=200, blank=False)
    column_header = models.CharField(max_length=200, blank=False)

    def __str__(self):
        return self.display_text


class ReservationChoiceCount(models.Model):
    count = models.IntegerField()
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE)
    reservation = models.ForeignKey("Reservation", on_delete=models.CASCADE)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['choice_id', 'reservation_id'], name='%(app_label)s_%(class)s_reservation*choice'),
            # TODO: constrain all choices to be for the same event
        ]

    def __repr__(self):
        return f"<ReservationChoiceCount {self.id}, {self.count}* from {self.choice}>"


class Reservation(BaseReservation):
    base_reservation_ptr = models.OneToOneField(BaseReservation,
                                                on_delete=models.CASCADE,
                                                parent_link=True,
                                                primary_key=True,
                                                related_name="%(class)s_set",
                                                related_query_name="%(app_label)s_%(class)ss")
    event = models.ForeignKey("Event",
                              on_delete=models.CASCADE,
                              related_name="%(class)s_set",
                              related_query_name="%(app_label)s_%(class)ss")

    class Meta:
        # Specify a unique related name for reverse access
        verbose_name = "Réservation concert"
        verbose_name_plural = "Réservations concert"

    def save(self, **kwargs):
        if not hasattr(self, 'base_event') or self.base_event is None:
            self.base_event = self.event.base_event_ptr
        super().save(**kwargs)

    @property
    def places(self) -> int:
        return self.reservationchoicecount_set.aggregate(models.Sum('count')).get('count__sum', 0)
