# Generated by Django 4.0.7 on 2022-10-15 13:05

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    replaces = [
        ("mail", "0001_initial"),
        ("mail", "0002_delete_emailnotification"),
        ("mail", "0003_emailforward"),
        ("mail", "0004_emailforward_enabled"),
        ("mail", "0005_auto_20201216_0844"),
        ("mail", "0006_auto_20201216_0844"),
        ("mail", "0007_delete_emailforward"),
    ]

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = []
