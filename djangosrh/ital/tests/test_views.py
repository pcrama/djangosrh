from datetime import date, datetime, timezone
from typing import Mapping
from uuid import uuid4

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from core.models import Payment, ReservationPayment
from core.models import get_reservations_with_likely_payments
from ..forms import ReservationForm
from ..models import (
    Choice,
    DishType,
    Event,
    Item,
    Reservation,
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


class GetExportCsvWithExampleList(TestCase):
    user: User
    test_url: str

    def setUp(self):
        super().setUp()
        event, *_ = fill_db()
        self.user = User.objects.create_user("john", "lennon@thebeatles.com", "johnpassword")
        self.test_url = reverse('ital:export_csv', kwargs={'event_id': event.id})

    def test_no_login__redirects(self):
        c = Client()
        response = c.get(self.test_url, follow=True)
        self.assertEqual(response.redirect_chain,
                         [(f'/login?next={self.test_url}', 302),
                          (f'/login/?next={self.test_url.replace("/", "%2F")}', 301)])
        self.assertNotEqual(len(response.content), 0)

    def test_after_login__lists_reservations(self):
        c = Client()
        c.force_login(self.user)
        response = c.get(self.test_url, follow=False)
        self.assertEqual(response.content.decode('utf8'),
                         'Nom,Places,Valeur,Déjà payé,Restant dû,Tomate Mozza,Croquettes,Bolo,Scampis,Vegetarian,Tiramisu,Glace,Commentaire\r\n'
                         'Priv Ate,1,22.00€,0.00€,22.00€,0,1,1,0,0,1,0,th¡rd\r\n'
                         'Mme Lara Croft,3,28.00€,0.00€,28.00€,0,1,1,0,0,2,0,\r\n'
                         'Mr Dupont,2,79.00€,1.00€,78.00€,2,1,0,1,1,1,1,First reservation\r\n')


class ReservationFormViewTests(TestCase):
    event: Event
    items: list[Item]
    choices_to_items: list[tuple[Choice, list[Item]]]
    reservations: list[Reservation]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.event, cls.items, cls.choices_to_items, cls.reservations = fill_db()

    def setUp(self):
        self.client = Client()

    def test_get_reservation_form_ok(self):
        """GET should render the reservation form."""
        url = reverse("ital:reservation_form", args=[self.event.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ital/reservation_form.html")
        self.assertContains(response, "Souper Italien")

    def test_post_email_with_underscore_and_dash_is_accepted(self):
        unique_email = f"jo_hn{uuid4().hex}-da.sh+plus@example.com"
        url = reverse("ital:reservation_form", args=[self.event.id])
        blank_reservation = ReservationForm(self.event) # get input names from empty form
        pack0items = blank_reservation.packs[0].items
        post_data = {
            "civility": "Mr",
            "first_name": "John",
            "last_name": "Doe",
            "email": unique_email,
            "places": "2",
            pack0items[DishType.DT1MAIN][0].name: "2",
            pack0items[DishType.DT2DESSERT][0].name: "2",
        }
        try:
            post_data[pack0items[DishType.DT0STARTER][0].name] = "2"
        except (KeyError, IndexError):
            pass
        response = self.client.post(url, data=post_data)
        self.assertEqual(response.status_code, 302)
        reservation = Reservation.objects.get(email=unique_email)
        self.assertIsNotNone(reservation)
        self.assertIn(str(reservation.uuid), response.url)
        self.assertEqual(reservation.first_name, "John")
        self.assertEqual(reservation.last_name, "Doe")
        self.assertEqual(reservation.email, unique_email)

# Local Variables:
# compile-command: "uv run python ../../manage.py test ital"
# End:
