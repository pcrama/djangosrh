from datetime import datetime, timezone

from django.core.management.base import (
    BaseCommand
)

from ...models import Event, Item, Reservation
from ...tests.test_models import fill_db

class Command(BaseCommand):
    def make_db_empty(self):
        for evt in Event.objects.all():
            evt.delete()
        for it in Item.objects.all():
            it.delete()
        for res in Reservation.objects.all():
            res.delete()

    # def fill_db(self):
    #     event = Event(name="Souper Italien", date=datetime(2025, 3, 29, 1, 0, 0, tzinfo=timezone.utc))
    #     event.save()
    #     print(f"Event {event}")
    #     items = [Item(display_text=f"<>{name}<>", column_header=name, short_text=name)
    #              for name, dish in (("Tomate Mozza", DishType.STARTER),
    #                        ("Croquettes", DishType.STARTER),
    #                        ("Bolo", DishType.MAIN),
    #                        ("Scampis", DishType.MAIN),
    #                        ("Vegetarian", DishType.MAIN),
    #                        ("Tiramisu", DishType.DESSERT),
    #                        ("Glace", DishType.DESSERT),
    #                        )]
    #     for item in items:
    #         item.save()
    #         print(f"Item {item}")

    #     choices = [(Choice(display_text=f"<c>{name}<c>", price_in_cents=100 * price_in_euro, available_in=event),
    #                 [items[idx - 1] for idx in items_off_by_1])
    #                for name, price_in_euro, items_off_by_1 in
    #                (("Tomate Mozza (single)", 9, [1]),
    #                 ("Croquettes (single)", 8, [2]),
    #                 ("Bolo (single)", 12, [3]),
    #                 ("Tiramisu (single)", 6, [6]),
    #                 ("Child menu", 20, [3, 5, 6, 7]),
    #                 ("Bolo menu", 22, [1, 2, 3, 6]),
    #                 ("Scampi menu", 27, [1, 2, 4, 6]),
    #                 ("Anything goes menu", 25, [1, 2, 3, 4, 5, 6, 7]))]
    #     for choice, choice_items in choices:
    #         choice.save()
    #         for item in choice_items:
    #             choice.item_set.add(item)
    #         print(f"Choice {choice}")

    #     reservation = Reservation(
    #         civility=Civility.man,
    #         first_name="",
    #         last_name="Dupont",
    #         email="dupont@yopmail.fr",
    #         accepts_rgpd_reuse=True,
    #         total_due_in_cents=7900,
    #         places=2,
    #     )
    #     reservation.save()
    #     for choice_idx, item_idx, count in (
    #             (6, 0, 2), (6, 3, 1), (6, 5, 1), (7,1,1), (7,4,1),(7,6,1)):
    #         reservation_item_count = ReservationItemCount(reservation=reservation, choice=choices[choice_idx][0], item=items[item_idx], count=count)
    #         reservation_item_count.save()
    #         reservation.reservationitemcount_set.add(reservation_item_count)
    #     print(f"Reservation {reservation}")

    #     reservation = Reservation(
    #         civility=Civility.woman,
    #         first_name="Lara",
    #         last_name="Croft",
    #         email="tomb-raider@yopmail.fr",
    #         accepts_rgpd_reuse=True,
    #         total_due_in_cents=2800,
    #         places=3,
    #     )
    #     reservation.save()
    #     for choice_idx, item_idx, count in ((5, 1, 1), (5, 2, 1), (5, 5, 1), (3,5,1)):
    #         reservation_item_count = ReservationItemCount(reservation=reservation, choice=choices[choice_idx][0], item=items[item_idx], count=count)
    #         reservation_item_count.save()
    #         reservation.reservationitemcount_set.add(reservation_item_count)
    #     print(f"Reservation {reservation}")

    #     reservation = Reservation(
    #         civility=Civility.__empty__,
    #         first_name="Priv",
    #         last_name="Ate",
    #         email="none-of@your.biz",
    #         accepts_rgpd_reuse=False,
    #         total_due_in_cents=2200,
    #         places=1,
    #     )
    #     reservation.save()
    #     for choice_idx, item_idx, count in ((5, 1, 1), (5, 2, 1), (5, 5, 1)):
    #         reservation_item_count = ReservationItemCount(reservation=reservation, choice=choices[choice_idx][0], item=items[item_idx], count=count)
    #         reservation_item_count.save()
    #         reservation.reservationitemcount_set.add(reservation_item_count)
    #     print(f"Reservation {reservation}")

    def handle(self, *args, **options):
        self.make_db_empty()
        fill_db()
