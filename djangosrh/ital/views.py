from collections import defaultdict
from typing import Any, Iterator, Mapping
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from django.http import HttpResponse, Http404, HttpResponseRedirect

from .models import Choice, DishType, Event, Item, Reservation


def index(request):
    return render(request, "ital/index.html")

def show_reservation(request, uuid: str) -> HttpResponse:
    reservation = get_object_or_404(Reservation, uuid=uuid)
    return render(request, "ital/show_reservation.html", {"reservation": reservation})

def reservations(request):
    try:
        offset = int(request.GET.get('offset', '0'))
    except Exception:
        offset = 0
    try:
        limit = int(request.GET.get('limit', '20'))
    except Exception:
        limit = 20
    offset = max(offset, 0)
    limit = max(20, min(limit, 200))

    return render(
        request,
        "ital/reservations.html",
        {"reservations": Reservation.objects.all()[offset:offset+limit]})

def validate_sum_groups(evt: Event, data: Mapping[str, Any]) -> Iterator[tuple[Choice, dict[str, dict[str, dict[str, Item | int]]]]]:
    idx = 0
    all_dishes = set()
    for choice in evt.choice_set.all():
        vals = defaultdict(dict)
        sums = defaultdict(int)
        for item in choice.item_set.all():
            key = f"counter{idx}"
            idx += 1
            try:
                val = int(data[key])
            except (KeyError, ValueError):
                val = 0
            all_dishes.add(item.dish)
            vals[item.dish][key] = {"item": item, "count": val}
            sums[item.dish] += val
            idx += 1
        sums_array = []
        for dish in all_dishes:
            if vals[dish]:
                sums_array.append(sums[dish])
        if sums_array and any(sums_array[0] != x for x in sums_array):
            for dish in all_dishes:
                for dict_items in vals[dish].values():
                    dict_items["error"] = "Sum mismatch"
        yield (choice, vals)

def reservation_form(request, event_id: int) -> HttpResponse:
    event = get_object_or_404(Event, pk=event_id)
    if request.method == "POST":
        choices = list(validate_sum_groups(event, request.POST))
        is_valid = False
        if is_valid:
            return HttpResponseRedirect("/thanks/")
        else:
            return render(
                request,
                "ital/reservation_form.html",
                {"event": event, "choices": choices}, status=422)
    choices = list(validate_sum_groups(event, defaultdict(int)))
    return render(
        request,
        "ital/reservation_form.html",
        {"event": event, "choices": choices})
