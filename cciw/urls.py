from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin
import cciw.officers.views
import mailer.admin

handler404 = 'cciw.cciwmain.views.handler404'

urlpatterns = patterns('',
    # Plug in the password reset views
    (r'^admin/password_reset/$', 'django.contrib.auth.views.password_reset'),
    (r'^admin/password_reset/done/$', 'django.contrib.auth.views.password_reset_done'),
    (r'^reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$', 'django.contrib.auth.views.password_reset_confirm'),
    (r'^reset/done/$', 'django.contrib.auth.views.password_reset_complete'),
    # Normal views
    (r'^admin/', include(admin.site.urls)),
    (r'^officers/', include('cciw.officers.urls'))
)

if settings.DEBUG:
    import django
    import os
    django_root = os.path.dirname(django.__file__)
    urlpatterns += patterns('',
                            (r'^validator/', include('output_validator.urls')),
                            (r'^admin_doc/', include('django.contrib.admindocs.urls')),
                            (r'^usermedia/(?P<path>.*)$', 'django.contrib.staticfiles.views.serve',
                             {'document_root': settings.MEDIA_ROOT}),
                            (r'^file/(?P<path>.*)$', 'django.contrib.staticfiles.views.serve',
                             {'document_root': settings.SECUREDOWNLOAD_SERVE_ROOT}),
    )

    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()

urlpatterns = urlpatterns + patterns('',
    (r'', include('cciw.cciwmain.urls'))
)
