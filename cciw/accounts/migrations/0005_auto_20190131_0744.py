# Generated by Django 2.0.10 on 2019-01-31 07:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_user_contact_phone_number"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="last_name",
            field=models.CharField(blank=True, max_length=150, verbose_name="last name"),
        ),
    ]
