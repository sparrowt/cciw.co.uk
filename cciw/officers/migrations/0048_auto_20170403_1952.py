# Generated by Django 1.10.5 on 2017-04-03 18:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("officers", "0047_dbscheck_applicant_accepted"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dbscheck",
            name="applicant_accepted",
            field=models.BooleanField(
                default=True, help_text="Uncheck if the applicant could not be accepted on the basis of this DBS check"
            ),
        ),
    ]
