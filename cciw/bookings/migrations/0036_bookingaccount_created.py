# Generated by Django 3.1.7 on 2021-04-02 09:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0035_auto_20210227_1637"),
    ]

    operations = [
        migrations.AddField(
            model_name="bookingaccount",
            name="created",
            field=models.DateTimeField(null=True),
        ),
    ]
