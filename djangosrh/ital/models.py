from django.db import models

from enum import Enum


# Event:
# 1."souper italien"@2024-03-29
# Item:
# 1. Tomate Mozza; starter
# 2. Croquettes; starter
# 3. Bolo; main
# 4. Scampis; main
# 5. Vegetarian; main
# 6. Tiramisu; dessert
# 7. Glace; dessert
# Choice
# 1. Tomate Mozza (single); 9EUR; event_id=1; item_ids=[1]
# 2. Croquettes (single); 8EUR; event_id=1; item_ids=[2]
# 3. Bolo (single); 12EUR; event_id=1; item_ids=[3]
# 4. Tiramisu (single); 6EUR; event_id=1; item_ids=[6]
# 5. Child menu; 20EUR; event_id=1; item_ids=[3, 5, 6, 7]
# 6. Bolo menu; 22EUR; event_id=1; item_ids=[1, 2, 3, 6]
# 7. Scampi menu; 27EUR; event_id=1; item_ids=[1, 2, 4, 6]
# 8. Anything goes menu; 25EUR; event_id=1; item_ids=[1, 2, 3, 4, 5, 6, 7]
# Reservation
# 1. Mr Dupont; dupont@yopmail.fr; [(choice_id_1,[(1,2)]),(choice_id_5,[(3,0),(5,3),(6,1),(7,2)])]; 78EUR
#        reservation_id=1; choice_id=1; item_id=1; count=2
#        reservation_id=1; choice_id=5; item_id=3; count=0 (optional row?)
#        reservation_id=1; choice_id=5; item_id=5; count=3
#        reservation_id=1; choice_id=5; item_id=6; count=1
#        reservation_id=1; choice_id=5; item_id=7; count=2

class Civility(models.Choices):
    man = "Mr"
    woman = "Mme"
    __empty__ = ""


class Event(models.Model):
    name = models.CharField(max_length=200)
    date = models.DateField()

    def __str__(self):
        return f"{self.name}@{self.date}"


class Choice(models.Model):
    "What a customer chooses, can be 1 or more items grouped together (e.g. a starter/main dish/dessert pack)"
    display_text = models.CharField(max_length=200)
    price_in_cents = models.PositiveIntegerField()
    available_in = models.ForeignKey(Event, on_delete=models.CASCADE)

    def __str__(self):
        return self.display_text


class Item(models.Model):
    display_text = models.CharField(max_length=200)
    column_header = models.CharField(max_length=200)
    short_text = models.CharField(max_length=200)
    choices = models.ManyToManyField(Choice)

    def __str__(self):
        return self.display_text


class ReservationItemCount(models.Model):
    count = models.IntegerField()
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    reservation = models.ForeignKey("Reservation", on_delete=models.CASCADE)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['choice_id', 'item_id', 'reservation_id'], name='reservation*item*choice'),
            # TODO: constrain all choices to be for the same event
        ]


class Reservation(models.Model):
    civility = models.CharField(max_length=20, choices=Civility)
    last_name = models.CharField(max_length=200)
    first_name = models.CharField(max_length=200)
    email = models.CharField(max_length=200)
    accepts_rgpd_reuse = models.BooleanField()
    total_due_in_cents = models.IntegerField()

    def __str__(self):
        fullname = " ".join(x for x in (self.civility, self.first_name, self.last_name) if x and x.strip())
        return f"{fullname} ({self.email})"
