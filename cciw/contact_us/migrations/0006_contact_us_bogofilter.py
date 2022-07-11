# Generated by Django 4.0.4 on 2022-07-11 15:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contact_us", "0005_message_subject"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="bogosity",
            field=models.FloatField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name="message",
            name="spam_classification_bogofilter",
            field=models.CharField(
                choices=[
                    ("HAM", "Ham"),
                    ("SPAM", "Spam"),
                    ("UNSURE", "Unsure"),
                    ("ERROR", "Error"),
                    ("UNCLASSIFIED", "Unclassified"),
                ],
                default="UNCLASSIFIED",
                max_length=12,
                verbose_name="Bogofilter status",
            ),
        ),
        migrations.AddField(
            model_name="message",
            name="spam_classification_manual",
            field=models.CharField(
                choices=[("HAM", "Ham"), ("SPAM", "Spam"), ("UNCLASSIFIED", "Unclassified")],
                default="UNCLASSIFIED",
                max_length=12,
                verbose_name="Marked spam",
            ),
        ),
    ]
