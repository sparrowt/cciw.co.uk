# Generated by Django 1.11.1 on 2017-06-02 07:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("officers", "0052_auto_20170422_1215"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="application",
            name="dbs_update_service_id",
        ),
        migrations.RemoveField(
            model_name="dbscheck",
            name="dbs_update_service_id",
        ),
    ]
