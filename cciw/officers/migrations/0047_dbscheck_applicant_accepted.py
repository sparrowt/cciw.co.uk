# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-04-03 18:16
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0046_auto_20170403_1916'),
    ]

    operations = [
        migrations.AddField(
            model_name='dbscheck',
            name='applicant_accepted',
            field=models.BooleanField(default=True, help_text="Enter 'No' if the applicant could not be accepted on the basis of this DBS check"),
        ),
    ]
