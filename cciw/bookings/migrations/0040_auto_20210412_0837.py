# Generated by Django 3.1.7 on 2021-04-12 07:37

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cciwmain', '0023_auto_20210412_0837'),
        ('bookings', '0039_auto_20210403_1924'),
    ]

    operations = [
        migrations.AlterField(
            model_name='accounttransferpayment',
            name='from_account',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='transfer_from_payments', to='bookings.bookingaccount'),
        ),
        migrations.AlterField(
            model_name='accounttransferpayment',
            name='to_account',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='transfer_to_payments', to='bookings.bookingaccount'),
        ),
        migrations.AlterField(
            model_name='booking',
            name='account',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='bookings', to='bookings.bookingaccount'),
        ),
        migrations.AlterField(
            model_name='booking',
            name='camp',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='bookings', to='cciwmain.camp'),
        ),
        migrations.AlterField(
            model_name='manualpayment',
            name='account',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='manual_payments', to='bookings.bookingaccount'),
        ),
        migrations.AlterField(
            model_name='payment',
            name='account',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='payments', to='bookings.bookingaccount'),
        ),
        migrations.AlterField(
            model_name='refundpayment',
            name='account',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='refund_payments', to='bookings.bookingaccount'),
        ),
    ]
