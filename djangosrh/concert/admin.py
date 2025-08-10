from django.contrib import admin

from .models import Event, Choice, Reservation, ReservationChoiceCount

# Register your models here.
admin.site.register(Event)
admin.site.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ('display_text', 'count')

admin.site.register(Reservation)
admin.site.register(ReservationChoiceCount)
