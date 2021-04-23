# Generated by Django 3.1.7 on 2021-04-03 18:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0038_auto_20210402_1106'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='erased_on',
            field=models.DateTimeField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name='bookingaccount',
            name='erased_on',
            field=models.DateTimeField(blank=True, default=None, null=True),
        ),
    ]