# Generated by Django 1.10.3 on 2016-11-18 18:16

from django.db import migrations


def forwards(apps, schema_editor):
    PaymentSource = apps.get_model("bookings.PaymentSource")
    Payment = apps.get_model("bookings.Payment")
    ManualPayment = apps.get_model("bookings.ManualPayment")
    RefundPayment = apps.get_model("bookings.RefundPayment")
    AccountTransferPayment = apps.get_model("bookings.AccountTransferPayment")
    PayPalIPN = apps.get_model("ipn.PayPalIPN")

    p_models_1 = {
        "manual_payment": ManualPayment,
        "refund_payment": RefundPayment,
        "account_transfer_payment": AccountTransferPayment,
        "ipn_payment": PayPalIPN,
    }
    p_models_2 = {m.__name__.lower(): (m, k) for k, m in p_models_1.items()}

    for p in Payment.objects.all():
        origin_id = p.origin_id
        name = p.origin_type.model
        kwargs = {}
        if name in p_models_2:
            m, a = p_models_2[name]
            try:
                item = m.objects.get(id=origin_id)
                kwargs[a] = item
            except m.DoesNotExist:
                print(f"Missing {name} {origin_id} for Payment {p.id}")
        else:
            raise AssertionError(f"Unexpected type {name} for Payment {p.id}")

        if kwargs:
            source = PaymentSource.objects.create(**kwargs)
            p.source = source
            p.save()


def backwards(apps, schema_editor):
    Payment = apps.get_model("bookings.Payment")
    Payment.objects.update(source=None)
    PaymentSource = apps.get_model("bookings.PaymentSource")
    PaymentSource.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0026_auto_20161118_1841"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
