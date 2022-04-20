# Generated by Django 4.0.3 on 2022-03-28 12:34

import django_countries.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0056_subscribe_to_newsletter_helptext"),
    ]

    operations = [
        migrations.AlterField(
            model_name="booking",
            name="address_country",
            field=django_countries.fields.CountryField(default="GB", max_length=2, null=True, verbose_name="country"),
        ),
        migrations.AlterField(
            model_name="booking",
            name="contact_country",
            field=django_countries.fields.CountryField(default="GB", max_length=2, null=True, verbose_name="country"),
        ),
        migrations.AlterField(
            model_name="booking",
            name="gp_country",
            field=django_countries.fields.CountryField(default="GB", max_length=2, null=True, verbose_name="country"),
        ),
        migrations.AlterField(
            model_name="bookingaccount",
            name="address_country",
            field=django_countries.fields.CountryField(
                blank=True, default="GB", max_length=2, null=True, verbose_name="country"
            ),
        ),
    ]