# Generated by Django 3.1.7 on 2021-05-28 16:01

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0041_auto_20210506_0806"),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomAgreement",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("year", models.IntegerField()),
                ("text", models.TextField()),
                ("active", models.BooleanField()),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={
                "unique_together": {("name", "year")},
            },
        ),
    ]
