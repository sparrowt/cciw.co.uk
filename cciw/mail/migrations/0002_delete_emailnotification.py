# Generated by Django 1.11.17 on 2019-01-23 12:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mail', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(
            name='EmailNotification',
        ),
    ]
