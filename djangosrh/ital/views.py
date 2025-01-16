from collections import defaultdict
from typing import Any, Iterator, Mapping
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.utils.autoreload import itertools

from .forms import ReservationForm

from .models import Choice, Civility, DishType, Event, Item, Reservation, ReservationItemCount


def index(request):
    return render(request, "ital/index.html")

def show_reservation(request, uuid: str) -> HttpResponse:
    reservation = get_object_or_404(Reservation, uuid=uuid)
    return render(request, "ital/show_reservation.html", {
        "reservation": reservation,
        "items": None})

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

def reservation_form(request, event_id: int) -> HttpResponse:
    event = get_object_or_404(Event, pk=event_id)
    if request.method == "POST":
        form = ReservationForm(event, data=request.POST)
        if reservation := form.save():
            return HttpResponseRedirect(reverse("show_reservation", kwargs={"uuid": reservation.uuid}))
        else:
            return render(
                request,
                "ital/reservation_form.html",
                {"form": form}, status=422)
    return render(request, "ital/reservation_form.html", {
        "form": ReservationForm(event)})
