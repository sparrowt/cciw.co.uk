# Generated by Django 1.11.1 on 2017-06-13 11:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("officers", "0054_auto_20170613_1208"),
    ]

    operations = [
        migrations.AlterField(
            model_name="application",
            name="date_saved",
            field=models.DateField(blank=True, null=True, verbose_name="date saved"),
        ),
    ]
