# Generated by Django 1.10.5 on 2017-03-04 11:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0040_auto_20170304_1134'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dbsactionlog',
            name='timestamp',
            field=models.DateTimeField(verbose_name='Timestamp'),
        ),
    ]
