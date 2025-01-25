from datetime import datetime, timezone
from typing import Mapping

from django.test import TestCase

from ..models import (
    Choice,
    Civility,
    DishType,
    Event,
    Item,
    Reservation,
    ReservationItemCount,
)
from ..forms import ReservationForm

from .test_models import fill_db

class IntegrationTestCases(TestCase):
    event: Event
    items: list[Item]
    choices: list[tuple[Choice, list[Item]]]
    reservations: list[Reservation]

    @staticmethod
    def get_pack(rsrvtn: ReservationForm, choice_display_text: str) -> ReservationForm.Pack:
        return next(pack for pack in rsrvtn.packs
                    if pack.choice.display_text == choice_display_text)

    @staticmethod
    def get_input(pack: ReservationForm.Pack | Mapping[str, list[ReservationForm.Input]], dish_type: str, item_display_text: str) -> ReservationForm.Input:
        item_map = pack.items if isinstance(pack, ReservationForm.Pack) else pack
        return next(input_ for input_ in item_map[dish_type]
                    if input_.item.display_text == item_display_text)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.event, cls.items, cls.choices, cls.reservations = fill_db()

    def test_ReservationForm__empty_form(self):
        reservation = ReservationForm(self.event)
        self.assertEqual(len(reservation.packs), 4)
        for choice_display_text, input_dicts in (
                ("<c>Child menu<c>",
                 {"dt1main": ["<>Bolo<>", "<>Vegetarian<>"],
                  "dt2dessert": ["<>Tiramisu<>", "<>Glace<>"],
                  "dt0starter": []}),
                ("<c>Bolo menu<c>",
                 {"dt1main": ["<>Bolo<>"],
                  "dt2dessert": ["<>Tiramisu<>"],
                  "dt0starter": ["<>Tomate Mozza<>", "<>Croquettes<>"]}),
                ("<c>Scampi menu<c>",
                 {"dt1main": ["<>Scampis<>"],
                  "dt2dessert": ["<>Tiramisu<>"],
                  "dt0starter": ["<>Tomate Mozza<>", "<>Croquettes<>"]}),
                ("<c>Anything goes menu<c>",
                 {"dt1main": ["<>Bolo<>", "<>Scampis<>", "<>Vegetarian<>"],
                  "dt2dessert": ["<>Tiramisu<>", "<>Glace<>"],
                  "dt0starter": ["<>Tomate Mozza<>", "<>Croquettes<>"]})
        ):
            pack = self.get_pack(reservation, choice_display_text)
            self.assertEqual(pack.errors, [])
            for dish_type, item_display_texts in input_dicts.items():
                self.assertEqual(len(pack.items[dish_type]), len(item_display_texts))
                for item_display_text in item_display_texts:
                    input_ = self.get_input(pack, dish_type, item_display_text)
                    self.assertEqual(input_.errors, [])
                    self.assertEqual(input_.value, 0)
                    self.assertEqual(input_.choice.display_text, choice_display_text)
                    self.assertIn(f"ch_{pack.choice.id}_", input_.id)
                    self.assertRegex(input_.id, f"_it_{input_.item.id}$")

    def test_ReservationForm__valid_3_bolo_menus(self):
        # get input names from empty form
        blank_reservation = ReservationForm(self.event)
        pack = self.get_pack(blank_reservation, "<c>Bolo menu<c>")
        tomate_mozza = self.get_input(pack, "dt0starter", "<>Tomate Mozza<>")
        croquettes = self.get_input(pack, "dt0starter", "<>Croquettes<>")
        bolo = self.get_input(pack, "dt1main", "<>Bolo<>")
        tiramisu = self.get_input(pack, "dt2dessert", "<>Tiramisu<>")

        reservation = ReservationForm(self.event, {
            tomate_mozza.name: "1",
            croquettes.name: "2",
            bolo.name: "3",
            tiramisu.name: "3",
            blank_reservation.last_name.name: "Last Name (valid 3 bolo)",
            blank_reservation.places.name: "4",
            blank_reservation.email.name: "valid@three.bolo.com",
            blank_reservation.extra_comment.name: "4th person eats?",
        })
        
        pack = self.get_pack(reservation, "<c>Bolo menu<c>")
        self.assertEqual(pack.errors, [])

        tomate_mozza = self.get_input(pack, "dt0starter", "<>Tomate Mozza<>")
        croquettes = self.get_input(pack, "dt0starter", "<>Croquettes<>")
        bolo = self.get_input(pack, "dt1main", "<>Bolo<>")
        tiramisu = self.get_input(pack, "dt2dessert", "<>Tiramisu<>")

        self.assertEqual(tomate_mozza.value, 1)
        self.assertEqual(croquettes.value, 2)
        self.assertEqual(bolo.value, 3)
        self.assertEqual(tiramisu.value, 3)
        self.assertTrue(reservation.is_valid())
        self.assertEqual(reservation.total_due_in_cents, 6600)
        self.assertEqual(reservation.civility.value, "")
        self.assertEqual(reservation.last_name.value, "Last Name (valid 3 bolo)")
        self.assertEqual(reservation.first_name.value, "")
        self.assertEqual(reservation.places.value, 4)
        self.assertEqual(reservation.email.value, "valid@three.bolo.com")
        self.assertEqual(reservation.extra_comment.value, "4th person eats?")

        data = reservation.save()
        self.assertIsNotNone(data)
        self.assertEqual(data.civility, "")
        self.assertEqual(data.last_name ,"Last Name (valid 3 bolo)")
        self.assertEqual(data.first_name, "")
        self.assertEqual(data.email, "valid@three.bolo.com")
        self.assertFalse(data.accepts_rgpd_reuse)
        self.assertEqual(data.places, 4)
        self.assertEqual(data.total_due_in_cents, 6600)
        self.assertEqual(data.extra_comment, "4th person eats?")
        
    def test_ReservationForm__too_many_tomate_mozzas(self):
        # get input names from empty form
        blank_reservation = ReservationForm(self.event)
        pack = self.get_pack(blank_reservation, "<c>Bolo menu<c>")
        tomate_mozza = self.get_input(pack, "dt0starter", "<>Tomate Mozza<>")
        single_mozza = self.get_input(blank_reservation.single_items, "dt0starter", "<>Tomate Mozza<>")
        reservation = ReservationForm(self.event, {
            tomate_mozza.name: "99",
            single_mozza.name: "21",
            "last_name": "Last Name (too many tomate mozzas)",
            "places": "99",
            "email": "too@many.tomato.es",
        })
        
        self.assertFalse(reservation.is_valid())
        pack = self.get_pack(reservation, "<c>Bolo menu<c>")
        self.assertEqual(len(pack.errors), 1)
        tomate_mozza = self.get_input(pack, "dt0starter", "<>Tomate Mozza<>")
        self.assertEqual(len(tomate_mozza.errors), 1)
        croquettes = self.get_input(pack, "dt0starter", "<>Croquettes<>")
        self.assertEqual(len(croquettes.errors), 0)
        single_mozza = self.get_input(reservation.single_items, "dt0starter", "<>Tomate Mozza<>")
        self.assertEqual(len(single_mozza.errors), 1)
        self.assertEqual(tomate_mozza.value, 99)
        self.assertEqual(croquettes.value, 0)
        self.assertEqual(single_mozza.value, 21)
        self.assertEqual(reservation.last_name.value, "Last Name (too many tomate mozzas)")
        self.assertEqual(reservation.first_name.value, "")
        self.assertEqual(reservation.places.value, 99)
        self.assertEqual(len(reservation.places.errors), 1)
        self.assertEqual(reservation.email.value, "too@many.tomato.es")
        self.assertFalse(reservation.accepts_rgpd_reuse.value)

        data = reservation.save()
        self.assertIsNone(data)

    def test_ReservationForm__valid_3_anything_goes_menus_and_single_croquettes_and_double_tiramisu(self):
        # get input names from empty form
        blank_reservation = ReservationForm(self.event)
        pack = self.get_pack(blank_reservation, "<c>Anything goes menu<c>")
        tomate_mozza = self.get_input(pack, "dt0starter", "<>Tomate Mozza<>")
        croquettes = self.get_input(pack, "dt0starter", "<>Croquettes<>")
        bolo = self.get_input(pack, "dt1main", "<>Bolo<>")
        vegetarian = self.get_input(pack, "dt1main", "<>Vegetarian<>")
        scampis = self.get_input(pack, "dt1main", "<>Scampis<>")
        tiramisu = self.get_input(pack, "dt2dessert", "<>Tiramisu<>")
        glace = self.get_input(pack, "dt2dessert", "<>Glace<>")
        a_la_carte_croquettes = self.get_input(blank_reservation.single_items, "dt0starter", "<>Croquettes<>")
        a_la_carte_tiramisu = self.get_input(blank_reservation.single_items, "dt2dessert", "<>Tiramisu<>")

        reservation = ReservationForm(self.event, {
            tomate_mozza.name: "1",
            croquettes.name: "2",
            bolo.name: "1",
            vegetarian.name: "1",
            scampis.name: "1",
            tiramisu.name: "2",
            glace.name: "1",
            a_la_carte_croquettes.name: "1",
            a_la_carte_tiramisu.name: "2",
            blank_reservation.last_name.name: "Last Name (valid 3 anything)",
            blank_reservation.places.name: "3",
            blank_reservation.email.name: "valid@three.anything.com",
            blank_reservation.civility.name: "Mlle",
            blank_reservation.first_name.name: "First Name",
            blank_reservation.accepts_rgpd_reuse.name: "yes",
        })
        
        pack = self.get_pack(reservation, "<c>Anything goes menu<c>")
        self.assertEqual(pack.errors, [])

        tomate_mozza = self.get_input(pack, "dt0starter", "<>Tomate Mozza<>")
        croquettes = self.get_input(pack, "dt0starter", "<>Croquettes<>")
        bolo = self.get_input(pack, "dt1main", "<>Bolo<>")
        vegetarian = self.get_input(pack, "dt1main", "<>Vegetarian<>")
        scampis = self.get_input(pack, "dt1main", "<>Scampis<>")
        tiramisu = self.get_input(pack, "dt2dessert", "<>Tiramisu<>")
        glace = self.get_input(pack, "dt2dessert", "<>Glace<>")
        a_la_carte_croquettes = self.get_input(reservation.single_items, "dt0starter", "<>Croquettes<>")
        a_la_carte_tiramisu = self.get_input(reservation.single_items, "dt2dessert", "<>Tiramisu<>")

        self.assertEqual(tomate_mozza.value, 1)
        self.assertEqual(croquettes.value, 2)
        self.assertEqual(bolo.value, 1)
        self.assertEqual(vegetarian.value, 1)
        self.assertEqual(scampis.value, 1)
        self.assertEqual(tiramisu.value, 2)
        self.assertEqual(glace.value, 1)
        self.assertEqual(a_la_carte_croquettes.value, 1)
        self.assertEqual(a_la_carte_tiramisu.value, 2)
        self.assertTrue(reservation.is_valid())
        self.assertEqual(reservation.total_due_in_cents, 3 * 2500 + 800 + 2 * 600)
        self.assertEqual(reservation.last_name.value, "Last Name (valid 3 anything)")
        self.assertEqual(reservation.first_name.value, "First Name")
        self.assertEqual(reservation.places.value, 3)
        self.assertEqual(reservation.email.value, "valid@three.anything.com")
        self.assertTrue(reservation.accepts_rgpd_reuse.value)

        data = reservation.save()
        self.assertIsNotNone(data)
        self.assertEqual(data.civility, "Mlle")
        self.assertEqual(data.last_name ,"Last Name (valid 3 anything)")
        self.assertEqual(data.first_name, "First Name")
        self.assertEqual(data.email, "valid@three.anything.com")
        self.assertTrue(data.accepts_rgpd_reuse)
        self.assertEqual(data.places, 3)
        self.assertEqual(data.extra_comment, "")
        self.assertEqual(data.count_items(self.items[0]), 1)
        self.assertEqual(data.count_items(self.items[1]), 2 + 1)
        self.assertEqual(data.count_items(self.items[2]), 1)
        self.assertEqual(data.count_items(self.items[3]), 1)
        self.assertEqual(data.count_items(self.items[4]), 1)
        self.assertEqual(data.count_items(self.items[5]), 2 + 2)
        self.assertEqual(data.count_items(self.items[6]), 1)
