# Generated by Django 4.0.7 on 2022-11-23 18:13

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("officers", "0002_invitation"),
    ]

    operations = [
        migrations.CreateModel(
            name="CampRole",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
            ],
        ),
    ]
