# Generated by Django 3.1.7 on 2021-04-02 10:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0037_populate_bookingaccount_created"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bookingaccount",
            name="created",
            field=models.DateTimeField(),
        ),
    ]
