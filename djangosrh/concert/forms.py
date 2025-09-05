from collections import defaultdict, namedtuple
from collections.abc import Sequence, Mapping
import itertools
import re
import time
from typing import Any, Callable

from core.banking import generate_bank_id
#from core.templatetags.currency_filter import plural

from core.models import Civility
from .models import Event, Reservation, ReservationChoiceCount


class ReservationForm:
    Input = namedtuple("Input", ("id", "name", "value", "errors", "choice"))
    choices: list[Input]
    total_due_in_cents: int
    errors: list[str]

    def __init__(self, evt: Event, data=None):
        self.event = evt
        self.was_validated, self.data = (False, defaultdict(int)) if data is None else (True, data)
        self.choices = []
        self.errors = []
        self.clean_data()

    def is_valid(self) -> bool:
        if not hasattr(self, "last_name"):
            self.clean_data()
        for inpt in itertools.chain(
                self.choices,
                [self.last_name, self.first_name, self.email, self.accepts_rgpd_reuse]):
            if inpt.errors:
                return False
        return self.errors == []

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
                id=id, name=id, value=val, errors=errors(id) if self.was_validated else [], choice=None)
        def _make_checkbox(id: str, default: bool, errors: Callable[[str], list[str]]) -> ReservationForm.Input:
            return self.Input(
                id=id, name=id,
                value=self.data.get(id) == "yes" if id in self.data else default,
                errors=errors(id) if self.was_validated else [],
                choice=None,
            )
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
                [] if id in self.data and (ss := self.data[id]) and isinstance(ss, str) and re.match(r" *[a-zA-Z.0-9-]+@[a-zA-Z.0-9-]+ *", ss) else ["Invalid email"])
        self.civility = _make_input("civility", Reservation.civility.field.default, _in_set([Civility.man, Civility.woman, Civility.__empty__]))
        self.last_name = _make_input("last_name", "", _non_blank)
        self.first_name = _make_input("first_name", Reservation.first_name.field.default, _any)
        self.email = _make_input("email", "", _mandatory_email)
        self.accepts_rgpd_reuse = _make_checkbox("accepts_rgpd_reuse", False, _any)
        self.validate_choices()

    def validate_choices(self):
        MAX_ALLOWED = 25
        total_due_in_cents = 0
        total_choices = 0
        idx = 0
        for choice in self.event.choice_set.all():
            errors: list[str] = []
            key = f"counter{idx}_ch_{choice.id}"
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
                elif val > MAX_ALLOWED:
                    errors.append(f"Too large, must be {MAX_ALLOWED} or less")
            self.choices.append(self.Input(
                id=key, name=key, value=val, errors=errors if self.was_validated else [], choice=choice))
            total_due_in_cents += choice.price_in_cents * val
            total_choices += val
        if total_choices < 1:
            self.errors.append("Total number of choices must be strictly positive")
        self.total_due_in_cents = total_due_in_cents

    def save(self) -> Reservation | None:
        if self.is_valid():
            if sum(chc.value for chc in self.choices) + self.event.occupied_seats() > self.event.max_seats:
                self.errors.append(f"Il n'y a plus assez de places.  Contactez nous: {self.event.contact_email}")
                return None
            reservation = Reservation(
                event=self.event,
                civility=self.civility.value,
                first_name=self.first_name.value.strip(),
                last_name=self.last_name.value.strip(),
                email=self.email.value.strip(),
                accepts_rgpd_reuse=self.accepts_rgpd_reuse.value,
                total_due_in_cents=self.total_due_in_cents,
                bank_id=generate_bank_id(time.time(), Reservation.objects.count()),
            )
            reservation.save()
            for inpt in self.choices:
                if inpt.value < 1:
                    continue
                reservation_item_count = ReservationChoiceCount(
                    reservation=reservation, choice=inpt.choice, count=inpt.value)
                reservation_item_count.save()
                reservation.reservationchoicecount_set.add(reservation_item_count)
            return reservation
