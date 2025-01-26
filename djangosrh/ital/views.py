from collections import defaultdict
from typing import Any, Iterator, Mapping

from django.db.models import Sum
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
import qrcode
from qrcode.image.svg import SvgPathFillImage

from .forms import ReservationForm
from .models import Choice, Civility, DishType, Event, Item, Reservation, ReservationItemCount
from .templatetags.currency_filter import cents_to_euros

def index(request):
    return render(request, "ital/index.html")


def generate_payment_QR_code_content(remaining_due: int, bank_id: str, event: Event) -> str:
    # See scan2pay.info
    iban = "".join(ch for ch in event.bank_account if ch in "BE" or ch.isdigit())
    amount = cents_to_euros(remaining_due, unit="")
    return ("BCD\n001\n1\nSCT\n" + event.organizer_bic + "\n" + event.organizer_name + "\n" + iban + "\n" + "EUR" + amount + "\n\n" + bank_id)


def show_reservation(request, uuid: str) -> HttpResponse:
    reservation = get_object_or_404(Reservation, uuid=uuid)
    items: list[dict[str, str|int]] = [
        itm | { "display_text_with_plural": (itm["item__display_text"], itm["item__display_text_plural"])}
        for itm in
        reservation.reservationitemcount_set
        .order_by('item__dish', 'item__display_text')
        .values("item__dish", "item__display_text", "item__display_text_plural")
        .annotate(total_count=Sum("count"))
    ]
    remaining_due = reservation.total_due_in_cents # TODO: integrate with payments
    return render(request, "ital/show_reservation.html", {
        "reservation": reservation,
        "remaining_amount_due_in_cents": remaining_due,
        "items": items,
        "payment_qrcode": qrcode.make(
            generate_payment_QR_code_content(remaining_due, reservation.bank_id, reservation.event),
            image_factory=SvgPathFillImage
        ).to_string().decode('utf8'),
        "page_qrcode": qrcode.make(
            request.build_absolute_uri(), image_factory=SvgPathFillImage
        ).to_string().decode('utf8')})

def reservations(request, event_id: int):
    event = get_object_or_404(Event, id=event_id)
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
        {
            "event": event,
            "reservations": Reservation.objects.filter(event_id=event_id)[offset:offset+limit]})

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
