# flake8: noqa
# isort:skip_file

# Settings file
import json
import os
import socket
import sys

hostname = socket.gethostname()

basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ../
parentdir = os.path.dirname(basedir)
SECRETS = json.load(open(os.path.join(basedir, 'config', 'secrets.json')))

PROJECT_ROOT = basedir
HOME_DIR = os.environ['HOME']
BASE_DIR = basedir

CHECK_DEPLOY = 'manage.py check --deploy' in ' '.join(sys.argv)
if CHECK_DEPLOY:
    LIVEBOX = True
    DEVBOX = False
else:
    LIVEBOX = hostname.startswith('cciw')
    DEVBOX = not LIVEBOX


if LIVEBOX and not CHECK_DEPLOY:
    LOG_DIR = os.path.join(HOME_DIR, "logs")  # See fabfile
else:
    LOG_DIR = os.path.join(parentdir, "logs")


if LIVEBOX:
    SECRET_KEY = SECRETS['PRODUCTION_SECRET_KEY']
else:
    # We don't want any SECRET_KEY in a file in a VCS, and we also want the
    # SECRET_KEY to be to be the same as for production so that we can use
    # downloaded session database if needed.
    SECRET_KEY = SECRETS['PRODUCTION_SECRET_KEY']

WEBSERVER_RUNNING = 'mod_wsgi' in sys.argv
TESTS_RUNNING = 'test' in sys.argv

# == MISC ==

if DEVBOX:
    def show_toolbar(request):
        if request.is_ajax():
            return False
        if '-stats' in request.get_full_path():
            # debug toolbar slows down the stats pages for some reason
            return False
        return True

    DEBUG = True
    DEBUG_TOOLBAR_CONFIG = {
        'DISABLE_PANELS': set(['debug_toolbar.panels.redirects.RedirectsPanel']),
        'SHOW_TOOLBAR_CALLBACK': 'cciw.settings.show_toolbar',
    }
else:
    DEBUG = False

INTERNAL_IPS = ('127.0.0.1',)

LANGUAGE_CODE = 'en-gb'

SITE_ID = 1
PRODUCTION_DOMAIN = 'www.cciw.co.uk'

ROOT_URLCONF = 'cciw.urls'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': f'unix:{HOME_DIR}/memcached.sock',
        'KEY_PREFIX': 'cciw.co.uk',
    }
} if LIVEBOX else {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}


TIME_ZONE = "Europe/London"

USE_I18N = False
USE_TZ = True

LOGIN_URL = "/officers/"

ALLOWED_HOSTS = [".cciw.co.uk", "cciw.local"]

INSTALLED_APPS = [
    # 3rd party
    'dal',
    'dal_select2',  # dal and dal_select2 need to come before contrib.admin
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',

    # Ours
    'cciw.accounts',
    'cciw.cciwmain.apps.CciwmainConfig',
    'cciw.sitecontent',
    'cciw.officers',
    'cciw.utils',
    'cciw.bookings',
    'cciw.mail',
    'cciw.contact_us',

    # 3rd party
    'django.contrib.messages',
    'paypal.standard.ipn',
    'django.contrib.humanize',
    'mptt',
    'sekizai',
    'sorl.thumbnail',
    'wiki',
    'wiki.plugins.attachments',
    'wiki.plugins.notifications',
    'wiki.plugins.images',
    'wiki.plugins.macros',
    'django_nyt',
    'compressor',
    'django_countries',
    'raven.contrib.django.raven_compat',
    'anymail',
    'mailer',
    'captcha',
]

if not (LIVEBOX and WEBSERVER_RUNNING):
    # Don't want the memory overhead of these if we are serving requests
    INSTALLED_APPS += [
        'django.contrib.staticfiles',
    ]

if DEVBOX and DEBUG:
    INSTALLED_APPS += [
        'django.contrib.admindocs',
        'debug_toolbar',
    ]


SILENCED_SYSTEM_CHECKS = [
    '1_6.W001',
    '1_8.W001',
    'urlchecker.W001',
    'urlchecker.W003',
]

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    'cciw.auth.CciwAuthBackend',
]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,

    'root': {
        'level': 'WARNING',
        'handlers': ['sentry'],
    },

    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },

    'formatters': {
        'django.server': {
            '()': 'django.utils.log.ServerFormatter',
            'format': '[%(server_time)s] %(message)s',
        },
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s '
                      '%(process)d %(thread)d %(message)s'
        },
    },

    'handlers': {
        'django.server': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'django.server',
        },
        'sentry': {
            'level': 'ERROR',
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
        },
        'console': {
            'level': 'INFO',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': 'INFO',
            'class': 'cloghandler.ConcurrentRotatingFileHandler',
            'formatter': 'verbose',
            'filename': os.path.join(LOG_DIR, 'info_cciw_django.log'),
            'maxBytes': 1000000,
            'backupCount': 5,
        },
        'paypal_debug': {
            'level': 'DEBUG',
            'class': 'cloghandler.ConcurrentRotatingFileHandler',
            'formatter': 'verbose',
            'filename': os.path.join(LOG_DIR, 'paypal_debug_cciw_django.log'),
            'maxBytes': 1000000,
            'backupCount': 5,
        },
    },

    'loggers': {
        'django.db.backends': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'django.server': {
            'handlers': ['django.server'],
            'level': 'INFO',
            'propagate': False,
        },
        'raven': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
        'sentry.errors': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
        'cciw.mail.mailgun': {
            'level': 'INFO',
            'handlers': ['file'],
            'propagate': False,
        },
        'paypal' : {
            'level': 'DEBUG',
            'handlers': ['paypal_debug'],
            'propagate': False,
        },
    },
}

# For large attachments to emails sent through mailgun endpoint:
DATA_UPLOAD_MAX_MEMORY_SIZE = 15 * 1024 * 1024


PASSWORD_RESET_TIMEOUT_DAYS = 7

# == DATABASE ==

if LIVEBOX:
    DB_NAME = SECRETS['PRODUCTION_DB_NAME']
    DB_USER = SECRETS['PRODUCTION_DB_USER']
    DB_PASSWORD = SECRETS['PRODUCTION_DB_PASSWORD']
    DB_PORT = SECRETS['PRODUCTION_DB_PORT']
else:
    DB_NAME = 'cciw'
    DB_USER = 'cciw'
    DB_PASSWORD = 'foo'  # Need to sync with Vagrantfile
    DB_PORT = '5432'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': DB_NAME,
        'USER': DB_USER,
        'PASSWORD': DB_PASSWORD,
        'PORT': DB_PORT,
        'HOST': 'localhost',
        'CONN_MAX_AGE': 30,
    }
}

# == SESSIONS ==

if LIVEBOX:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.BCryptPasswordHasher',
    'django.contrib.auth.hashers.SHA1PasswordHasher',
    'django.contrib.auth.hashers.MD5PasswordHasher',
    'django.contrib.auth.hashers.CryptPasswordHasher',
)

# == TEMPLATES ==

TEMPLATE_CONTEXT_PROCESSORS = [  # backwards compat for django-wiki
    'django.template.context_processors.request',
    'django.contrib.auth.context_processors.auth',
    'django.template.context_processors.media',
    'django.template.context_processors.static',
    'django.template.context_processors.request',
    'django.template.context_processors.tz',
    "django.contrib.messages.context_processors.messages",
    'cciw.cciwmain.common.standard_processor',
    'sekizai.context_processors.sekizai',
] + ([] if not DEBUG else ['django.template.context_processors.debug'])

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            basedir + r'/templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': TEMPLATE_CONTEXT_PROCESSORS,
            'debug': DEBUG,
        },
    },
]

# == EMAIL ==

# Try to ensure we don't send mail via Mailgun when testing.

# First step: set EMAIL_BACKEND correctly. This deals with mail sent via
# django's send_mail.

# However, we also use Mailgun API directly for some tasks (some sending and all
# receiving). So we patch up outgoing emails in cciw.mail.mailgun to use the
# sandbox domain when in development/testing.

MAILGUN_API_KEY = SECRETS['MAILGUN_API_KEY']
if LIVEBOX:
    MAILGUN_DOMAIN = "cciw.co.uk"
else:
    MAILGUN_DOMAIN = SECRETS['MAILGUN_SANDBOX_DOMAIN']

# This address has to be set up as an authorized recipient for the sandbox
# account:
MAILGUN_TEST_RECEIVER = SECRETS['MAILGUN_TEST_RECEIVER']


EMAIL_RECIPIENTS = SECRETS["EMAIL_RECIPIENTS"]
SERVER_EMAIL = "CCIW website <noreply@cciw.co.uk>"
DEFAULT_FROM_EMAIL = SERVER_EMAIL
ADMINS = [
    ('webmaster', email)
    for email in EMAIL_RECIPIENTS['WEBMASTER']
]


if LIVEBOX:
    # We currently send using SMTP (amazon SES), while we receive using mailgun
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = SECRETS["SMTP_HOST"]
    EMAIL_PORT = SECRETS["SMTP_PORT"]
    EMAIL_HOST_USER = SECRETS["SMTP_USERNAME"]
    EMAIL_HOST_PASSWORD = SECRETS["SMTP_PASSWORD"]
    EMAIL_USE_TLS = SECRETS["SMTP_USE_TLS"]
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# django-mailer - used for some things where we need a queue. It is not used as
# default backend via EMAIL_BACKEND, but by calling mailer.send_mail explicitly,
# usally aliased as queued_mail.send_mail. We also can test this is being used
# e.g. in TestBaseMixin
MAILER_EMAIL_BACKEND = EMAIL_BACKEND

ANYMAIL = {
    "MAILGUN_API_KEY": MAILGUN_API_KEY,
}

if TESTS_RUNNING:
    # This doesn't seem to take effect, see TestBaseMixin
    EMAIL_BACKEND = "cciw.mail.tests.TestMailBackend"
    MAILER_EMAIL_BACKEND = EMAIL_BACKEND

EMAIL_ENCRYPTION_PUBLIC_KEYS = SECRETS["EMAIL_ENCRYPTION_PUBLIC_KEYS"]

# == MAILING LISTS ==


# == SECURE DOWNLOADS ==

SECURE_DOWNLOAD_URL_BASE = "/protected/"  # See nginx conf

# == MIDDLEWARE ==

_MIDDLEWARE = [
    (LIVEBOX,    "cciw.middleware.http.webfaction_fixes"),
    (True, 'django.middleware.security.SecurityMiddleware'),
    (True,       "django.middleware.gzip.GZipMiddleware"),
    (DEVBOX and DEBUG, "debug_toolbar.middleware.DebugToolbarMiddleware"),
    (True,       "django.contrib.sessions.middleware.SessionMiddleware"),
    (True,       "django.middleware.common.CommonMiddleware"),
    (True,       'django.middleware.csrf.CsrfViewMiddleware'),
    (DEVBOX and DEBUG, "cciw.middleware.debug.debug_middleware"),
    (True,       "django.contrib.auth.middleware.AuthenticationMiddleware"),
    (True,       "django.contrib.messages.middleware.MessageMiddleware"),
    (True,       'django.middleware.clickjacking.XFrameOptionsMiddleware'),
    (True,       "cciw.middleware.auth.private_wiki"),
    (True,       "cciw.bookings.middleware.booking_token_login"),
    (True,       "cciw.middleware.threadlocals.thread_locals"),
]

MIDDLEWARE = tuple([val for (test, val) in _MIDDLEWARE if test])

# == MESSAGES ==

MESSAGE_STORAGE = "django.contrib.messages.storage.fallback.FallbackStorage"

# == MEDIA ==

MEDIA_ROOT = os.path.join(parentdir, 'usermedia')
STATIC_ROOT = os.path.join(parentdir, 'static')

MEDIA_URL = '/usermedia/'
STATIC_URL = '/static/'

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
]

FILE_UPLOAD_MAX_MEMORY_SIZE = 262144

COMPRESS_PRECOMPILERS = [
    ('text/less', 'lessc {infile} {outfile}'),
]

####################

# CCIW SPECIFIC SETTINGS AND CONSTANTS

# This 'from' email address is used on emails where the user
# might want to press 'reply' and get to a person e.g. for
# booking issues
WEBMASTER_FROM_EMAIL = "webmaster@cciw.co.uk"

BOOKING_FORMS_EMAILS = EMAIL_RECIPIENTS["BOOKING_FORMS"]
BOOKING_SECRETARY_EMAILS = EMAIL_RECIPIENTS["BOOKING_SECRETARY"]
GENERAL_CONTACT_EMAILS = EMAIL_RECIPIENTS["GENERAL_CONTACT"]
SECRETARY_EMAILS = EMAIL_RECIPIENTS["SECRETARY"]
WEBMASTER_EMAILS = EMAIL_RECIPIENTS["WEBMASTER"]

BOOKINGFORMDIR = "downloads"

ESV_KEY = 'IP'
DBS_VALID_FOR = 365 * 3  # We consider a DBS check valid for 3 years
GROUPS_CONFIG_FILE = os.path.join(basedir, 'config', 'groups.yaml')

# Referenced from style.less
COLORS_LESS_DIR = "cciw/cciwmain/static/"
COLORS_LESS_FILE = "css/camp_colors.less"


# == Bookings ==
BOOKING_EMAIL_VERIFY_TIMEOUT_DAYS = 3
BOOKING_SESSION_TIMEOUT_SECONDS = 60 * 60 * 24 * 14  # 2 weeks
BOOKING_FULL_PAYMENT_DUE_DAYS = 3 * 30  # 3 months
BOOKING_FULL_PAYMENT_DUE_TIME = "3 months"  # for display purposes
BOOKING_EMAIL_REMINDER_FREQUENCY_DAYS = 3

# == DBS ==

# This should be a dictionary with 'name', 'email' and 'organisation' keys:
EXTERNAL_DBS_OFFICER = SECRETS['EXTERNAL_DBS_OFFICER']


# == Third party ==

# Wiki
WIKI_ATTACHMENTS_EXTENSIONS = [
    'pdf', 'doc', 'odt', 'docx', 'txt',
    'svg', 'png', 'jpg', 'jpeg',
]
WIKI_CHECK_SLUG_URL_AVAILABLE = False  # it checks it incorrectly for our situation

# Mailchimp
if LIVEBOX:
    MAILCHIMP_API_KEY = SECRETS['PRODUCTION_MAILCHIMP_API_KEY']
    MAILCHIMP_NEWSLETTER_LIST_ID = SECRETS['PRODUCTION_MAILCHIMP_NEWSLETTER_LIST_ID']
    MAILCHIMP_URL_BASE = SECRETS['PRODUCTION_MAILCHIMP_URL_BASE']
else:
    MAILCHIMP_API_KEY = SECRETS['DEV_MAILCHIMP_API_KEY']
    MAILCHIMP_NEWSLETTER_LIST_ID = SECRETS['DEV_MAILCHIMP_NEWSLETTER_LIST_ID']
    MAILCHIMP_URL_BASE = SECRETS['DEV_MAILCHIMP_URL_BASE']

# PayPal
if LIVEBOX:
    PAYPAL_TEST = False
    PAYPAL_RECEIVER_EMAIL = SECRETS['PRODUCTION_PAYPAL_RECEIVER_EMAIL']
else:
    PAYPAL_TEST = True
    PAYPAL_RECEIVER_EMAIL = SECRETS['DEV_PAYPAL_RECEIVER_EMAIL']

PAYPAL_BUY_BUTTON_IMAGE = "https://www.paypalobjects.com/en_US/GB/i/btn/btn_buynowCC_LG.gif"

# Raven
if LIVEBOX:
    RAVEN_CONFIG = SECRETS['PRODUCTION_RAVEN_CONFIG']
else:
    RAVEN_CONFIG = {}

# Google analytics
if LIVEBOX:
    GOOGLE_ANALYTICS_ACCOUNT = SECRETS['GOOGLE_ANALYTICS_ACCOUNT']
else:
    GOOGLE_ANALYTICS_ACCOUNT = ''

CAPTCHA_FONT_PATH = os.path.join(BASE_DIR, "cciw", "cciwmain", "static", "fonts", "Jurassic_Park.ttf")
if not os.path.exists(CAPTCHA_FONT_PATH):
    raise ValueError(f"CAPTCHA_FONT_PATH is incorrect - file missing {CAPTCHA_FONT_PATH}")
CAPTCHA_FONT_SIZE = 60   # Jurassic Park font is really small for some reason
CAPTCHA_LETTER_ROTATION = (-30, 30)

if TESTS_RUNNING:
    CAPTCHA_TEST_MODE = True
