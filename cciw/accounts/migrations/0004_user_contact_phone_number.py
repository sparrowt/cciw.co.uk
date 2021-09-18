# Generated by Django 1.11.1 on 2017-06-26 17:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_auto_20161118_2008'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='contact_phone_number',
            field=models.CharField(blank=True, help_text='Required only for staff like CPO who need to be contacted.', max_length=40, verbose_name='Phone number'),
        ),
    ]
