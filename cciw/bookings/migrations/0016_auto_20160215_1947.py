# Generated by Django 1.9.2 on 2016-02-15 19:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0015_auto_20160215_1946'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bookingaccount',
            name='address_post_code',
            field=models.CharField(blank=True, max_length=10),
        ),
        migrations.AlterField(
            model_name='bookingaccount',
            name='name',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
