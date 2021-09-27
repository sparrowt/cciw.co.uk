# Generated by Django 1.10.5 on 2017-04-22 11:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("officers", "0051_auto_20170422_1133"),
    ]

    operations = [
        migrations.AlterField(
            model_name="application",
            name="dbs_number",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Current enhanced DBS number with update service. Number usually starts 00…",
                max_length=128,
                verbose_name="DBS number",
            ),
        ),
        migrations.AlterField(
            model_name="application",
            name="dbs_update_service_id",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Number usually starts C…",
                max_length=128,
                verbose_name="DBS update service ID",
            ),
        ),
    ]
