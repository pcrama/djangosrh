from datetime import date, datetime, timezone

from django.test import TestCase

from core.models import Civility, Payment, ReservationPayment
from ..models import (
    Choice,
    DishType,
    Event,
    Item,
    Reservation,
    ReservationItemCount,
)


def fill_db() -> tuple[Event, list[Item], list[tuple[Choice, list[Item]]], list[Reservation]]:
    event = Event(
        name="Souper Italien",
        date=datetime(2025, 3, 29, 1, 0, 0, tzinfo=timezone.utc),
        contact_email="dont-spam@me.com",
        max_seats=120)
    event.save()
    items = [Item(display_text=f"<>{name}<>", column_header=name, short_text=name, display_text_plural=f"P({name})", dish=dish)
             for name, dish in (("Tomate Mozza", DishType.DT0STARTER),
                       ("Croquettes", DishType.DT0STARTER),
                       ("Bolo", DishType.DT1MAIN),
                       ("Scampis", DishType.DT1MAIN),
                       ("Vegetarian", DishType.DT1MAIN),
                       ("Tiramisu", DishType.DT2DESSERT),
                       ("Glace", DishType.DT2DESSERT),
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
        event=event,
        bank_id="001000100001",
        extra_comment="First reservation",
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
        event=event,
        bank_id="002000200002",
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
        event=event,
        bank_id="003000300003",
        extra_comment="th¡rd",
    ))
    rsrvtn.save()
    for choice_idx, item_idx, count in ((5, 1, 1), (5, 2, 1), (5, 5, 1)):
        reservation_item_count = ReservationItemCount(reservation=rsrvtn, choice=choices[choice_idx][0], item=items[item_idx], count=count)
        reservation_item_count.save()
        rsrvtn.reservationitemcount_set.add(reservation_item_count)

    Payment(
        date_received=date(2025, 2, 22),
        amount_in_cents=2200,
        comment="+++003/0003/00003+++",
        src_id="2025-0001",
        bank_ref="202503221234560001",
        other_account="BE00 1234 1234 1234 2134",
        other_name="Priv Ate's bank account",
        status="Accepté",
        active=True,
        srh_bank_id="003000300003",
    ).save()
    Payment(
        date_received=date(2025, 2, 13),
        comment="001000100001",
        src_id="2025-00122",
        bank_ref="2025010000000",
        other_account="Mr Who's broken bank account",
        other_name="Mr Who refused",
        amount_in_cents=2345,
        status="Refusé",
        active=True,
        srh_bank_id="001000100001",
    ).save()
    Payment(
        date_received=date(2025, 2, 13),
        comment="001000100001",
        src_id="2025-00121",
        bank_ref="2025010000001",
        other_account="Mr Who's inactive bank account",
        other_name="Mr Who refused",
        amount_in_cents=2345,
        status="Accepté",
        active=False,
        srh_bank_id="001000100001",
    ).save()
    Payment(
        date_received=date(2025, 2, 13),
        comment="001000100001",
        src_id="2025-00123",
        bank_ref="2025032812345",
        other_account="Mr Who's bank account",
        other_name="Mr Who",
        amount_in_cents=2345,
        status="Accepté",
        active=True,
        srh_bank_id="001000100001",
    ).save()
    Payment(
        date_received=date(2025, 2, 13),
        comment="+++001/0001/00001+++",
        src_id="2025-00124",
        bank_ref="2025032812444",
        other_account="",
        other_name="Dupont",
        amount_in_cents=5455,
        status="Accepté",
        active=True,
        srh_bank_id="001000100001",
    ).save()
    already_payed = Payment(
        date_received=date(2025, 2, 13),
        comment="+++001/0001/00001+++",
        src_id="2025-00115",
        bank_ref="2025032999999",
        other_account="Mr Who already payed",
        other_name="Dupont, Mr Who's sponsor",
        amount_in_cents=100,
        status="Accepté",
        active=True,
        srh_bank_id="001000100001",
    )
    already_payed.save()
    ReservationPayment(reservation=reservations[0], payment=already_payed, confirmation_sent_timestamp=None).save()

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

    def test_event_reservation_items(self):
        self.assertEqual(
            self.event.reservation_items(),
            [
                Event.ItemSummary(id=1, display_text='<>Tomate Mozza<>', display_text_plural='P(Tomate Mozza)', column_header='Tomate Mozza', total_count=2),
                Event.ItemSummary(id=2, display_text='<>Croquettes<>', display_text_plural='P(Croquettes)', column_header='Croquettes', total_count=3),
                Event.ItemSummary(id=3, display_text='<>Bolo<>', display_text_plural='P(Bolo)', column_header='Bolo', total_count=2),
                Event.ItemSummary(id=4, display_text='<>Scampis<>', display_text_plural='P(Scampis)', column_header='Scampis', total_count=1),
                Event.ItemSummary(id=5, display_text='<>Vegetarian<>', display_text_plural='P(Vegetarian)', column_header='Vegetarian', total_count=1),
                Event.ItemSummary(id=6, display_text='<>Tiramisu<>', display_text_plural='P(Tiramisu)', column_header='Tiramisu', total_count=4),
                Event.ItemSummary(id=7, display_text='<>Glace<>', display_text_plural='P(Glace)', column_header='Glace', total_count=1)])

    def test_Reservation_remaining_amount_due_in_cents(self):
        self.assertEqual(self.reservations[0].remaining_amount_due_in_cents(), 7800)
        self.assertEqual(self.reservations[1].remaining_amount_due_in_cents(), 2800)
        self.assertEqual(self.reservations[2].remaining_amount_due_in_cents(), 2200)


# Local Variables:
# compile-command: "uv run python ../../manage.py test ital"
# End:
