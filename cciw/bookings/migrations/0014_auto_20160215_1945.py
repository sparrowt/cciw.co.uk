# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-02-15 19:45
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0013_auto_20160215_1718'),
    ]

    operations = [
        migrations.RenameField(
            model_name='booking',
            old_name='post_code',
            new_name='address_post_code',
        ),
    ]