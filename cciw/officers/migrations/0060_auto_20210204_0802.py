# Generated by Django 3.1.5 on 2021-02-04 08:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0059_auto_20201218_1322'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dbscheck',
            name='registered_with_dbs_update',
            field=models.BooleanField(null=True, verbose_name='registered with DBS update service'),
        ),
    ]