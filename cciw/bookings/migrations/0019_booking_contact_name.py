# Generated by Django 1.9.2 on 2016-02-16 11:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0018_auto_20160215_2101'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='contact_name',
            field=models.CharField(default='', max_length=255, verbose_name='contact name'),
            preserve_default=False,
        ),
    ]
