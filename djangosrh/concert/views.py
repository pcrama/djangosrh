import csv
from datetime import timedelta
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import login_required
from django.core.mail import EmailMultiAlternatives
from django.db.models import Exists, OuterRef, Prefetch, QuerySet, Subquery, Sum, IntegerField, CharField
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import html
from django.views.generic import ListView
import qrcode
from qrcode.image.svg import SvgPathFillImage

from .forms import ReservationForm
from .models import Event, Reservation
from core.banking import cents_to_euros, format_bank_id, generate_payment_QR_code_content
from core.models import get_reservations_with_likely_payments
from core.views import aux_send_payment_reception_confirmation

def index(request):
    events = [(str(evt), reverse("concert:reservations", query={"event_id": evt.id}))
              for evt in Event.objects.filter(disabled=False).order_by("date")]
    return render(request, "concert/index.html", context={"events": events})


class ReservationListView(LoginRequiredMixin, ListView):
    event_id: int | None = None
    event: Event | None = None
    template_name = "concert/reservations.html"
    context_object_name = "reservations"
    paginate_by = 20

    def setup(self, request, *args, **kwargs) -> None:
        super().setup(request, *args, **kwargs)
        event_id = request.GET.get('event_id')
        if event_id is not None:
            try:
                event_id = int(event_id)
            except ValueError:
                raise Http404(f"Invalid event {event_id!r}.")
        self.event = (
            Event.objects.filter(disabled=False).order_by("date").first()
            if event_id is None
            else get_object_or_404(Event, id=event_id))
        self.event_id = None if self.event is None else self.event.id

    def get_queryset(self):
        return get_reservations_with_likely_payments(
            date(2025, 2, 12)
            if self.event is None else
            (self.event.date - timedelta(days=90)),
            Reservation.objects.filter(event_id=self.event_id).order_by("id"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.event is not None:
            context["event"] = self.event
            context["total_count"] = self.event.occupied_seats()
        return context


def reservation_form(request, event_id: int) -> HttpResponse:
    try:
        if request.method == "POST" or request.GET.get("force") == "True":
            reservation_cookie = None
        else:
            # Check for recent reservations in the session
            reservation_cookie = request.session.get("recent_reservation")

        if (reservation_cookie
            and (uuid := reservation_cookie.get("uuid"))
            and (reservation_time := reservation_cookie.get("time"))
            and (time.time() > reservation_time)
            and (time.time() - reservation_time <= 30 * 60)
            and (recent_reservation := Reservation.objects.get(uuid=uuid))):
            return render(
                request,
                "concert/double_reservation.html",
                {"reservation": recent_reservation, "event_id": event_id})
    except Exception:
        pass

    event = get_object_or_404(Event, pk=event_id)
    if event.disabled or event.occupied_seats() >= event.max_seats:
        return render(request, "concert/event_disabled.html", context={"event": event})

    if request.method == "POST":
        form = ReservationForm(event, data=request.POST)
        if reservation := form.save():
            # Store reservation info in the session
            request.session["recent_reservation"] = {"uuid": str(reservation.uuid), "time": time.time()}
            return HttpResponseRedirect(reverse("concert:show_reservation", kwargs={"uuid": reservation.uuid}))
        else:
            return render(
                request,
                "concert/reservation_form.html",
                {"form": form}, status=422)
    return render(request, "concert/reservation_form.html", {
        "form": ReservationForm(event)})


def show_reservation(request: HttpRequest, uuid: str) -> HttpResponse:
    reservation = get_object_or_404(Reservation, uuid=uuid)
    choices: list[dict[str, str|int]] = [
        chc | { "display_text_with_plural": (chc["choice__display_text"], chc["choice__display_text_plural"])}
        for chc in
        reservation.reservationchoicecount_set
        .order_by('choice__display_text')
        .values("choice__display_text", "choice__display_text_plural", "count")
    ]
    remaining_due = (
        reservation.total_due_in_cents -
        reservation.reservationpayment_set.aggregate(
            Sum("payment__amount_in_cents", default=0))['payment__amount_in_cents__sum'])
    return render(request, "concert/show_reservation.html", {
        "reservation": reservation,
        "remaining_amount_due_in_cents": remaining_due,
        "choices": choices,
        "payment_qrcode": qrcode.make(
            generate_payment_QR_code_content(
                remaining_due,
                bank_id=reservation.bank_id,
                bank_account=reservation.event.bank_account,
                organizer_bic=reservation.event.organizer_bic,
                organizer_name=reservation.event.organizer_name),
            image_factory=SvgPathFillImage
        ).to_string().decode('utf8'),
        "page_qrcode": qrcode.make(
            request.build_absolute_uri(), image_factory=SvgPathFillImage
        ).to_string().decode('utf8')})
   


@login_required
def send_payment_reception_confirmation(request) -> HttpResponseRedirect:
    return aux_send_payment_reception_confirmation(request, "concert:reservations", "concert:show_reservation")


@login_required
def export_csv(request, event_id: int) -> HttpResponse:
    event = get_object_or_404(Event, pk=event_id)
    if event.disabled:
        return render(request, "ital/event_disabled.html", context={"event": event})
    reservation_choices = event.reservation_choices()
    response = HttpResponse(
        content_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="reservations.csv"'},
    )
    writer = csv.writer(response)
    writer.writerow(["Nom", "Places", "Valeur", "Déjà payé", "Restant dû", *(
        chc.column_header for chc in reservation_choices)])
    # N+1 queries, so what... I won't have that many reservations anyway.
    for res in event.reservation_set.order_by('last_name', 'first_name'):
        total_due = res.total_due_in_cents
        remaining = res.remaining_amount_due_in_cents()
        choice_counts = {res_chc_count.choice.id: res_chc_count.count for res_chc_count in res.reservationchoicecount_set.all()}
        writer.writerow([
            res.full_name,
            str(res.places),
            cents_to_euros(total_due),
            cents_to_euros(total_due - remaining),
            cents_to_euros(remaining),
            *(choice_counts.get(chc.id, 0) for chc in reservation_choices)])
    return response
