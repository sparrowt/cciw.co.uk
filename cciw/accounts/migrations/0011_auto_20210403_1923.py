# Generated by Django 3.1.7 on 2021-04-03 18:23

from django.db import migrations

import cciw.accounts.models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_auto_20210118_0700'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='user',
            managers=[
                ('objects', cciw.accounts.models.UserManager()),
            ],
        ),
    ]
