# Generated by Django 3.1.7 on 2021-06-11 08:28

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0046_auto_20210529_0852'),
    ]

    operations = [
        migrations.AlterField(
            model_name='booking',
            name='custom_agreements_checked',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(), blank=True, default=list, help_text='Comma separated list of IDs of custom agreements the user has agreed to.', size=None),
        ),
    ]
