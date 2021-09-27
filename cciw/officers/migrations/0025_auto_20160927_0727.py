# Generated by Django 1.9.3 on 2016-09-27 06:27

from django.db import migrations, models

import cciw.officers.fields


class Migration(migrations.Migration):

    dependencies = [
        ("officers", "0024_auto_20151009_1632"),
    ]

    operations = [
        migrations.AlterField(
            model_name="application",
            name="address_email",
            field=cciw.officers.fields.RequiredEmailField(blank=True, max_length=254, verbose_name="email"),
        ),
        migrations.AlterField(
            model_name="referee",
            name="email",
            field=models.EmailField(blank=True, max_length=254, verbose_name="email"),
        ),
    ]
