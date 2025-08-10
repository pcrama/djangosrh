from asyncio import base_events
from datetime import date
import uuid
from typing import Self

from django.db import models

class BaseEvent(models.Model):
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


class Payment(models.Model):
    date_received = models.DateField(null=False) # When payment was received by the bank
    amount_in_cents = models.IntegerField(null=False)
    comment = models.CharField(max_length=512, blank=True)
    src_id = models.CharField(max_length=32, blank=True)
    bank_ref = models.CharField(max_length=32, blank=False, null=False)
    other_account = models.CharField(max_length=40, blank=True)
    other_name = models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=16, blank=False)
    active = models.BooleanField(db_default=True)
    srh_bank_id = models.CharField(max_length=12, blank=True, null=False)
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["src_id"]),
            models.Index(fields=["bank_ref"]),
            models.Index(fields=["srh_bank_id"])
        ]
        constraints = [models.UniqueConstraint(fields=["bank_ref"], name="%(app_label)s_%(class)s_unique_bank_ref")]

    def __str__(self):
        return f"{self.bank_ref}:{self.amount_in_cents}c€"

    @classmethod
    def find_by_bank_ref(cls, bank_ref: str) -> Self | None:
        try:
            return cls.objects.get(bank_ref=bank_ref)
        except cls.DoesNotExist:
            return None


class Civility(models.TextChoices):
    man = "Mr"
    woman = "Mme"
    miss = "Mlle"
    __empty__ = ""


class BaseReservation(models.Model):
    civility = models.CharField(max_length=20, choices=Civility, default=Civility.__empty__)
    last_name = models.CharField(max_length=200, blank=False)
    first_name = models.CharField(max_length=200, default="")
    email = models.CharField(max_length=200)
    accepts_rgpd_reuse = models.BooleanField()
    total_due_in_cents = models.IntegerField()
    extra_comment = models.CharField(default="", max_length=200, blank=True)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    bank_id = models.CharField(unique=True, editable=False, max_length=16)
    base_event = models.ForeignKey("BaseEvent",
                                   on_delete=models.CASCADE,
                                   related_name="%(app_label)s_%(class)s_related",
                                   related_query_name="%(app_label)s_%(class)ss")

    @property
    def full_name(self) -> str:
        return " ".join(x for x in (self.civility, self.first_name, self.last_name) if x and x.strip())

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    def remaining_amount_due_in_cents(self) -> int:
        return self.total_due_in_cents - self.reservationpayment_set.aggregate(sum=models.Sum("payment__amount_in_cents", default=0))['sum']


class ReservationPayment(models.Model):
    reservation = models.ForeignKey(BaseReservation, on_delete=models.PROTECT)
    payment = models.OneToOneField(Payment, on_delete=models.PROTECT)
    confirmation_sent_timestamp = models.DateTimeField(null=True)

    # class Meta:
    #     constraints = [models.UniqueConstraint("payment", name="%(app_label)s_%(class)s_unique_payment")]


def get_reservations_with_likely_payments(min_date_received: date, reservations: models.QuerySet):
    # Subquery to get the payment with the lowest bank_ref that matches the constraints
    matching_payment_subquery = (
        Payment.objects.filter(
            srh_bank_id=models.OuterRef("bank_id"),
            status="Accepté",
            active=True,
            date_received__gt=min_date_received,
        )
        .exclude(
            id__in=ReservationPayment.objects.values_list("payment_id", flat=True)
        )
        .order_by("bank_ref")  # Order by lowest bank_ref
        [:1]
    )

    # Use a single subquery instance to avoid duplication
    matching_payment = models.Subquery(matching_payment_subquery)

    # Annotate the Reservation with the matching payment details
    reservations_with_payment = (reservations
        .annotate(
            total_received_in_cents=models.Sum("reservationpayment__payment__amount_in_cents", default=0),
            likely_payment_id=models.Subquery(matching_payment_subquery.values("id"), output_field=models.IntegerField()),
            likely_payment_other_name=models.Subquery(matching_payment_subquery.values("other_name"), output_field=models.CharField()),
            likely_payment_other_account=models.Subquery(matching_payment_subquery.values("other_account"), output_field=models.CharField()),
            likely_payment_amount_in_cents=models.Subquery(matching_payment_subquery.values("amount_in_cents"), output_field=models.IntegerField()),
            likely_payment_src_id=models.Subquery(matching_payment_subquery.values("src_id"), output_field=models.CharField()),
    ))

    return reservations_with_payment
