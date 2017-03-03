# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-03-03 21:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0036_dbscheck_check_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dbscheck',
            name='completed',
            field=models.DateField(help_text='For full forms, use the date of issue. For online checks, use the date of the check', verbose_name='Date of issue/check'),
        ),
    ]