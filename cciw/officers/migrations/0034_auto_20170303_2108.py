# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-03-03 21:08
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0033_auto_20170303_2056'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='dbscheck',
            options={'verbose_name': 'DBS/CRB Disclosure', 'verbose_name_plural': 'DBS/CRB Disclosures'},
        ),
        migrations.AlterModelOptions(
            name='dbsformlog',
            options={'verbose_name': 'DBS form log', 'verbose_name_plural': 'DBS form logs'},
        ),
        migrations.RenameField(
            model_name='application',
            old_name='crb_check_consent',
            new_name='dbs_check_consent',
        ),
        migrations.RenameField(
            model_name='application',
            old_name='crb_number',
            new_name='dbs_number',
        ),
        migrations.RenameField(
            model_name='dbscheck',
            old_name='crb_number',
            new_name='dbs_number',
        ),
        migrations.AlterField(
            model_name='dbscheck',
            name='officer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dbs_applications', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='dbsformlog',
            name='officer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dbsformlogs', to=settings.AUTH_USER_MODEL),
        ),
    ]
