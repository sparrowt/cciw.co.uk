# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2016-11-18 22:23
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0026_qualificationtype'),
    ]

    operations = [
        migrations.CreateModel(
            name='Qualification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_issued', models.DateField()),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='qualifications', to='officers.Application')),
                ('type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='qualifications', to='officers.QualificationType')),
            ],
        ),
    ]