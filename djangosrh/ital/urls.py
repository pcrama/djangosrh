from django.conf import settings
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("show_reservation/<str:uuid>", views.show_reservation, name="show_reservation"),
    path("reservations", view=views.ReservationListView.as_view(), name="reservations"),
    path("events/<int:event_id>/reservation_form", views.reservation_form, name="reservation_form"),
    path("send_payment_reception_confirmation", views.send_payment_reception_confirmation, name="send_payment_reception_confirmation"),
    path("events/<int:event_id>/item_tickets", views.item_tickets, name="item_tickets"),
]
