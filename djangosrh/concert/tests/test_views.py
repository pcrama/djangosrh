from datetime import date, datetime, timezone
from uuid import uuid4

from django.contrib.auth.models import User
from django.core import mail
from django.test import Client, TestCase
from django.urls import reverse

from core.models import Payment, ReservationPayment
from core.models import get_reservations_with_likely_payments
from ..forms import ReservationForm
from ..models import (
    Choice,
    Event,
    Reservation,
)

from .test_models import fill_db


class IndexView(TestCase):
    event: Event
    choices: list[Choice]
    reservations: list[Reservation]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.event, cls.choices, cls.reservations = fill_db()
        cls.test_url = reverse("concert:index")

    def setUp(self):
        self.client = Client()

    def test_with_two_enabled_events(self):
        response = self.client.get(self.test_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "concert/index.html")
        self.assertContains(response, "Gala (Samedi)")
        self.assertContains(response, "Gala (Dimanche)")

    def test_with_disabled_event(self):
        Event(
            name="Gala (Disabled)",
            date=datetime(2025, 11, 11, 17, 0, 0, tzinfo=timezone.utc),
            contact_email="dont-spam@me.com",
            max_seats=200,
            disabled=True,
        ).save()

        response = self.client.get(self.test_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "concert/index.html")
        self.assertContains(response, "Gala (Samedi)")
        self.assertContains(response, "Gala (Dimanche)")
        self.assertNotContains(response, "Gala (Disabled)")


class ReservationFormViewTests(TestCase):
    event: Event
    choices: list[Choice]
    reservations: list[Reservation]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.event, cls.choices, cls.reservations = fill_db()

    def setUp(self):
        self.client = Client()

    def test_get_reservation_form_ok(self):
        """GET should render the reservation form."""
        url = reverse("concert:reservation_form", args=[self.event.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "concert/reservation_form.html")
        self.assertContains(response, "Gala (Samedi)")

    def test_get_reservation_form_disabled_event(self):
        """If event is disabled, should render event_disabled template."""
        self.event.disabled = True
        self.event.save()
        url = reverse("concert:reservation_form", args=[self.event.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "concert/event_disabled.html")

    def test_get_reservation_form_disabled_for_overcrowded_event(self):
        """If event is overcrowded, should render event_disabled template."""
        self.event.max_seats = -1
        self.event.save()
        url = reverse("concert:reservation_form", args=[self.event.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "concert/event_disabled.html")

    def test_post_valid_reservation_redirects(self):
        """Posting a valid reservation should create Reservation and redirect."""
        unique_email = f"john.{uuid4().hex}@example.com"
        url = reverse("concert:reservation_form", args=[self.event.id])
        blank_reservation = ReservationForm(self.event) # get input names from empty form
        post_data = {
            "civility": "Mr",
            "first_name": "John",
            "last_name": "Doe",
            "email": unique_email,
                    blank_reservation.choices[0].id: "2",
        }
        response = self.client.post(url, data=post_data)
        self.assertEqual(response.status_code, 302)
        reservation = Reservation.objects.get(email=unique_email)
        self.assertIsNotNone(reservation)
        self.assertIn(str(reservation.uuid), response.url)

    def test_post_invalid_reservation_rerenders_with_user_input(self):
        """Posting invalid data should re-render the form with 422."""
        invalid_unique_email = f"john+{uuid4().hex}@@x.y"
        url = reverse("concert:reservation_form", args=[self.event.id])
        post_data = {
            "civility": "Mr",
            "email": invalid_unique_email,
        }
        response = self.client.post(url, data=post_data)
        self.assertTemplateUsed(response, "concert/reservation_form.html")
        for fragment in (
                '<span class="invalid-feedback">Mandatory field</span>',
                f'value="{invalid_unique_email}"',
                '<span class="invalid-feedback">Invalid email</span>',
        ):
            self.assertContains(response, fragment, status_code=422)

    def test_double_reservation_detected(self):
        """After posting a valid reservation, a second GET should show double_reservation template."""
        url = reverse("concert:reservation_form", args=[self.event.id])
        blank_reservation = ReservationForm(self.event) # get input names from empty form

        # 1. Make a valid POST to create a reservation
        post_data = {
            "civility": "Mr",
            "first_name": "Alice",
            "last_name": "Smith",
            "email": "alice@example.com",
            blank_reservation.choices[0].id: "1",
        }
        response = self.client.post(url, data=post_data)
        self.assertEqual(response.status_code, 302)
        reservation = Reservation.objects.get(last_name="Smith")

        # 2. Immediately call GET again -> should detect recent reservation
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "concert/double_reservation.html")
        self.assertContains(response, "Alice")
        self.assertContains(response, reservation.uuid)


class ShowReservationViewTests(TestCase):
    event: Event
    choices: list[Choice]
    reservations: list[Reservation]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.event, cls.choices, cls.reservations = fill_db()

    def setUp(self):
        self.client = Client()

    def test_show_reservation_template_and_choices_with_partial_payment(self):
        """It should render the show_reservation page with the right choices and amounts."""
        url = reverse("concert:show_reservation", args=[self.reservations[0].uuid])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "concert/show_reservation.html")

        for fragment in (
                # Check the choices are listed with correct plural form
                "2 P(Adulte)", "2 P(Enfant)", "1 &lt;&gt;Étudiant&lt;&gt;",
                # remaining amount due
                "dont 78.00",
                # total amount due
                "prix total est de 79.00",
        ):
            self.assertContains(response, fragment)

    def test_show_reservation_template_and_choices_without_any_payment(self):
        """It should render the show_reservation page with the right choices and amounts."""
        url = reverse("concert:show_reservation", args=[self.reservations[1].uuid])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "concert/show_reservation.html")

        for fragment in (
                # Check the choices are listed with correct plural form
                "1 &lt;&gt;Adulte&lt;&gt;", # "2 P(Enfant)", "1 &lt;&gt;Étudiant&lt;&gt;",
                "<code>+++092/0002/00002+++</code>",
                # total amount due
                "prix total est de 28.00",
        ):
            self.assertContains(response, fragment)
        for fragment in (
                # no amount payed yet:
                " dont ", "déjà pay",
                # no other choices
                "Enfant", "Étudiant",
        ):
            self.assertNotContains(response, fragment)

    def test_show_reservation_contains_qrcodes(self):
        """It should embed QR codes in the page (payment and page)."""
        url = reverse("concert:show_reservation", args=[self.reservations[0].uuid])
        response = self.client.get(url)
        # The view produces SVG-based QR codes
        self.assertIn("<svg ", response.content.decode())
        self.assertIn("<path ", response.content.decode())


class AdminTestCase(TestCase):
    event: Event
    choices: list[Choice]
    reservations: list[Reservation]
    user: User
    test_url: str

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user("john", "lennon@thebeatles.com", "johnpassword")
        cls.event, cls.choices, cls.reservations = fill_db()

    def setUp(self):
        self.client = Client()

    def do_test_no_login__redirects(self):
        response = self.client.get(self.test_url, follow=True)
        self.assertEqual(response.redirect_chain,
                         [(f'/login?next={self.test_url}', 302),
                          (f'/login/?next={self.test_url.replace("/", "%2F")}', 301)])
        self.assertNotEqual(len(response.content), 0)


class GetExportCsvWithExampleList(AdminTestCase):
    test_url: str

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        self.test_url = reverse('concert:export_csv', kwargs={'event_id': self.event.id})

    def test_no_login__redirects(self):
        self.do_test_no_login__redirects()

    def test_after_login__lists_reservations(self):
        self.client.force_login(self.user)
        response = self.client.get(self.test_url, follow=False)
        self.assertEqual(response.content.decode('utf8'),
                         'Nom,Places,Valeur,Déjà payé,Restant dû,Adulte,Enfant,Étudiant,Commentaire\r\n'
                         'Priv Ate,1,22.00€,0.00€,22.00€,0,0,1,\r\n'
                         'Mme Lara Croft,1,28.00€,0.00€,28.00€,1,0,0,\r\n'
                         'Mr Dupont,5,79.00€,1.00€,78.00€,2,2,1,"Places offertes, donc ""gratuites"""\r\n')


class ReservationList(AdminTestCase):
    test_url: str

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_url = reverse("concert:reservations")

    def test_no_login__redirects(self):
        self.do_test_no_login__redirects()

    def test_after_login__lists_reservations_of_default_event(self):
        self.client.force_login(self.user)
        response = self.client.get(self.test_url, follow=False)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "concert/reservations.html")
        self.assertEqual(
            [res.likely_payment_id for res in response.context["object_list"]],
            [Payment.objects.get(src_id="2025-09123").id,
             None,
             Payment.objects.get(src_id="2025-0901").id])

    def test_after_login__404_if_no_such_event(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("concert:reservations") + "?event_id=Does-NOT-exist", follow=False)
        self.assertEqual(response.status_code, 404)
        response = self.client.get(reverse("concert:reservations") + "?event_id=-9999", follow=False)
        self.assertEqual(response.status_code, 404)


class SendPaymentReceptionConfirmation(AdminTestCase):
    event: Event
    choices: list[Choice]
    reservations: list[Reservation]
    test_url: str
    payment: Payment
    user: User

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_url = reverse("concert:send_payment_reception_confirmation")
        cls.payment = Payment.objects.get(bank_ref="202502221234560001")

    def test_no_login__redirects(self):
        self.do_test_no_login__redirects()

    def test_GET_after_login__redirects_to_reservations_list(self):
        self.client.force_login(self.user)
        response = self.client.get(self.test_url, follow=False)
        self.assertEqual(response.url, "/concert/reservations")
        self.assertEqual(len(mail.outbox), 0)

    def test_404_if_payment_does_not_exist(self):
        """POST should return 404 if payment does not exist"""
        self.client.force_login(self.user)
        payment_id = 9999
        response = self.client.post(
            reverse("concert:send_payment_reception_confirmation"),
            {"payment_id": payment_id, "reservation_id": self.reservations[0].id},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(len(mail.outbox), 0)
        self.assertRaises(
            ReservationPayment.DoesNotExist, ReservationPayment.objects.get, payment_id=self.payment.id)

    def test_404_if_reservation_does_not_exist(self):
        """POST should return 404 if reservation does not exist"""
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("concert:send_payment_reception_confirmation"),
            {"payment_id": self.payment.id, "reservation_id": 9999},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(len(mail.outbox), 0)
        self.assertRaises(
            ReservationPayment.DoesNotExist, ReservationPayment.objects.get, payment_id=self.payment.id)

    def test_mail_sent_if_payment_and_reservation_exist(self):
        """Mail should be sent and redirect if payment and reservation exist"""
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("concert:send_payment_reception_confirmation"),
            {"payment_id": self.payment.id, "reservation_id": self.reservations[0].id},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)

        sent_email = mail.outbox[0]
        self.assertIn("Merci pour votre paiement", sent_email.subject)
        self.assertIn("dupont@yopmail.fr", sent_email.to)
        self.assertIn("dont-spam@me.com", sent_email.cc)
        self.assertIsNotNone(ReservationPayment.objects.get(payment_id=self.payment.id))


class GetReservationsWithLikelyPayments091000100001_after_1st_payment_linked(TestCase):
    event: Event
    choices: list[Choice]
    reservations: list[Reservation]
    expected_account = "Mr Who's bank account"
    expected_name = "Mr Who"
    expected_amount_in_cents = 2345
    expected_src_id = "2025-09123"

    def setUp(self):
        super().setUp()
        self.event, self.choices, self.reservations = fill_db()

    def test_get_reservations_with_likely_payments(self):
        reservations = list(get_reservations_with_likely_payments(date(2025, 9, 1), Reservation.objects))
        res1 = next(res for res in reservations if res.bank_id == self.reservations[0].bank_id)
        if self.expected_src_id:
            self.assertEqual(res1.likely_payment_id, Payment.objects.get(src_id=self.expected_src_id).id)
        else:
            self.assertIsNone(res1.likely_payment_id)
        self.assertEqual(res1.likely_payment_other_account, self.expected_account)
        self.assertEqual(res1.likely_payment_other_name, self.expected_name)
        self.assertEqual(res1.likely_payment_amount_in_cents, self.expected_amount_in_cents)
        self.assertEqual(res1.likely_payment_src_id, self.expected_src_id)


class GetReservationsWithLikelyPayments091000100001_after_2nd_payment_linked(
        GetReservationsWithLikelyPayments091000100001_after_1st_payment_linked):
    event: Event
    choices: list[Choice]
    reservations: list[Reservation]
    expected_account = ""
    expected_name = "Dupont"
    expected_amount_in_cents = 5455
    expected_src_id = "2025-09124"

    def setUp(self):
        super().setUp()
        ReservationPayment(reservation=self.reservations[0], payment=Payment.objects.get(src_id="2025-09123")).save()


class GetReservationsWithLikelyPayments091000100001_after_3rd_payment_linked(
        GetReservationsWithLikelyPayments091000100001_after_2nd_payment_linked):
    event: Event
    choices: list[Choice]
    reservations: list[Reservation]
    expected_account = None
    expected_name = None
    expected_amount_in_cents = None
    expected_src_id = None

    def setUp(self):
        super().setUp()
        ReservationPayment(reservation=self.reservations[0], payment=Payment.objects.get(src_id="2025-09124")).save()


class GetReservationsWithLikelyPayments092000200002(TestCase):
    event: Event
    choices: list[Choice]
    reservations: list[Reservation]

    def setUp(self):
        super().setUp()
        self.event, self.choices, self.reservations = fill_db()

    def test_get_reservations_with_likely_payments(self):
        reservations = list(get_reservations_with_likely_payments(date(2025, 9, 1), Reservation.objects))
        res2 = next(res for res in reservations if res.bank_id == self.reservations[1].bank_id)
        self.assertIsNone(res2.likely_payment_other_account)
        self.assertIsNone(res2.likely_payment_other_name)
        self.assertIsNone(res2.likely_payment_amount_in_cents)
        self.assertIsNone(res2.likely_payment_src_id)


class GetReservationsWithLikelyPayments093000300003(TestCase):
    event: Event
    choices: list[Choice]
    reservations: list[Reservation]
    expected_account = "BE00 1234 1234 1234 2134"
    expected_name = "Priv Ate's bank account"
    expected_amount_in_cents = 2200
    expected_src_id = "2025-0901"

    def setUp(self):
        super().setUp()
        self.event, self.choices, self.reservations = fill_db()

    def test_get_reservations_with_likely_payments(self):
        reservations = list(get_reservations_with_likely_payments(date(2025, 9, 1), Reservation.objects))
        res3 = next(res for res in reservations if res.bank_id == self.reservations[2].bank_id)
        self.assertEqual(res3.likely_payment_other_account, self.expected_account)
        self.assertEqual(res3.likely_payment_other_name, self.expected_name)
        self.assertEqual(res3.likely_payment_amount_in_cents, self.expected_amount_in_cents)
        self.assertEqual(res3.likely_payment_src_id, self.expected_src_id)


class GetReservationsWithLikelyPayments093000300003_after_1st_payment_linked(
        GetReservationsWithLikelyPayments093000300003):
    event: Event
    choices: list[Choice]
    reservations: list[Reservation]
    expected_account = None
    expected_name = None
    expected_amount_in_cents = None
    expected_src_id = None

    def setUp(self):
        super().setUp()
        ReservationPayment(reservation=self.reservations[2], payment=Payment.objects.get(src_id="2025-0901")).save()

# Local Variables:
# compile-command: "uv run python ../../manage.py test concert"
# End:
