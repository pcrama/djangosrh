from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from django.http import HttpResponse, Http404

from .models import Reservation


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
