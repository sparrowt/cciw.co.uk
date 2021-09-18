# Generated by Django 1.11.1 on 2017-06-26 19:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cciwmain', '0019_auto_20170410_1828'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='person',
            name='phone_number',
        ),
        migrations.RemoveField(
            model_name='person',
            name='roles',
        ),
        migrations.AlterField(
            model_name='campname',
            name='name',
            field=models.CharField(help_text='Name of set of camps. Should start with capital letter', max_length=255, unique=True),
        ),
        migrations.DeleteModel(
            name='Role',
        ),
    ]
