import io
from collections import defaultdict
import time
from typing import Any, Iterator, Mapping

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import login_required
from django.db.models import Sum
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import ListView

from .banking import cents_to_euros, generate_payment_QR_code_content, import_bank_statements

from .models import Payment

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
