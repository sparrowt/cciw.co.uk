# Generated by Django 3.2.6 on 2021-10-07 14:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0051_auto_20211006_1330"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="writeoffdebt",
            options={
                "base_manager_name": "objects",
                "verbose_name": "Write-off debt record",
                "verbose_name_plural": "Write-off debt records",
            },
        ),
    ]
