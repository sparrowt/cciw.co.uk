# Generated by Django 1.9.2 on 2016-02-18 16:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0023_auto_20160216_1558"),
    ]

    operations = [
        migrations.AlterField(
            model_name="booking",
            name="address",
            field=models.TextField(blank=True, help_text="deprecated"),
        ),
        migrations.AlterField(
            model_name="booking",
            name="contact_address",
            field=models.TextField(blank=True, help_text="deprecated"),
        ),
        migrations.AlterField(
            model_name="booking",
            name="gp_address",
            field=models.TextField(blank=True, help_text="deprecated", verbose_name="GP address"),
        ),
        migrations.AlterField(
            model_name="bookingaccount",
            name="address",
            field=models.TextField(blank=True, help_text="deprecated"),
        ),
    ]
