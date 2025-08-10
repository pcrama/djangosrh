from collections import namedtuple
from collections.abc import Iterator
import uuid

from django.db import models

from core.models import Payment


class Civility(models.TextChoices):
    man = "Mr"
    woman = "Mme"
    miss = "Mlle"
    __empty__ = ""


class DishType(models.TextChoices):
    DT0STARTER = "dt0starter"
    DT1MAIN = "dt1main"
    DT2DESSERT = "dt2dessert"


class Event(models.Model):
    name = models.CharField(max_length=200)
    date = models.DateField()
    contact_email = models.CharField(max_length=200)
    organizer_name = models.CharField(max_length=200, default="Organizer name")
    organizer_bic = models.CharField(max_length=16, default="GABBBEBB")
    bank_account = models.CharField(max_length=32, default="BE00 0000 0000 0000")
    disabled = models.BooleanField(default=False)
    full_payment_confirmation_template = models.CharField(max_length=1024, default='<p>Hi,</p><p>Thank you for your payment for <a class="link-primary" href="%reservation_url%">your reservation</a>.</p><p>Greetings,<br>--&nbsp;<br>Signature</p>')
    partial_payment_confirmation_template = models.CharField(max_length=1024, default='<p>Hi,</p><p>Thank you for your payment for <a class="link-primary" href="%reservation_url%">your reservation</a>.</p><p>You can wire the remaining %remaining_amount_in_euro% € to %organizer_name% (%bank_account%, %organizer_bic%) with the communication <pre>%formatted_bank_id%</pre>.</p><p>Greetings,<br>--&nbsp;<br>Signature</p>')
    max_seats = models.IntegerField()

    def __str__(self):
        return f"{self.name}@{self.date}"

    def occupied_seats(self) ->int:
        return self.reservation_set.aggregate(models.Sum("places", default=0))["places__sum"]

    ItemSummary = namedtuple("ItemSummary", "id,display_text,display_text_plural,column_header,total_count")

    def reservation_items(self) -> list[ItemSummary]:
        return list(
            self.ItemSummary(
                id=itm["item__id"],
                display_text=itm["item__display_text"],
                display_text_plural=itm["item__display_text_plural"],
                column_header=itm["item__column_header"],
                total_count=itm["total_count"]
            ) for itm in
        ReservationItemCount.objects
        .filter(reservation__event_id=self.id)
        .values("item__display_text", "item__id", "item__display_text", "item__display_text_plural", "item__column_header")
        .annotate(total_count=models.Sum("count", default=0))
        .order_by("item__dish", "item__id")
    )


class Choice(models.Model):
    "What a customer chooses, can be 1 or more items grouped together (e.g. a starter/main dish/dessert pack)"
    display_text = models.CharField(max_length=200)
    price_in_cents = models.PositiveIntegerField()
    available_in = models.ForeignKey(Event, on_delete=models.CASCADE)

    def __str__(self):
        return self.display_text


class Item(models.Model):
    display_text = models.CharField(max_length=200, blank=False)
    display_text_plural = models.CharField(max_length=200, blank=False)
    column_header = models.CharField(max_length=200, blank=False)
    short_text = models.CharField(max_length=200, blank=False)
    dish = models.CharField(max_length=10, choices=DishType)
    choices = models.ManyToManyField(Choice)
    image = models.ImageField(upload_to='images/', null=True, blank=True)

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
    civility = models.CharField(max_length=20, choices=Civility, default=Civility.__empty__)
    last_name = models.CharField(max_length=200, blank=False)
    first_name = models.CharField(max_length=200, default="")
    email = models.CharField(max_length=200)
    accepts_rgpd_reuse = models.BooleanField()
    total_due_in_cents = models.IntegerField()
    places = models.IntegerField()
    extra_comment = models.CharField(default="", max_length=200, blank=True)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    bank_id = models.CharField(unique=True, editable=False, max_length=16)
    event = models.ForeignKey("Event", on_delete=models.CASCADE)

    @property
    def full_name(self) -> str:
        return " ".join(x for x in (self.civility, self.first_name, self.last_name) if x and x.strip())

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    def count_items(self, item: Item|int) -> int:
        item_id = item.id if isinstance(item, Item) else item
        return sum(it.count for it in self.reservationitemcount_set.filter(item_id=item_id))

    def remaining_amount_due_in_cents(self) -> int:
        return self.total_due_in_cents - self.reservationpayment_set.aggregate(sum=models.Sum("payment__amount_in_cents", default=0))['sum']


class ReservationPayment(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.PROTECT)
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT)
    confirmation_sent_timestamp = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint("payment", name="%(app_label)s_%(class)s_unique_payment")]
