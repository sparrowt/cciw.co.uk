# Generated by Django 1.9.2 on 2016-02-15 17:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0012_bookingaccount_subscribe_to_newsletter"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bookingaccount",
            name="name",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AlterField(
            model_name="bookingaccount",
            name="post_code",
            field=models.CharField(blank=True, default="", max_length=10),
        ),
    ]
