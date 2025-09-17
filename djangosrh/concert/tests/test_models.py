from datetime import date, datetime, timezone

from django.test import TestCase

from core.models import Civility, Payment, ReservationPayment
from ..models import (
    Choice,
    Event,
    Reservation,
    ReservationChoiceCount,
)


def fill_db() -> tuple[Event, list[Choice], list[Reservation]]:
    Event(
        name="Gala (Dimanche)",
        date=datetime(2025, 11, 9, 17, 0, 0, tzinfo=timezone.utc),
        contact_email="dont-spam@me.com",
        max_seats=200
    ).save()
    event = Event(
        name="Gala (Samedi)",
        date=datetime(2025, 11, 8, 21, 0, 0, tzinfo=timezone.utc),
        contact_email="dont-spam@me.com",
        max_seats=200)
    event.save()
    choices = [Choice(display_text=f"<>{name}<>", column_header=name, display_text_plural=f"P({name})", price_in_cents=price_in_cents, available_in=event)
               for name, price_in_cents in (("Adulte", 1500), ("Enfant", 0), ("Étudiant", 1000))]
    for choice in choices:
        choice.save()

    reservations = []
    reservations.append(rsrvtn := Reservation(
        civility=Civility.man,
        first_name="",
        last_name="Dupont",
        email="dupont@yopmail.fr",
        accepts_rgpd_reuse=True,
        total_due_in_cents=7900,
        event=event,
        bank_id="091000100001",
        extra_comment="Places offertes, donc \"gratuites\"",
    ))
    rsrvtn.save()
    for choice_idx, count in ((0, 2), (1, 2), (2, 1)):
        reservation_choice_count = ReservationChoiceCount(reservation=rsrvtn, choice=choices[choice_idx], count=count)
        reservation_choice_count.save()
        rsrvtn.reservationchoicecount_set.add(reservation_choice_count)

    reservations.append(rsrvtn := Reservation(
        civility=Civility.woman,
        first_name="Lara",
        last_name="Croft",
        email="tomb-raider@yopmail.fr",
        accepts_rgpd_reuse=True,
        total_due_in_cents=2800,
        event=event,
        bank_id="092000200002",
    ))
    rsrvtn.save()
    for choice_idx, count in ((0, 1),):
        reservation_choice_count = ReservationChoiceCount(reservation=rsrvtn, choice=choices[choice_idx], count=count)
        reservation_choice_count.save()
        rsrvtn.reservationchoicecount_set.add(reservation_choice_count)

    reservations.append(rsrvtn := Reservation(
        civility=Civility.__empty__,
        first_name="Priv",
        last_name="Ate",
        email="none-of@your.biz",
        accepts_rgpd_reuse=False,
        total_due_in_cents=2200,
        event=event,
        bank_id="093000300003",
    ))
    rsrvtn.save()
    for choice_idx, count in ((2, 1),):
        reservation_choice_count = ReservationChoiceCount(reservation=rsrvtn, choice=choices[choice_idx], count=count)
        reservation_choice_count.save()
        rsrvtn.reservationchoicecount_set.add(reservation_choice_count)

    Payment(
        date_received=date(2025, 10, 22),
        amount_in_cents=2200,
        comment="+++093/0003/00003+++",
        src_id="2025-0901",
        bank_ref="202502221234560001",
        other_account="BE00 1234 1234 1234 2134",
        other_name="Priv Ate's bank account",
        status="Accepté",
        active=True,
        srh_bank_id="093000300003",
    ).save()
    Payment(
        date_received=date(2025, 10, 13),
        comment="091000100001",
        src_id="2025-09122",
        bank_ref="2025000000000",
        other_account="Mr Who's broken bank account",
        other_name="Mr Who refused",
        amount_in_cents=2345,
        status="Refusé",
        active=True,
        srh_bank_id="091000100001",
    ).save()
    Payment(
        date_received=date(2025, 10, 13),
        comment="091000100001",
        src_id="2025-09121",
        bank_ref="2025000000001",
        other_account="Mr Who's inactive bank account",
        other_name="Mr Who refused",
        amount_in_cents=2345,
        status="Accepté",
        active=False,
        srh_bank_id="091000100001",
    ).save()
    Payment(
        date_received=date(2025, 10, 13),
        comment="091000100001",
        src_id="2025-09123",
        bank_ref="2025022812345",
        other_account="Mr Who's bank account",
        other_name="Mr Who",
        amount_in_cents=2345,
        status="Accepté",
        active=True,
        srh_bank_id="091000100001",
    ).save()
    Payment(
        date_received=date(2025, 10, 13),
        comment="+++091/0001/00001+++",
        src_id="2025-09124",
        bank_ref="2025022812444",
        other_account="",
        other_name="Dupont",
        amount_in_cents=5455,
        status="Accepté",
        active=True,
        srh_bank_id="091000100001",
    ).save()
    already_payed = Payment(
        date_received=date(2025, 10, 13),
        comment="+++091/0001/00001+++",
        src_id="2025-09115",
        bank_ref="2025022999999",
        other_account="Mr Who already payed",
        other_name="Dupont, Mr Who's sponsor",
        amount_in_cents=100,
        status="Accepté",
        active=True,
        srh_bank_id="091000100001",
    )
    already_payed.save()
    ReservationPayment(reservation=reservations[0], payment=already_payed, confirmation_sent_timestamp=None).save()

    return event, choices, reservations


class IntegrationTestCases(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.event, cls.choices, cls.reservations = fill_db()

    def test_Reservation__count_choices(self):
        for reservation_idx, expected_count in ((0, 5), (1, 1), (2, 1)):
            reservation = self.reservations[reservation_idx]
            with self.subTest(reservation=reservation):
                self.assertEqual(reservation.places, expected_count)

    def test_Reservation_remaining_amount_due_in_cents(self):
        self.assertEqual(self.reservations[0].remaining_amount_due_in_cents(), 7800)
        self.assertEqual(self.reservations[1].remaining_amount_due_in_cents(), 2800)
        self.assertEqual(self.reservations[2].remaining_amount_due_in_cents(), 2200)


# Local Variables:
# compile-command: "uv run python ../../manage.py test concert"
# End:
