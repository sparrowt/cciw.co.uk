# Generated by Django 4.2.5 on 2024-01-09 21:29

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sitecontent", "0005_alter_htmlchunk_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="htmlchunk",
            name="name",
            field=models.SlugField(verbose_name="name"),
        ),
        migrations.AlterField(
            model_name="htmlchunk",
            name="id",
            field=models.BigIntegerField(primary_key=True, serialize=False),
        ),
    ]