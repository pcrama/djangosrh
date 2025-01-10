from datetime import datetime, timezone

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


def fill_db() -> tuple[Event, list[Item], list[Choice], list[Reservation]]:
    event = Event(name="Souper Italien", date=datetime(2025, 3, 29, 1, 0, 0, tzinfo=timezone.utc))
    event.save()
    items = [Item(display_text=f"<>{name}<>", column_header=name, short_text=name, dish=dish)
             for name, dish in (("Tomate Mozza", DishType.STARTER),
                       ("Croquettes", DishType.STARTER),
                       ("Bolo", DishType.MAIN),
                       ("Scampis", DishType.MAIN),
                       ("Vegetarian", DishType.MAIN),
                       ("Tiramisu", DishType.DESSERT),
                       ("Glace", DishType.DESSERT),
                       )]
    for item in items:
        item.save()

    choices = [(Choice(display_text=f"<c>{name}<c>", price_in_cents=100 * price_in_euro, available_in=event),
                [items[idx - 1] for idx in items_off_by_1])
               for name, price_in_euro, items_off_by_1 in
               (("Tomate Mozza (single)", 9, [1]),
                ("Croquettes (single)", 8, [2]),
                ("Bolo (single)", 12, [3]),
                ("Tiramisu (single)", 6, [6]),
                ("Child menu", 20, [3, 5, 6, 7]),
                ("Bolo menu", 22, [1, 2, 3, 6]),
                ("Scampi menu", 27, [1, 2, 4, 6]),
                ("Anything goes menu", 25, [1, 2, 3, 4, 5, 6, 7]))]
    for choice, choice_items in choices:
        choice.save()
        for item in choice_items:
            choice.item_set.add(item)

    reservations = []
    reservations.append(rsrvtn := Reservation(
        civility=Civility.man,
        first_name="",
        last_name="Dupont",
        email="dupont@yopmail.fr",
        accepts_rgpd_reuse=True,
        total_due_in_cents=7900,
        places=2,
    ))
    rsrvtn.save()
    for choice_idx, item_idx, count in (
            (6, 0, 2), (6, 3, 1), (6, 5, 1), (7, 1, 1), (7, 4, 1), (7, 6, 1)):
        reservation_item_count = ReservationItemCount(reservation=rsrvtn, choice=choices[choice_idx][0], item=items[item_idx], count=count)
        reservation_item_count.save()
        rsrvtn.reservationitemcount_set.add(reservation_item_count)

    reservations.append(rsrvtn := Reservation(
        civility=Civility.woman,
        first_name="Lara",
        last_name="Croft",
        email="tomb-raider@yopmail.fr",
        accepts_rgpd_reuse=True,
        total_due_in_cents=2800,
        places=3,
    ))
    rsrvtn.save()
    for choice_idx, item_idx, count in ((5, 1, 1), (5, 2, 1), (5, 5, 1), (3, 5, 1)):
        reservation_item_count = ReservationItemCount(reservation=rsrvtn, choice=choices[choice_idx][0], item=items[item_idx], count=count)
        reservation_item_count.save()
        rsrvtn.reservationitemcount_set.add(reservation_item_count)

    reservations.append(rsrvtn := Reservation(
        civility=Civility.__empty__,
        first_name="Priv",
        last_name="Ate",
        email="none-of@your.biz",
        accepts_rgpd_reuse=False,
        total_due_in_cents=2200,
        places=1,
    ))
    rsrvtn.save()
    for choice_idx, item_idx, count in ((5, 1, 1), (5, 2, 1), (5, 5, 1)):
        reservation_item_count = ReservationItemCount(reservation=rsrvtn, choice=choices[choice_idx][0], item=items[item_idx], count=count)
        reservation_item_count.save()
        rsrvtn.reservationitemcount_set.add(reservation_item_count)

    return event, items, choices, reservations


class IntegrationTestCases(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.event, cls.items, cls.choices, cls.reservations = fill_db()

    def test_Reservation__count_items(self):
        for reservation_idx, item_idx, expected_count in (
                (0, 0, 2),
                (0, 1, 1),
                (0, 2, 0),
                (0, 3, 1),
                (0, 4, 1),
                (0, 5, 1),
                (0, 6, 1),
                (1, 0, 0),
                (1, 1, 1),
                (1, 2, 1),
                (1, 3, 0),
                (1, 4, 0),
                (1, 5, 2),
                (1, 6, 0),
                (2, 0, 0),
                (2, 1, 1),
                (2, 2, 1),
                (2, 3, 0),
                (2, 4, 0),
                (2, 5, 1),
                (2, 6, 0),
        ):
            reservation = self.reservations[reservation_idx]
            item = self.items[item_idx]
            with self.subTest(reservation=reservation, item=item):
                self.assertEqual(reservation.count_items(item), expected_count)
