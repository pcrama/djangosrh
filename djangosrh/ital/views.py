import csv
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
import itertools
import time
from typing import Any, Iterator, Mapping

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.db.models import Exists, OuterRef, Prefetch, QuerySet, Subquery, Sum, IntegerField, CharField
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import html
from django.views.generic import ListView

import qrcode
from qrcode.image.svg import SvgPathFillImage

from core.banking import cents_to_euros, format_bank_id, generate_payment_QR_code_content

from core.models import Payment
from djangosrh import settings
from .forms import ItemTicketsGenerationForm, ReservationForm
from .models import Choice, Civility, DishType, Event, Item, Reservation, ReservationItemCount, ReservationPayment
from .templatetags.currency_filter import plural

def index(request):
    return render(request, "ital/index.html")


def show_reservation(request, uuid: str) -> HttpResponse:
    reservation = get_object_or_404(Reservation, uuid=uuid)
    items: list[dict[str, str|int]] = [
        itm | { "display_text_with_plural": (itm["item__display_text"], itm["item__display_text_plural"])}
        for itm in
        reservation.reservationitemcount_set
        .order_by('item__dish', 'item__display_text')
        .values("item__dish", "item__display_text", "item__display_text_plural")
        .annotate(total_count=Sum("count", default=0))
    ]
    remaining_due = (
        reservation.total_due_in_cents -
        reservation.reservationpayment_set.aggregate(
            Sum("payment__amount_in_cents", default=0))['payment__amount_in_cents__sum'])
    return render(request, "ital/show_reservation.html", {
        "reservation": reservation,
        "remaining_amount_due_in_cents": remaining_due,
        "items": items,
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


class ReservationListView(LoginRequiredMixin, ListView):
    event_id: int | None = None
    event: Event | None = None
    template_name = "ital/reservations.html"
    context_object_name = "reservations"
    paginate_by = 20

    def setup(self, request, *args, **kwargs) -> None:
        super().setup(request, *args, **kwargs)
        self.event = (
            Event.objects.filter(disabled=False).order_by("date").first()
            if (event_id := request.GET.get('event_id')) is None
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
                "ital/double_reservation.html",
                {"reservation": recent_reservation})
    except Exception:
        pass

    event = get_object_or_404(Event, pk=event_id)
    if event.disabled or event.occupied_seats() >= event.max_seats:
        return render(request, "ital/event_disabled.html", context={"event": event})

    if request.method == "POST":
        form = ReservationForm(event, data=request.POST)
        if reservation := form.save():
            # Store reservation info in the session
            request.session["recent_reservation"] = {"uuid": str(reservation.uuid), "time": time.time()}
            return HttpResponseRedirect(reverse("show_reservation", kwargs={"uuid": reservation.uuid}))
        else:
            return render(
                request,
                "ital/reservation_form.html",
                {"form": form}, status=422)
    return render(request, "ital/reservation_form.html", {
        "form": ReservationForm(event)})


def get_reservations_with_likely_payments(min_date_received: date, reservations: QuerySet):
    # Subquery to get the payment with the lowest bank_ref that matches the constraints
    matching_payment_subquery = (
        Payment.objects.filter(
            srh_bank_id=OuterRef("bank_id"),
            status="Accepté",
            active=True,
            date_received__gt=min_date_received,
        )
        .exclude(
            id__in=ReservationPayment.objects.values_list("payment_id", flat=True)
        )
        .order_by("bank_ref")  # Order by lowest bank_ref
        [:1]
    )

    # Use a single subquery instance to avoid duplication
    matching_payment = Subquery(matching_payment_subquery)

    # Annotate the Reservation with the matching payment details
    reservations_with_payment = (reservations
        .annotate(
            total_received_in_cents=Sum("reservationpayment__payment__amount_in_cents", default=0),
            likely_payment_id=Subquery(matching_payment_subquery.values("id"), output_field=IntegerField()),
            likely_payment_other_name=Subquery(matching_payment_subquery.values("other_name"), output_field=CharField()),
            likely_payment_other_account=Subquery(matching_payment_subquery.values("other_account"), output_field=CharField()),
            likely_payment_amount_in_cents=Subquery(matching_payment_subquery.values("amount_in_cents"), output_field=IntegerField()),
            likely_payment_src_id=Subquery(matching_payment_subquery.values("src_id"), output_field=CharField()),
    ))

    return reservations_with_payment


@login_required
def send_payment_reception_confirmation(request):
    if request.method != "POST":
        return HttpResponseRedirect(reverse("reservations"))

    payment = get_object_or_404(Payment, pk=request.POST["payment_id"])
    reservation = get_object_or_404(Reservation, pk=request.POST["reservation_id"])
    event = reservation.event

    reservation_payment = ReservationPayment(payment=payment, reservation=reservation, confirmation_sent_timestamp=None)
    reservation_payment.save()

    template = (event.full_payment_confirmation_template
                if (remaining_amount_due_in_cents := reservation.remaining_amount_due_in_cents()) <= 0
                else event.partial_payment_confirmation_template)
    for key,val in (("organizer_name", html.escape(event.organizer_name)),
                    ("organizer_bic", html.escape(event.organizer_bic)),
                    ('bank_account', html.escape(event.bank_account)),
                    ('reservation_url', request.build_absolute_uri(reverse("show_reservation", kwargs={"uuid": reservation.uuid}))),
                    ('formatted_bank_id', html.escape(format_bank_id(reservation.bank_id))),
                    ('remaining_amount_in_euro', html.escape(cents_to_euros(remaining_amount_due_in_cents))),
                    ):
        template = template.replace(f"%{key}%", val)

    msg = EmailMultiAlternatives(
        f"Merci pour votre paiement pour le {event.name}",
        "Please see the attached HTML message. Veuillez lire le message HTML joint, svp.",
        settings.EMAIL_HOST_USER,
        [reservation.email],
        cc=[event.contact_email],
        reply_to=[event.contact_email])
    msg.attach_alternative(template, "text/html")

    try:
        msg.send()
    except Exception as e:
        messages.add_message(request, messages.ERROR, f"Unable to send confirmation mail to {reservation.email}: {e}. {template}")
    else:
        reservation_payment.confirmation_sent_timestamp = datetime.now(tz=UTC)
        reservation_payment.save()
        messages.add_message(request, messages.INFO, f"Confirmation mail sent to {reservation.email}.")

    return HttpResponseRedirect(reverse("reservations"))


@login_required
def item_tickets(request, event_id: int):
    event = get_object_or_404(Event, pk=event_id)
    if event.disabled:
        return render(request, "ital/event_disabled.html", context={"event": event})

    if request.method == "POST":
        form = ItemTicketsGenerationForm(event, data=request.POST)
        if form.is_valid():
            return render_generated_tickets(request, form)
        else:
            return render(
                request,
                "ital/item_tickets_form.html",
                {"form": form}, status=422)

    return render(request, "ital/item_tickets_form.html", {
        "form": ItemTicketsGenerationForm(event)})


@login_required
def render_generated_tickets(request, form: ItemTicketsGenerationForm) -> HttpResponse:
    return render(
        request,
        "ital/item_tickets.html",
        {"form": form,
         "reservations": list(create_full_ticket_list(form)),
         "MEDIA_URL": settings.MEDIA_URL}
    )


def create_full_ticket_list(form: ItemTicketsGenerationForm) -> Iterator[Any]:
    dish_names = {DishType.DT0STARTER: "Entrée", DishType.DT1MAIN: "Plat", DishType.DT2DESSERT: "Dessert"}
    for r in form.event.reservation_set.order_by("last_name", "first_name"):
        if not (tickets := create_tickets_for_one_reservation(r)):
            continue
        for itm in tickets["items"]:
            form.decrease_item_count(itm["item_id"], itm["total_count"])
            itm["item__dish"] = dish_names[itm["item__dish"]]
        tickets["reservation"] = r
        yield tickets
    if all(cnt <= 0 for cnt in form.data.values()):
        return
    yield {
        "reservation": {
            "no_amount_due": True,
            "full_name": "Tickets de réserve",
        },
        "total_tickets": sum(cnt for cnt in form.data.values() if cnt > 0),
        "ticket_details": ', '.join(
            plural(form.data[key], [itm.display_text, itm.display_text_plural])
            for key, itm in form.reference_data.items()
            if form.data[key] > 0),
        "items": list(itertools.chain(*(itertools.repeat(
            {
            "item_id": val.id,
            "item__short_text": (itm := Item.objects.get(pk=val.id)).short_text,
            "item__display_text": itm.display_text,
            "item__display_text_plural": itm.display_text_plural,
            "item__image": itm.image,
            "item__dish": dish_names[itm.dish],
            }, form.data[key]) for key, val in form.reference_data.items()))),
    }


def create_tickets_for_one_reservation(r: Reservation) -> dict[str, int | str | list[dict[str, int | str]]]:
    items = list(
        r.reservationitemcount_set.order_by('item__dish', 'item_id')
        .values(
            "item_id",
            "item__short_text",
            "item__display_text",
            "item__display_text_plural",
            "item__image",
            "item__dish",
        )
        .annotate(total_count=Sum("count"))
    )
    return {
        'total_tickets': total_tickets,
        'ticket_details': ', '.join(
            plural(itm['total_count'], [itm['item__display_text'], itm['item__display_text_plural']])
            for itm in items),
        'items': items,
    } if (total_tickets := sum(itm['total_count'] for itm in items)) > 0 else {}


@login_required
def export_csv(request, event_id: int) -> HttpResponse:
    event = get_object_or_404(Event, pk=event_id)
    if event.disabled:
        return render(request, "ital/event_disabled.html", context={"event": event})
    reservation_items = event.reservation_items()
    response = HttpResponse(
        content_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="reservations.csv"'},
    )
    writer = csv.writer(response)
    writer.writerow(["Nom", "Places", "Valeur", "Déjà payé", "Restant dû", *(
        itm.column_header for itm in reservation_items), "Commentaire"])
    # N+1 queries, so what... I won't have that many reservations anyway.
    for res in event.reservation_set.order_by('last_name', 'first_name'):
        total_due = res.total_due_in_cents
        remaining = res.remaining_amount_due_in_cents()
        writer.writerow([
            res.full_name,
            str(res.places),
            cents_to_euros(total_due),
            cents_to_euros(total_due - remaining),
            cents_to_euros(remaining),
            *(res.count_items(item) for item in reservation_items),
            res.extra_comment.strip()])
    return response
