# Generated by Django 1.9.2 on 2016-02-16 15:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0022_auto_20160216_1130"),
    ]

    operations = [
        migrations.AlterField(
            model_name="booking",
            name="address",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="booking",
            name="contact_address",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="booking",
            name="contact_name",
            field=models.CharField(blank=True, max_length=255, verbose_name="contact name"),
        ),
        migrations.AlterField(
            model_name="booking",
            name="contact_post_code",
            field=models.CharField(max_length=10, verbose_name="post code"),
        ),
        migrations.AlterField(
            model_name="booking",
            name="gp_address",
            field=models.TextField(blank=True, verbose_name="GP address"),
        ),
    ]
