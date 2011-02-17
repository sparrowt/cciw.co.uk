from django.conf.urls.defaults import patterns, url
from django.views.generic.base import TemplateView

urlpatterns = patterns('cciw.officers.views',
    (r'^$', 'index'),
    (r'^applications/$', 'applications'),
    (r'^view-application/$', 'view_application'),
    (r'^update-email/(?P<username>.*)/$', 'update_email'),
    (r'^leaders/$', 'leaders_index'),
    (r'^leaders/applications/(?P<year>\d{4})/(?P<number>\d+)/$', 'manage_applications'),
    (r'^leaders/references/(?P<year>\d{4})/(?P<number>\d+)/$', 'manage_references'),
    (r'^leaders/officer-list/(?P<year>\d{4})/(?P<number>\d+)/$', 'officer_list'),
    (r'^leaders/remove-officer/(?P<year>\d{4})/(?P<number>\d+)/$', 'remove_officer'),
    (r'^leaders/add-officers/(?P<year>\d{4})/(?P<number>\d+)/$', 'add_officers'),
    (r'^leaders/officer-details/$', 'officer_details'),
    (r'^leaders/update-officer/$', 'update_officer'),
    (r'^leaders/resend-email/$', 'resend_email'),
    (r'^leaders/request-reference/$', 'request_reference'),
    (r'^leaders/reference/(?P<ref_id>\d+)/$', 'view_reference'),
    (r'^leaders/edit-reference/(?P<ref_id>\d+)/$', 'edit_reference_form_manually'),
    (r'^leaders/stats/(?P<year>\d{4})/$', 'stats'),
    (r'^ref/(?P<ref_id>\d+)-(?P<prev_ref_id>\d*)-(?P<hash>.*)/$', 'create_reference_form'),
    (r'^ref/thanks/$', 'create_reference_thanks'),
    (r'^add-officer/$', 'create_officer'),
    (r'^files/(.*)$', 'officer_files'),
    url(r'^info/$', TemplateView.as_view(template_name='cciw/officers/info.html'), name="cciw.officers.views.info"),
)
