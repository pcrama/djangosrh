from django.urls import path

from . import views

urlpatterns = [
    path("payments", view=views.PaymentListView.as_view(), name="payments"),
    path("toggle_payment_active_status", view=views.toggle_payment_active_status, name="toggle_payment_active_status"),
    path("upload_payment_csv", view=views.upload_payment_csv, name="upload_payment_csv"),
]
