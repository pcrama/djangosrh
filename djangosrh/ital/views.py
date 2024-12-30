from django.shortcuts import render
from django.urls import reverse

from django.http import HttpResponse, Http404

from .models import Reservation


def index(request):
    return HttpResponse(b"<html><head><title>Title</title></head><body>Hello, world. You're at the polls index.</body></html>")

def show_reservation(request, uuid: str) -> HttpResponse:
    try:
        reservation = Reservation.objects.get(uuid=uuid)
    except Reservation.DoesNotExist:
        raise Http404()
    return HttpResponse(f"<html><head><title>{reservation.first_name} {reservation.last_name}</title></head><body>Hello, world. You have reserved {reservation.places} places.</body></html>".encode())

def reservations(request):
    try:
        offset = int(request.GET.get('offset', '0'))
    except Exception:
        offset = 0
    try:
        limit = int(request.GET.get('limit', '20'))
    except Exception:
        limit = 20
    offset = max(offset, 0)
    limit = max(20, min(limit, 200))

    return HttpResponse(b"".join((
        b"<html><head><title>",
        str(Reservation.objects.count()).encode(),
        b" Reservations</title></head><body><table>",
        *((f'<tr><td><a href="{reverse(show_reservation, args=[reservation.uuid])}">{reservation.first_name} {reservation.last_name}</a>'
           f"</td><td>{reservation.places}</td></tr>").encode()
          for reservation in Reservation.objects.all()[offset:offset+limit]),
        b"</table></body></html>"
    )))
