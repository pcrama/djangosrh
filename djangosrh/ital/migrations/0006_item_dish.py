# Generated by Django 5.1.4 on 2025-01-10 21:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ital', '0005_reservation_uuid'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='dish',
            field=models.CharField(choices=[('starter', 'Starter'), ('main', 'Main'), ('dessert', 'Dessert')], default='starter', max_length=10),
            preserve_default=False,
        ),
    ]
