# Generated by Django 5.1.4 on 2025-01-17 21:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ital', '0006_item_dish'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='extra_comment',
            field=models.CharField(default='', max_length=200),
        ),
        migrations.AlterField(
            model_name='item',
            name='dish',
            field=models.CharField(choices=[('dt0starter', 'Dt0Starter'), ('dt1main', 'Dt1Main'), ('dt2dessert', 'Dt2Dessert')], max_length=10),
        ),
    ]
