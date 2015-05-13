# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('officers', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReferenceAction',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('action_type', models.CharField(choices=[('request', 'Reference requested'), ('received', 'Reference receieved'), ('nag', 'Applicant nagged')], max_length=20)),
                ('reference', models.ForeignKey(related_name='actions', to='officers.Reference')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]