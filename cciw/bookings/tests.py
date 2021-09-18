import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest import TestCase, mock

import vcr
import xlrd
from django.conf import settings
from django.core import mail, signing
from django.db import models
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from django_functest import FuncBaseMixin
from hypothesis import example, given
from hypothesis import strategies as st
from paypal.standard.ipn.models import PayPalIPN

from cciw.accounts.models import User
from cciw.bookings.email import EmailVerifyTokenGenerator, VerifyExpired, VerifyFailed, send_payment_reminder_emails
from cciw.bookings.hooks import paypal_payment_received, unrecognised_payment
from cciw.bookings.mailchimp import get_status
from cciw.bookings.management.commands.expire_bookings import Command as ExpireBookingsCommand
from cciw.bookings.middleware import BOOKING_COOKIE_SALT
from cciw.bookings.models import (AccountTransferPayment, AgreementFetcher, Booking, BookingAccount, BookingState,
                                  CustomAgreement, ManualPayment, ManualPaymentType, Payment, PaymentSource, Price,
                                  PriceChecker, PriceType, RefundPayment, book_basket_now, build_paypal_custom_field,
                                  expire_bookings)
from cciw.bookings.utils import camp_bookings_to_spreadsheet, payments_to_spreadsheet
from cciw.cciwmain.models import Camp, Person
from cciw.cciwmain.tests.base import factories as camps_factories
from cciw.cciwmain.tests.mailhelpers import path_and_query_to_url, read_email_url
from cciw.mail.tests import send_queued_mail
from cciw.officers.tests.base import (BOOKING_SECRETARY, BOOKING_SECRETARY_PASSWORD, BOOKING_SECRETARY_USERNAME,
                                      OFFICER, OfficersSetupMixin)
from cciw.sitecontent.models import HtmlChunk
from cciw.utils.spreadsheet import ExcelFormatter
from cciw.utils.tests.base import AtomicChecksMixin, FactoriesBase, TestBase, disable_logging
from cciw.utils.tests.db import refresh
from cciw.utils.tests.webtest import SeleniumBase, WebTestBase


class Factories(FactoriesBase):
    def create_booking(
            self,
            camp=None,
            sex='m',
            state=BookingState.INFO_COMPLETE,
            account=None,
            amount_due=100,
            address_line1='',
            date_of_birth=None,
    ) -> Booking:
        camp = camp or camps_factories.get_any_camp()
        account = account or self.create_booking_account()
        if date_of_birth is None:
            date_of_birth = date(date.today().year - camp.minimum_age - 2, 1, 1)
        return Booking.objects.create(
            camp=camp,
            account=account,
            state=state,
            sex=sex,
            date_of_birth=date_of_birth,
            price_type=PriceType.FULL,
            amount_due=amount_due,
            address_line1=address_line1,
        )

    def create_booking_account(
            self,
            address_line1='',
    ) -> BookingAccount:
        return BookingAccount.objects.create(
            name='A Booker',
            address_line1=address_line1,
        )

    def create_processed_payment(
            self,
            account=None,
            amount=1,
    ):
        manual_payment = self.create_manual_payment(account=account, amount=amount)
        payment = manual_payment.paymentsource.payment
        payment.refresh_from_db()
        assert payment.processed  # should have been done via process_all_payments via signals
        return payment

    def create_manual_payment(
            self,
            account=None,
            amount=1,
    ):
        return ManualPayment.objects.create(
            account=account or self.create_booking_account(),
            amount=amount,
            payment_type=ManualPaymentType.CHEQUE,
        )

    def create_refund_payment(
            self,
            account=None,
            amount=1,
    ):
        return RefundPayment.objects.create(
            account=account or self.create_booking_account(),
            amount=amount,
            payment_type=ManualPaymentType.CHEQUE,
        )

    def create_ipn(self, account=None, **kwargs):
        if account is not None:
            custom = build_paypal_custom_field(account)
        else:
            custom = ''
        defaults = dict(mc_gross=Decimal('1.00'),
                        custom=custom,
                        ipaddress='127.0.0.1',
                        payment_status='Completed',
                        txn_id='1',
                        business=settings.PAYPAL_RECEIVER_EMAIL,
                        payment_date=timezone.now(),
                        )
        defaults.update(kwargs)
        ipn = PayPalIPN.objects.create(**defaults)
        ipn.send_signals()
        return ipn

    def create_custom_agreement(self, *, year, name, text_html='Text'):
        return CustomAgreement.objects.create(
            year=year,
            name=name,
            text_html=text_html,
            active=True,
        )


factories = Factories()


class IpnMock:
    payment_status = 'Completed'
    business = settings.PAYPAL_RECEIVER_EMAIL


# == Mixins to reduce duplication ==
class CreateCampMixin:

    camp_minimum_age = 11
    camp_maximum_age = 17

    def create_camps(self):
        if hasattr(self, 'camp'):
            return
        self.today = date.today()
        # Need to create a Camp that we can choose i.e. is in the future.
        # We also need it so that payments can be made when only the deposit is due
        delta_days = 20 + settings.BOOKING_FULL_PAYMENT_DUE_DAYS
        start_date = self.today + timedelta(delta_days)
        camp_name = camps_factories.get_or_create_camp_name("Blue")
        camp_name_2 = camps_factories.get_or_create_camp_name("Red")
        self.camp = camps_factories.create_camp(
            year=start_date.year,
            camp_name=camp_name,
            minimum_age=self.camp_minimum_age,
            maximum_age=self.camp_maximum_age,
            start_date=start_date,
        )
        self.camp_2 = camps_factories.create_camp(
            year=start_date.year,
            camp_name=camp_name_2,
            minimum_age=self.camp_minimum_age,
            maximum_age=self.camp_maximum_age,
            start_date=start_date + timedelta(days=7),
        )


class CreateLeadersMixin:
    def create_leaders(self):
        self.leader_1 = Person.objects.create(name="Mr Leader")
        self.leader_2 = Person.objects.create(name="Mrs Leaderess")

        self.leader_1_user = User.objects.create(username="leader1",
                                                 email="leader1@mail.com")
        self.leader_2_user = User.objects.create(username="leader2",
                                                 email="leader2@mail.com")

        self.leader_1.users.add(self.leader_1_user)
        self.leader_2.users.add(self.leader_2_user)

        self.camp.leaders.add(self.leader_1)
        self.camp.leaders.add(self.leader_2)


class CreatePricesMixin:
    def add_prices(self, deposit=None):
        if deposit is None:
            deposit = Decimal(20)
        else:
            deposit = Decimal(deposit)
        year = self.camp.year
        self.price_full = Price.objects.get_or_create(year=year,
                                                      price_type=PriceType.FULL,
                                                      price=Decimal('100'))[0].price
        self.price_2nd_child = Price.objects.get_or_create(year=year,
                                                           price_type=PriceType.SECOND_CHILD,
                                                           price=Decimal('75'))[0].price
        self.price_3rd_child = Price.objects.get_or_create(year=year,
                                                           price_type=PriceType.THIRD_CHILD,
                                                           price=Decimal('50'))[0].price
        self.price_deposit = Price.objects.get_or_create(year=year,
                                                         price_type=PriceType.DEPOSIT,
                                                         defaults={'price': deposit})[0].price
        self.price_early_bird_discount = Price.objects.get_or_create(year=year,
                                                                     price_type=PriceType.EARLY_BIRD_DISCOUNT,
                                                                     price=Decimal('10'))[0].price

    def setUp(self):
        super().setUp()
        self.create_camps()


class LogInMixin:
    email = 'booker@bookers.com'

    def login(self, add_account_details=True, shortcut=None):
        if hasattr(self, '_logged_in'):
            return

        if shortcut is None:
            shortcut = self.is_full_browser_test

        if shortcut:
            account, _ = BookingAccount.objects.get_or_create(email=self.email)
            self._set_signed_cookie('bookingaccount', account.id,
                                    salt=BOOKING_COOKIE_SALT,
                                    max_age=settings.BOOKING_SESSION_TIMEOUT_SECONDS)
        else:
            # Easiest way is to simulate what the user actually has to do
            self.get_url('cciw-bookings-start')
            self.fill_by_name({'email': self.email})
            self.submit('[type=submit]')
            url, path, querydata = read_email_url(mail.outbox.pop(), "https://.*/booking/v/.*")
            self.get_literal_url(path_and_query_to_url(path, querydata))

        if add_account_details:
            BookingAccount.objects.filter(email=self.email).update(name='Joe',
                                                                   address_line1='456 My Street',
                                                                   address_city='Metrocity',
                                                                   address_country='GB',
                                                                   address_post_code='XYZ',
                                                                   phone_number='0123 456789')
        self._logged_in = True

    def get_account(self):
        return BookingAccount.objects.get(email=self.email)

    def _set_signed_cookie(self, key, value, salt='', **kwargs):
        value = signing.get_cookie_signer(salt=key + salt).sign(value)
        if self.is_full_browser_test:
            if not self._have_visited_page():
                self.get_url('django_functest.emptypage')
            return self._add_cookie({'name': key,
                                     'value': value,
                                     'path': '/'})
        else:
            return self.app.set_cookie(key, value)


class PlaceDetailsMixin(CreateCampMixin):

    @property
    def place_details(self):
        return {
            'camp': self.camp,
            'first_name': 'Frédéric',
            'last_name': 'Bloggs',
            'sex': 'm',
            'date_of_birth': f'{self.camp.year - 14}-01-01',
            'address_line1': '123 My street',
            'address_city': 'Metrocity',
            'address_country': 'GB',
            'address_post_code': 'ABC 123',
            'contact_name': 'Mr Father',
            'contact_line1': '98 Main Street',
            'contact_city': 'Metrocity',
            'contact_country': 'GB',
            'contact_post_code': 'ABC 456',
            'contact_phone_number': '01982 987654',
            'gp_name': 'Doctor Who',
            'gp_line1': 'The Tardis',
            'gp_city': 'London',
            'gp_country': 'GB',
            'gp_post_code': 'SW1 1PQ',
            'gp_phone_number': '01234 456789',
            'medical_card_number': 'asdfasdf',
            'agreement': True,
            'price_type': '0',
            'last_tetanus_injection_date': f'{self.camp.year - 5}-02-03',
        }

    def setUp(self):
        super().setUp()
        self.create_camps()


class CreateBookingModelMixin(CreatePricesMixin, PlaceDetailsMixin):
    """
    Mixin that provides method to create bookings in the database,
    similar to how they are created in public views
    """
    email = 'booker@bookers.com'

    def create_booking_model(self, extra=None) -> Booking:
        """
        Creates a complete Booking place in the database directly, without using public views
        """
        self.add_prices()
        data = self.place_details.copy()
        data['account'] = self.get_account()
        data['state'] = BookingState.INFO_COMPLETE
        data['amount_due'] = Decimal('0.00')
        if extra:
            data.update(extra)

        booking = Booking.objects.create(**data)
        booking.auto_set_amount_due()
        booking.save()
        # Ensure we get a copy as it is from the DB
        return Booking.objects.get(id=booking.id)

    def create_booking(self, extra=None, shortcut=True) -> Booking:
        return self.create_booking_model(extra=extra)

    def get_account(self):
        return BookingAccount.objects.get_or_create(email=self.email)[0]


class CreateBookingWebMixin(CreateBookingModelMixin, LogInMixin):

    def create_booking(self, extra=None, shortcut=None) -> Booking:
        """
        Logs in and creates a booking
        """
        if shortcut is None:
            shortcut = self.is_full_browser_test

        self.login(shortcut=shortcut)

        if shortcut:
            return self.create_booking_model(extra=extra)

        # Otherwise, we use public views to create place, to ensure that they
        # are created in the same way that a user would.
        old_booking_ids = list(Booking.objects.values_list('id', flat=True))
        self.add_prices()
        data = self.place_details.copy()
        if extra is not None:
            data.update(extra)

        self.get_url('cciw-bookings-add_place')
        # Sanity check:
        self.assertTextPresent("Please enter the details needed to book a place on a camp")
        self.fill_by_name(data)
        self.submit('#id_save_btn')
        self.assertUrlsEqual(reverse('cciw-bookings-list_bookings'))
        new_booking = Booking.objects.exclude(id__in=old_booking_ids).get()
        return new_booking

    def fill(self, data):
        data2 = {}
        for k, v in data.items():
            if isinstance(v, models.Model):
                # Allow using Camp instances
                data2[k] = v.id
            else:
                data2[k] = v
        return super().fill(data2)


class BookingBaseMixin(AtomicChecksMixin):

    # Constants used in 'assertTextPresent' and 'assertTextAbsent', the latter
    # being prone to false positives if a constant isn't used.
    ABOVE_MAXIMUM_AGE = "above the maximum age"
    BELOW_MINIMUM_AGE = "below the minimum age"
    CAMP_CLOSED_FOR_BOOKINGS = "This camp is closed for bookings"
    CANNOT_USE_2ND_CHILD = "You cannot use a 2nd child discount"
    CANNOT_USE_MULTIPLE_DISCOUNT_FOR_ONE_CAMPER = "only one place may use a 2nd/3rd child discount"
    MULTIPLE_2ND_CHILD_WARNING = "You have multiple places at '2nd child"
    MULTIPLE_FULL_PRICE_WARNING = "You have multiple places at 'Full price"
    NOT_ENOUGH_PLACES = "There are not enough places left on this camp"
    NOT_ENOUGH_PLACES_FOR_BOYS = "There are not enough places for boys left on this camp"
    NOT_ENOUGH_PLACES_FOR_GIRLS = "There are not enough places for girls left on this camp"
    NO_PLACES_LEFT = "There are no places left on this camp"
    NO_PLACES_LEFT_FOR_BOYS = "There are no places left for boys"
    NO_PLACES_LEFT_FOR_GIRLS = "There are no places left for girls"
    PRICES_NOT_SET = "prices have not been set"
    LAST_TETANUS_INJECTION_DATE_REQUIRED = "last tetanus injection"
    BOOKINGS_WILL_EXPIRE = 'you have 24 hours to complete payment online'
    THANK_YOU_FOR_PAYMENT = 'Thank you for your payment'

    def setUp(self):
        super().setUp()
        HtmlChunk.objects.get_or_create(name="bookingform_post_to", menu_link=None)
        HtmlChunk.objects.get_or_create(name="booking_secretary_address", menu_link=None)


# == Test cases ==

# Most tests are against views, instead of model-based tests.
# Booking.get_booking_problems(), for instance, is tested especially in
# TestListBookings. In theory this could be tested using model-based tests
# instead, but the way that multiple bookings and the basket/shelf interact mean
# we need to test the view code as well. It would probably be good to rewrite
# using a class like "CheckoutPage", which combines shelf and basket bookings,
# and some of the logic in BookingListBookings. There is also the advantage that
# using self.create_booking() (which uses a view) ensures Booking instances are
# created the same way a user would.


class TestBookingModels(CreateBookingModelMixin, AtomicChecksMixin, TestBase):

    def get_account(self) -> BookingAccount:
        if BookingAccount.objects.filter(email=self.email).count() == 0:
            BookingAccount.objects.create(email=self.email)

        if getattr(self, 'use_prefetch_related_for_get_account', False):
            return BookingAccount.objects.filter(email=self.email).prefetch_related('bookings')[0]
        else:
            return BookingAccount.objects.get(email=self.email)

    def test_camp_open_for_bookings(self):
        self.assertTrue(self.camp.open_for_bookings(self.today))
        self.assertTrue(self.camp.open_for_bookings(self.camp.start_date))
        self.assertFalse(self.camp.open_for_bookings(self.camp.start_date + timedelta(days=1)))

        self.camp.last_booking_date = self.today
        self.assertTrue(self.camp.open_for_bookings(self.today))
        self.assertFalse(self.camp.open_for_bookings(self.today + timedelta(days=1)))

    @mock.patch('cciw.bookings.models.early_bird_is_available', return_value=False)
    def test_book_with_money_in_account(self, m):
        self.create_booking_model()

        # Put some money in the account - just the deposit price will do.
        acc = self.get_account()
        acc.receive_payment(self.price_deposit)
        acc.save()

        # Book
        book_basket_now(acc.bookings.all())

        # Place should be booked AND should not expire
        acc = self.get_account()
        b = acc.bookings.all()[0]
        self.assertEqual(b.state, BookingState.BOOKED)
        self.assertEqual(b.booking_expires, None)

        acc = self.get_account()
        # balance should be zero
        price_checker = PriceChecker()
        price_checker._fetch_deposit_prices(b.camp.year)  # Force evaluation to check for zero queries later.
        with self.assertNumQueries(0 if getattr(self, 'use_prefetch_related_for_get_account', False) else 2):
            self.assertEqual(acc.get_balance(
                confirmed_only=False,
                allow_deposits=True,
                price_checker=price_checker,
            ), Decimal('0.00'))
            self.assertEqual(acc.get_balance(
                confirmed_only=True,
                allow_deposits=True,
                price_checker=price_checker,
            ), Decimal('0.00'))

        # But for full amount, they still owe 80 (full price minus deposit)
        self.assertEqual(acc.get_balance_full(), Decimal('80.00'))

        # Test some model methods:
        self.assertEqual(len(acc.bookings.payable(confirmed_only=False)),
                         1)

    def test_get_balance_opts(self):
        # Tests that the other code paths in get_balance/BookingManager.payable
        # work.
        self.use_prefetch_related_for_get_account = True
        self.test_book_with_money_in_account()

    def test_booking_missing_agreements(self):
        booking = factories.create_booking(state=BookingState.BOOKED)
        agreement = factories.create_custom_agreement(year=self.camp.year, name='test')
        # Other agreement, different year so should be irrelevant:
        factories.create_custom_agreement(year=self.camp.year - 1, name='x')
        assert booking in Booking.objects.agreement_fix_required()
        assert booking not in Booking.objects.no_missing_agreements()
        assert booking.get_missing_agreements() == [agreement]

        booking.custom_agreements_checked = [agreement.id]
        booking.save()

        assert booking not in Booking.objects.agreement_fix_required()
        assert booking not in Booking.objects.missing_agreements()
        assert booking in Booking.objects.no_missing_agreements()
        assert booking.get_missing_agreements() == []

    def test_get_missing_agreements_performance(self):
        # We can use common AgreementFetcher with get_missing_agreements to get
        # good performance:
        bookings = []
        for i in range(0, 20):
            bookings.append(factories.create_booking())
        agreement = factories.create_custom_agreement(year=self.camp.year, name='test')
        agreement_fetcher = AgreementFetcher()
        with self.assertNumQueries(2):
            bookings = Booking.objects.filter(id__in=[booking.id for booking in bookings]).select_related('camp')
            for booking in bookings:
                assert booking.get_missing_agreements(agreement_fetcher=agreement_fetcher) == [agreement]


class TestBookingIndex(BookingBaseMixin, CreatePricesMixin, CreateCampMixin, WebTestBase):

    def test_show_with_no_prices(self):
        self.get_url('cciw-bookings-index')
        self.assertTextPresent(f"Prices for {self.camp.year} have not been finalised yet")

    def test_show_with_prices(self):
        self.add_prices()  # need for booking to be open
        self.get_url('cciw-bookings-index')
        self.assertTextPresent("£100")
        self.assertTextPresent("£20")  # Deposit price


class BookingStartBase(BookingBaseMixin, CreateBookingWebMixin, FuncBaseMixin):

    urlname = 'cciw-bookings-start'

    def submit(self, css_selector='[type=submit]'):
        return super().submit(css_selector)

    def test_show_form(self):
        self.get_url(self.urlname)
        self.assertTextPresent('id_email')

    def test_complete_form(self):
        self.assertEqual(BookingAccount.objects.all().count(), 0)
        self.get_url(self.urlname)
        self.fill_by_name({'email': 'booker@bookers.com'})
        self.submit()
        self.assertEqual(BookingAccount.objects.all().count(), 0)
        self.assertEqual(len(mail.outbox), 1)

    def test_complete_form_existing_email(self):
        BookingAccount.objects.create(email="booker@bookers.com")
        self.assertEqual(BookingAccount.objects.all().count(), 1)
        self.get_url(self.urlname)
        self.fill_by_name({'email': 'booker@bookers.com'})
        self.submit()
        self.assertEqual(BookingAccount.objects.all().count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_complete_form_existing_email_different_case(self):
        BookingAccount.objects.create(email="booker@bookers.com")
        self.assertEqual(BookingAccount.objects.all().count(), 1)
        self.get_url(self.urlname)
        self.fill_by_name({'email': 'BOOKER@bookers.com'})
        self.submit()
        self.assertEqual(BookingAccount.objects.all().count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_skip_if_logged_in(self):
        # This assumes verification process works
        # Check redirect to step 3 - account details
        self.login(add_account_details=False)
        self.get_url(self.urlname)
        self.assertUrlsEqual(reverse('cciw-bookings-account_details'))

    def test_skip_if_account_details(self):
        # Check redirect to step 4 - add place
        self.login()
        self.get_url(self.urlname)
        self.assertUrlsEqual(reverse('cciw-bookings-add_place'))

    def test_skip_if_has_place_details(self):
        # Check redirect to overview
        self.create_booking()
        self.get_url(self.urlname)
        self.assertUrlsEqual(reverse('cciw-bookings-account_overview'))


class TestBookingStartWT(BookingStartBase, WebTestBase):
    pass


class TestBookingStartSL(BookingStartBase, SeleniumBase):
    pass


class BookingVerifyBase(BookingBaseMixin, FuncBaseMixin):

    def submit(self, css_selector='[type=submit]'):
        return super().submit(css_selector)

    def _read_email_verify_email(self, email):
        return read_email_url(email, "https://.*/booking/v/.*")

    def _start(self):
        # Assumes booking_start works:
        self.get_url('cciw-bookings-start')
        self.fill_by_name({'email': 'booker@bookers.com'})
        self.submit()

    def test_verify_correct(self):
        """
        Test the email verification stage when the URL is correct
        """
        self._start()
        url, path, querydata = self._read_email_verify_email(mail.outbox[-1])
        self.get_literal_url(path_and_query_to_url(path, querydata))
        self.assertUrlsEqual(reverse('cciw-bookings-account_details'))
        self.assertTextPresent("Logged in as booker@bookers.com! You will stay logged in for two weeks")
        acc = BookingAccount.objects.get(email='booker@bookers.com')
        self.assertTrue(acc.last_login is not None)
        self.assertTrue(acc.first_login is not None)

    def _add_booking_account_address(self):
        acc, _ = BookingAccount.objects.get_or_create(email='booker@bookers.com')
        acc.name = "Joe"
        acc.address_line1 = "Home"
        acc.address_city = "My city"
        acc.address_country = "GB"
        acc.address_post_code = "XY1 D45"
        acc.save()

    def test_verify_correct_and_has_details(self):
        """
        Test the email verification stage when the URL is correct and the
        account already has name and address
        """
        self._start()
        self._add_booking_account_address()
        url, path, querydata = self._read_email_verify_email(mail.outbox[-1])
        self.get_literal_url(path_and_query_to_url(path, querydata))
        self.assertUrlsEqual(reverse('cciw-bookings-add_place'))

    def test_verify_correct_and_has_old_details(self):
        """
        Test the email verification stage when the URL is correct and the
        account already has name and address, but they haven't logged in
        for 'a while'.
        """
        self._start()
        self._add_booking_account_address()
        acc = BookingAccount.objects.get(email='booker@bookers.com')
        acc.first_login = timezone.now() - timedelta(30 * 7)
        acc.last_login = acc.first_login
        acc.save()

        url, path, querydata = self._read_email_verify_email(mail.outbox[-1])
        self.get_literal_url(path_and_query_to_url(path, querydata))
        self.assertUrlsEqual(reverse('cciw-bookings-account_details'))
        self.assertTextPresent("Welcome back!")
        self.assertTextPresent("Please check and update your account details")

    def test_verify_incorrect(self):
        """
        Test the email verification stage when the URL is incorrect
        """
        self._start()

        # The following will trigger a BadSignature
        url, path, querydata = self._read_email_verify_email(mail.outbox[-1])
        querydata['bt'] = 'a000' + querydata['bt']
        self.get_literal_url(path_and_query_to_url(path, querydata))
        self.assertTextPresent("failed")

        # This will trigger a base64 decode error:
        url, path, querydata = self._read_email_verify_email(mail.outbox[-1])
        querydata['bt'] = 'XXX' + querydata['bt']
        self.get_literal_url(path_and_query_to_url(path, querydata))
        self.assertTextPresent("failed")

        # This will trigger a UnicodeDecodeError
        url, path, querydata = self._read_email_verify_email(mail.outbox[-1])
        querydata['bt'] = 'xxxx'
        self.get_literal_url(path_and_query_to_url(path, querydata))
        self.assertTextPresent("failed")


class TestBookingVerifyWT(BookingVerifyBase, WebTestBase):
    pass


class TestBookingVerifySL(BookingVerifyBase, SeleniumBase):
    pass


class TestPaymentReminderEmails(CreateBookingModelMixin, BookingBaseMixin, WebTestBase):

    def _create_booking(self):
        booking = self.create_booking_model()
        book_basket_now(booking.account.bookings.all())
        booking = Booking.objects.get(id=booking.id)
        booking.confirm()
        self.assertEqual(len(BookingAccount.objects.payments_due()), 1)
        return booking

    def test_payment_reminder_email(self):
        booking = self._create_booking()
        mail.outbox = []
        send_payment_reminder_emails()
        self.assertEqual(len(mail.outbox), 1)
        m = mail.outbox[0]
        self.assertIn("You have payments due", m.body)
        self.assertEqual("[CCIW] Payment due", m.subject)
        url, path, querydata = read_email_url(m, "https://.*/booking/p.*")
        self.get_literal_url(path_and_query_to_url(path, querydata))
        self.assertUrlsEqual(reverse('cciw-bookings-pay'))
        self.assertTextPresent(booking.account.get_balance_due_now(price_checker=PriceChecker()))

    def test_payment_reminder_email_link_expired(self):
        self._create_booking()
        mail.outbox = []
        send_payment_reminder_emails()
        m = mail.outbox[0]
        url, path, querydata = read_email_url(m, "https://.*/booking/p.*")

        with override_settings(BOOKING_EMAIL_VERIFY_TIMEOUT_DAYS=-1):
            self.get_literal_url(path_and_query_to_url(path, querydata))

        # link expired, new email should be sent.
        self.assertUrlsEqual(reverse('cciw-bookings-link_expired_email_sent'))
        self.assertEqual(len(mail.outbox), 2)
        m2 = mail.outbox[1]

        url2, path2, querydata2 = read_email_url(m2, "https://.*/booking/p.*")
        self.get_literal_url(path_and_query_to_url(path2, querydata2))
        self.assertUrlsEqual(reverse('cciw-bookings-pay'))


class AccountDetailsBase(BookingBaseMixin, LogInMixin, FuncBaseMixin):

    urlname = 'cciw-bookings-account_details'
    submit_css_selector = '[type=submit]'

    def submit(self, css_selector=submit_css_selector):
        return super().submit(css_selector)

    def test_redirect_if_not_logged_in(self):
        self.get_url(self.urlname)
        self.assertUrlsEqual(reverse('cciw-bookings-not_logged_in'))

    def test_show_if_logged_in(self):
        self.login(add_account_details=False)
        self.get_url(self.urlname)
        self.assertUrlsEqual(reverse(self.urlname))

    def test_missing_name(self):
        self.login(add_account_details=False)
        self.get_url(self.urlname)
        self.submit_expecting_html5_validation_errors()
        self.assertTextPresent("This field is required")

    @mock.patch('cciw.bookings.mailchimp.update_newsletter_subscription')
    def test_complete(self, UNS_func):
        """
        Test that we can complete the account details page
        """
        self.login(add_account_details=False)
        self.get_url(self.urlname)
        self._fill_in_account_details()
        self.submit()
        acc = self.get_account()
        self.assertEqual(acc.name, 'Mr Booker')
        self.assertEqual(UNS_func.call_count, 0)

    @mock.patch('cciw.bookings.mailchimp.update_newsletter_subscription')
    def test_news_letter_subscribe(self, UNS_func):
        self.login(add_account_details=False)
        self.get_url(self.urlname)
        self._fill_in_account_details()
        self.fill({'#id_subscribe_to_newsletter': True})
        self.submit()
        acc = self.get_account()
        self.assertEqual(acc.subscribe_to_newsletter, True)
        self.assertEqual(UNS_func.call_count, 1)

    def test_subscribe_to_mailings_unselected(self):
        self.login(add_account_details=False)
        self.get_url(self.urlname)
        acc = self.get_account()
        #  Initial value should be NULL - we haven't asked.
        self.assertIs(acc.subscribe_to_mailings, None)
        self.assertIs(acc.include_in_mailings, True)
        self._fill_in_account_details()
        self.submit()
        acc = self.get_account()
        # The form should default to 'False'. As soon as this
        # page has been submitted, we *have* asked the question
        # and they have said 'no' by not selecting the box.
        self.assertIs(acc.subscribe_to_mailings, False)
        self.assertIs(acc.include_in_mailings, False)

    def test_subscribe_to_mailings_selected(self):
        self.login(add_account_details=False)
        self.get_url(self.urlname)
        acc = self.get_account()
        self._fill_in_account_details()
        self.fill({'#id_subscribe_to_mailings': True})
        self.submit()
        acc = self.get_account()
        self.assertIs(acc.subscribe_to_mailings, True)
        self.assertIs(acc.include_in_mailings, True)

    def _fill_in_account_details(self):
        self.fill_by_name({'name': 'Mr Booker',
                           'address_line1': '123, A Street',
                           'address_city': 'Metrocity',
                           'address_country': 'GB',
                           'address_post_code': 'XY1 D45',
                           })

    # For updating this, see:
    # https://vcrpy.readthedocs.org/en/latest/usage.html

    @vcr.use_cassette('cciw/bookings/fixtures/vcr_cassettes/subscribe.yaml', ignore_localhost=True)
    def test_subscribe(self):
        self.login(add_account_details=False)
        self.get_url(self.urlname)
        self._fill_in_account_details()
        self.fill_by_name({'subscribe_to_newsletter': True})
        self.submit()
        acc = self.get_account()
        self.assertEqual(acc.subscribe_to_newsletter, True)
        self.assertEqual(get_status(acc), "subscribed")

    @vcr.use_cassette('cciw/bookings/fixtures/vcr_cassettes/unsubscribe.yaml', ignore_localhost=True)
    def test_unsubscribe(self):
        self.login()
        BookingAccount.objects.filter(id=self.get_account().id).update(subscribe_to_newsletter=True)

        self.get_url(self.urlname)
        self.fill_by_name({'subscribe_to_newsletter': False})
        self.submit()
        acc = self.get_account()
        self.assertEqual(acc.subscribe_to_newsletter, False)
        self.assertEqual(get_status(acc), "unsubscribed")


class TestAccountDetailsWT(AccountDetailsBase, WebTestBase):
    pass


class TestAccountDetailsSL(AccountDetailsBase, SeleniumBase):
    pass


class AddPlaceBase(BookingBaseMixin, CreateBookingWebMixin, FuncBaseMixin):

    urlname = 'cciw-bookings-add_place'

    SAVE_BTN = '#id_save_btn'

    submit_css_selector = SAVE_BTN

    def submit(self, css_selector=submit_css_selector):
        return super().submit(css_selector)

    def test_redirect_if_not_logged_in(self):
        self.get_url(self.urlname)
        self.assertUrlsEqual(reverse('cciw-bookings-not_logged_in'))

    def test_redirect_if_no_account_details(self):
        self.login(add_account_details=False)
        self.get_url(self.urlname)
        self.assertUrlsEqual(reverse('cciw-bookings-account_details'))

    def test_show_if_logged_in(self):
        self.login()
        self.get_url(self.urlname)
        self.assertUrlsEqual(reverse(self.urlname))

    def test_show_error_if_no_prices(self):
        self.login()
        self.get_url(self.urlname)
        self.assertTextPresent(self.PRICES_NOT_SET)

    def test_post_not_allowed_if_no_prices(self):
        self.login()
        self.get_url(self.urlname)
        self.assertFalse(self.is_element_present(self.SAVE_BTN))

        self.add_prices()
        self.get_url(self.urlname)
        data = self.place_details.copy()
        self.fill_by_name(data)
        # Now remove prices, just to be awkward:
        Price.objects.all().delete()
        self.submit()
        self.assertTextPresent(self.PRICES_NOT_SET)

    def test_allowed_if_prices_set(self):
        self.login()
        self.add_prices()
        self.get_url(self.urlname)
        self.assertTextAbsent(self.PRICES_NOT_SET)

    def test_incomplete(self):
        self.login()
        self.add_prices()
        self.get_url(self.urlname)
        self.submit_expecting_html5_validation_errors()
        self.assertTextPresent("This field is required")

    def test_complete(self):
        self.login()
        self.add_prices()
        self.get_url(self.urlname)
        acc = self.get_account()
        self.assertEqual(acc.bookings.count(), 0)
        data = self.place_details.copy()
        self.fill_by_name(data)
        self.submit()
        self.assertUrlsEqual(reverse('cciw-bookings-list_bookings'))

        # Did we create it?
        self.assertEqual(acc.bookings.count(), 1)

        b = acc.bookings.get()

        # Check attributes set correctly
        self.assertEqual(b.amount_due, self.price_full)
        self.assertEqual(b.created_online, True)
        assert not b.publicity_photos_agreement

    def test_custom_agreement(self):
        agreement = factories.create_custom_agreement(
            name=(agreement_name := 'MONEY!!'),
            year=self.camp.year,
            text_html=(agreement_text := "Do you agree to give us all your money?")
        )
        self.login()
        self.add_prices()
        self.get_url(self.urlname)
        self.assertTextPresent(agreement_name)
        self.assertTextPresent(agreement_text)

        self.fill_by_name(self.place_details.copy())
        self.fill({f'#id_custom_agreement_{agreement.id}': True})
        self.submit()
        self.assertUrlsEqual(reverse('cciw-bookings-list_bookings'))

        acc = self.get_account()
        booking = acc.bookings.get()
        assert booking.custom_agreements_checked == [agreement.id]


class TestAddPlaceWT(AddPlaceBase, WebTestBase):
    pass


class TestAddPlaceSL(AddPlaceBase, SeleniumBase):

    def _use_existing_start(self):
        self.login()
        self.add_prices()
        self.create_booking_model()
        self.get_url(self.urlname)

    def assertValues(self, data):
        for k, v in data.items():
            self.assertEqual(self.value(k), v)

    def test_use_existing_addresses(self):
        self._use_existing_start()

        self.click('.use_existing_btn')
        self.click('#id_use_address_btn')

        self.assertValues({'#id_address_line1': '123 My street',
                           '#id_address_country': 'GB',
                           '#id_address_post_code': 'ABC 123',

                           '#id_contact_name': 'Mr Father',
                           '#id_contact_line1': '98 Main Street',
                           '#id_contact_country': 'GB',
                           '#id_contact_post_code': 'ABC 456',

                           '#id_first_name': '',

                           '#id_gp_name': '',
                           '#id_gp_line1': '',
                           '#id_gp_country': ''})

    def test_use_existing_gp(self):
        self._use_existing_start()

        self.click('.use_existing_btn')
        self.click('#id_use_gp_info_btn')

        self.assertValues({'#id_address_line1': '',
                           '#id_address_country': '',
                           '#id_address_post_code': '',

                           '#id_contact_name': '',
                           '#id_contact_line1': '',
                           '#id_contact_country': '',
                           '#id_contact_post_code': '',

                           '#id_first_name': '',

                           '#id_gp_name': 'Doctor Who',
                           '#id_gp_line1': 'The Tardis',
                           '#id_gp_country': 'GB'})

    def test_use_existing_all(self):
        self._use_existing_start()

        self.click('.use_existing_btn')
        self.click('#id_use_all_btn')

        self.assertValues({'#id_address_line1': '123 My street',
                           '#id_address_country': 'GB',
                           '#id_address_post_code': 'ABC 123',

                           '#id_contact_name': 'Mr Father',
                           '#id_contact_line1': '98 Main Street',
                           '#id_contact_country': 'GB',
                           '#id_contact_post_code': 'ABC 456',

                           '#id_first_name': 'Frédéric',

                           '#id_gp_name': 'Doctor Who',
                           '#id_gp_line1': 'The Tardis',
                           '#id_gp_country': 'GB'})

    def test_use_account_data(self):
        self._use_existing_start()

        self.click('#id_use_account_1_btn')
        self.assertValues({'#id_address_line1': '456 My Street',
                           '#id_address_city': 'Metrocity',
                           '#id_address_country': 'GB',
                           '#id_phone_number': '0123 456789',
                           '#id_address_post_code': 'XYZ'})

        self.click('#id_use_account_2_btn')
        self.assertValues({'#id_contact_line1': '456 My Street',
                           '#id_contact_name': 'Joe',
                           '#id_contact_city': 'Metrocity',
                           '#id_contact_country': 'GB',
                           '#id_contact_phone_number': '0123 456789',
                           '#id_contact_post_code': 'XYZ'})


class EditPlaceBase(BookingBaseMixin, CreateBookingWebMixin, FuncBaseMixin):

    # Most functionality is shared with the 'add' form, so doesn't need testing separately.

    submit_css_selector = '#id_save_btn'

    def edit_place(self, booking, expect_code=None):
        url = reverse('cciw-bookings-edit_place', kwargs={'booking_id': str(booking.id)})
        expect_errors = expect_code is not None and str(expect_code).startswith('4')
        action = lambda: self.get_literal_url(url, expect_errors=expect_errors)
        if expect_errors:
            with disable_logging():  # suppress django.request warning
                action()
        else:
            action()
        if expect_code is not None:
            self.assertCode(expect_code)

    def submit(self, css_selector=submit_css_selector):
        return super().submit(css_selector)

    def test_redirect_if_not_logged_in(self):
        self.get_url('cciw-bookings-edit_place', booking_id='1')
        self.assertUrlsEqual(reverse('cciw-bookings-not_logged_in'))

    def test_show_if_owner(self):
        self.create_booking()
        self.edit_place(self.get_account().bookings.all()[0])
        self.assertTextPresent("id_save_btn")

    def test_404_if_not_owner(self):
        self.create_booking()
        other_account = BookingAccount.objects.create(email='other@mail.com')
        Booking.objects.all().update(account=other_account)
        self.edit_place(Booking.objects.get(), expect_code=404)
        self.assertTextPresent("Page Not Found")

    def test_incomplete(self):
        self.create_booking()
        self.edit_place(self.get_account().bookings.all()[0])
        self.fill_by_name({'first_name': ''})
        self.submit_expecting_html5_validation_errors()
        self.assertTextPresent("This field is required")

    def test_complete(self):
        self.create_booking()
        self.edit_place(self.get_account().bookings.get())
        data = self.place_details.copy()
        data['first_name'] = "A New Name"
        self.fill_by_name(data)
        self.submit()
        self.assertUrlsEqual(reverse('cciw-bookings-list_bookings'))

        # Did we alter it?
        self.assertEqual(self.get_account().bookings.all()[0].first_name, "A New Name")

    def test_edit_booked(self):
        """
        Test we can't edit a booking when it is already booked.
        (or anything but BookingState.INFO_COMPLETE)
        """
        self.create_booking()
        acc = self.get_account()
        b = acc.bookings.get()

        for state in [BookingState.APPROVED, BookingState.BOOKED]:
            b.state = state
            b.save()

            # Check there is no save button
            self.edit_place(b)
            self.assertFalse(self.is_element_present("#id_save_btn"))
            # Check for message
            self.assertTextPresent("can only be changed by an admin.")

            # Attempt a post.

            # First, load a page with a working submit button:
            b.state = BookingState.INFO_COMPLETE
            b.save()
            self.edit_place(b)

            # Now change behind the scenes:
            b.state = state
            b.save()

            # Now submit
            data = self.place_details.copy()
            data['first_name'] = "A New Name"
            self.fill_by_name(data)
            self.submit()
            # Check we didn't alter it
            self.assertNotEqual(acc.bookings.get().first_name, "A New Name")


class TestEditPlaceWT(EditPlaceBase, WebTestBase):
    pass


class TestEditPlaceSL(EditPlaceBase, SeleniumBase):
    pass


def fix_autocomplete_fields(field_names):
    class FixAutocompleteFieldMixin:
        def fill_by_name(self, fields):
            new_fields = {}
            to_fix = []
            for field_name, value in fields.items():
                if field_name in field_names:
                    if self.is_full_browser_test:
                        # Fix later
                        to_fix.append((field_name, value))
                    else:
                        # Hack needed to cope with autocomplete_light widget and WebTest:
                        form, field, item = self._find_form_and_field_by_css_selector(
                            self.last_response,
                            f'[name={field_name}]',
                        )
                        # Modify the select widget so that it has the value we need
                        form.fields[field_name][0].options.append((str(value), False, ''))
                        new_fields[field_name] = value
                else:
                    new_fields[field_name] = value

            super().fill_by_name(new_fields)

            if self.is_full_browser_test:
                for field_name, value in to_fix:
                    # Hack to cope with autocomplete_light widget and Selenium
                    self.execute_script(
                        f"""django.jQuery('[name={field_name}]').append('<option value="{value}" selected="selected"></option>');"""
                    )

    return FixAutocompleteFieldMixin


class EditPlaceAdminBase(BookingBaseMixin, fix_autocomplete_fields(['account']),
                         OfficersSetupMixin, CreateBookingWebMixin, FuncBaseMixin):

    def test_approve(self):
        self.create_booking({'price_type': PriceType.CUSTOM})
        acc = self.get_account()
        b = acc.bookings.all()[0]

        self.officer_login(BOOKING_SECRETARY)
        self.get_url("admin:bookings_booking_change", b.id)
        self.fill_by_name({'state': BookingState.APPROVED})
        self.submit('[name=_save]')
        self.assertTextPresent("An email has been sent")
        mails = send_queued_mail()
        self.assertEqual(len(mails), 1)

    def test_create(self):
        self.add_prices()
        self.officer_login(BOOKING_SECRETARY)
        account = BookingAccount.objects.create(
            email=self.email,
            name='Joe',
            address_post_code='XYZ',
        )
        self.get_url("admin:bookings_booking_add")
        fields = self.place_details.copy()
        fields.update({
            'account': account.id,
            'state': BookingState.BOOKED,
            'amount_due': '130.00',
            'manual_payment_amount': '100',
            'manual_payment_payment_type': str(ManualPaymentType.CHEQUE),
        })
        self.fill_by_name(fields)
        self.submit('[name=_save]')
        self.assertTextPresent('Select booking')
        self.assertTextPresent('A confirmation email has been sent')
        booking = Booking.objects.get()
        self.assertEqual(booking.created_online, False)
        self.assertEqual(booking.account.manual_payments.count(), 1)
        mp = booking.account.manual_payments.get()
        self.assertEqual(mp.payment_type, ManualPaymentType.CHEQUE)
        self.assertEqual(mp.amount, Decimal('100'))


class TestEditPlaceAdminWT(EditPlaceAdminBase, WebTestBase):
    pass


class TestEditPlaceAdminSL(EditPlaceAdminBase, SeleniumBase):
    pass


class EditAccountAdminBase(BookingBaseMixin, OfficersSetupMixin, CreateBookingModelMixin, FuncBaseMixin):
    def test_create(self):
        self.officer_login(BOOKING_SECRETARY)
        self.get_url("admin:bookings_bookingaccount_add")
        self.fill_by_name({'name': 'Joe',
                           'email': self.email,
                           'address_post_code': 'XYZ',
                           })
        self.submit('[name=_save]')
        self.assertTextPresent("was added successfully")
        account = BookingAccount.objects.get(email=self.email)
        self.assertEqual(account.name, 'Joe')

    def test_edit(self):
        account = BookingAccount.objects.create(
            email=self.email,
            name='Joe',
            address_post_code='XYZ',
        )
        account.manual_payments.create(
            amount=Decimal('10.00'),
            payment_type=ManualPaymentType.CHEQUE,
        )
        self.assertEqual(account.payments.count(), 1)
        self.officer_login(BOOKING_SECRETARY)
        self.get_url("admin:bookings_bookingaccount_change", account.id)
        self.assertTextPresent("Payments")
        self.assertTextPresent("Payment: 10.00 from Joe via Cheque")
        self.fill_by_name({'name': 'Mr New Name'})
        self.submit('[name=_save]')
        self.assertTextPresent("was changed successfully")
        account = refresh(account)
        self.assertEqual(account.name, 'Mr New Name')


class TestEditAccountAdminWT(EditAccountAdminBase, WebTestBase):
    pass


class TestEditAccountAdminSL(EditAccountAdminBase, SeleniumBase):
    pass


class EditPaymentAdminBase(fix_autocomplete_fields(['account']), BookingBaseMixin,
                           OfficersSetupMixin, CreateBookingModelMixin, FuncBaseMixin):
    def test_add_manual_payment(self):
        self.create_booking()
        self.officer_login(BOOKING_SECRETARY)
        account = self.get_account()
        self.get_url("admin:bookings_manualpayment_add")
        self.fill_by_name({
            'account': account.id,
            'amount': '12.00',
        })
        self.submit('[name=_save]')
        self.assertTextPresent("Manual payment of £12")
        self.assertTextPresent("was added successfully")
        self.assertEqual(account.manual_payments.count(), 1)
        account = self.get_account()
        self.assertEqual(account.total_received, Decimal('12'))


class TestEditPaymentAdminWT(EditPaymentAdminBase, WebTestBase):
    pass


class TestEditPaymentAdminSL(EditPaymentAdminBase, SeleniumBase):
    pass


class AccountTransferBase(fix_autocomplete_fields(['from_account', 'to_account']),
                          AtomicChecksMixin,
                          OfficersSetupMixin, FuncBaseMixin):
    def test_add_account_transfer(self):

        account_1 = BookingAccount.objects.create(email="account1@example.com", name="Joe")
        account_2 = BookingAccount.objects.create(email="account2@example.com", name="Jane")
        account_1.manual_payments.create(amount="100.00")
        account_1 = refresh(account_1)
        self.assertEqual(account_1.total_received, Decimal('100.00'))

        self.assertEqual(account_1.payments.count(), 1)

        self.officer_login(BOOKING_SECRETARY)

        self.get_url("admin:bookings_accounttransferpayment_add")
        self.fill_by_name({
            'from_account': account_1.id,
            'to_account': account_2.id,
            'amount': '15',
        })
        self.submit('[name=_save]')
        self.assertTextPresent("was added successfully")

        account_1 = refresh(account_1)
        account_2 = refresh(account_2)

        self.assertEqual(account_1.payments.count(), 2)
        self.assertEqual(account_2.payments.count(), 1)

        self.assertEqual(account_1.total_received, Decimal('85.00'))
        self.assertEqual(account_2.total_received, Decimal('15.00'))

        # Deleting causes more payments to restore the original value
        account_1.transfer_from_payments.get().delete()

        account_1 = refresh(account_1)
        account_2 = refresh(account_2)

        self.assertEqual(account_1.payments.count(), 3)
        self.assertEqual(account_2.payments.count(), 2)

        self.assertEqual(account_1.total_received, Decimal('100.00'))
        self.assertEqual(account_2.total_received, Decimal('0.00'))


class TestAccountTransferWT(AccountTransferBase, WebTestBase):
    pass


class TestAccountTransferSL(AccountTransferBase, SeleniumBase):
    pass


class ListBookingsBase(BookingBaseMixin, CreateBookingWebMixin, FuncBaseMixin):
    # This includes tests for most of the business logic

    urlname = 'cciw-bookings-list_bookings'

    def assert_book_button_enabled(self):
        self.assertTrue(self.is_element_present('#id_book_now_btn'))
        self.assertFalse(self.is_element_present('#id_book_now_btn[disabled]'))

    def assert_book_button_disabled(self):
        self.assertTrue(self.is_element_present('#id_book_now_btn'))
        self.assertTrue(self.is_element_present('#id_book_now_btn[disabled]'))

    def enable_book_button(self):
        # Used for testing what happens if user enables button using browser
        # tools etc. i.e. checking that we have proper server side validation
        if self.is_full_browser_test:
            self.execute_script("""$('#id_book_now_btn').removeAttr('disabled')""")

    def test_redirect_if_not_logged_in(self):
        self.get_url(self.urlname)
        self.assertUrlsEqual(reverse('cciw-bookings-not_logged_in'))

    def test_show_bookings(self):
        self.create_booking()
        self.get_url(self.urlname)

        self.assertTextPresent("Camp Blue")
        self.assertTextPresent("Frédéric Bloggs")
        self.assertTextPresent("£100")
        self.assertTextPresent("This place can be booked")
        self.assert_book_button_enabled()

    def test_handle_custom_price(self):
        self.create_booking({'price_type': PriceType.CUSTOM})
        self.get_url(self.urlname)

        self.assertTextPresent("Camp Blue")
        self.assertTextPresent("Frédéric Bloggs")
        self.assertTextPresent("TBA")
        self.assertTextPresent("A custom discount needs to be arranged by the booking secretary")
        self.assert_book_button_disabled()
        self.assertTextPresent("This place cannot be booked for the reasons described above")

    def test_2nd_child_discount_allowed(self):
        self.create_booking({'price_type': PriceType.SECOND_CHILD})

        self.get_url(self.urlname)
        self.assertTextPresent(self.CANNOT_USE_2ND_CHILD)
        self.assert_book_button_disabled()

        # 2 places, both at 2nd child discount, is not allowed.
        self.create_booking({'price_type': PriceType.SECOND_CHILD})

        self.get_url(self.urlname)
        self.assertTextPresent(self.CANNOT_USE_2ND_CHILD)
        self.assert_book_button_disabled()

    def test_2nd_child_discount_allowed_if_booked(self):
        """
        Test that we can have 2nd child discount if full price
        place is already booked.
        """
        self.create_booking()
        acc = self.get_account()
        acc.bookings.update(state=BookingState.BOOKED)

        self.create_booking({'price_type': PriceType.SECOND_CHILD,
                             'first_name': 'Mary'})

        self.get_url(self.urlname)
        self.assert_book_button_enabled()

    def test_3rd_child_discount_allowed(self):
        self.create_booking({'price_type': PriceType.FULL})
        self.create_booking({'price_type': PriceType.THIRD_CHILD})

        self.get_url(self.urlname)
        self.assertTextPresent("You cannot use a 3rd child discount")
        self.assert_book_button_disabled()

        # 3 places, with 2 at 3rd child discount, is not allowed.
        self.create_booking({'price_type': PriceType.THIRD_CHILD})

        self.get_url(self.urlname)
        self.assertTextPresent("You cannot use a 3rd child discount")
        self.assert_book_button_disabled()

    def test_handle_serious_illness(self):
        booking = self.create_booking({'serious_illness': '1'})
        self.get_url(self.urlname)
        self.assertTextPresent("Must be approved by leader due to serious illness/condition")
        self.assert_book_button_disabled()
        self.assertIn(booking, Booking.objects.need_approving())

    def test_minimum_age(self):
        # if born Aug 31st 2001, and thisyear == 2012, should be allowed on camp with
        # minimum_age == 11
        self.create_booking({'date_of_birth': '%d-08-31' %
                             (self.camp.year - self.camp_minimum_age)})
        self.get_url(self.urlname)
        self.assertTextAbsent(self.BELOW_MINIMUM_AGE)

        # if born 1st Sept 2001, and thisyear == 2012, should not be allowed on camp with
        # minimum_age == 11
        Booking.objects.all().delete()
        self.create_booking({'date_of_birth': '%d-09-01' %
                             (self.camp.year - self.camp_minimum_age)})
        self.get_url(self.urlname)
        self.assertTextPresent(self.BELOW_MINIMUM_AGE)

    def test_maximum_age(self):
        # if born 1st Sept 2001, and thisyear == 2019, should be allowed on camp with
        # maximum_age == 17
        self.create_booking({'date_of_birth': '%d-09-01' %
                             (self.camp.year - (self.camp_maximum_age + 1))})
        self.get_url(self.urlname)
        self.assertTextAbsent(self.ABOVE_MAXIMUM_AGE)

        # if born Aug 31st 2001, and thisyear == 2019, should not be allowed on camp with
        # maximum_age == 17
        Booking.objects.all().delete()
        self.create_booking({'date_of_birth': '%d-08-31' %
                             (self.camp.year - (self.camp_maximum_age + 1))})
        self.get_url(self.urlname)
        self.assertTextPresent(self.ABOVE_MAXIMUM_AGE)

    def test_no_places_left(self):
        for i in range(0, self.camp.max_campers):
            factories.create_booking(camp=self.camp, state=BookingState.BOOKED)

        self.create_booking({'sex': 'm'})
        self.get_url(self.urlname)
        self.assertTextPresent(self.NO_PLACES_LEFT)
        self.assert_book_button_disabled()

        # Don't want a redundant message
        self.assertTextAbsent(self.NO_PLACES_LEFT_FOR_BOYS)

    def test_no_male_places_left(self):
        for i in range(0, self.camp.max_male_campers):
            factories.create_booking(camp=self.camp, sex='m', state=BookingState.BOOKED)

        self.create_booking({'sex': 'm'})
        self.get_url(self.urlname)
        self.assertTextPresent(self.NO_PLACES_LEFT_FOR_BOYS)
        self.assert_book_button_disabled()

        # Check that we can still book female places
        Booking.objects.filter(state=BookingState.INFO_COMPLETE).delete()
        self.create_booking({'sex': 'f'})
        self.get_url(self.urlname)
        self.assertTextAbsent(self.NO_PLACES_LEFT)
        self.assert_book_button_enabled()

    def test_no_female_places_left(self):
        for i in range(0, self.camp.max_female_campers):
            factories.create_booking(camp=self.camp, sex='f', state=BookingState.BOOKED)

        self.create_booking({'sex': 'f'})
        self.get_url(self.urlname)
        self.assertTextPresent(self.NO_PLACES_LEFT_FOR_GIRLS)
        self.assert_book_button_disabled()

    def test_not_enough_places_left(self):
        for i in range(0, self.camp.max_campers - 1):
            factories.create_booking(camp=self.camp, sex='m', state=BookingState.BOOKED)

        self.create_booking({'sex': 'f'})
        self.create_booking({'sex': 'f'})
        self.get_url(self.urlname)
        self.assertTextPresent(self.NOT_ENOUGH_PLACES)
        self.assert_book_button_disabled()

    def test_not_enough_male_places_left(self):
        for i in range(0, self.camp.max_male_campers - 1):
            factories.create_booking(camp=self.camp, sex='m', state=BookingState.BOOKED)
        self.camp.bookings.update(state=BookingState.BOOKED)

        self.create_booking({'sex': 'm'})
        self.create_booking({'sex': 'm'})
        self.get_url(self.urlname)
        self.assertTextPresent(self.NOT_ENOUGH_PLACES_FOR_BOYS)
        self.assert_book_button_disabled()

    def test_not_enough_female_places_left(self):
        for i in range(0, self.camp.max_female_campers - 1):
            factories.create_booking(camp=self.camp, sex='f', state=BookingState.BOOKED)
        self.camp.bookings.update(state=BookingState.BOOKED)

        self.create_booking({'sex': 'f'})
        self.create_booking({'sex': 'f'})
        self.get_url(self.urlname)
        self.assertTextPresent(self.NOT_ENOUGH_PLACES_FOR_GIRLS)
        self.assert_book_button_disabled()

    def test_booking_after_closing_date(self):
        self.camp.last_booking_date = self.today - timedelta(days=1)
        self.camp.save()

        self.create_booking()
        self.get_url(self.urlname)
        self.assertTextPresent(self.CAMP_CLOSED_FOR_BOOKINGS)
        self.assert_book_button_disabled()

    def test_handle_two_problem_bookings(self):
        # Test the error we get for more than one problem booking
        self.create_booking({'price_type': PriceType.CUSTOM})
        self.create_booking({'first_name': 'Another',
                             'last_name': 'Child',
                             'price_type': PriceType.CUSTOM})
        self.get_url(self.urlname)

        self.assertTextPresent("Camp Blue")
        self.assertTextPresent("Frédéric Bloggs")
        self.assertTextPresent("TBA")
        self.assertTextPresent("A custom discount needs to be arranged by the booking secretary")
        self.assert_book_button_disabled()
        self.assertTextPresent("These places cannot be booked for the reasons described above")

    def test_handle_mixed_problem_and_non_problem(self):
        # Test the message we get if one place is bookable and the other is not
        self.create_booking()  # bookable
        self.create_booking({'first_name': 'Another',
                             'last_name': 'Child',
                             'price_type': PriceType.CUSTOM})  # not bookable
        self.get_url(self.urlname)
        self.assert_book_button_disabled()
        self.assertTextPresent("One or more of the places cannot be booked")

    def test_total(self):
        self.create_booking()
        self.create_booking({'first_name': 'Another',
                             'last_name': 'Child'})
        self.get_url(self.urlname)
        self.assertTextPresent("£200")

    def test_manually_approved(self):
        # manually approved places should appear as OK to book
        self.create_booking()  # bookable
        self.create_booking({'first_name': 'Another',
                             'last_name': 'Child',
                             'price_type': PriceType.CUSTOM})  # not bookable
        Booking.objects.filter(price_type=PriceType.CUSTOM).update(state=BookingState.APPROVED,
                                                                   amount_due=Decimal('0.01'))
        self.get_url(self.urlname)

        self.assertTextPresent("Camp Blue")
        self.assertTextPresent("Frédéric Bloggs")
        self.assertTextPresent("£100")
        self.assertTextPresent("This place can be booked")

        self.assertTextPresent("Another Child")
        self.assertTextPresent("£0.01")

        self.assert_book_button_enabled()
        # Total:
        self.assertTextPresent("£100.01")

    def test_add_another_btn(self):
        self.create_booking()
        self.get_url(self.urlname)
        self.submit('[name=add_another]')
        self.assertUrlsEqual(reverse('cciw-bookings-add_place'))

    def test_move_to_shelf(self):
        self.create_booking()
        acc = self.get_account()
        b = acc.bookings.all()[0]
        self.assertEqual(b.shelved, False)
        self.get_url(self.urlname)

        self.submit(f"[name=shelve_{b.id}]")

        # Should be changed
        b2 = acc.bookings.all()[0]
        self.assertEqual(b2.shelved, True)

        # Different button should appear
        self.assertFalse(self.is_element_present(f"[name=shelve_{b.id}]"))
        self.assertTrue(self.is_element_present(f"[name=unshelve_{b.id}]"))

        self.assertTextPresent("Shelf")

    def test_move_to_basket(self):
        self.create_booking()
        acc = self.get_account()
        b = acc.bookings.all()[0]
        b.shelved = True
        b.save()

        self.get_url(self.urlname)
        self.submit(f"[name=unshelve_{b.id}]")

        # Should be changed
        b2 = acc.bookings.all()[0]
        self.assertEqual(b2.shelved, False)

        # Shelf section should disappear.
        self.assertTextAbsent("Shelf")

    def test_delete_place(self):
        self.create_booking()
        acc = self.get_account()
        b = acc.bookings.all()[0]
        self.get_url(self.urlname)

        if self.is_full_browser_test:
            self.click_expecting_alert(f"[name=delete_{b.id}]")
            self.accept_alert()
            self.wait_until_loaded('body')
        else:
            self.submit(f"[name=delete_{b.id}]")

        # Should be gone
        self.assertEqual(0, acc.bookings.count())

    def test_edit_place_btn(self):
        self.create_booking()
        acc = self.get_account()
        b = acc.bookings.all()[0]
        self.get_url(self.urlname)

        self.submit(f"[name=edit_{b.id}]")
        self.assertUrlsEqual(reverse('cciw-bookings-edit_place', kwargs={'booking_id': b.id}))

    def test_book_ok(self):
        """
        Test that we can book a place
        """
        self.create_booking()
        self.get_url(self.urlname)
        self.submit('[name=book_now]')
        acc = self.get_account()
        b = acc.bookings.all()[0]
        assert b.state == BookingState.BOOKED
        assert not b.is_confirmed
        self.assertUrlsEqual(reverse('cciw-bookings-pay'))
        self.assertTextPresent(self.BOOKINGS_WILL_EXPIRE)

    def test_book_with_zero_deposit(self):
        """
        Test that when deposit is zero, we confirm the place
        immediately and don't ask for payment.
        """
        self.add_prices(deposit=0)
        self.create_booking()
        self.get_url(self.urlname)
        self.submit('[name=book_now]')
        acc = self.get_account()
        b = acc.bookings.all()[0]
        assert b.state == BookingState.BOOKED
        assert b.is_confirmed
        self.assertUrlsEqual(reverse('cciw-bookings-pay'))
        self.assertTextAbsent(self.BOOKINGS_WILL_EXPIRE)
        self.assertTextPresent('no deposit to pay')
        self.assertTextPresent('do not pay yet')

        # We should immediately send email confirming place in this case:
        mails = send_queued_mail()
        assert len(mails) == 1
        mail, = mails
        assert mail.subject == "[CCIW] Booking - place confirmed"
        assert mail.to == [acc.email]
        assert self.THANK_YOU_FOR_PAYMENT not in mail.body  # They didn't actually pay

    def test_book_with_other_bookings(self):
        """
        Test that when we have other bookings which are not "booked",
        distribute_balance doesn't fail.
        """
        self.add_prices(deposit=0)  # Zero deposit to allow confirmation without payment

        def make_booking(state):
            booking = self.create_booking(shortcut=True)
            booking.state = state
            booking.save()
            return booking

        make_booking(BookingState.CANCELLED_FULL_REFUND)
        make_booking(BookingState.CANCELLED_HALF_REFUND)
        make_booking(BookingState.INFO_COMPLETE)

        booking = self.create_booking(shortcut=True)
        self.get_url(self.urlname)
        self.submit('[name=book_now]')
        acc = self.get_account()
        booking = acc.bookings.all()[0]
        assert booking.state == BookingState.BOOKED
        assert booking.is_confirmed
        self.assertUrlsEqual(reverse('cciw-bookings-pay'))

    def test_book_unbookable(self):
        """
        Test that an unbookable place can't be booked
        """
        self.create_booking({'serious_illness': '1'})
        self.get_url(self.urlname)
        self.assert_book_button_disabled()
        self.enable_book_button()
        self.submit('[name=book_now]')
        acc = self.get_account()
        b = acc.bookings.all()[0]
        self.assertEqual(b.state, BookingState.INFO_COMPLETE)
        self.assertTextPresent("These places cannot be booked")

    def test_book_one_unbookable(self):
        """
        Test that if one places is unbookable, no place can be booked
        """
        self.create_booking()
        self.create_booking({'serious_illness': '1'})
        self.get_url(self.urlname)
        self.assert_book_button_disabled()
        self.enable_book_button()
        self.submit('[name=book_now]')
        acc = self.get_account()
        for b in acc.bookings.all():
            self.assertEqual(b.state, BookingState.INFO_COMPLETE)
        self.assertTextPresent("These places cannot be booked")

    def test_same_name_same_camp(self):
        self.create_booking()
        self.create_booking()  # Identical

        self.get_url(self.urlname)
        self.assertTextPresent("You have entered another set of place details for a camper called")
        # This is only a warning:
        self.assert_book_button_enabled()

    def test_warn_about_multiple_full_price(self):
        self.create_booking()
        self.create_booking({'first_name': 'Mary',
                             'last_name': 'Bloggs'})

        self.get_url(self.urlname)
        self.assertTextPresent(self.MULTIPLE_FULL_PRICE_WARNING)
        self.assertTextPresent("If Mary Bloggs and Frédéric Bloggs")
        # This is only a warning:
        self.assert_book_button_enabled()

        # Check for more than 2
        self.create_booking({'first_name': 'Peter',
                             'last_name': 'Bloggs'})
        self.get_url(self.urlname)
        self.assertTextPresent("If Mary Bloggs, Peter Bloggs and Frédéric Bloggs")

    def test_warn_about_multiple_2nd_child(self):
        self.create_booking()
        self.create_booking({'first_name': 'Mary',
                             'last_name': 'Bloggs',
                             'price_type': PriceType.SECOND_CHILD})
        self.create_booking({'first_name': 'Peter',
                             'last_name': 'Bloggs',
                             'price_type': PriceType.SECOND_CHILD})

        self.get_url(self.urlname)
        self.assertTextPresent(self.MULTIPLE_2ND_CHILD_WARNING)
        self.assertTextPresent("If Peter Bloggs and Mary Bloggs")
        self.assertTextPresent("one is eligible")
        # This is only a warning:
        self.assert_book_button_enabled()

        self.create_booking({'first_name': 'Zac',
                             'last_name': 'Bloggs',
                             'price_type': PriceType.SECOND_CHILD})
        self.get_url(self.urlname)
        self.assertTextPresent("2 are eligible")

    def test_dont_warn_about_multiple_full_price_for_same_child(self):
        self.create_booking()
        self.create_booking({'camp': self.camp_2})

        self.get_url(self.urlname)
        self.assertTextAbsent(self.MULTIPLE_FULL_PRICE_WARNING)
        self.assert_book_button_enabled()

    def test_error_for_2nd_child_discount_for_same_camper(self):
        self.create_booking()
        self.create_booking({'camp': self.camp_2,
                             'price_type': PriceType.SECOND_CHILD})

        self.get_url(self.urlname)
        self.assertTextPresent(self.CANNOT_USE_2ND_CHILD)
        self.assert_book_button_disabled()

    def test_error_for_multiple_2nd_child_discount(self):
        # Frederik x2
        self.create_booking()
        self.create_booking({'camp': self.camp_2})

        # Mary x2
        self.create_booking({'first_name': 'Mary',
                             'price_type': PriceType.SECOND_CHILD})
        self.create_booking({'first_name': 'Mary',
                             'camp': self.camp_2,
                             'price_type': PriceType.SECOND_CHILD})

        self.get_url(self.urlname)
        self.assertTextPresent(self.CANNOT_USE_MULTIPLE_DISCOUNT_FOR_ONE_CAMPER)
        self.assert_book_button_disabled()

    def test_book_now_safeguard(self):
        # It might be possible to alter the list of items in the basket in one
        # tab, and then press 'Book now' from an out-of-date representation of
        # the basket. We need a safeguard against this.

        # Must include at least id,price,camp choice for each booking
        self.create_booking()
        self.get_url(self.urlname)

        # Now modify
        acc = self.get_account()
        b = acc.bookings.all()[0]
        b.amount_due = Decimal('35.01')
        b.save()

        self.submit('[name=book_now]')
        # Should not be modified
        b = acc.bookings.all()[0]
        self.assertEqual(b.state, BookingState.INFO_COMPLETE)
        self.assertTextPresent("Places were not booked due to modifications made")

    def test_book_disallowed_if_missing_agreement(self):
        # Test that we cannot book a place if an agreement is missing
        self.create_booking()
        self.get_url(self.urlname)

        # Suppose an agreement is added split second later by admin:
        # (test done this way to ensure we are not just relying
        # on a disabled book button)
        factories.create_custom_agreement(year=self.camp.year, name='COVID-19')

        self.submit('[name=book_now]')
        booking = self.get_account().bookings.get()
        assert booking.state != BookingState.BOOKED

        self.assertTextPresent('You need to confirm your agreement in section "COVID-19"')
        self.assert_book_button_disabled()


class TestListBookingsWT(ListBookingsBase, WebTestBase):
    pass


class TestListBookingsSL(ListBookingsBase, SeleniumBase):
    pass


class PayBase(BookingBaseMixin, CreateBookingWebMixin, FuncBaseMixin):

    def test_balance_empty(self):
        self.login()
        self.add_prices()
        self.get_url('cciw-bookings-pay')
        self.assertTextPresent('£0.00')

    def test_balance_after_booking(self):
        booking1 = self.create_booking()
        booking2 = self.create_booking()
        book_basket_now([booking1, booking2])

        self.get_url('cciw-bookings-pay')

        # 2 deposits
        expected_price = 2 * self.price_deposit
        self.assertTextPresent(f'£{expected_price}')

        # Move forward to after the time when just deposits are allowed:
        Camp.objects.update(start_date=date.today() + timedelta(10))

        self.get_url('cciw-bookings-pay')

        # 2 full price
        expected_price = 2 * self.price_full
        self.assertTextPresent(f'£{expected_price}')

    def test_redirect_if_missing_agreements(self):
        booking = self.create_booking(shortcut=True)
        book_basket_now([booking])
        factories.create_custom_agreement(year=self.camp.year, name='COVID-19')
        self.get_url('cciw-bookings-pay')
        self.assertUrlsEqual(reverse('cciw-bookings-account_overview'))
        self.assertTextPresent('There is an issue with your existing bookings')
        self.assertTextPresent('COVID-19')


class TestPayWT(PayBase, WebTestBase):
    pass


class TestPaySL(PayBase, SeleniumBase):
    pass


class TestPayReturnPoints(BookingBaseMixin, LogInMixin, WebTestBase):

    def test_pay_done(self):
        self.login()
        self.get_url('cciw-bookings-pay_done')
        self.assertTextPresent("Payment complete!")
        # Paypal posts to these, check we support that
        resp = self.client.post(reverse('cciw-bookings-pay_done'), {})
        self.assertEqual(resp.status_code, 200)

    def test_pay_cancelled(self):
        self.login()
        self.get_url('cciw-bookings-pay_cancelled')
        self.assertTextPresent("Payment cancelled")
        # Paypal posts to these, check we support that
        resp = self.client.post(reverse('cciw-bookings-pay_cancelled'), {})
        self.assertEqual(resp.status_code, 200)


class TestPaymentReceived(BookingBaseMixin, CreateBookingModelMixin, CreateLeadersMixin,
                          TestBase):

    def test_receive_payment(self):
        # Late booking:
        Camp.objects.update(start_date=date.today() + timedelta(days=1))

        self.create_booking()
        self.create_leaders()
        acc = self.get_account()
        book_basket_now(acc.bookings.for_year(self.camp.year).in_basket())
        self.assertTrue(acc.bookings.all()[0].booking_expires is not None)

        mail.outbox = []
        ManualPayment.objects.create(
            account=acc,
            amount=self.price_full)

        acc = self.get_account()

        # Check we updated the account
        self.assertEqual(acc.total_received, self.price_full)

        # Check we updated the bookings
        self.assertTrue(acc.bookings.all()[0].booking_expires is None)

        # Check for emails sent
        # 1 to account
        mails = send_queued_mail()
        account_mails = [m for m in mails if m.to == [self.email]]
        assert len(account_mails) == 1

        # This is a late booking, therefore there is also:
        # 1 to camp leaders altogether
        leader_emails = [m for m in mails
                         if sorted(m.to) == sorted([self.leader_1_user.email,
                                                    self.leader_2_user.email])]
        assert len(leader_emails) == 1
        assert leader_emails[0].subject.startswith('[CCIW] Late booking:')

    def test_insufficient_receive_payment(self):
        # Need to move into region where deposits are not allowed.
        Camp.objects.update(start_date=date.today() + timedelta(days=20))
        self.create_booking()
        self.create_booking({'price_type': PriceType.SECOND_CHILD,
                             'first_name': 'Mary'})
        acc = self.get_account()
        book_basket_now(acc.bookings.for_year(self.camp.year).in_basket())
        self.assertTrue(acc.bookings.all()[0].booking_expires is not None)

        # Between the two
        p = (self.price_full + self.price_2nd_child) / 2
        acc.receive_payment(p)

        # Check we updated the account
        self.assertEqual(acc.total_received, p)

        # Check we updated the one we had enough funds for
        self.assertTrue(acc.bookings.filter(price_type=PriceType.SECOND_CHILD)[0].booking_expires is None)
        # but not the one which was too much.
        self.assertTrue(acc.bookings.filter(price_type=PriceType.FULL)[0].booking_expires is not None)

        # We can rectify it with a payment of the rest
        acc.receive_payment((self.price_full + self.price_2nd_child) - p)
        self.assertTrue(acc.bookings.filter(price_type=PriceType.FULL)[0].booking_expires is None)

    def test_email_for_bad_payment_1(self):
        ipn_1 = IpnMock()
        ipn_1.id = 123
        ipn_1.mc_gross = Decimal('1.00')
        ipn_1.custom = "x"  # wrong format

        mail.outbox = []
        self.assertEqual(len(mail.outbox), 0)
        paypal_payment_received(ipn_1)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/admin/ipn/paypal', mail.outbox[0].body)
        self.assertIn('No associated account', mail.outbox[0].body)

    def test_email_for_bad_payment_2(self):
        account = BookingAccount(id=1234567)  # bad ID, not in DB
        ipn_1 = IpnMock()
        ipn_1.id = 123
        ipn_1.mc_gross = Decimal('1.00')
        ipn_1.custom = build_paypal_custom_field(account)

        mail.outbox = []
        self.assertEqual(len(mail.outbox), 0)
        paypal_payment_received(ipn_1)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/admin/ipn/paypal', mail.outbox[0].body)
        self.assertIn('No associated account', mail.outbox[0].body)

    def test_email_for_bad_payment_3(self):
        ipn_1 = IpnMock()
        ipn_1.id = 123
        ipn_1.mc_gross = Decimal('1.00')

        mail.outbox = []
        self.assertEqual(len(mail.outbox), 0)
        unrecognised_payment(ipn_1)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/admin/ipn/paypal', mail.outbox[0].body)
        self.assertIn('Invalid IPN', mail.outbox[0].body)

    def test_receive_payment_handler(self):
        # Use the actual signal handler, check the good path.
        account = self.get_account()
        self.assertEqual(account.total_received, Decimal(0))

        ipn_1 = factories.create_ipn(account)

        # Test for Payment objects
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(Payment.objects.all()[0].amount, ipn_1.mc_gross)

        # Test account updated
        account = self.get_account()  # refresh
        self.assertEqual(account.total_received, ipn_1.mc_gross)

        # Test refund is wired up
        ipn_2 = factories.create_ipn(
            account,
            parent_txn_id='1',
            txn_id='2',
            mc_gross=-1 * ipn_1.mc_gross,
            payment_status='Refunded',
        )

        self.assertEqual(Payment.objects.count(), 2)
        self.assertEqual(Payment.objects.order_by('-created_at')[0].amount, ipn_2.mc_gross)

        account = self.get_account()  # refresh
        self.assertEqual(account.total_received, Decimal(0))

    def test_email_for_good_payment(self):
        self.create_booking()
        acc = self.get_account()
        book_basket_now(acc.bookings.for_year(self.camp.year).in_basket())

        mail.outbox = []
        factories.create_ipn(acc, mc_gross=acc.bookings.all()[0].amount_due)

        mails = send_queued_mail()
        assert len(mails) == 1

        assert mails[0].subject == "[CCIW] Booking - place confirmed"
        assert mails[0].to == [self.email]
        assert self.THANK_YOU_FOR_PAYMENT in mails[0].body

    def test_only_one_email_for_multiple_places(self):
        self.create_booking()
        self.create_booking({'first_name': 'Another',
                             'last_name': 'Child'})

        acc = self.get_account()
        book_basket_now(acc.bookings.for_year(self.camp.year).in_basket())

        mail.outbox = []
        acc.receive_payment(acc.get_balance_full())

        mails = send_queued_mail()
        self.assertEqual(len(mails), 1)

        self.assertEqual(mails[0].subject, "[CCIW] Booking - place confirmed")
        self.assertEqual(mails[0].to, [self.email])
        self.assertTrue(self.place_details['first_name'] in mails[0].body)
        self.assertTrue('Another Child' in mails[0].body)

    def test_concurrent_save(self):
        acc1 = BookingAccount.objects.create(email='foo@foo.com')
        acc2 = BookingAccount.objects.get(email='foo@foo.com')

        acc1.receive_payment(Decimal('100.00'))

        self.assertEqual(BookingAccount.objects.get(email='foo@foo.com').total_received,
                         Decimal('100.00'))

        acc2.save()  # this will have total_received = 0.00

        self.assertEqual(BookingAccount.objects.get(email='foo@foo.com').total_received,
                         Decimal('100.00'))

    def test_pending_payment_handling(self):
        # This test is story-style - checks the whole process
        # of handling pending payments.

        # Create a place

        booking = self.create_booking()
        account = self.get_account()

        # Book it
        book_basket_now([booking])
        # Sanity check initial condition:
        mail.outbox = []
        booking.refresh_from_db()
        self.assertNotEqual(booking.booking_expires, None)

        # Send payment that doesn't complete immediately
        ipn_1 = factories.create_ipn(
            account,
            txn_id='8DX10782PJ789360R',
            mc_gross=Decimal('20.00'),
            payment_status="Pending",
            pending_reason="echeck",
        )

        # Money should not be counted as received
        account = refresh(account)
        self.assertEqual(account.total_received, Decimal("0.00"))

        # Custom email sent:
        self.assertEqual(len(mail.outbox), 1)
        m = mail.outbox[0]
        self.assertIn("We have received a payment of £20.00 that is pending", m.body)
        self.assertIn("echeck", m.body)

        # Check that we can tell the account has pending payments
        # and how much.
        three_days_later = timezone.now() + timedelta(days=3)
        self.assertEqual(account.get_pending_payment_total(now=three_days_later), Decimal("20.00"))

        # But pending payments are considered abandoned after 3 months.
        three_months_later = three_days_later + timedelta(days=30 * 3)
        self.assertEqual(account.get_pending_payment_total(now=three_months_later), Decimal("0.00"))

        # Booking should not expire if they have pending payments against them.
        # This is the easiest way to handle this, we have no idea when the
        # payment will complete.
        mail.outbox = []
        expire_bookings(now=three_days_later)
        booking.refresh_from_db()
        self.assertNotEqual(booking.booking_expires, None)

        # Once confirmed payment comes in, we consider that there are no pending payments.

        # A different payment doesn't affect whether pending ones are completed:
        factories.create_ipn(
            account,
            txn_id="ABCDEF123",  # DIFFERENT txn_id
            mc_gross=Decimal("10.00"),
            payment_status="Completed",
        )
        account = refresh(account)
        self.assertEqual(account.total_received, Decimal("10.00"))
        self.assertEqual(account.get_pending_payment_total(now=three_days_later), Decimal("20.00"))

        # But the same TXN id is recognised as cancelling the pending payment
        factories.create_ipn(
            account,
            txn_id=ipn_1.txn_id,  # SAME txn_id
            mc_gross=ipn_1.mc_gross,
            payment_status="Completed",
        )
        account = refresh(account)
        self.assertEqual(account.total_received, Decimal("30.00"))
        self.assertEqual(account.get_pending_payment_total(now=three_days_later), Decimal("0.00"))


class TestAjaxViews(BookingBaseMixin, OfficersSetupMixin, CreateBookingWebMixin, WebTestBase):
    # Basic tests to ensure that the views that serve AJAX return something
    # sensible.

    # NB use a mixture of WebTest and Django client tests

    def test_places_json(self):
        self.create_booking()
        resp = self.get_url('cciw-bookings-places_json')
        j = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(j['places'][0]['first_name'], self.place_details['first_name'])

    def test_places_json_with_exclusion(self):
        self.create_booking()
        acc = self.get_account()
        resp = self.get_literal_url(reverse('cciw-bookings-places_json') +
                                    f"?exclude={acc.bookings.all()[0].id}")
        j = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(j['places'], [])

    def test_places_json_with_bad_exclusion(self):
        self.login()
        resp = self.get_literal_url(reverse('cciw-bookings-places_json') + "?exclude=x")
        j = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(j['places'], [])

    def test_account_json(self):
        self.login()
        acc = self.get_account()
        acc.address_line1 = '123 Main Street'
        acc.address_country = 'FR'
        acc.save()

        resp = self.get_url('cciw-bookings-account_json')
        j = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(j['account']['address_line1'], '123 Main Street')
        self.assertEqual(j['account']['address_country'], 'FR')

    def test_all_accounts_json(self):
        acc1 = BookingAccount.objects.create(email="foo@foo.com",
                                             address_post_code="ABC",
                                             name="Mr Foo")

        self.officer_login(OFFICER)
        resp = self.get_literal_url(reverse('cciw-bookings-all_accounts_json'), expect_errors=True)
        self.assertEqual(resp.status_code, 403)

        # Now as booking secretary
        self.officer_login(BOOKING_SECRETARY)
        resp = self.get_literal_url(reverse('cciw-bookings-all_accounts_json') + f"?id={acc1.id}")
        self.assertEqual(resp.status_code, 200)

        j = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(j['account']['address_post_code'], 'ABC')

    def _booking_problems_json(self, place_details):
        data = {}
        for k, v in place_details.items():
            data[k] = v.id if isinstance(v, models.Model) else v

        resp = self.client.post(reverse('cciw-bookings-booking_problems_json'),
                                data)
        return json.loads(resp.content.decode('utf-8'))

    def _initial_place_details(self):
        data = self.place_details.copy()
        data['created_at_0'] = '1970-01-01'  # Simulate form, which doesn't supply created
        data['created_at_1'] = '00:00:00'
        return data

    def test_booking_problems(self):
        self.add_prices()
        acc1 = BookingAccount.objects.create(email="foo@foo.com",
                                             address_post_code="ABC",
                                             name="Mr Foo")
        self.client.login(username=BOOKING_SECRETARY_USERNAME,
                          password=BOOKING_SECRETARY_PASSWORD)
        resp = self.client.post(reverse('cciw-bookings-booking_problems_json'),
                                {'account': str(acc1.id)})

        self.assertEqual(resp.status_code, 200)
        j = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(j['valid'], False)

        data = self._initial_place_details()
        data['account'] = str(acc1.id)
        data['state'] = BookingState.APPROVED
        data['amount_due'] = '100.00'
        data['price_type'] = PriceType.CUSTOM
        j = self._booking_problems_json(data)
        self.assertEqual(j['valid'], True)
        self.assertTrue("A custom discount needs to be arranged by the booking secretary" in
                        j['problems'])

    def test_booking_problems_price_check(self):
        # Test that the price is checked.
        # This is a check that is only run for booking secretary
        self.add_prices()
        acc1 = BookingAccount.objects.create(email="foo@foo.com",
                                             address_post_code="ABC",
                                             name="Mr Foo")
        self.client.login(username=BOOKING_SECRETARY_USERNAME,
                          password=BOOKING_SECRETARY_PASSWORD)

        data = self._initial_place_details()
        data['account'] = str(acc1.id)
        data['state'] = BookingState.BOOKED
        data['amount_due'] = '0.00'
        data['price_type'] = PriceType.FULL
        j = self._booking_problems_json(data)
        self.assertTrue(any(p.startswith(f"The 'amount due' is not the expected value of £{self.price_full}")
                            for p in j['problems']))

    def test_booking_problems_deposit_check(self):
        # Test that the price is checked.
        # This is a check that is only run for booking secretary
        self.add_prices()
        acc1 = BookingAccount.objects.create(email="foo@foo.com",
                                             address_post_code="ABC",
                                             name="Mr Foo")
        self.client.login(username=BOOKING_SECRETARY_USERNAME,
                          password=BOOKING_SECRETARY_PASSWORD)

        data = self._initial_place_details()
        data['account'] = str(acc1.id)
        data['state'] = BookingState.CANCELLED_DEPOSIT_KEPT
        data['amount_due'] = '0.00'
        data['price_type'] = PriceType.FULL
        j = self._booking_problems_json(data)
        self.assertTrue(any(p.startswith(f"The 'amount due' is not the expected value of £{self.price_deposit}")
                            for p in j['problems']))

        # Check 'full refund' cancellation.
        data['state'] = BookingState.CANCELLED_FULL_REFUND
        data['amount_due'] = '20.00'
        data['price_type'] = PriceType.FULL
        j = self._booking_problems_json(data)
        self.assertTrue(any(p.startswith("The 'amount due' is not the expected value of £0.00")
                            for p in j['problems']))

    def test_booking_problems_early_bird_check(self):
        self.add_prices()
        acc1 = BookingAccount.objects.create(email="foo@foo.com",
                                             address_post_code="ABC",
                                             name="Mr Foo")
        self.client.login(username=BOOKING_SECRETARY_USERNAME,
                          password=BOOKING_SECRETARY_PASSWORD)
        data = self._initial_place_details()
        data['early_bird_discount'] = '1'
        data['account'] = str(acc1.id)
        data['state'] = BookingState.BOOKED
        data['amount_due'] = '90.00'
        j = self._booking_problems_json(data)
        self.assertIn("The early bird discount is only allowed for bookings created online.",
                      j['problems'])


class AccountOverviewBase(BookingBaseMixin, CreateBookingWebMixin, FuncBaseMixin):

    urlname = 'cciw-bookings-account_overview'

    def test_show(self):
        # Book a place and pay
        self.create_booking()
        acc = self.get_account()
        book_basket_now(acc.bookings.for_year(self.camp.year).in_basket())
        acc.receive_payment(self.price_deposit)

        # Book another
        self.create_booking({'first_name': 'Another',
                             'last_name': 'Child'})
        book_basket_now(acc.bookings.for_year(self.camp.year).in_basket())

        # 3rd place, not booked at all
        self.create_booking({'first_name': '3rd',
                             'last_name': 'child'})

        # 4th place, cancelled
        self.create_booking({'first_name': '4th',
                             'last_name': 'child'})
        b = acc.bookings.get(first_name='4th', last_name='child')
        b.state = BookingState.CANCELLED_DEPOSIT_KEPT
        b.auto_set_amount_due()
        b.save()

        self.get_url(self.urlname)

        # Another one, so that messages are cleared
        self.get_url(self.urlname)

        # Confirmed place
        self.assertTextPresent(self.place_details['first_name'])

        # Booked place
        self.assertTextPresent('Another Child')
        self.assertTextPresent('will expire soon')

        # Basket/Shelf
        self.assertTextPresent('Basket / shelf')

        # Deposit for cancellation
        self.assertTextPresent("Cancelled places")
        self.assertTextPresent("£20")

    def test_bookings_with_missing_agreements(self):
        booking1 = self.create_booking()
        booking2 = self.create_booking()
        booking3 = self.create_booking()
        book_basket_now([booking1, booking2, booking3])

        account = self.get_account()
        agreement = factories.create_custom_agreement(year=self.camp.year, name='COVID-19')

        assert account.bookings.agreement_fix_required().count() == 3
        self.get_url(self.urlname)

        assert self.is_element_present(f'#id_edit_booking_{booking1.id}')
        assert self.is_element_present(f'#id_edit_booking_{booking2.id}')

        assert self.is_element_present(f'#id_cancel_booking_{booking1.id}')
        assert self.is_element_present(f'#id_cancel_booking_{booking2.id}')

        self.assertTextPresent('you need to confirm your agreement in section "COVID-19"')

        # Cancel button for booking1
        self.submit(f'#id_cancel_booking_{booking1.id}')
        booking1.refresh_from_db()
        assert not booking1.is_booked
        assert booking1.shelved

        assert account.bookings.agreement_fix_required().count() == 2

        # booking1 buttons should now disappear
        assert not self.is_element_present(f'#id_edit_booking_{booking1.id}')
        assert not self.is_element_present(f'#id_cancel_booking_{booking1.id}')

        # Edit button for booking2
        # This is really a test for the edit booking page
        # - it needs to allow edits in this case, even though the
        #   place is already booked.
        self.submit(f'#id_edit_booking_{booking2.id}')
        self.assertUrlsEqual(reverse('cciw-bookings-edit_place',
                                     kwargs={'booking_id': booking2.id}))
        self.fill({f'#id_custom_agreement_{agreement.id}': True})
        self.submit(AddPlaceBase.SAVE_BTN)

        assert account.bookings.agreement_fix_required().count() == 1
        booking2.refresh_from_db()

        # This process should not have unbooked the booking:
        assert booking2.is_booked

        # We still have booking3 to sort out, we should be back at
        # account overview
        self.assertUrlsEqual(reverse('cciw-bookings-account_overview'))


class TestAccountOverviewWT(AccountOverviewBase, WebTestBase):
    pass


class TestAccountOverviewSL(AccountOverviewBase, SeleniumBase):
    pass


class LogOutBase(BookingBaseMixin, LogInMixin, FuncBaseMixin):

    def test_logout(self):
        self.login()
        self.get_url('cciw-bookings-account_overview')
        self.submit('[name=logout]')
        self.assertUrlsEqual(reverse('cciw-bookings-index'))

        # Try accessing a page which is restricted
        self.get_url('cciw-bookings-account_overview')
        self.assertUrlsEqual(reverse('cciw-bookings-not_logged_in'))


class TestLogOutWT(LogOutBase, WebTestBase):
    pass


class TestLogOutSL(LogOutBase, SeleniumBase):
    pass


class TestExpireBookingsCommand(CreateBookingModelMixin, TestBase):

    def test_just_created(self):
        """
        Test no mail if just created
        """
        self.create_booking()

        acc = self.get_account()
        book_basket_now(acc.bookings.for_year(self.camp.year).in_basket())

        mail.outbox = []

        ExpireBookingsCommand().handle()
        self.assertEqual(len(mail.outbox), 0)

    def test_warning(self):
        """
        Test that we get a warning email after 12 hours
        """
        self.create_booking()

        acc = self.get_account()
        book_basket_now(acc.bookings.for_year(self.camp.year).in_basket())
        b = acc.bookings.all()[0]
        b.booking_expires = b.booking_expires - timedelta(0.49)
        b.save()

        mail.outbox = []
        ExpireBookingsCommand().handle()
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue("warning" in mail.outbox[0].subject)

        b = acc.bookings.all()[0]
        self.assertNotEqual(b.booking_expires, None)
        self.assertEqual(b.state, BookingState.BOOKED)

    def test_expires(self):
        """
        Test that we get an expiry email after 24 hours
        """
        self.create_booking()

        acc = self.get_account()
        book_basket_now(acc.bookings.for_year(self.camp.year).in_basket())
        b = acc.bookings.all()[0]
        b.booking_expires = b.booking_expires - timedelta(1.01)
        b.save()

        mail.outbox = []
        ExpireBookingsCommand().handle()
        # NB - should get one, not two (shouldn't get warning)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue("expired" in mail.outbox[0].subject)
        self.assertTrue("have expired" in mail.outbox[0].body)

        b = acc.bookings.all()[0]
        self.assertEqual(b.booking_expires, None)
        self.assertEqual(b.state, BookingState.INFO_COMPLETE)

    def test_grouping(self):
        """
        Test the emails are grouped as we expect
        """
        self.create_booking({'first_name': 'Child',
                             'last_name': 'One'})
        self.create_booking({'first_name': 'Child',
                             'last_name': 'Two'})

        acc = self.get_account()
        book_basket_now(acc.bookings.for_year(self.camp.year).in_basket())
        acc.bookings.update(booking_expires=timezone.now() - timedelta(1))

        mail.outbox = []
        ExpireBookingsCommand().handle()

        # Should get one, not two, because they will be grouped.
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue("expired" in mail.outbox[0].subject)
        self.assertTrue("have expired" in mail.outbox[0].body)
        self.assertTrue("Child One" in mail.outbox[0].body)
        self.assertTrue("Child Two" in mail.outbox[0].body)

        for b in acc.bookings.all():
            self.assertEqual(b.booking_expires, None)
            self.assertEqual(b.state, BookingState.INFO_COMPLETE)


class TestManualPayment(TestBase):

    def test_create(self):
        acc = BookingAccount.objects.create(email='foo@foo.com')
        self.assertEqual(Payment.objects.count(), 0)
        ManualPayment.objects.create(account=acc,
                                     amount=Decimal('100.00'))
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(Payment.objects.all()[0].amount, Decimal('100.00'))

        acc = BookingAccount.objects.get(id=acc.id)
        self.assertEqual(acc.total_received, Decimal('100.00'))

    def test_delete(self):
        # Setup
        acc = BookingAccount.objects.create(email='foo@foo.com')
        cp = ManualPayment.objects.create(account=acc,
                                          amount=Decimal('100.00'))
        self.assertEqual(Payment.objects.count(), 1)

        # Test
        cp.delete()
        self.assertEqual(Payment.objects.count(), 2)
        acc = BookingAccount.objects.get(id=acc.id)
        self.assertEqual(acc.total_received, Decimal('0.00'))

    def test_edit(self):
        # Setup
        acc = BookingAccount.objects.create(email='foo@foo.com')
        cp = ManualPayment.objects.create(account=acc,
                                          amount=Decimal('100.00'))

        cp.amount = Decimal("101.00")
        self.assertRaises(Exception, cp.save)


class TestRefundPayment(TestBase):

    def test_create(self):
        acc = BookingAccount.objects.create(email='foo@foo.com')
        self.assertEqual(Payment.objects.count(), 0)
        RefundPayment.objects.create(account=acc,
                                     amount=Decimal('100.00'))
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(Payment.objects.all()[0].amount, Decimal('-100.00'))

        acc = BookingAccount.objects.get(id=acc.id)
        self.assertEqual(acc.total_received, Decimal('-100.00'))

    def test_delete(self):
        # Setup
        acc = BookingAccount.objects.create(email='foo@foo.com')
        cp = RefundPayment.objects.create(account=acc,
                                          amount=Decimal('100.00'))
        self.assertEqual(Payment.objects.count(), 1)

        # Test
        cp.delete()
        self.assertEqual(Payment.objects.count(), 2)
        acc = BookingAccount.objects.get(id=acc.id)
        self.assertEqual(acc.total_received, Decimal('0.00'))

    def test_edit(self):
        # Setup
        acc = BookingAccount.objects.create(email='foo@foo.com')
        cp = RefundPayment.objects.create(account=acc,
                                          amount=Decimal('100.00'))

        cp.amount = Decimal("101.00")
        self.assertRaises(Exception, cp.save)


class TestCancel(CreateBookingModelMixin, TestBase):
    """
    Tests covering what happens when a user cancels.
    """

    def test_amount_due(self):
        self.create_booking()
        acc = self.get_account()
        booking = acc.bookings.all()[0]
        booking.state = BookingState.CANCELLED_DEPOSIT_KEPT
        self.assertEqual(booking.expected_amount_due(), self.price_deposit)

    def test_account_amount_due(self):
        self.create_booking()
        acc = self.get_account()
        booking = acc.bookings.all()[0]
        booking.state = BookingState.CANCELLED_DEPOSIT_KEPT
        booking.auto_set_amount_due()
        booking.save()

        acc = self.get_account()
        self.assertEqual(acc.get_balance_full(), booking.amount_due)


class TestCancelFullRefund(CreateBookingModelMixin, TestBase):
    """
    Tests covering what happens when CCiW cancels a camp,
    using 'full refund'.
    """

    def test_amount_due(self):
        self.create_booking()
        acc = self.get_account()
        booking = acc.bookings.all()[0]
        booking.state = BookingState.CANCELLED_FULL_REFUND
        self.assertEqual(booking.expected_amount_due(), Decimal('0.00'))

    def test_account_amount_due(self):
        self.create_booking()
        acc = self.get_account()
        booking = acc.bookings.all()[0]
        booking.state = BookingState.CANCELLED_FULL_REFUND
        booking.auto_set_amount_due()
        booking.save()

        acc = self.get_account()
        self.assertEqual(acc.get_balance_full(), booking.amount_due)


class TestEarlyBird(CreateBookingModelMixin, TestBase):

    def test_expected_amount_due(self):
        self.create_booking()
        acc = self.get_account()
        booking = acc.bookings.all()[0]
        self.assertEqual(booking.expected_amount_due(), self.price_full)

        booking.early_bird_discount = True
        self.assertEqual(booking.expected_amount_due(), self.price_full - self.price_early_bird_discount)

    def test_book_basket_applies_discount(self):
        self.create_booking()
        acc = self.get_account()

        with mock.patch('cciw.bookings.models.get_early_bird_cutoff_date') as mock_f:
            # Cut off date definitely in the future
            mock_f.return_value = timezone.get_default_timezone().localize(datetime(self.camp.year + 10, 1, 1))
            book_basket_now(acc.bookings.for_year(self.camp.year).in_basket())
        self.assertTrue(acc.bookings.all()[0].early_bird_discount)
        self.assertEqual(acc.bookings.all()[0].amount_due, self.price_full - self.price_early_bird_discount)

    def test_book_basket_doesnt_apply_discount(self):
        self.create_booking()
        acc = self.get_account()
        with mock.patch('cciw.bookings.models.get_early_bird_cutoff_date') as mock_f:
            # Cut off date definitely in the past
            mock_f.return_value = timezone.get_default_timezone().localize(datetime(self.camp.year - 10, 1, 1))
            book_basket_now(acc.bookings.for_year(self.camp.year).in_basket())
        self.assertFalse(acc.bookings.all()[0].early_bird_discount)
        self.assertEqual(acc.bookings.all()[0].amount_due, self.price_full)

    def test_expire(self):
        self.test_book_basket_applies_discount()
        acc = self.get_account()
        booking = acc.bookings.all()[0]
        booking.expire()

        self.assertFalse(booking.early_bird_discount)
        # For the sake of 'list bookings' view, we need to display the
        # un-discounted price.
        self.assertEqual(booking.amount_due, self.price_full)
        self.assertEqual(booking.booked_at, None)

    def test_non_early_bird_booking_warning(self):
        self.create_booking()
        mail.outbox = []
        acc = self.get_account()
        with mock.patch('cciw.bookings.models.get_early_bird_cutoff_date') as mock_f:
            mock_f.return_value = timezone.now() - timedelta(days=10)
            book_basket_now(acc.bookings.for_year(self.camp.year).in_basket())
            acc.receive_payment(self.price_full)
        acc = self.get_account()
        mails = [m for m in send_queued_mail() if m.to == [self.email]]
        assert len(mails) == 1
        self.assertIn("If you had booked earlier", mails[0].body)
        self.assertIn("£10", mails[0].body)


class TestExportPlaces(CreateBookingModelMixin, TestBase):

    def test_summary(self):
        self.create_booking()
        acc = self.get_account()
        acc.bookings.update(state=BookingState.BOOKED)

        workbook = camp_bookings_to_spreadsheet(self.camp, ExcelFormatter()).to_bytes()
        wkbk = xlrd.open_workbook(file_contents=workbook)
        wksh_all = wkbk.sheet_by_index(0)

        self.assertEqual(wksh_all.cell(0, 0).value, "First name")
        self.assertEqual(wksh_all.cell(1, 0).value, acc.bookings.all()[0].first_name)

    def test_birthdays(self):
        bday = self.camp.start_date + timedelta(1)
        dob = bday.replace(bday.year - 12)
        self.create_booking({'date_of_birth': dob.isoformat()})

        acc = self.get_account()
        acc.bookings.update(state=BookingState.BOOKED)

        workbook = camp_bookings_to_spreadsheet(self.camp, ExcelFormatter()).to_bytes()
        wkbk = xlrd.open_workbook(file_contents=workbook)
        wksh_bdays = wkbk.sheet_by_index(2)

        self.assertEqual(wksh_bdays.cell(0, 0).value, "First name")
        self.assertEqual(wksh_bdays.cell(1, 0).value, acc.bookings.all()[0].first_name)

        self.assertEqual(wksh_bdays.cell(0, 2).value, "Birthday")
        self.assertEqual(wksh_bdays.cell(1, 2).value, bday.strftime("%A %d %B"))

        self.assertEqual(wksh_bdays.cell(0, 3).value, "Age")
        self.assertEqual(wksh_bdays.cell(1, 3).value, "12")


class TestExportPaymentData(TestBase):

    def test_export(self):
        account1 = BookingAccount.objects.create(
            name="Joe Bloggs",
            email='joe@foo.com')
        account2 = BookingAccount.objects.create(
            name="Mary Muddle",
            email='mary@foo.com')
        factories.create_ipn(
            account1,
            mc_gross=Decimal('10.00')
        )
        ManualPayment.objects.create(account=account1,
                                     amount=Decimal('11.50'))
        RefundPayment.objects.create(account=account1,
                                     amount=Decimal('0.25'))
        AccountTransferPayment.objects.create(from_account=account2,
                                              to_account=account1,
                                              amount=Decimal("100.00"))
        mp2 = ManualPayment.objects.create(account=account1,
                                           amount=Decimal('1.23'))
        mp2.delete()

        now = timezone.now()
        workbook = payments_to_spreadsheet(now - timedelta(days=3),
                                           now + timedelta(days=3),
                                           ExcelFormatter()).to_bytes()

        wkbk = xlrd.open_workbook(file_contents=workbook)
        wksh = wkbk.sheet_by_index(0)
        data = [[c.value for c in r] for r in wksh.get_rows()]
        self.assertEqual(data[0],
                         ['Account name', 'Account email', 'Amount', 'Date', 'Type'])

        # Excel dates are a pain, so we ignore them
        data2 = [[c for i, c in enumerate(r) if i != 3] for r in data[1:]]
        self.assertIn(['Joe Bloggs', 'joe@foo.com', 10.0, 'PayPal'],
                      data2)
        self.assertIn(['Joe Bloggs', 'joe@foo.com', 11.5, 'Cheque'],
                      data2)
        self.assertIn(['Joe Bloggs', 'joe@foo.com', -0.25, 'Refund Cheque'],
                      data2)
        self.assertIn(['Joe Bloggs', 'joe@foo.com', 100.00, 'Account transfer'],
                      data2)

        self.assertNotIn(['Joe Bloggs', 'joe@foo.com', 1.23, 'ManualPayment (deleted)'],
                         data2)
        self.assertNotIn(['Joe Bloggs', 'joe@foo.com', -1.23, 'ManualPayment (deleted)'],
                         data2)


class TestBookingModel(CreateBookingModelMixin, TestBase):

    def test_need_approving(self):
        self.create_booking()
        self.assertEqual(len(Booking.objects.need_approving()), 0)

        Booking.objects.update(serious_illness=True)
        self.assertEqual(len(Booking.objects.need_approving()), 1)

        Booking.objects.update(serious_illness=False)
        Booking.objects.update(date_of_birth=date(1980, 1, 1))
        self.assertEqual(len(Booking.objects.need_approving()), 1)

        self.assertEqual(Booking.objects.get().approval_reasons(), ['Too old'])


class TestPaymentModels(TestBase):

    def test_payment_source_save_bad(self):
        manual = factories.create_manual_payment()
        refund = factories.create_refund_payment()
        self.assertRaises(AssertionError,
                          lambda: PaymentSource.objects.create(
                              manual_payment=manual,
                              refund_payment=refund))

    def test_payment_source_save_good(self):
        manual = factories.create_manual_payment()
        PaymentSource.objects.all().delete()
        p = PaymentSource.objects.create(manual_payment=manual)
        self.assertNotEqual(p.id, None)


class TestEmailVerifyTokenGenerator(TestCase):
    @given(st.emails())
    def test_decode_inverts_encode(self, email):
        v = EmailVerifyTokenGenerator()
        self.assertEqual(v.email_for_token(v.token_for_email(email)),
                         email)

    @given(st.emails())
    def test_truncated_returns_invalid(self, email):
        v = EmailVerifyTokenGenerator()
        self.assertEqual(v.email_for_token(v.token_for_email(email)[2:]),
                         VerifyFailed)

    @given(st.emails())
    def test_expired_returns_expired(self, email):
        v = EmailVerifyTokenGenerator()
        self.assertEqual(v.email_for_token(v.token_for_email(email),
                                           max_age=-1),
                         VerifyExpired(email))

    @given(email=st.text())
    @example(email='abcdefgh')  # b64 encode results in trailing ==
    def test_tolerate_truncated_trailing_equals(self, email):
        v = EmailVerifyTokenGenerator()

        # Either some silly people, or some dumb email programs, decide to strip
        # trailing = from URLs (despite this being a supposedly URL safe
        # character). Ensure that we tolerate this.
        def remove_equals(s):
            return s.rstrip('=')

        self.assertEqual(v.email_for_token(remove_equals(v.token_for_email(email))),
                         email)
