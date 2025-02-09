from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("show_reservation/<str:uuid>", views.show_reservation, name="show_reservation"),
    path("reservations", view=views.ReservationListView.as_view(), name="reservations"),
    path("events/<int:event_id>/reservation_form", views.reservation_form, name="reservation_form"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
