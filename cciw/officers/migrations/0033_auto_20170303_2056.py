# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-03-03 20:56
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0032_auto_20170303_2056'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='CRBFormLog',
            new_name='DBSFormLog',
        ),
    ]