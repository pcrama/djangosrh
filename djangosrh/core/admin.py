from django.contrib import admin

from .models import Payment, ReservationPayment

admin.site.register(Payment)
admin.site.register(ReservationPayment)
