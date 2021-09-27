# Generated by Django 1.10.3 on 2016-11-18 18:41

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0025_auto_20161118_1648"),
    ]

    operations = [
        migrations.AlterField(
            model_name="paymentsource",
            name="account_transfer_payment",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="bookings.AccountTransferPayment"
            ),
        ),
    ]
