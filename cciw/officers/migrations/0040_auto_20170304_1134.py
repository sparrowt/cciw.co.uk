# Generated by Django 1.10.5 on 2017-03-04 11:34

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0039_auto_20170304_1119'),
    ]

    operations = [
        migrations.RenameField(
            model_name='dbsactionlog',
            old_name='sent',
            new_name='timestamp',
        ),
    ]
