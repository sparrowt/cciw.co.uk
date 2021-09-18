# Generated by Django 1.10.5 on 2017-04-22 10:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('officers', '0050_auto_20170421_1328'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='dbs_update_service_id',
            field=models.CharField(blank=True, default='', max_length=128, verbose_name='DBS update service ID'),
        ),
        migrations.AddField(
            model_name='dbscheck',
            name='dbs_update_service_id',
            field=models.CharField(blank=True, default='', max_length=128, verbose_name='DBS update service ID'),
        ),
    ]
