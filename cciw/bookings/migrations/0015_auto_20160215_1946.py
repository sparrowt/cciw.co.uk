# Generated by Django 1.9.2 on 2016-02-15 19:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0014_auto_20160215_1945"),
    ]

    operations = [
        migrations.RenameField(
            model_name="bookingaccount",
            old_name="post_code",
            new_name="address_post_code",
        ),
    ]
