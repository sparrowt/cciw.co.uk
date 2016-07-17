import binascii
import base64
from datetime import datetime

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core import mail
from django.core.signing import BadSignature, TimestampSigner
from django.template import loader
from django.utils import timezone

from cciw.officers.email import admin_emails_for_camp

LATE_BOOKING_THRESHOLD = 30  # days


class EmailVerifyTokenGenerator(object):
    """
    Strategy object used to generate and check tokens for the email verification
    mechanism.
    """
    def __init__(self):
        self.signer = TimestampSigner(salt="cciw.bookings.EmailVerifyTokenGenerator")

    def token_for_email(self, email):
        """
        Returns a verification token for the provided email address
        """
        return base64.urlsafe_b64encode(
            self.signer.sign(email).encode('utf-8')).decode('utf-8')

    def email_for_token(self, token):
        """
        Extracts the verified email address from the token, or None if verification failed
        """
        try:
            return self.signer.unsign(
                base64.urlsafe_b64decode(token.encode('utf-8')).decode('utf-8'),
                max_age=settings.BOOKING_EMAIL_VERIFY_TIMEOUT_DAYS * 60 * 60 * 24
            )
        except (binascii.Error, BadSignature, UnicodeDecodeError):
            return None


def send_verify_email(request, booking_account_email):
    current_site = get_current_site(request)
    domain = current_site.domain
    c = {
        'domain': domain,
        'token': EmailVerifyTokenGenerator().token_for_email(booking_account_email),
        'protocol': 'https' if request.is_secure() else 'http',
    }

    body = loader.render_to_string("cciw/bookings/verification_email.txt", c)
    subject = "CCIW booking account"
    mail.send_mail(subject, body, settings.SERVER_EMAIL, [booking_account_email])


def site_address_url_start():
    """
    Returns start of URL (protocol and domain) for this site
    (a guess)
    """
    protocol = 'https' if settings.SESSION_COOKIE_SECURE else 'http'  # best guess
    return protocol + '://' + get_current_site(None).domain


def send_unrecognised_payment_email(ipn_obj):
    c = {
        'url_start': site_address_url_start(),
        'ipn_obj': ipn_obj,
    }

    body = loader.render_to_string("cciw/bookings/unrecognised_payment_email.txt", c)
    subject = "CCIW booking - unrecognised payment"
    mail.send_mail(subject, body, settings.SERVER_EMAIL, [settings.WEBMASTER_EMAIL])


def send_pending_payment_email(account, ipn_obj):
    c = {
        'account': account,
        'ipn_obj': ipn_obj,
    }
    body = loader.render_to_string("cciw/bookings/pending_payment_email.txt", c)
    subject = "CCIW booking - pending payment"
    mail.send_mail(subject, body, settings.SERVER_EMAIL, [account.email])


def send_places_confirmed_email(bookings, **kwargs):
    if not bookings:
        return
    account = bookings[0].account
    if not account.email:
        return

    c = {
        'url_start': site_address_url_start(),
        'account': account,
        'bookings': bookings,
        'payment_received': 'payment_received' in kwargs,
        'early_bird_discount_missed': sum(b.early_bird_discount_missed() for b in bookings)
    }
    body = loader.render_to_string('cciw/bookings/place_confirmed_email.txt', c)
    subject = "CCIW booking - place confirmed"
    mail.send_mail(subject, body, settings.SERVER_EMAIL, [account.email])

    # Email leaders. Bookings could be for different camps, so send different
    # emails.

    # We don't care about timezones, or about accuracy better than 1 day,
    # so use naive UTC datetimes, not aware datetimes.
    today = datetime.utcnow().date()

    for booking in bookings:
        if (booking.camp.start_date - today).days < LATE_BOOKING_THRESHOLD:

            c = {
                'account': account,
                'booking': booking,
                'camp': booking.camp,
                'url_start': site_address_url_start(),
            }
            body = loader.render_to_string('cciw/bookings/late_place_confirmed_email.txt', c)
            subject = "CCIW late booking: %s" % booking.name

            mail.send_mail(subject, body, settings.SERVER_EMAIL,
                           admin_emails_for_camp(booking.camp))


def send_booking_expiry_mail(account, bookings, expired):
    if not account.email:
        return

    c = {
        'url_start': site_address_url_start(),
        'account': account,
        'bookings': bookings,
        'expired': expired,
    }
    body = loader.render_to_string('cciw/bookings/place_expired_mail.txt', c)
    if expired:
        subject = "CCIW booking - booking expired"
    else:
        subject = "CCIW booking - booking expiry warning"
    mail.send_mail(subject, body, settings.SERVER_EMAIL, [account.email])


def send_booking_approved_mail(booking):
    account = booking.account
    if not account.email:
        return False

    c = {
        'url_start': site_address_url_start(),
        'account': account,
        'booking': booking,
    }
    body = loader.render_to_string('cciw/bookings/place_approved_email.txt', c)
    subject = "CCIW booking - approved"
    mail.send_mail(subject, body, settings.SERVER_EMAIL, [account.email])

    return True


def send_booking_confirmed_mail(booking):
    account = booking.account
    if not account.email:
        return False

    c = {
        'account': account,
        'booking': booking,
    }
    body = loader.render_to_string('cciw/bookings/place_booked_email.txt', c)
    subject = "CCIW booking - confirmed"
    mail.send_mail(subject, body, settings.SERVER_EMAIL, [account.email])

    return True


def send_payment_reminder_emails():
    from cciw.bookings.models import BookingAccount
    accounts = BookingAccount.objects.payments_due()

    subject = "CCIW payments due"
    now = timezone.now()
    for account in accounts:
        if (account.last_payment_reminder is not None and
                (now - account.last_payment_reminder).days < settings.BOOKING_EMAIL_REMINDER_FREQUENCY_DAYS):
            continue

        if account.email is None:
            continue

        account.last_payment_reminder = now
        account.save()

        c = {
            'account': account,
            'token': EmailVerifyTokenGenerator().token_for_email(account.email),
        }
        body = loader.render_to_string('cciw/bookings/payments_due_email.txt', c)
        mail.send_mail(subject, body, settings.BOOKING_SECRETARY_EMAIL, [account.email])
