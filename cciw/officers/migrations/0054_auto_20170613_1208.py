# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-06-13 11:08
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0053_auto_20170602_0851'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='application',
            options={'base_manager_name': 'objects', 'ordering': ('-date_saved', 'officer__first_name', 'officer__last_name')},
        ),
        migrations.AlterModelOptions(
            name='referee',
            options={'ordering': ('application__date_saved', 'application__officer__first_name', 'application__officer__last_name', 'referee_number')},
        ),
        migrations.RenameField(
            model_name='application',
            old_name='date_submitted',
            new_name='date_saved',
        ),
    ]
