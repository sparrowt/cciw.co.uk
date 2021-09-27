# Generated by Django 1.9.2 on 2016-02-16 11:30

import json
import os

from django.db import migrations
from django_countries import countries


def forwards(apps, schema):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "addresses_migration_final.json")
    data = json.load(open(path))

    Booking = apps.get_model("bookings", "Booking")
    BookingAccount = apps.get_model("bookings", "BookingAccount")
    models = {
        "Booking": Booking,
        "BookingAccount": BookingAccount,
    }

    c = 0
    for item in data:
        if item["OK"] == "y":
            model = models[item["Model"]]
            part = item["Part"]
            id = item["id"]
            print(f"Fixing {model.__name__}:{id}:{part}")
            if part == "address":
                prefix = "address_"
            elif part == "contact_address":
                prefix = "contact_"
            elif part == "gp_address":
                prefix = "gp_"
            else:
                prefix = None
            item["country"] = countries.by_name(item["country"])
            field_d = {prefix + f: item[f] for f in ["line1", "line2", "city", "county", "country", "post_code"]}
            field_d[part] = ""

            model.objects.filter(id=id).update(**field_d)
            c += 1
    print(f"Migrated {c} records")


def backwards(apps, schema):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0021_auto_20160216_1128"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
