import io
from collections import defaultdict
from datetime import datetime, UTC
from typing import Mapping

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import login_required
from django.core.mail import EmailMultiAlternatives
from django.db.models import Sum
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import html
from django.views.generic import ListView

from .banking import cents_to_euros, format_bank_id, generate_payment_QR_code_content, import_bank_statements

from .models import BaseReservation, Payment, ReservationPayment

class PaymentListView(LoginRequiredMixin, ListView):
    template_name = "core/payments.html"
    context_object_name = "payments"
    paginate_by = 20
    only_active = True
    order_by = 'bank_ref'

    def setup(self, request, *args, **kwargs) -> None:
        super().setup(request, *args, **kwargs)
        self.only_active = request.GET.get('only_active') != "False"
        self.order_by = request.GET.get('order_by', self.order_by)
        try:
            self.paginate_by = int(request.GET.get('paginate_by', self.paginate_by))
        except Exception:
            pass

    def get_queryset(self):
        unordered_set = Payment.objects.filter(active=True) if self.only_active else Payment.objects
        order_by = self.order_by.lower()
        return unordered_set.order_by(('' if order_by == self.order_by else '-') + order_by)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["only_active"] = self.only_active
        context["order_by"] = self.order_by
        context["paginate_by"] = self.paginate_by
        context["page_sizes"] = [10, 20, 50]
        return context


@login_required
def toggle_payment_active_status(request):
    default_next = reverse('payments')
    if not (bank_ref := request.POST.get('bank_ref')) or not (new_active := request.POST.get('new_active')):
        return redirect(default_next)

    payment = get_object_or_404(Payment, bank_ref=bank_ref)
    payment.active = new_active
    payment.save()

    return redirect(request.POST.get('next', default_next))


@login_required
def upload_payment_csv(request):
    default_next = reverse('payments')
    if not (file := request.FILES.get('formFile')):
        return redirect(default_next)

    result = import_bank_statements(io.TextIOWrapper(file, errors='replace', encoding='utf-8'))

    if all(exc is None for exc, _ in result):
        return redirect(request.POST.get('next', default_next))
    else:
        return render(request, "core/payment_upload_csv_result.html", context={"result": result})



def aux_send_payment_reception_confirmation(request, redirect_view: str, show_reservation_view: str) -> HttpResponseRedirect:
    if request.method != "POST":
        return HttpResponseRedirect(reverse(redirect_view))

    payment = get_object_or_404(Payment, pk=request.POST["payment_id"])
    reservation = get_object_or_404(BaseReservation, pk=request.POST["reservation_id"])
    event = reservation.base_event

    reservation_payment = ReservationPayment(payment=payment, reservation=reservation, confirmation_sent_timestamp=None)
    reservation_payment.save()

    template = (event.full_payment_confirmation_template
                if (remaining_amount_due_in_cents := reservation.remaining_amount_due_in_cents()) <= 0
                else event.partial_payment_confirmation_template)
    for key,val in (("organizer_name", html.escape(event.organizer_name)),
                    ("organizer_bic", html.escape(event.organizer_bic)),
                    ('bank_account', html.escape(event.bank_account)),
                    ('reservation_url', request.build_absolute_uri(reverse(show_reservation_view, kwargs={"uuid": reservation.uuid}))),
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

    return HttpResponseRedirect(reverse(redirect_view))
