import itertools
import re
import datetime
from django import forms
from django import template
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db import models
from django.core.validators import email_re
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template.loader import render_to_string
from django.template.defaultfilters import wordwrap
from django.utils.hashcompat import sha_constructor
from django.views.decorators.cache import never_cache
from cciw.cciwmain import common
from cciw.cciwmain.models import Camp
from cciw.cciwmain.views.memberadmin import email_hash
from cciw.mail.lists import address_for_camp_officers, address_for_camp_slackers
from cciw.officers.applications import application_to_text, application_to_rtf, application_rtf_filename, application_txt_filename
from cciw.officers import create
from cciw.officers.email_utils import send_mail_with_attachments, formatted_email
from cciw.officers.email import make_update_email_hash, send_reference_request_email, make_ref_form_url, make_ref_form_url_hash, send_leaders_reference_email
from cciw.officers.widgets import ExplicitBooleanFieldSelect
from cciw.officers.models import Application, Reference, ReferenceForm
from cciw.officers.utils import camp_officer_list, camp_slacker_list
from cciw.officers.references import reference_form_info
from cciw.utils.views import close_window_response
import smtplib

def _copy_application(application):
    new_obj = Application(id=None)
    for field in Application._meta.fields:
        if field.attname != 'id':
            setattr(new_obj, field.attname, getattr(application, field.attname))
    new_obj.camp = None
    new_obj.youth_work_declined = None
    new_obj.relevant_illness = None
    new_obj.crime_declaration = None
    new_obj.court_declaration = None
    new_obj.concern_declaration = None
    new_obj.allegation_declaration = None
    new_obj.crb_check_consent = None
    new_obj.finished = False
    new_obj.date_submitted = None
    return new_obj

def _is_camp_admin(user):
    """
    Returns True is the user is an admin for any camp.
    """
    return (user.groups.filter(name='Leaders').exists()) \
        or user.camps_as_admin.exists() > 0

def _camps_as_admin_or_leader(user):
    """
    Returns all the camps for which the user is an admin or leader.
    """
    # If the user is am 'admin' for some camps:
    camps = user.camps_as_admin.all()
    # Find the 'Person' object that corresponds to this user
    leaders = list(user.person_set.all())
    # Find the camps for this leader
    # (We could do:
    #    Person.objects.get(user=user.id).camps_as_leader.all(),
    #  but we also must we handle the possibility that two Person
    #  objects have the same User objects, which could happen in the
    #  case where a leader leads by themselves and as part of a couple)
    for leader in leaders:
        camps = camps | leader.camps_as_leader.all()

    return camps

# /officers/
@staff_member_required
@never_cache
def index(request):
    """Displays a list of links/buttons for various actions."""
    user = request.user
    context = template.RequestContext(request)
    if _is_camp_admin(user):
        context['show_leader_links'] = True
        context['show_admin_link'] = True

    return render_to_response('cciw/officers/index.html',
                              context_instance=context)

@staff_member_required
@user_passes_test(_is_camp_admin)
def leaders_index(request):
    """Displays a list of links for actions for leaders"""
    user = request.user
    context = template.RequestContext(request)
    thisyear = common.get_thisyear()
    context['current_camps'] = _camps_as_admin_or_leader(user).filter(year=thisyear)
    context['old_camps'] = _camps_as_admin_or_leader(user).filter(year__lt=thisyear)

    return render_to_response('cciw/officers/leaders_index.html', context_instance=context)

def get_next_camp_guess(camp):
    """
    Given a camp that an officer had been on, returns the camp that they are
    likely to apply to, or None if no suitable guess can be found.
    """
    next_camps = list(camp.next_camps.filter(online_applications=True))
    if len(next_camps) > 0:
        next_camp = next_camps[0]
        if next_camp.is_past():
            return get_next_camp_guess(next_camp)
        else:
            return next_camp
    else:
        return None

@staff_member_required
@never_cache
def applications(request):
    """Displays a list of tasks related to applications."""
    user = request.user
    context = template.RequestContext(request)
    context['finished_applications'] = user.application_set\
                                       .filter(finished=True)\
                                       .order_by('-date_submitted')
    context['unfinished_applications'] = user.application_set\
                                         .filter(finished=False)\
                                         .order_by('-date_submitted')

    if request.POST.has_key('edit'):
        # Edit existing application
        id = request.POST.get('edit_application', None)
        if id is not None:
            return HttpResponseRedirect('/admin/officers/application/%s/' % id)
    elif request.POST.has_key('new'):
        # Create new application based on old one
        obj = None
        try:
            id = int(request.POST['new_application'])
        except (ValueError, KeyError):
            id = None
        if id is not None:
            try:
                obj = Application.objects.get(pk=id)
            except Application.DoesNotExist:
                # should never get here
                obj = None
        if obj is not None:
            # Create a copy
            new_obj = _copy_application(obj)
            # We *have* to set 'camp' otherwise object cannot be seen
            # in admin, due to default 'ordering'
            next_camp = get_next_camp_guess(obj.camp)
            if next_camp is not None:
                new_obj.camp = next_camp
            else:
                new_obj.camp = Camp.objects\
                               .filter(online_applications=True)\
                               .order_by('-year', 'number')[0]
            new_obj.save()
            return HttpResponseRedirect('/admin/officers/application/%s/' % \
                                        new_obj.id)

    elif request.POST.has_key('delete'):
        # Delete an unfinished application
        pass

    return render_to_response('cciw/officers/applications.html',
                              context_instance=context)

@staff_member_required
def view_application(request):
    try:
        application_id = int(request.POST['application'])
    except:
        raise Http404

    try:
        app = Application.objects.get(id=application_id)
    except Application.DoesNotExist:
        raise Http404

    if app.officer_id != request.user.id and \
            not _is_camp_admin(request.user):
        raise PermissionDenied

    # NB, this is is called by both normal users and leaders.
    # In the latter case, request.user != app.officer

    format = request.POST.get('format', '')
    if format == 'txt':
        resp = HttpResponse(application_to_text(app), mimetype="text/plain")
        resp['Content-Disposition'] = 'attachment; filename=%s;' % \
                                      application_txt_filename(app)
        return resp
    elif format == 'rtf':
        resp = HttpResponse(application_to_rtf(app), mimetype="text/rtf")
        resp['Content-Disposition'] = 'attachment; filename=%s;' % \
                                      application_rtf_filename(app)
        return resp
    elif format == 'send':
        application_text = application_to_text(app)
        application_rtf = application_to_rtf(app)
        rtf_attachment = (application_rtf_filename(app),
                          application_rtf, 'text/rtf')

        msg = \
u"""Dear %s,

Please find attached a copy of the application you requested
 -- in plain text below and an RTF version attached.

""" % request.user.first_name
        msg = msg + application_text

        send_mail_with_attachments("Copy of CCIW application - %s" % app.full_name,
                                   msg, settings.SERVER_EMAIL,
                                   [formatted_email(request.user)],
                                   attachments=[rtf_attachment])
        messages.info(request, "Email sent.")

        # Redirect back where we came from
        return HttpResponseRedirect(request.POST.get('to', '/officers/'))

    else:
        raise Http404

    return resp


def _thisyears_camp_for_leader(user):
    leaders = list(user.person_set.all())
    try:
        return leaders[0].camps_as_leader.get(year=common.get_thisyear(),
                                              online_applications=True)
    except (ObjectDoesNotExist, IndexError):
        return None

@staff_member_required
@user_passes_test(_is_camp_admin)
@never_cache
def manage_applications(request, year=None, number=None):
    user = request.user
    camp = _get_camp_or_404(year, number)
    context = template.RequestContext(request)
    context['finished_applications'] =  camp.application_set.filter(finished=True)
    context['camp'] = camp

    return render_to_response('cciw/officers/manage_applications.html',
                              context_instance=context)

def _get_camp_or_404(year, number):
    try:
        return Camp.objects.get(year=int(year), number=int(number))
    except Camp.DoesNotExist, ValueError:
        raise Http404

def get_previous_references(ref):
    """
    Returns a tuple of:
     (possible previous References ordered by relevance,
      exact match for previous Reference or None if it doesn't exist)
    """
    # Look for ReferenceForms for same officer, within the previous five
    # years.  Don't look for references from this year's
    # application (which will be the other referee).
    cutoffdate = ref.application.camp.start_date - datetime.timedelta(365*5)
    prev = list(ReferenceForm.objects\
                .filter(reference_info__application__officer=ref.application.officer,
                        reference_info__application__finished=True,
                        date_created__gte=cutoffdate)\
                .exclude(reference_info__application=ref.application)\
                .order_by('-reference_info__application__camp__year'))

    # Sort by relevance
    def relevance_key(refform):
        # Matching name or e-mail address is better, so has lower value,
        # so it comes first.
        return -(int(refform.reference_info.referee.email==ref.referee.email) +
                 int(refform.reference_info.referee.name ==ref.referee.name))
    prev.sort(key=relevance_key) # sort is stable, so previous sort by year should be kept

    exact = None
    for refform in prev:
        if refform.reference_info.referee == ref.referee:
            exact = refform.reference_info
            break
    return ([rf.reference_info for rf in prev], exact)

@staff_member_required
@user_passes_test(_is_camp_admin) # we don't care which camp they are admin for.
@never_cache
def manage_references(request, year=None, number=None):
    camp = _get_camp_or_404(year, number)

    c = template.RequestContext(request)
    c['camp'] = camp

    apps = camp.application_set.filter(finished=True)
    # force creation of Reference objects.
    if Reference.objects.filter(application__finished=True,
                                application__camp=camp).count() < apps.count() * 2:
        [a.references for a in apps]

    # TODO - check for case where user has submitted multiple application forms.
    # User.objects.all().filter(application__camp=camp).annotate(num_applications=models.Count('application')).filter(num_applications__gt=1)

    refinfo = Reference.objects\
              .filter(application__camp=camp, application__finished=True)\
              .order_by('application__officer__first_name', 'referee_number')
    received = refinfo.filter(received=True)
    requested = refinfo.filter(received=False, requested=True)
    notrequested = refinfo.filter(received=False, requested=False)

    for l in (received, requested, notrequested):
        # decorate each Reference with suggested previous ReferenceForms.
        for curref in l:
            (prev, exact) = get_previous_references(curref)
            if exact is not None:
                curref.previous_reference = exact
            else:
                curref.possible_previous_references = prev

    c['notrequested'] = notrequested
    c['requested'] = requested
    c['received'] = received

    return render_to_response('cciw/officers/manage_references.html',
                              context_instance=c)

def email_sending_failed_response():
    return HttpResponse("""<p>Email failed to send.  This is likely a temporary
    error, please press back in your browser and try again.</p>""")

@staff_member_required
@user_passes_test(_is_camp_admin) # we don't care which camp they are admin for.
def request_reference(request):
    try:
        ref_id = int(request.GET.get('ref_id'))
    except ValueError, TypeError:
        raise Http404
    ref = get_object_or_404(Reference.objects.filter(id=ref_id))

    if 'manual' in request.GET:
        return manage_reference_manually(request, ref)

    if request.method == 'POST':
        if 'send' in request.POST:
            try:
                send_reference_request_email(wordwrap(request.POST.get('message', ''), 70), ref)
            except smtplib.SMTPException:
                return email_sending_failed_response()
            ref.requested = True
            ref.comments = ref.comments + \
                           ("\nReference requested by user %s via online system on %s\n" % \
                            (request.user.username, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            ref.save()
        return close_window_response()

    c = template.RequestContext(request)
    update = 'update' in request.GET
    if update:
        (possible, exact) = get_previous_references(ref)
        prev_ref_id = request.GET.get('prev_ref_id', None)
        if prev_ref_id is None:
            # require an exact.
            assert exact is not None
            # The above can only fail if the user has been
            # trying to hack things.
            url = make_ref_form_url(ref.id, exact.id)
            c['known_email_address'] = True
        else:
            # These can error if the user has been hacking
            prev_ref_id = int(prev_ref_id)
            refs = [r for r in possible if r.id == prev_ref_id]
            assert len(refs) == 1
            url = make_ref_form_url(ref.id, prev_ref_id)
            c['old_referee'] = refs[0].referee
        msg_template = 'cciw/officers/request_reference_update.txt'
    else:
        url = make_ref_form_url(ref.id, None)
        msg_template = 'cciw/officers/request_reference_new.txt'

    if not email_re.match(ref.referee.email.strip()):
        c['bad_email'] = True
    app = ref.application
    camp = app.camp
    msg = render_to_string(msg_template,
                           dict(referee=ref.referee,
                                applicant=app.officer,
                                camp=camp,
                                url=url))
    c['is_popup'] = True
    c['already_requested'] = ref.requested
    c['referee'] = ref.referee
    c['app'] = app
    c['default_message'] = msg
    c['is_update'] = update
    return render_to_response('cciw/officers/request_reference.html',
                              context_instance=c)

class ReferenceFormForm(forms.ModelForm):
    class Meta:
        model = ReferenceForm
        fields = ('referee_name',
                  'how_long_known',
                  'capacity_known',
                  'known_offences',
                  'known_offences_details',
                  'capability_children',
                  'character',
                  'concerns',
                  'comments')

normal_textarea = forms.Textarea(attrs={'cols':80, 'rows':10})
small_textarea = forms.Textarea(attrs={'cols':80, 'rows':5})
ReferenceFormForm.base_fields['capacity_known'].widget = small_textarea
ReferenceFormForm.base_fields['known_offences'].widget = ExplicitBooleanFieldSelect()
ReferenceFormForm.base_fields['known_offences_details'].widget = normal_textarea
ReferenceFormForm.base_fields['capability_children'].widget = normal_textarea
ReferenceFormForm.base_fields['character'].widget = normal_textarea
ReferenceFormForm.base_fields['concerns'].widget = normal_textarea
ReferenceFormForm.base_fields['comments'].widget = normal_textarea

# I have models called Reference and ReferenceForm.  What do I call a Form
# for model Reference? I'm a loser...
class ReferenceEditForm(forms.ModelForm):
    class Meta:
        model = Reference
        fields = ('requested', 'received', 'comments')

def manage_reference_manually(request, ref):
    """
    Returns page for manually editing Reference and ReferenceForm details.
    """
    c = template.RequestContext(request)
    c['ref'] = ref
    c['referee'] = ref.referee
    c['officer'] = ref.application.officer
    if request.method == 'POST':
        if 'save' in request.POST:
            form = ReferenceEditForm(request.POST, instance=ref)
            if form.is_valid():
                form.save()
                return close_window_response()
        else:
            return close_window_response()
    else:
        form = ReferenceEditForm(instance=ref)
    c['form'] = form
    return render_to_response("cciw/officers/manage_reference_manual.html",
                              context_instance=c)

@staff_member_required
@user_passes_test(_is_camp_admin) # we don't care which camp they are admin for.
def edit_reference_form_manually(request, ref_id=None):
    """
    Create ReferenceForm if necessary, then launch normal admin popup for
    editing it.
    """
    ref = get_object_or_404(Reference.objects.filter(id=int(ref_id)))
    if not ref.referenceform_set.exists():
        # Create it
        ref.referenceform_set.create(referee_name=ref.referee.name,
                                     date_created=datetime.date.today(),
                                     known_offences=False)
    return HttpResponseRedirect(reverse("admin:officers_referenceform_change",
                                        args=(ref.referenceform_set.all()[0].id,)) + \
                                "?_popup=1")

def initial_reference_form_data(ref, prev_ref_form):
    """
    Return the initial data to be used for ReferenceFormForm, given the current
    Reference objects and the ReferenceForm object with data to be copied.
    """
    retval =  {}
    if prev_ref_form is not None:
        # Copy data over
        for f in ReferenceFormForm._meta.fields:
            retval[f] = getattr(prev_ref_form, f)
    retval['referee_name'] = ref.referee.name
    retval.pop('date_created', None)
    return retval

def create_reference_form(request, ref_id="", prev_ref_id="", hash=""):
    """
    View for allowing referee to submit reference (create the ReferenceForm object)
    """
    c = template.RequestContext(request)
    if hash != make_ref_form_url_hash(ref_id, prev_ref_id):
        c['incorrect_url'] = True
    else:
        ref = get_object_or_404(Reference.objects.filter(id=int(ref_id)))
        if prev_ref_id != "":
            prev_ref = get_object_or_404(Reference.objects.filter(id=int(prev_ref_id)))
            assert prev_ref.referenceform_set.all().count() == 1
            prev_ref_form = prev_ref.referenceform_set.all()[0]
            c['update'] = True
        else:
            prev_ref = None
            prev_ref_form = None

        ref_forms = ref.referenceform_set.all()
        if len(ref_forms) > 0:
            # For the case where a ReferenceForm has been created (accidentally)
            # by an admin, we need to re-use it, rather than create another.
            instance = ref_forms[0]
        else:
            instance = None

        if len(ref_forms) > 0 and ref.received:
            # It's possible, if an admin has done 'Manage reference manually'
            # and clicked "Create/edit reference form" but then cancelled, that
            # the ReferenceForm will exist but be empty.  So we check both that
            # it exists and that the 'ref.received' is True, otherwise a referee
            # will be unable to fill out the form.
            c['already_submitted'] = True
        else:
            if request.method == 'POST':
                form = ReferenceFormForm(request.POST, instance=instance) # A form bound to the POST data
                if form.is_valid():
                    obj = form.save(commit=False)
                    obj.reference_info = ref
                    obj.date_created = datetime.date.today()
                    obj.save()
                    ref.received = True
                    ref.comments = ref.comments + \
                                   ("\nReference received via online system on %s\n" % \
                                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    ref.save()
                    send_leaders_reference_email(obj)
                    return HttpResponseRedirect(reverse('cciw.officers.views.create_reference_thanks'))
            else:
                if instance is not None:
                    form = ReferenceFormForm(instance=instance)
                else:
                    form = ReferenceFormForm(initial=initial_reference_form_data(ref, prev_ref_form))
            c['form'] = form
        c['officer'] = ref.application.officer
    return render_to_response('cciw/officers/create_reference.html',
                              context_instance=c)

def create_reference_thanks(request):
    return render_to_response('cciw/officers/create_reference_thanks.html',
                              context_instance=template.RequestContext(request))

class OfficerChoice(forms.ModelMultipleChoiceField):
    def label_from_instance(self, u):
        return u"%s %s <%s>" % (u.first_name, u.last_name, u.email)

class OfficerListForm(forms.Form):
    officers = OfficerChoice(
        widget=forms.SelectMultiple(attrs={'class':'vSelectMultipleField'}),
        queryset=User.objects.filter(is_staff=True).order_by('first_name', 'last_name'),
        required=False
        )


@staff_member_required
@user_passes_test(_is_camp_admin)
def view_reference(request, ref_id=None):
    ref = get_object_or_404(Reference.objects.filter(id=ref_id))
    forms = list(ref.referenceform_set.all())
    c = template.RequestContext(request)
    if len(forms) > 0:
        refform = forms[0]
        c['refform'] = refform
        c['info'] = reference_form_info(refform)
    c['ref'] = ref
    c['officer'] = ref.application.officer
    c['referee'] = ref.referee
    c['is_popup'] = True

    return render_to_response("cciw/officers/view_reference_form.html",
                              context_instance=c)

@staff_member_required
@user_passes_test(_is_camp_admin)
def officer_list(request, year=None, number=None):
    camp = _get_camp_or_404(year, number)

    c = template.RequestContext(request)
    c['camp'] = camp

    if request.method == 'POST':
        form = OfficerListForm(request.POST)
        if form.is_valid():
            camp.invitation_set.all().delete()
            for o in form.cleaned_data['officers']:
                camp.invitation_set.create(officer=o).save()
    else:
        form = OfficerListForm({'officers': [unicode(inv.officer_id) for inv in camp.invitation_set.all()]})

    c['form'] = form

    # Make sure these queries come after the above data modification
    c['officers_all'] = camp_officer_list(camp)
    c['officers_noapplicationform'] = camp_slacker_list(camp)
    c['addresses_all'] = address_for_camp_officers(camp)
    c['addresses_noapplicationform'] = address_for_camp_slackers(camp)

    return render_to_response('cciw/officers/officer_list.html',
                              context_instance=c)

def update_email(request, username=''):
    c = {}
    u = get_object_or_404(User.objects.filter(username=username))
    email = request.GET.get('email', '')
    hash = request.GET.get('hash', '')

    if email == u.email:
        c['message'] = "The e-mail address has already been updated, thanks."
    else:
        if make_update_email_hash(u.email, email) != hash:
            c['message'] = "The URL was invalid. Please ensure you copied the URL from the e-mail correctly"
        else:
            c['message'] = "Your e-mail address has been updated, thanks."
            c['success'] = True
            u.email = email
            u.save()

    return render_to_response('cciw/officers/email_update.html',
                              context_instance=template.RequestContext(request, c))


class CreateOfficerForm(forms.Form):
    first_name = forms.CharField()
    last_name = forms.CharField()
    email = forms.EmailField()

    def save(self):
        return create.create_officer(None, self.cleaned_data['first_name'],
                                     self.cleaned_data['last_name'],
                                     self.cleaned_data['email'])

@staff_member_required
@user_passes_test(_is_camp_admin)
def create_officer(request):
    allow_confirm = True
    duplicate_message = ""
    existing_users = None
    message = ""
    if request.method == "POST":
        form = CreateOfficerForm(request.POST)
        process_form = False
        if form.is_valid():
            if "add" in request.POST:
                same_name_users = User.objects.filter(first_name__iexact=form.cleaned_data['first_name'],
                                                      last_name__iexact=form.cleaned_data['last_name'])
                same_email_users = User.objects.filter(email__iexact=form.cleaned_data['email'])
                same_user = same_name_users & same_email_users
                if same_user.exists():
                    allow_confirm = False
                    duplicate_message = "A user with that name and e-mail address already exists. You can change the details above and try again."
                elif len(same_name_users) > 0:
                    existing_users = same_name_users
                    if len(existing_users) == 1:
                        duplicate_message = "A user with that first name and last name " + \
                                            "already exists:"
                    else:
                        duplicate_message = "%d users with that first name and last name " + \
                                            "already exist:" % len(existing_users)
                elif len(same_email_users):
                    existing_users = same_email_users
                    if len(existing_users) == 1:
                        duplicate_message = "A user with that e-mail address already exists:"
                    else:
                        duplicate_message = "%d users with that e-mail address already exist:"\
                                            % len(existing_users)
                else:
                    process_form = True

            elif "confirm" in request.POST:
                process_form = True

            if process_form:
                u = form.save()
                form = CreateOfficerForm()
                message = "Officer %s has been added and e-mailed.  You can add another if required." % u.username
    else:
        form = CreateOfficerForm()

    c = {'form': form,
         'duplicate_message': duplicate_message,
         'existing_users': existing_users,
         'allow_confirm': allow_confirm,
         'message': message,
         }
    return render_to_response('cciw/officers/create_officer.html',
                              context_instance=template.RequestContext(request, c))
