from datetime import date, datetime, timezone
from typing import Mapping

from django.test import TestCase

from core.models import Payment
from ..views import get_reservations_with_likely_payments
from ..models import (
    Choice,
    Event,
    Item,
    Reservation,
    ReservationPayment,
)

from .test_models import fill_db

class GetReservationsWithLikelyPayments001000100001_after_1st_payment_linked(TestCase):
    event: Event
    items: list[Item]
    choices: list[tuple[Choice, list[Item]]]
    reservations: list[Reservation]
    expected_account = "Mr Who's bank account"
    expected_name = "Mr Who"
    expected_amount_in_cents = 2345
    expected_src_id = "2025-00123"

    def setUp(self):
        super().setUp()
        self.event, self.items, self.choices, self.reservations = fill_db()

    def test_get_reservations_with_likely_payments(self):
        reservations = list(get_reservations_with_likely_payments(date(2025, 2, 12), Reservation.objects))
        res1 = next(res for res in reservations if res.bank_id == self.reservations[0].bank_id)
        self.assertEqual(res1.likely_payment_other_account, self.expected_account)
        self.assertEqual(res1.likely_payment_other_name, self.expected_name)
        self.assertEqual(res1.likely_payment_amount_in_cents, self.expected_amount_in_cents)
        self.assertEqual(res1.likely_payment_src_id, self.expected_src_id)


class GetReservationsWithLikelyPayments001000100001_after_2nd_payment_linked(
        GetReservationsWithLikelyPayments001000100001_after_1st_payment_linked):
    event: Event
    items: list[Item]
    choices: list[tuple[Choice, list[Item]]]
    reservations: list[Reservation]
    expected_account = ""
    expected_name = "Dupont"
    expected_amount_in_cents = 5455
    expected_src_id = "2025-00124"

    def setUp(self):
        super().setUp()
        ReservationPayment(reservation=self.reservations[0], payment=Payment.objects.get(src_id="2025-00123")).save()


class GetReservationsWithLikelyPayments001000100001_after_3rd_payment_linked(
        GetReservationsWithLikelyPayments001000100001_after_2nd_payment_linked):
    event: Event
    items: list[Item]
    choices: list[tuple[Choice, list[Item]]]
    reservations: list[Reservation]
    expected_account = None
    expected_name = None
    expected_amount_in_cents = None
    expected_src_id = None

    def setUp(self):
        super().setUp()
        ReservationPayment(reservation=self.reservations[0], payment=Payment.objects.get(src_id="2025-00124")).save()


class GetReservationsWithLikelyPayments002000200002(TestCase):
    event: Event
    items: list[Item]
    choices: list[tuple[Choice, list[Item]]]
    reservations: list[Reservation]

    def setUp(self):
        super().setUp()
        self.event, self.items, self.choices, self.reservations = fill_db()

    def test_get_reservations_with_likely_payments(self):
        reservations = list(get_reservations_with_likely_payments(date(2025, 2, 12), Reservation.objects))
        res2 = next(res for res in reservations if res.bank_id == self.reservations[1].bank_id)
        self.assertIsNone(res2.likely_payment_other_account)
        self.assertIsNone(res2.likely_payment_other_name)
        self.assertIsNone(res2.likely_payment_amount_in_cents)
        self.assertIsNone(res2.likely_payment_src_id)


class GetReservationsWithLikelyPayments003000300003(TestCase):
    event: Event
    items: list[Item]
    choices: list[tuple[Choice, list[Item]]]
    reservations: list[Reservation]
    expected_account = "BE00 1234 1234 1234 2134"
    expected_name = "Priv Ate's bank account"
    expected_amount_in_cents = 2200
    expected_src_id = "2025-0001"

    def setUp(self):
        super().setUp()
        self.event, self.items, self.choices, self.reservations = fill_db()

    def test_get_reservations_with_likely_payments(self):
        reservations = list(get_reservations_with_likely_payments(date(2025, 2, 12), Reservation.objects))
        res3 = next(res for res in reservations if res.bank_id == self.reservations[2].bank_id)
        self.assertEqual(res3.likely_payment_other_account, self.expected_account)
        self.assertEqual(res3.likely_payment_other_name, self.expected_name)
        self.assertEqual(res3.likely_payment_amount_in_cents, self.expected_amount_in_cents)
        self.assertEqual(res3.likely_payment_src_id, self.expected_src_id)


class GetReservationsWithLikelyPayments003000300003_after_1st_payment_linked(
        GetReservationsWithLikelyPayments003000300003):
    event: Event
    items: list[Item]
    choices: list[tuple[Choice, list[Item]]]
    reservations: list[Reservation]
    expected_account = None
    expected_name = None
    expected_amount_in_cents = None
    expected_src_id = None

    def setUp(self):
        super().setUp()
        ReservationPayment(reservation=self.reservations[2], payment=Payment.objects.get(src_id="2025-0001")).save()


# Local Variables:
# compile-command: "uv run python ../../manage.py test ital"
# End:
