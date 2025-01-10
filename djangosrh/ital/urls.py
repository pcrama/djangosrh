from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("show_reservation/<str:uuid>", views.show_reservation, name="show_reservation"),
    path("reservations/", views.reservations, name="reservations"),
    path("events/<int:event_id>/reservation_form", views.reservation_form, name="reservation_form"),
]

