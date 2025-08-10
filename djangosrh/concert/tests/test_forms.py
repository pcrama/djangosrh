from datetime import datetime, timezone
from typing import Mapping

from django.test import TestCase

from core.models import (
    Civility,
)
from ..models import (
    Choice,
    Event,
    Choice,
    Reservation,
    ReservationChoiceCount,
)
from ..forms import ReservationForm

from .test_models import fill_db

class IntegrationTestCases(TestCase):
    event: Event
    choices: list[Choice]
    reservations: list[Reservation]

    @staticmethod
    def get_input(rsrvtn: ReservationForm, choice_display_text: str) -> ReservationForm.Input:
        return next(inpt for inpt in rsrvtn.choices
                    if inpt.choice.display_text == choice_display_text)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.event, cls.choices, cls.reservations = fill_db()

    def test_ReservationForm__empty_form(self):
        reservation = ReservationForm(self.event)
        self.assertEqual(len(reservation.choices), 3)
        for choice_display_text in ("<>Adulte<>", "<>Enfant<>", "<>Étudiant<>"):
            input_ = self.get_input(reservation, choice_display_text)
            self.assertEqual(input_.errors, [])
            self.assertEqual(input_.value, 0)
            self.assertEqual(input_.choice.display_text, choice_display_text)
            self.assertRegex(input_.id, f"_ch_{input_.choice.id}$")
        
    def test_ReservationForm__too_many_adults_and_non_numeric_children(self):
        # get input names from empty form
        blank_reservation = ReservationForm(self.event)
        adultes = self.get_input(blank_reservation, "<>Adulte<>")
        enfants = self.get_input(blank_reservation, "<>Enfant<>")
        etudiants = self.get_input(blank_reservation, "<>Étudiant<>")
        reservation = ReservationForm(self.event, {
            adultes.name: "99",
            enfants.name: "xxyyzz",
            "last_name": "Last Name (too many adulte places)",
            "email": "too@many.adult.es",
        })
        
        self.assertFalse(reservation.is_valid())
        input_ = self.get_input(reservation, "<>Adulte<>")
        self.assertEqual(len(input_.errors), 1)
        self.assertEqual(input_.value, 99)
        input_ = self.get_input(reservation, "<>Enfant<>")
        self.assertEqual(len(input_.errors), 1)
        self.assertEqual(input_.value, 0)
        input_ = self.get_input(reservation, "<>Étudiant<>")
        self.assertEqual(len(input_.errors), 0)
        self.assertEqual(input_.value, 0)
        self.assertEqual(reservation.last_name.value, "Last Name (too many adulte places)")
        self.assertEqual(reservation.first_name.value, "")
        self.assertEqual(reservation.email.value, "too@many.adult.es")
        self.assertFalse(reservation.accepts_rgpd_reuse.value)

        data = reservation.save()
        self.assertIsNone(data)

    def test_ReservationForm__valid_3_adultes_2_enfants_1_etudiant(self):
        # get input names from empty form
        blank_reservation = ReservationForm(self.event)
        adultes = self.get_input(blank_reservation, "<>Adulte<>")
        enfants = self.get_input(blank_reservation, "<>Enfant<>")
        etudiants = self.get_input(blank_reservation, "<>Étudiant<>")
        reservation = ReservationForm(self.event, {
            adultes.name: "3",
            enfants.name: "2",
            etudiants.name: "1",
            "last_name": "Last Name (3+2+1)",
            "accepts_rgpd_reuse": "yes",
            "first_name": "Primus",
            "email": "three@two.o.ne",
        })
        
        self.assertTrue(reservation.is_valid())
        input_ = self.get_input(reservation, "<>Adulte<>")
        self.assertEqual(input_.errors, [])
        self.assertEqual(input_.value, 3)
        input_ = self.get_input(reservation, "<>Enfant<>")
        self.assertEqual(input_.errors, [])
        self.assertEqual(input_.value, 2)
        input_ = self.get_input(reservation, "<>Étudiant<>")
        self.assertEqual(input_.errors, [])
        self.assertEqual(input_.value, 1)
        self.assertEqual(reservation.last_name.value, "Last Name (3+2+1)")
        self.assertEqual(reservation.first_name.value, "Primus")
        self.assertEqual(reservation.email.value, "three@two.o.ne")
        self.assertTrue(reservation.accepts_rgpd_reuse.value)

        data = reservation.save()
        self.assertIsNotNone(data)
        self.assertEqual(data.event, self.event)
        self.assertEqual(data.total_due_in_cents, 3 * 1500 + 1 * 1000)
        self.assertEqual(data.places, 6)
        self.assertEqual(data.remaining_amount_due_in_cents(), data.total_due_in_cents)

# Local Variables:
# compile-command: "uv run python ../../manage.py test concert"
# End:
