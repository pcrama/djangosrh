# Generated by Django 5.1.4 on 2024-12-26 20:12

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ital', '0004_reservation_places'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
