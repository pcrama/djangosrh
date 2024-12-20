from django.db import models

# Create your models here.


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


class Reservation(models.Model):
    last_name = models.CharField(max_length=200)
    first_name = models.CharField(max_length=200)
    email = models.CharField(max_length=200)
    accepts_rpgd_reuse = models.BooleanField()
    attends = models.ForeignKey(Event, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
