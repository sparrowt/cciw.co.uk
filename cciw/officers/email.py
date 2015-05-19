from datetime import timedelta, datetime
from email.mime.base import MIMEBase
import email.parser
import email.utils
import logging

from cciw.cciwmain import common
from cciw.cciwmain.models import Camp
from cciw.officers.applications import application_to_text, application_to_rtf, application_rtf_filename, application_difference, camps_for_application
from cciw.officers.email_utils import send_mail_with_attachments, formatted_email
from cciw.officers.references import reference_form_to_text
from django.conf import settings
from django.contrib import messages
from django.core import signing
from django.core.mail import send_mail, EmailMessage
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.utils.http import urlquote


logger = logging.getLogger(__name__)


def admin_emails_for_camp(camp):
    leaders = ([user for leader in camp.leaders.all()
                for user in leader.users.all()] +
               list(camp.admins.all()))

    return list(filter(lambda x: x is not None,
                       map(formatted_email, leaders)))


def admin_emails_for_application(application):
    """
    For the supplied application, finds the camps admins that are relevant.
    Returns results in groups of (camp, leaders), for each relevant camp.
    """
    camps = camps_for_application(application)
    groups = []
    for camp in camps:
        groups.append((camp, admin_emails_for_camp(camp)))
    return groups


def send_application_emails(request, application):
    if not application.finished:
        return

    # Email to the leaders:

    application_text = application_to_text(application)
    application_rtf = application_to_rtf(application)
    rtf_attachment = (application_rtf_filename(application), application_rtf, 'text/rtf')

    # Collect e-mails to send to
    leader_email_groups = admin_emails_for_application(application)
    for camp, leader_emails in leader_email_groups:
        # Did the officer submit one last year?
        previous_camp = camp.previous_camp
        application_diff = None
        if previous_camp is not None:
            officer = application.officer
            previous_app = None
            if previous_camp.invitations.filter(officer=officer).exists():
                try:
                    previous_app = officer.applications.filter(date_submitted__lte=previous_camp.start_date,
                                                               date_submitted__gte=previous_camp.start_date + timedelta(-365),
                                                               finished=True)[0]
                except IndexError:
                    pass
            if previous_app is not None:
                application_diff = ("differences_from_last_year.html",
                                    application_difference(previous_app, application),
                                    "text/html")

        if len(leader_emails) > 0:
            send_leader_email(leader_emails, application, application_text, rtf_attachment,
                              application_diff)
        messages.info(request, "The completed application form has been sent to the leaders (%s) via e-mail." %
                      camp.leaders_formatted)

    if len(leader_email_groups) == 0:
        application_text = """PLEASE NOTE: This has not been sent to any leaders,
since the officer was not on any invitation list.

""" + application_text
        send_leader_email([settings.WEBMASTER_EMAIL], application, application_text, rtf_attachment, None)

    # If an admin user corrected an application, we don't send the user a copy
    # (usually they just get the year of the camp wrong(!))
    if request.user == application.officer:
        send_officer_email(application.officer, application, application_text, rtf_attachment)
        messages.info(request, "A copy of the application form has been sent to you via e-mail.")

        if application.officer.email.lower() != application.address_email.lower():
            send_email_change_emails(application.officer, application)


def send_officer_email(officer, application, application_text, rtf_attachment):
    subject = "CCIW application form submitted"

    # Email to the officer
    user_email = formatted_email(application.officer)
    user_msg = (
"""%s,

For your records, here is a copy of the application you have submitted
to CCIW. It is also attached to this e-mail as an RTF file.

""" % application.officer.first_name) + application_text

    if user_email is not None:
        send_mail_with_attachments(subject, user_msg, settings.SERVER_EMAIL,
                                   [user_email], attachments=[rtf_attachment])


def send_leader_email(leader_emails, application, application_text, rtf_attachment,
                      application_diff):
    subject = "CCIW application form from %s" % application.full_name
    body = (
"""The following application form has been submitted via the
CCIW website.  It is also attached to this e-mail as an RTF file.

""")
    if application_diff is not None:
        body += (
"""The second attachment shows the differences between this year's
application form and last year's - pink indicates information that has
been removed, green indicates new information.

""")

    body += application_text

    attachments = [rtf_attachment]
    if application_diff is not None:
        attachments.append(application_diff)

    send_mail_with_attachments(subject, body, settings.SERVER_EMAIL,
                               leader_emails, attachments=attachments)


def make_update_email_url(application):
    return 'https://%(domain)s%(path)s?t=%(token)s' % dict(
        domain=common.get_current_domain(),
        path=reverse('cciw-officers-correct_email'),
        token=signing.dumps([application.officer.username,
                             application.address_email],
                            salt="cciw-officers-correct_email"))


def make_update_application_url(application, email):
    return 'https://%(domain)s%(path)s?t=%(token)s' % dict(
        domain=common.get_current_domain(),
        path=reverse('cciw-officers-correct_application'),
        token=signing.dumps([application.id,
                             email],
                            salt="cciw-officers-correct_application"))


def send_email_change_emails(officer, application):
    subject = "E-mail change on CCIW"
    user_email = formatted_email(officer)
    user_msg = (
"""%(name)s,

In your most recently submitted application form, you entered your
e-mail address as %(new)s.  The e-mail address stored against your
account is %(old)s.  If you would like this to be updated to '%(new)s'
then click the link below:

 %(correct_email_url)s

If the e-mail address you entered on your application form (%(new)s)
is, in fact, incorrect, then click the link below to correct
your application form to %(old)s:

 %(correct_application_url)s

NB. This e-mail has been sent to both the old and new e-mail
addresses, you only need to respond to one e-mail.

Thanks,


This was an automated response by the CCIW website.


""" % dict(name=officer.first_name, old=officer.email,
           new=application.address_email,
           correct_email_url=make_update_email_url(application),
           correct_application_url=make_update_application_url(application, officer.email),
           )
    )

    send_mail(subject, user_msg, settings.SERVER_EMAIL,
              [user_email, application.address_email], fail_silently=True)


def make_ref_form_url_hash(ref_id, prev_ref_id):
    return salted_hmac("cciw.officers.create_reference_form", "%s:%s" % (ref_id, prev_ref_id)).hexdigest()[::2]


def make_ref_form_url(ref_id, prev_ref_id):
    if prev_ref_id is None:
        prev_ref_id = ""
    return "https://%s%s" % (common.get_current_domain(),
                             reverse('cciw-officers-create_reference_form',
                                     kwargs=dict(ref_id=ref_id,
                                                 prev_ref_id=prev_ref_id,
                                                 hash=make_ref_form_url_hash(ref_id, prev_ref_id))))


def send_reference_request_email(message, ref, sending_officer, camp):
    officer = ref.application.officer
    EmailMessage(subject="Reference for %s %s" % (officer.first_name, officer.last_name),
                 body=message,
                 from_email=settings.REFERENCES_EMAIL,
                 to=[ref.referee.email],
                 headers={
                     'Reply-To': sending_officer.email,
                     'X-CCIW-Camp': '{0}-{1}'.format(camp.year, camp.number),
                     'X-CCIW-Action': 'ReferenceRequest',
                 }).send()


def send_leaders_reference_email(refform):
    """
    Send the leaders/admins an email with contents of submitted reference form.
    Fails silently.
    """
    ref = refform.reference_info
    app = ref.application
    officer = app.officer

    refform_text = reference_form_to_text(refform)
    subject = "CCIW reference form for %s %s from %s" % (officer.first_name, officer.last_name, ref.referee.name)
    body = (
"""The following reference form has been submitted via the
CCIW website for officer %s %s.

%s
""" % (officer.first_name, officer.last_name, refform_text)
    )

    leader_email_groups = admin_emails_for_application(app)
    for camp, leader_emails in leader_email_groups:
        send_mail(subject, body, settings.SERVER_EMAIL,
                  leader_emails, fail_silently=False)


def send_nag_by_officer(message, officer, ref, sending_officer):
    EmailMessage(subject="Need reference from %s" % ref.referee.name,
                 body=message,
                 from_email=settings.DEFAULT_FROM_EMAIL,
                 to=[officer.email],
                 headers={'Reply-To': sending_officer.email}).send()


def send_crb_consent_problem_email(message, officer, camps):
    # If more than one camp involved, we deliberately put all camp leaders
    # together on a single e-mail, so that they can see that more than one camp
    # is involved
    emails = []
    for c in camps:
        emails.extend(admin_emails_for_camp(c))
    send_mail("CRB consent problem for %s %s" % (officer.first_name, officer.last_name),
              message,
              settings.DEFAULT_FROM_EMAIL,
              emails,
              fail_silently=False)


def handle_reference_bounce(email_file):
    p = email.parser.Parser()
    msg = p.parse(email_file)

    admin_emails = [e for name, e in settings.ADMINS]
    if msg.get_content_type() != 'multipart/report':
        logger.warn("Unrecognised content type '%s' in bounce email", msg.get_content_type())
        forward_with_text(admin_emails, "Unrecognised message", "Unrecognised message:\n\n", msg)
        return

    bounced_email = None
    bounced_email_address = None
    if len(msg.get_payload()) > 1:
        status = msg.get_payload(1)
        if status.get_content_type() == 'message/delivery-status':
            for dsn in status.get_payload():
                if dsn.get('action', '').lower() == 'failed':
                    address_type, email_address = dsn['Final-Recipient'].split(';')
                    email_address = email_address.strip()
                    if address_type.lower() == 'rfc822':
                        bounced_email_address = email_address

    if bounced_email_address is not None:
        reply_to = admin_emails
        camp = None
        if len(msg.get_payload()) > 2:
            bounced_email = msg.get_payload(2)
            payload = bounced_email.get_payload()
            if len(payload) > 0:
                reply_to = payload[0].get('Reply-To', reply_to)
                camp_s = payload[0].get('X-CCIW-Camp', camp)
                if camp_s is not None:
                    try:
                        camp_year, camp_number = camp_s.split("-")
                        camp = Camp.objects.get(year=int(camp_year),
                                                number=int(camp_number))
                    except (ValueError, Camp.DoesNotExist):
                        pass

        forward_bounce_to([reply_to], bounced_email_address, msg, camp)
    else:
        forward_with_text(admin_emails, "Unrecognised DSN message", "Unrecognised DSN message:\n\n", msg)


def forward_with_text(email_addresses, subject, text, original_message):
    rfcmessage = MIMEBase("message", "rfc822")
    rfcmessage.attach(original_message)

    forward = EmailMessage(subject=subject,
                           body=text,
                           from_email=settings.DEFAULT_FROM_EMAIL,
                           to=email_addresses,
                           attachments=[rfcmessage])
    forward.send()


def forward_bounce_to(email_addresses, bounced_email_address, original_message, camp):
    forward_body = """
The message below to {email} was not received.

If this message was asking for a reference, you will need
to find a correct email address for this referee.
""".format(email=bounced_email_address)

    if camp is not None:
        forward_body += """
Use the following link to manage this reference:

{link}
""".format(link="https://www.cciw.co.uk"
           + reverse('cciw-officers-manage_references',
                     kwargs=dict(year=camp.year, number=camp.number))
           + "?ref_email=" + urlquote(bounced_email_address))

    forward_with_text(email_addresses,
                      "Reference request to {0} bounced.".format(bounced_email_address),
                      forward_body,
                      original_message)
