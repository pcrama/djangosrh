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
            "last_name": "Last Name (valid 3 bolo)",
            "places": "3",
            "email": "valid@three.bolo.com",
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
            "last_name": "Last Name (valid 3 anything)",
            "places": "3",
            "email": "valid@three.anything.com",
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
