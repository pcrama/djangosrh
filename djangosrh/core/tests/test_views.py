from datetime import date
from uuid import uuid4

from django.contrib.auth.models import User
from django.core import mail
from django.test import Client, TestCase
from django.urls import reverse

from core.models import Payment, ReservationPayment
from core.models import get_reservations_with_likely_payments

from concert.tests.test_models import fill_db as fill_concert_db
from ital.tests.test_models import fill_db as fill_ital_db


class PaymentList(TestCase):
    test_url: str
    client: Client

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user("john", "lennon@thebeatles.com", "johnpassword")
        fill_concert_db()
        fill_ital_db()
        cls.test_url = reverse("payments")

    def setUp(self):
        self.client = Client()

    def test_no_login__redirects(self):
        response = self.client.get(self.test_url, follow=True)
        self.assertEqual(response.redirect_chain,
                         [(f'/login?next={self.test_url}', 302),
                          (f'/login/?next={self.test_url.replace("/", "%2F")}', 301)])
        self.assertNotEqual(len(response.content), 0)

    def test_after_login__lists_reservations_of_default_event(self):
        self.client.force_login(self.user)
        response = self.client.get(self.test_url, follow=False)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/payments.html")
