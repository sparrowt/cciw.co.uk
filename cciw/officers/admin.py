
import datetime

from dal import autocomplete
from django import forms
from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin
from django.contrib.auth.models import Group
from django.core import urlresolvers
from django.forms import ValidationError
from django.forms.utils import ErrorList
from django.utils.safestring import mark_safe

from cciw.cciwmain.models import Camp
from cciw.middleware import threadlocals
from cciw.officers import widgets
from cciw.officers.fields import ExplicitBooleanField
from cciw.officers.models import (REFEREE_DATA_FIELDS, REFEREE_NUMBERS, Application, DBSActionLog, DBSCheck, Invitation,
                                  Qualification, QualificationType, Referee, Reference)
from cciw.utils.admin import RerouteResponseAdminMixin
from cciw.utils.views import close_window_response

officer_autocomplete_widget = lambda: autocomplete.ModelSelect2(url='officer-autocomplete')


referee_field = lambda n, f: 'referee{0}_{1}'.format(n, f)


class ApplicationAdminModelForm(forms.ModelForm):

    class Meta:
        widgets = {
            'officer': officer_autocomplete_widget(),
        }

    def __init__(self, *args, **kwargs):
        try:
            initial = kwargs['initial']
        except KeyError:
            initial = {}
            kwargs['initial'] = initial

        if 'instance' not in kwargs:
            # Set some initial values for new form

            # Set officer
            user = threadlocals.get_current_user()
            if user is not None:
                # Setting 'officer' is needed when leaders/admins are using the form
                # to fill in their own application form, rather than editing someone
                # else's.
                initial['officer'] = user
                # Fill out officer name
                initial['full_name'] = "%s %s" % (user.first_name, user.last_name)
                initial['address_email'] = user.email

        else:
            instance = kwargs['instance']
            for n in REFEREE_NUMBERS:
                for f in REFEREE_DATA_FIELDS:
                    initial[referee_field(n, f)] = getattr(instance.referees[n - 1], f)

        super(ApplicationAdminModelForm, self).__init__(*args, **kwargs)

    def clean(self):
        # Import here to avoid cycle
        from cciw.officers.applications import thisyears_applications

        app_finished = self.cleaned_data.get('finished', False)
        user = threadlocals.get_current_user()
        if user.can_manage_application_forms:
            officer = self.cleaned_data.get('officer', None)
        else:
            officer = self.instance.officer

        editing_old = self.instance.pk is not None and self.instance.finished
        if editing_old and not user.can_manage_application_forms:
            # Once an Application has been marked 'finished' we don't allow any
            # value to be changed, to stop the possibility of tampering with saved
            # data.
            self._errors.setdefault('__all__', ErrorList()).append("You cannot change a submitted application form.")

        future_camps = Camp.objects.filter(start_date__gte=datetime.date.today())

        self.editing_old = editing_old

        if not editing_old:
            if len(future_camps) == 0:
                self._errors.setdefault('__all__', ErrorList()).append("You cannot submit an application form until the upcoming camps are decided on.")

            else:
                thisyears_apps = thisyears_applications(officer)
                if self.instance.pk is not None:
                    thisyears_apps = thisyears_apps.exclude(id=self.instance.pk)
                if thisyears_apps.exists():
                    self._errors.setdefault('__all__', ErrorList()).append("You've already submitted an application form this year.")

        if editing_old:
            # Ensure we don't overwrite this
            self.cleaned_data['date_submitted'] = self.instance.date_submitted

        if self.cleaned_data.get('dbs_number', '').strip() != "":
            if self.cleaned_data.get('dbs_update_service_id', '').strip() == "":
                self.add_error('dbs_update_service_id',
                               ValidationError("If you enter a DBS number you need to enter the update service ID.", code='required'))

        if self.cleaned_data.get('dbs_update_service_id', '').strip() != "":
            if self.cleaned_data.get('dbs_number', '').strip() == "":
                self.add_error('dbs_number',
                               ValidationError("If you enter the update service ID you need to enter the DBS certificate number.", code='required'))

        if app_finished:
            # All fields decorated with 'required_field' need to be
            # non-empty
            for name, field in self.fields.items():
                if getattr(field, 'required_field', False):
                    data = self.cleaned_data.get(name)
                    if data is None or data == "":
                        self._errors[name] = ErrorList(["This is a required field"])
        return self.cleaned_data

    def save(self, **kwargs):
        if not self.editing_old:
            self.instance.date_submitted = datetime.date.today()
        retval = super(ApplicationAdminModelForm, self).save(**kwargs)
        for n in REFEREE_NUMBERS:
            ref = self.instance.referees[n - 1]
            for f in REFEREE_DATA_FIELDS:
                setattr(ref, f, self.cleaned_data[referee_field(n, f)])
            ref.save()

        return retval


for f in REFEREE_DATA_FIELDS:
    for n in REFEREE_NUMBERS:
        field = Referee._meta.get_field(f).formfield()
        if f == 'name':
            field.label = "Referee {0} name".format(n)
        ApplicationAdminModelForm.base_fields[referee_field(n, f)] = field


class QualificationInline(admin.TabularInline):
    model = Qualification

    def has_add_permission(self, request):
        if request.user.is_potential_camp_officer:
            return True
        else:
            return super(QualificationInline, self).has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        if request.user.is_potential_camp_officer and (obj is None or obj.officer_id == request.user.id):
            return True
        else:
            return super(QualificationInline, self).has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if request.user.is_potential_camp_officer and (obj is None or obj.officer_id == request.user.id):
            return True
        else:
            return super(QualificationInline, self).has_delete_permission(request, obj)


class InconsistentDBSNumbersFilter(admin.SimpleListFilter):
    title = "Inconsistent DBS numbers"
    parameter_name = "dbs_numbers_problems"

    def lookups(self, request, model_admin):
        return [
            (1, 'Inconsistent'),
        ]

    def queryset(self, request, queryset):
        val = self.value()
        if val is None:
            return queryset
        if val == '1':
            return (queryset.filter(dbs_number="").exclude(dbs_update_service_id="") |
                    queryset.exclude(dbs_number="").filter(dbs_update_service_id=""))


class CampAdminPermissionMixin(object):
    # NB also CciwAuthBackend
    def has_change_permission(self, request, obj=None):
        if request.user.can_manage_application_forms:
            return True
        return super(CampAdminPermissionMixin, self).has_change_permission(request, obj)


class ApplicationAdmin(CampAdminPermissionMixin, admin.ModelAdmin):
    save_as = False

    def officer_username(self, obj):
        return obj.officer.username
    officer_username.admin_order_field = 'officer__username'
    officer_username.short_description = 'username'
    list_display = ['full_name', 'officer_username', 'address_email', 'finished', 'date_submitted']
    list_filter = ['finished', 'date_submitted', InconsistentDBSNumbersFilter]
    ordering = ['full_name']
    search_fields = ['full_name']
    readonly_fields = ['date_submitted']
    date_hierarchy = 'date_submitted'
    form = ApplicationAdminModelForm

    camp_officer_application_fieldsets = [
        ('Personal info',
            {'fields': ['full_name', 'full_maiden_name', 'birth_date', 'birth_place'],
             'classes': ['applicationpersonal', 'wide']}
         ),
        ('Address',
            {'fields': ['address_firstline', 'address_town', 'address_county',
                        'address_postcode', 'address_country', 'address_tel',
                        'address_mobile', 'address_since', 'address_email'],
             'classes': ['wide']}
         ),
        ('Experience',
            {'fields': ['christian_experience'],
             'classes': ['applicationexperience', 'wide'],
             'description': '''Please tells us about your Christian experience '''
             '''(i.e. how you became a Christian and how long you have been a Christian, '''
             '''which Churches you have attended and dates, names of minister/leader)'''}
         ),
        (None,
            {'fields': ['youth_experience'],
             'classes': ['wide'],
             'description': '''Please give details of previous experience of '''
             '''looking after or working with children/young people - '''
             '''include any qualifications or training you have. '''}
         ),
        (None,
            {'fields': ['youth_work_declined', 'youth_work_declined_details'],
             'classes': ['wide'],
             'description': 'If you have ever had an offer to work with children/young people declined, you must declare it below and give details.'}
         ),
        ('Illnesses',
            {'fields': ['relevant_illness', 'illness_details'],
             'classes': ['applicationillness', 'wide']}
         ),
        ('Employment history',
            {'fields': ['employer1_name', 'employer1_from', 'employer1_to',
                        'employer1_job', 'employer1_leaving', 'employer2_name',
                        'employer2_from', 'employer2_to', 'employer2_job',
                        'employer2_leaving'],
             'classes': ['wide'],
             'description': 'Please tell us about your past and current employers below (if applicable)'}
         ),
        ('References',
            {'fields': ['referee1_name', 'referee1_address', 'referee1_tel', 'referee1_mobile', 'referee1_email',
                        'referee2_name', 'referee2_address', 'referee2_tel', 'referee2_mobile', 'referee2_email'],
             'classes': ['wide'],
             'description': '''Please give the names and addresses,
             telephones numbers and email addresses and role or
             relationship of <strong>two</strong> people who know you
             well and who would be able to give a personal character reference.
             In addition we reserve the right to take up additional character
             references from any other individuals deemed necessary. <strong>One
             reference must be from a Church leader. The other reference should
             be from someone who has known you for more than 3 years.</strong>'''}
         ),
        ('Declarations (see note below)',
            {'fields': ['crime_declaration', 'crime_details'],
             'classes': ['wide'],
             'description': '''Note: The disclosure of an offence may not
                prohibit your appointment'''},
         ),
        (None,
            {'fields': ['court_declaration', 'court_details'],
             'classes': ['wide']}
         ),
        (None,
            {'fields': ['concern_declaration', 'concern_details'],
             'classes': ['wide']}
         ),
        (None,
            {'fields': ['allegation_declaration'],
             'classes': ['wide'],
             'description': '''If you answer yes to the following question
                we will need to discuss this with you'''}
         ),
        ('DBS checks',
            {'fields': ['dbs_number', 'dbs_update_service_id', 'dbs_check_consent'],
             'classes': ['wide'],
             'description': mark_safe("""
<h3>Important information, please read:</h3>

<p>You need to give permission for us to obtain a DBS check for you. Otherwise
we regret that we cannot proceed with your application.</p>

<p>If you have a current enhanced Disclosure and Barring Service check and have
signed up for the update system, and if you give permission for CCIW to look at
it, please enter the number and the update service ID below.</p>

<p>If we need a new DBS check for you, once your application form is received a
DBS application form will be sent to you, so please ensure your postal address
is up to date. The DBS form must be filled in and all instructions adhered to.
<b>By CCIW policy, failure to do so will mean that you will be unable to come on
camp.</b></p>

<p><b>Please also note</b> the instructions to sign up for the <b>update
service</b>. This will save you and everyone else a lot of time in subsequent
years. You will receive an e-mail from DBS with a reference number and at the
bottom of the e-mail are details of signing up for the update service. THIS MUST
BE DONE WITHIN 19 DAYS of the issue of the DBS. Otherwise after 3 years you will
have to fill in another DBS.</p> """)}
         ),
        ("Confirmation",
            {'fields': ('finished',),
             'classes': ('wide',),
             'description': """<div>By ticking the following box and pressing save, you confirm
             that:</div>
             <ol>
             <li>the information you have submitted is <strong>correct and complete</strong>,</li>
             <li>you have <strong>read and understood</strong> the relevant sections of the
             <a target="_blank" href="/officers/files/CCIW%20CPP.doc">camp manual</a>.</li>
             <li>you permit CCIW to store this information and the references that we will collect
             for as long as necessary.</li>
             </ol>
             <div>Your information will then be sent to the camp leader.  By leaving this
             box un-ticked, you can save what you have done so far and edit it later.</div>"""
             }
         ),
    ]

    camp_leader_application_fieldsets = [
        (None,
            {'fields': ['officer', 'date_submitted'],
             'classes': ['wide']}
         )] + camp_officer_application_fieldsets

    inlines = [QualificationInline]

    class Media:
        js = ['js/application_form.js']

    def get_fieldsets(self, request, obj=None):
        user = request.user
        if user is None or user.is_anonymous:
            # never get here normally
            return ()
        else:
            if user.can_manage_application_forms:
                return self.camp_leader_application_fieldsets
            else:
                return self.camp_officer_application_fieldsets

    def formfield_for_dbfield(self, db_field, **kwargs):
        if isinstance(db_field, ExplicitBooleanField):
            defaults = {'widget': widgets.ExplicitBooleanFieldSelect}
            defaults.update(kwargs)
            defaults.pop("request")
            return db_field.formfield(**defaults)
        return super(ApplicationAdmin, self).formfield_for_dbfield(db_field, **kwargs)

    def _force_no_add_another(self, request):
        if '_addanother' in request.POST:
            del request.POST['_addanother']

    def _force_user_val(self, request):
        user = request.user
        if not user.can_manage_application_forms:
            request.POST['officer'] = str(request.user.id)
        else:
            # The leader possibly forgot to set the 'user' box while submitting
            # their own application form.
            if request.POST.get('officer', '') == '':
                request.POST['officer'] = str(request.user.id)

    def _force_post_vals(self, request):
        request.POST = request.POST.copy()
        self._force_no_add_another(request)
        self._force_user_val(request)

    def change_view(self, request, obj_id):
        if request.method == "POST":
            self._force_post_vals(request)

        return super(ApplicationAdmin, self).change_view(request, obj_id)

    def has_change_permission(self, request, obj=None):
        # Normal users do not have change permission, unless they are editing
        # their own object.  For officers, this method will return False when
        # adding a new object (which we have to fix elsewhere), and for the case
        # of listing all objects (which is what we want)
        if (obj is not None and
                (obj.officer_id is not None and obj.officer_id == request.user.id)):
            return True
        return super(ApplicationAdmin, self).has_change_permission(request, obj)

    def _redirect(self, request, response):
        if '_continue' not in request.POST and response.has_header("Location"):
            location = request.GET.get('_redirect_to',
                                       urlresolvers.reverse('cciw-officers-applications'))
            response["Location"] = location
        return response

    def response_change(self, request, new_object):
        resp = super(ApplicationAdmin, self).response_change(request, new_object)
        return self._redirect(request, resp)

    def save_model(self, request, obj, form, change):
        super(ApplicationAdmin, self).save_model(request, obj, form, change)
        if obj.finished and obj.officer == request.user:
            # We clear out any unfinished application forms, as they will just
            # confuse the officer in future.  It is possible for an admin to be
            # editing an old form of their own, while a new form of their own is
            # still unfinished. So we filter on date_submitted.  If
            # date_submitted is NULL, the form has never been saved, so its fine
            # to delete.
            old = obj.officer.applications.filter(finished=False)
            old2 = old.filter(date_submitted__isnull=True)
            if obj.date_submitted is not None:
                old2 = old2 | old.filter(date_submitted__lt=obj.date_submitted)
            old2.delete()

    def save_related(self, request, form, formsets, change):
        from cciw.officers import email
        retval = super(ApplicationAdmin, self).save_related(request, form, formsets, change)
        email.send_application_emails(request, form.instance)
        return retval


class InvitationAdmin(admin.ModelAdmin):
    list_display = ['officer', 'camp', 'notes', 'date_added']
    list_filter = ['camp']
    search_fields = ['officer__first_name', 'officer__last_name', 'officer__username']

    def get_queryset(self, *args, **kwargs):
        return super(InvitationAdmin, self).get_queryset(*args, **kwargs).prefetch_related('camp__leaders')


class ReferenceAdmin(CampAdminPermissionMixin, admin.ModelAdmin):
    save_as = False
    list_display = ['referee_name', 'applicant_name', 'date_created']
    ordering = ['referee_name']
    search_fields = ['referee_name', 'referee__application__officer__last_name',
                     'referee__application__officer__first_name']
    date_hierarchy = 'date_created'
    raw_id_fields = ['referee']

    fieldsets = [
        (None,
            {'fields': ['referee_name',
                        'how_long_known',
                        'capacity_known',
                        'known_offences',
                        'known_offences_details',
                        'capability_children',
                        'character',
                        'concerns',
                        'comments',
                        'date_created',
                        'referee',
                        ],
             'classes': ['wide']}
         ),
    ]

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'known_offences':
            defaults = {'widget': widgets.ExplicitBooleanFieldSelect}
            defaults.update(kwargs)
            defaults.pop("request")
            return db_field.formfield(**defaults)
        return super(ReferenceAdmin, self).formfield_for_dbfield(db_field, **kwargs)

    def response_change(self, request, obj):
        # Little hack to allow popups for changing References
        if '_popup' in request.POST:
            return close_window_response()
        else:
            return super(ReferenceAdmin, self).response_change(request, obj)


class DBSCheckModelForm(forms.ModelForm):

    class Meta:
        widgets = {
            'officer': officer_autocomplete_widget(),
        }


class DBSCheckAdmin(RerouteResponseAdminMixin, admin.ModelAdmin):

    form = DBSCheckModelForm

    search_fields = ['officer__first_name', 'officer__last_name', 'dbs_number']
    list_display = ['first_name', 'last_name', 'dbs_number', 'completed',
                    'requested_by', 'registered_with_dbs_update', 'dbs_update_service_id']
    list_display_links = ('first_name', 'last_name', 'dbs_number')
    list_filter = ['requested_by', 'registered_with_dbs_update', 'check_type']
    ordering = ('-completed',)
    date_hierarchy = 'completed'

    def first_name(self, obj):
        return obj.officer.first_name
    first_name.admin_order_field = 'officer__first_name'

    def last_name(self, obj):
        return obj.officer.last_name
    last_name.admin_order_field = 'officer__last_name'


class DBSActionLogModelForm(forms.ModelForm):

    class Meta:
        widgets = {
            'officer': officer_autocomplete_widget(),
            'user': officer_autocomplete_widget(),
        }


class DBSActionLogAdmin(admin.ModelAdmin):

    form = DBSActionLogModelForm

    search_fields = ('officer__first_name', 'officer__last_name')
    list_display = ['action_type', 'first_name', 'last_name', 'timestamp', 'user']
    list_display_links = ['action_type']
    list_filter = ['action_type']
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'

    def first_name(self, obj):
        return obj.officer.first_name
    first_name.admin_order_field = 'officer__first_name'

    def last_name(self, obj):
        return obj.officer.last_name
    last_name.admin_order_field = 'officer__last_name'


admin.site.register(Application, ApplicationAdmin)
admin.site.register(Invitation, InvitationAdmin)
admin.site.register(Reference, ReferenceAdmin)
admin.site.register(DBSCheck, DBSCheckAdmin)
admin.site.register(DBSActionLog, DBSActionLogAdmin)
admin.site.register(QualificationType)


# Hack the Group admin so that we can edit users belonging to a group
Membership = Group.user_set.through


class MembershipAdminForm(forms.ModelForm):

    class Meta:
        widgets = {
            'user': officer_autocomplete_widget(),
        }


class MembershipInline(admin.TabularInline):
    model = Membership
    form = MembershipAdminForm
    extra = 0

GroupAdmin.inlines = list(GroupAdmin.inlines) + [MembershipInline]
