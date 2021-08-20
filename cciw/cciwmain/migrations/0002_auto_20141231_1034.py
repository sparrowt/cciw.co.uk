# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0001_initial'),
        ('cciwmain', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='camp',
            name='officers',
            field=models.ManyToManyField(through='officers.Invitation', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='camp',
            name='previous_camp',
            field=models.ForeignKey(null=True, to='cciwmain.Camp', blank=True, verbose_name='previous camp', related_name='next_camps', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='camp',
            name='site',
            field=models.ForeignKey(to='cciwmain.Site', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='camp',
            unique_together={('number', 'year')},
        ),
    ]
