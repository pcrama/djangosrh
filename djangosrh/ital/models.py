import uuid
from django.db import models

from enum import Enum


class Civility(models.TextChoices):
    man = "Mr"
    woman = "Mme"
    __empty__ = ""


class DishType(models.TextChoices):
    STARTER = "starter"
    MAIN = "main"
    DESSERT = "dessert"


class Event(models.Model):
    name = models.CharField(max_length=200)
    date = models.DateField()

    def __str__(self):
        return f"{self.name}@{self.date}"


class Choice(models.Model):
    "What a customer chooses, can be 1 or more items grouped together (e.g. a starter/main dish/dessert pack)"
    display_text = models.CharField(max_length=200)
    price_in_cents = models.PositiveIntegerField()
    available_in = models.ForeignKey(Event, on_delete=models.CASCADE)

    def __str__(self):
        return self.display_text


class Item(models.Model):
    display_text = models.CharField(max_length=200)
    column_header = models.CharField(max_length=200)
    short_text = models.CharField(max_length=200)
    dish = models.CharField(max_length=10, choices=DishType)
    choices = models.ManyToManyField(Choice)

    def __str__(self):
        return self.display_text


class ReservationItemCount(models.Model):
    count = models.IntegerField()
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    reservation = models.ForeignKey("Reservation", on_delete=models.CASCADE)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['choice_id', 'item_id', 'reservation_id'], name='reservation*item*choice'),
            # TODO: constrain all choices to be for the same event
        ]

    def __repr__(self):
        return f"<ReservationItemCount {self.id}, {self.count}*{self.item} from {self.choice}>"


class Reservation(models.Model):
    civility = models.CharField(max_length=20, choices=Civility)
    last_name = models.CharField(max_length=200)
    first_name = models.CharField(max_length=200)
    email = models.CharField(max_length=200)
    accepts_rgpd_reuse = models.BooleanField()
    total_due_in_cents = models.IntegerField()
    places = models.IntegerField()
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    @property
    def full_name(self) -> str:
        return " ".join(x for x in (self.civility, self.first_name, self.last_name) if x and x.strip())

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    def count_items(self, item: Item|int) -> int:
        item_id = item.id if isinstance(item, Item) else item
        return sum(it.count for it in self.reservationitemcount_set.filter(item_id=item_id))
