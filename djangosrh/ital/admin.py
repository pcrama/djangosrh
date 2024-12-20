from django.contrib import admin

from .models import Event, Choice, Item, Reservation

# Register your models here.
admin.site.register(Event)
admin.site.register(Choice)
admin.site.register(Item)
admin.site.register(Reservation)
