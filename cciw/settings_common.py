# Django settings for cciw project.



INTERNAL_IPS = ('127.0.0.1')

ADMINS = (
    ('Luke Plant', 'L.Plant.98@cantab.net'),
)

MANAGERS = ADMINS

LANGUAGE_CODE = 'en-gb'

DATABASE_ENGINE = 'postgresql'

SITE_ID = 1


# Make this unique, and don't share it with anybody.
SECRET_KEY = '__=9o22)i0c=ci+9u$@g77tvdsg9y-wu6v6#f4iott(@jgwig+'

CACHE_MIDDLEWARE_SECONDS = 200

CSRF_MIDDLEWARE_SECRET = SECRET_KEY

ROOT_URLCONF = 'cciw.urls'

VALIDATOR_APP_VALIDATORS = {
#    'text/html': '/usr/bin/validate',
    'text/html': '/home/luke/bin/myvalidate.sh',
    'application/xml+xhtml': '/home/luke/bin/myvalidate.sh',
}

VALIDATOR_APP_IGNORE_PATHS = (
   
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'cciw.cciwmain',
)

TIME_ZONE = "Europe/London"
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "cciw.cciwmain.common.standard_processor",
)
