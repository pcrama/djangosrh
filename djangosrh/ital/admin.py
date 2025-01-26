from django.contrib import admin

from .models import Event, Choice, Item, Reservation, ReservationItemCount

# Register your models here.
admin.site.register(Event)
admin.site.register(Choice)
admin.site.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('display_text', 'count', 'image')

admin.site.register(Reservation)
admin.site.register(ReservationItemCount)
