# Generated by Django 4.0.7 on 2022-10-15 13:15

import datetime
from decimal import Decimal

import django.contrib.postgres.fields
import django.db.models.deletion
import django.utils.timezone
import django_countries.fields
from django.db import migrations, models

import cciw.bookings.models
import cciw.documents.fields


class Migration(migrations.Migration):
    replaces = [
        ("bookings", "0001_initial"),
        ("bookings", "0002_booking_created_online"),
        ("bookings", "0003_auto_20150107_0959"),
        ("bookings", "0004_auto_20150407_1332"),
        ("bookings", "0005_auto_20150407_1333"),
        ("bookings", "0006_auto_20150610_1649"),
        ("bookings", "0007_fix_empty_values"),
        ("bookings", "0008_auto_20150814_1150"),
        ("bookings", "0009_auto_20151202_1629"),
        ("bookings", "0010_auto_20151210_1900"),
        ("bookings", "0011_auto_20160206_2214"),
        ("bookings", "0012_bookingaccount_subscribe_to_newsletter"),
        ("bookings", "0013_auto_20160215_1718"),
        ("bookings", "0014_auto_20160215_1945"),
        ("bookings", "0015_auto_20160215_1946"),
        ("bookings", "0016_auto_20160215_1947"),
        ("bookings", "0017_auto_20160215_2052"),
        ("bookings", "0018_auto_20160215_2101"),
        ("bookings", "0019_booking_contact_name"),
        ("bookings", "0020_booking_gp_post_code"),
        ("bookings", "0021_auto_20160216_1128"),
        ("bookings", "0022_auto_20160216_1130"),
        ("bookings", "0023_auto_20160216_1558"),
        ("bookings", "0024_auto_20160218_1622"),
        ("bookings", "0025_auto_20161118_1648"),
        ("bookings", "0026_auto_20161118_1841"),
        ("bookings", "0027_migrate_to_payment_source"),
        ("bookings", "0028_auto_20161118_1943"),
        ("bookings", "0029_auto_20170410_1828"),
        ("bookings", "0030_auto_20180406_1839"),
        ("bookings", "0031_auto_20180513_1934"),
        ("bookings", "0032_auto_20181215_1205"),
        ("bookings", "0033_auto_20190801_2018"),
        ("bookings", "0034_auto_20210204_0802"),
        ("bookings", "0035_auto_20210227_1637"),
        ("bookings", "0036_bookingaccount_created"),
        ("bookings", "0037_populate_bookingaccount_created"),
        ("bookings", "0038_auto_20210402_1106"),
        ("bookings", "0039_auto_20210403_1924"),
        ("bookings", "0040_auto_20210412_0837"),
        ("bookings", "0041_auto_20210506_0806"),
        ("bookings", "0042_customagreement"),
        ("bookings", "0043_auto_20210528_1702"),
        ("bookings", "0044_auto_20210528_1713"),
        ("bookings", "0045_auto_20210529_0728"),
        ("bookings", "0046_auto_20210529_0852"),
        ("bookings", "0047_auto_20210611_0928"),
        ("bookings", "0048_booking_publicity_photos_agreement"),
        ("bookings", "0049_populate_publicity_photos_agreement"),
        ("bookings", "0050_auto_20210818_1235"),
        ("bookings", "0051_auto_20211006_1330"),
        ("bookings", "0052_alter_writeoffdebt_options"),
        ("bookings", "0053_supporting_information"),
        ("bookings", "0054_alter_writeoffdebt_options"),
        ("bookings", "0055_auto_20211015_0050"),
        ("bookings", "0056_subscribe_to_newsletter_helptext"),
        ("bookings", "0057_default_country"),
    ]

    initial = True

    dependencies = [
        ("admin", "0001_initial"),
        ("ipn", "0007_auto_20160219_1135"),
        ("ipn", "0003_auto_20141117_1647"),
        ("cciwmain", "0023_auto_20210412_0837"),
        ("contenttypes", "0001_initial"),
        ("cciwmain", "0002_auto_20141231_1034"),
    ]

    operations = [
        migrations.CreateModel(
            name="BookingAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(blank=True, max_length=254, null=True, unique=True)),
                ("name", models.CharField(blank=True, max_length=100)),
                ("address_post_code", models.CharField(blank=True, max_length=10, verbose_name="post code")),
                ("phone_number", models.CharField(blank=True, max_length=22)),
                (
                    "share_phone_number",
                    models.BooleanField(
                        blank=True,
                        default=False,
                        verbose_name="Allow this phone number to be passed on to other parents to help organise transport",
                    ),
                ),
                (
                    "email_communication",
                    models.BooleanField(
                        blank=True,
                        default=True,
                        verbose_name="Receive all communication from CCiW by email where possible",
                    ),
                ),
                ("total_received", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10)),
                ("first_login", models.DateTimeField(blank=True, null=True)),
                ("last_login", models.DateTimeField(blank=True, null=True)),
                ("last_payment_reminder", models.DateTimeField(blank=True, null=True)),
                (
                    "subscribe_to_newsletter",
                    models.BooleanField(default=False, verbose_name="Subscribe to email newsletter"),
                ),
                ("address_city", models.CharField(blank=True, max_length=255, verbose_name="town/city")),
                (
                    "address_country",
                    django_countries.fields.CountryField(
                        blank=True, default="GB", max_length=2, null=True, verbose_name="country"
                    ),
                ),
                ("address_county", models.CharField(blank=True, max_length=255, verbose_name="county/state")),
                ("address_line1", models.CharField(blank=True, max_length=255, verbose_name="address line 1")),
                ("address_line2", models.CharField(blank=True, max_length=255, verbose_name="address line 2")),
                (
                    "subscribe_to_mailings",
                    models.BooleanField(
                        blank=True, default=None, null=True, verbose_name="Receive mailings about future camps"
                    ),
                ),
                ("created_at", models.DateTimeField()),
                ("erased_on", models.DateTimeField(blank=True, default=None, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="ManualPayment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "payment_type",
                    models.PositiveSmallIntegerField(
                        choices=[(0, "Cheque"), (1, "Cash"), (2, "e-Cheque"), (3, "Bank transfer")], default=0
                    ),
                ),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="manual_payments",
                        to="bookings.bookingaccount",
                    ),
                ),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
        ),
        migrations.CreateModel(
            name="RefundPayment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "payment_type",
                    models.PositiveSmallIntegerField(
                        choices=[(0, "Cheque"), (1, "Cash"), (2, "e-Cheque"), (3, "Bank transfer")], default=0
                    ),
                ),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="refund_payments",
                        to="bookings.bookingaccount",
                    ),
                ),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
        ),
        migrations.CreateModel(
            name="AccountTransferPayment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "from_account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="transfer_from_payments",
                        to="bookings.bookingaccount",
                    ),
                ),
                (
                    "to_account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="transfer_to_payments",
                        to="bookings.bookingaccount",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="PaymentSource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "account_transfer_payment",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="bookings.accounttransferpayment",
                    ),
                ),
                (
                    "ipn_payment",
                    models.OneToOneField(
                        blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="ipn.paypalipn"
                    ),
                ),
                (
                    "manual_payment",
                    models.OneToOneField(
                        blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="bookings.manualpayment"
                    ),
                ),
                (
                    "refund_payment",
                    models.OneToOneField(
                        blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="bookings.refundpayment"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Booking",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("first_name", models.CharField(max_length=100)),
                ("last_name", models.CharField(max_length=100)),
                ("sex", models.CharField(choices=[("m", "Male"), ("f", "Female")], max_length=1)),
                ("date_of_birth", models.DateField()),
                ("address_post_code", models.CharField(max_length=10, verbose_name="post code")),
                ("phone_number", models.CharField(blank=True, max_length=22)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("church", models.CharField(blank=True, max_length=100, verbose_name="name of church")),
                (
                    "south_wales_transport",
                    models.BooleanField(blank=True, default=False, verbose_name="require transport from South Wales"),
                ),
                ("contact_post_code", models.CharField(max_length=10, verbose_name="post code")),
                ("contact_phone_number", models.CharField(max_length=22)),
                ("dietary_requirements", models.TextField(blank=True)),
                ("gp_name", models.CharField(max_length=100, verbose_name="GP name")),
                ("gp_phone_number", models.CharField(max_length=22, verbose_name="GP phone number")),
                ("medical_card_number", models.CharField(max_length=100, verbose_name="NHS number")),
                ("last_tetanus_injection_date", models.DateField(blank=True, null=True)),
                ("allergies", models.TextField(blank=True)),
                ("regular_medication_required", models.TextField(blank=True)),
                ("illnesses", models.TextField(blank=True, verbose_name="Medical conditions")),
                (
                    "can_swim_25m",
                    models.BooleanField(blank=True, default=False, verbose_name="Can the camper swim 25m?"),
                ),
                ("learning_difficulties", models.TextField(blank=True)),
                ("serious_illness", models.BooleanField(blank=True, default=False)),
                ("agreement", models.BooleanField(default=False)),
                (
                    "price_type",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (0, "Full price"),
                            (1, "2nd child discount"),
                            (2, "3rd child discount"),
                            (3, "Custom discount"),
                        ]
                    ),
                ),
                ("early_bird_discount", models.BooleanField(default=False, help_text="Online bookings only")),
                ("booked_at", models.DateTimeField(blank=True, help_text="Online bookings only", null=True)),
                ("amount_due", models.DecimalField(decimal_places=2, max_digits=10)),
                ("shelved", models.BooleanField(default=False, help_text="Used by user to put on 'shelf'")),
                (
                    "state",
                    models.IntegerField(
                        choices=[
                            (0, "Information complete"),
                            (1, "Manually approved"),
                            (2, "Booked"),
                            (3, "Cancelled - deposit kept"),
                            (4, "Cancelled - half refund (pre 2015 only)"),
                            (5, "Cancelled - full refund"),
                        ],
                        help_text="<ul><li>To book, set to 'Booked' <b>and</b> ensure 'Booking expires' is empty</li><li>For people paying online who have been stopped (e.g. due to having a custom discount or serious illness or child too young etc.), set to 'Manually approved' to allow them to book and pay</li><li>If there are queries before it can be booked, set to 'Information complete'</li></ul>",
                    ),
                ),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("booking_expires", models.DateTimeField(blank=True, null=True)),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="bookings",
                        to="bookings.bookingaccount",
                    ),
                ),
                (
                    "camp",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, related_name="bookings", to="cciwmain.camp"
                    ),
                ),
                ("created_online", models.BooleanField(blank=True, default=False)),
                ("address_city", models.CharField(max_length=255, verbose_name="town/city")),
                (
                    "address_country",
                    django_countries.fields.CountryField(default="GB", max_length=2, null=True, verbose_name="country"),
                ),
                ("address_county", models.CharField(blank=True, max_length=255, verbose_name="county/state")),
                ("address_line1", models.CharField(max_length=255, verbose_name="address line 1")),
                ("address_line2", models.CharField(blank=True, max_length=255, verbose_name="address line 2")),
                ("contact_city", models.CharField(max_length=255, verbose_name="town/city")),
                (
                    "contact_country",
                    django_countries.fields.CountryField(default="GB", max_length=2, null=True, verbose_name="country"),
                ),
                ("contact_county", models.CharField(blank=True, max_length=255, verbose_name="county/state")),
                ("contact_line1", models.CharField(max_length=255, verbose_name="address line 1")),
                ("contact_line2", models.CharField(blank=True, max_length=255, verbose_name="address line 2")),
                ("gp_city", models.CharField(max_length=255, verbose_name="town/city")),
                (
                    "gp_country",
                    django_countries.fields.CountryField(default="GB", max_length=2, null=True, verbose_name="country"),
                ),
                ("gp_county", models.CharField(blank=True, max_length=255, verbose_name="county/state")),
                ("gp_line1", models.CharField(max_length=255, verbose_name="address line 1")),
                ("gp_line2", models.CharField(blank=True, max_length=255, verbose_name="address line 2")),
                ("contact_name", models.CharField(blank=True, max_length=255, verbose_name="contact name")),
                ("gp_post_code", models.CharField(max_length=10, verbose_name="post code")),
                ("erased_on", models.DateTimeField(blank=True, default=None, null=True)),
                (
                    "custom_agreements_checked",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.IntegerField(),
                        blank=True,
                        default=list,
                        help_text="Comma separated list of IDs of custom agreements the user has agreed to.",
                        size=None,
                    ),
                ),
                ("publicity_photos_agreement", models.BooleanField(blank=True, default=False)),
            ],
            options={
                "ordering": ["-created_at"],
                "base_manager_name": "objects",
            },
        ),
        migrations.CreateModel(
            name="CustomAgreement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(help_text="Appears as a title on 'Add place' page", max_length=255)),
                ("year", models.IntegerField(help_text="Camp year this applies to")),
                ("text_html", models.TextField(help_text="Text of the agreement, in HTML format")),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("sort_order", models.IntegerField(default=1)),
            ],
            options={
                "unique_together": {("name", "year")},
                "ordering": ["year", "sort_order"],
            },
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("processed", models.DateTimeField(null=True)),
                ("created_at", models.DateTimeField()),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="payments",
                        to="bookings.bookingaccount",
                    ),
                ),
                (
                    "source",
                    models.OneToOneField(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="bookings.paymentsource"
                    ),
                ),
            ],
            options={
                "base_manager_name": "objects",
            },
        ),
        migrations.CreateModel(
            name="Price",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("year", models.PositiveSmallIntegerField()),
                (
                    "price_type",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (0, "Full price"),
                            (1, "2nd child discount"),
                            (2, "3rd child discount"),
                            (4, "South wales transport surcharge (pre 2015)"),
                            (5, "Deposit"),
                            (6, "Early bird discount"),
                        ]
                    ),
                ),
                ("price", models.DecimalField(decimal_places=2, max_digits=10)),
            ],
            options={
                "unique_together": {("year", "price_type")},
            },
        ),
        migrations.CreateModel(
            name="WriteOffDebt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="write_off_debt",
                        to="bookings.bookingaccount",
                    ),
                ),
            ],
            options={
                "base_manager_name": "objects",
                "verbose_name": "write-off debt record",
                "verbose_name_plural": "write-off debt records",
            },
            bases=(cciw.bookings.models.NoEditMixin, models.Model),
        ),
        migrations.AddField(
            model_name="paymentsource",
            name="write_off_debt",
            field=models.OneToOneField(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="bookings.writeoffdebt"
            ),
        ),
        migrations.CreateModel(
            name="SupportingInformationDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("filename", models.CharField(max_length=255)),
                ("mimetype", models.CharField(max_length=255)),
                ("size", models.PositiveIntegerField()),
                ("content", models.BinaryField()),
                ("erased_on", models.DateTimeField(blank=True, default=None, null=True)),
            ],
            options={
                "base_manager_name": "objects",
            },
        ),
        migrations.CreateModel(
            name="SupportingInformationType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="SupportingInformation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("date_received", models.DateField(default=datetime.date.today)),
                (
                    "from_name",
                    models.CharField(
                        help_text="Name of person or organisation the information is from", max_length=100
                    ),
                ),
                ("from_email", models.EmailField(blank=True, max_length=254)),
                ("from_telephone", models.CharField(blank=True, max_length=30)),
                ("notes", models.TextField(blank=True)),
                (
                    "booking",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="supporting_information_records",
                        to="bookings.booking",
                    ),
                ),
                (
                    "document",
                    cciw.documents.fields.DocumentField(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="supporting_information",
                        to="bookings.supportinginformationdocument",
                    ),
                ),
                (
                    "information_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to="bookings.supportinginformationtype"
                    ),
                ),
                ("erased_on", models.DateTimeField(blank=True, default=None, null=True)),
            ],
            options={
                "verbose_name": "supporting information record",
                "verbose_name_plural": "supporting information records",
            },
        ),
    ]
