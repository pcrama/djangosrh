from django.urls import path

from . import views

app_name = "concert"
urlpatterns = [
    path("", views.index, name="index"),
    path("reservations", views.ReservationListView.as_view(), name="reservations"),
    path("show_reservation/<str:uuid>", views.show_reservation, name="show_reservation"),
    path("events/<int:event_id>/reservation_form", views.reservation_form, name="reservation_form"),
    path("send_payment_reception_confirmation", views.send_payment_reception_confirmation, name="send_payment_reception_confirmation"),
    path("events/<int:event_id>/export_csv", views.export_csv, name="export_csv"),
]
