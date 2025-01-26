from collections import defaultdict, namedtuple
import functools
import itertools
import operator
import re
from typing import Any, Callable, Sequence

from .models import Civility, Event, Item, Reservation, ReservationItemCount

class ReservationForm:
    Input = namedtuple("Input", ("id", "name", "value", "errors", "choice", "item"))
    Pack = namedtuple("Pack", (
        "id",
        "choice",
        "items",  # dict[str, list[Input]]
        "errors", # list[str]
    ))
    single_items: dict[str, list[Input]]
    packs: list[Pack]
    total_due_in_cents: int

    def __init__(self, evt: Event, data=None):
        self.event = evt
        self.was_validated, self.data = (False, defaultdict(int)) if data is None else (True, data)
        self.single_items = defaultdict(list)
        self.packs = []
        self.clean_data()

    def is_valid(self) -> bool:
        if not hasattr(self, "last_name"):
            self.clean_data()
        for inpt in itertools.chain(
                *self.single_items.values(),
                [self.last_name, self.first_name, self.email,
                 self.accepts_rgpd_reuse, self.places,
                 self.extra_comment]):
            if inpt.errors:
                return False
        for pack in self.packs:
            if pack.errors:
                return False
            for inpt in itertools.chain(*pack.items.values()):
                if inpt.errors:
                    return False
        return True

    def clean_data(self):
        def _make_input(id: str, default: Any, errors: Callable[[str], list[str]], parse: Callable[[Any], Any]|None=None) -> ReservationForm.Input:
            sentinel = object()
            val: Any
            if (val_str := self.data.get(id, sentinel)) is sentinel:
                val = default
            else:
                try:
                    val = val_str if parse is None else parse(val_str)
                except Exception:
                    val = val_str
            return self.Input(
                id=id, name=id, value=val, errors=errors(id) if self.was_validated else [], choice=None, item=None)
        def _mandatory(id: str) -> list[str]:
            return [] if id in self.data else ["Mandatory field"]
        def _non_blank(id: str) -> list[str]:
            return [] if id in self.data and (ss := self.data[id]) and isinstance(ss, str) and ss.strip() else ["Mandatory field"]
        def _in_set(values_set: Sequence[str]) -> Callable[[str], list[str]]:
            def work(id: str) -> list[str]:
                return [] if id not in self.data or self.data[id] in values_set else ["Unknown value"]
            return work
        def _any(id: str) -> list[str]:
            return []
        def _mandatory_email(id: str) -> list[str]:
            return _mandatory(id) or (
                [] if id in self.data and (ss := self.data[id]) and isinstance(ss, str) and re.match(r" *[a-z.0-9-]+@[a-z.0-9-]+ *", ss) else ["Invalid email"])
        def _mandatory_in_range(low: int, high: int) -> Callable[[str], list[str]]:
            def work(id: str) -> list[str]:
                if (err := _mandatory(id)):
                    return err
                ss = self.data.get(id)
                try:
                    vv = int(ss)
                except Exception:
                    return [f"Must be between {low} and {high}"]
                return [] if low <= vv <= high else [f"Must be between {low} and {high}"]
            return work
        self.civility = _make_input("civility", Reservation.civility.field.default, _in_set([Civility.man, Civility.woman, Civility.__empty__]))
        self.last_name = _make_input("last_name", "", _non_blank)
        self.first_name = _make_input("first_name", Reservation.first_name.field.default, _any)
        self.email = _make_input("email", "", _mandatory_email)
        self.accepts_rgpd_reuse = _make_input("accepts_rgpd_reuse", False, _any, functools.partial(operator.eq, "yes"))
        self.places = _make_input("places", 1, _mandatory_in_range(1, 50), int)
        self.extra_comment = _make_input("extra_comment", "", _any)
        self.validate_sum_groups()

    def validate_sum_groups(self):
        total_due_in_cents = 0
        idx = 0
        all_dishes: set[str] = set()
        for choice in self.event.choice_set.all():
            vals: defaultdict[str, list[ReservationForm.Input]] = defaultdict(list)
            sums: defaultdict[str, int] = defaultdict(int)
            item: Item
            for idx, item in enumerate(choice.item_set.all()):
                errors: list[str] = []
                key = f"counter{idx}_ch_{choice.id}_it_{item.id}"
                try:
                    val = int(self.data[key])
                except ValueError:
                    errors.append("Must be a number")
                    val = 0
                except KeyError:
                    val = 0
                else:
                    if val < 0:
                        errors.append("Must not be negative")
                    elif val > 20:
                        errors.append("Too large")
                all_dishes.add(item.dish)
                vals[item.dish].append(self.Input(
                    id=key, name=key, value=val, errors=errors if self.was_validated else [], choice=choice, item=item))
                sums[item.dish] += val
            if sum(len(items) for items in vals.values()) == 1:
                input_ = next(iter(vals.values()))[0]
                total_due_in_cents += choice.price_in_cents * input_.value
                self.single_items[input_.item.dish].append(input_)
            else:
                sums_array = []
                for dish in all_dishes:
                    if vals[dish]:
                        sums_array.append(sums[dish])
                total_due_in_cents += choice.price_in_cents * sums_array[0]
                self.packs.append(self.Pack(
                    id=f"pack_id_{len(self.packs)}",
                    choice=choice,
                    items=dict(vals),  # django templating gets confused by defaultdict
                    errors=["Sum mismatch"] if sums_array and any(sums_array[0] != x for x in sums_array) else [],
                ))
        self.total_due_in_cents = total_due_in_cents
        self.all_dishes = list(all_dishes)
        self.single_items = dict(self.single_items) # django templating gets confused by defaultdict
        self.all_dishes.sort()

    def save(self) -> Reservation | None:
        if self.is_valid():
            reservation = Reservation(
                civility=self.civility.value,
                first_name=self.first_name.value,
                last_name=self.last_name.value,
                email=self.email.value,
                accepts_rgpd_reuse=self.accepts_rgpd_reuse.value,
                total_due_in_cents=self.total_due_in_cents,
                places=self.places.value,
                extra_comment=self.extra_comment.value,
            )
            reservation.save()
            for inpt in itertools.chain(
                    *self.single_items.values(),
                    *itertools.chain(*(pack.items.values() for pack in self.packs))):
                if inpt.value < 1:
                    continue
                reservation_item_count = ReservationItemCount(
                    reservation=reservation,
                    choice=inpt.choice,
                    item=inpt.item,
                    count=inpt.value)
                reservation_item_count.save()
                reservation.reservationitemcount_set.add(reservation_item_count)
            return reservation
