# -*- coding: utf-8 -*-

import os
# Importing GeoNode should only be used for locating path,
# not accessing a settings file there.
from geonode import __file__ as geonode_path
# dj-database-url is used for passing a single DB connection string.
import dj_database_url


def str2bool(v):
        return v.lower() in ("yes", "true", "t", "1")

SITENAME = '{{ project_name }}'

DEBUG = str2bool(os.getenv('DEBUG', 'False'))
TEMPLATE_DEBUG = str2bool(os.getenv('TEMPLATE_DEBUG', 'False'))

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
GEONODE_ROOT = os.path.abspath(os.path.dirname(geonode_path))

SECRET_KEY = os.getenv('SECRET_KEY', "{{ secret_key }}")

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///development.db')
DATABASES = {'default': 
              dj_database_url.parse(DATABASE_URL, conn_max_age=600),
            }


MANAGERS = ADMINS = os.getenv('ADMINS', [])

SITE_ID = int(os.getenv('SITE_ID', '1'))

# TODO: env var - default True
USE_I18N = True
# TODO: env var - default True
USE_L10N = True

TIME_ZONE = os.getenv('TIME_ZONE', "America/Chicago")
LANGUAGE_CODE = os.getenv('LANGUAGE_CODE', "en-us")

# Underscore at the beginning added to represent a private variable.
# should not be used in the application.
_DEFAULT_LANGUAGES = (
    ('en', 'English'),
    ('es', 'Spanish'),
    ('it', 'Italian'),
    ('fr', 'French'),
    ('de', 'German'),
    ('el', 'Greek'),
    ('id', 'Indonesian'),
    ('zh', 'Chinese'),
)

LANGUAGES = os.getenv('LANGUAGES', _DEFAULT_LANGUAGES)

# TODO: env var
WSGI_APPLICATION = "{{ project_name }}.wsgi.application"

# These are for user-uploaded content.
# TODO: env var
MEDIA_ROOT = os.path.join(PROJECT_ROOT, "media")
# TODO: env var
MEDIA_URL = "/media/"

# These are for site static media (e.g. CSS and JS)
# This one is where static content is collected to.
# TODO: env var
STATIC_ROOT = os.path.join(PROJECT_ROOT, "static_root")
# TODO: env var
STATIC_URL = "/static/"


# TODO: env var
STATICFILES_DIRS = [
    os.path.join(PROJECT_ROOT, "static"),
    os.path.join(GEONODE_ROOT, "static"),
]

# TODO: env var
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# Template stuff   
# TODO: env var
TEMPLATE_LOADERS = [
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",    
]

# TODO: env var
TEMPLATE_CONTEXT_PROCESSORS = [
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    "django.contrib.messages.context_processors.messages",
]

# TODO: env var
TEMPLATE_DIRS = [
    os.path.join(PROJECT_ROOT, "templates"),
    os.path.join(GEONODE_ROOT, "templates"),
]


# TODO: env var
ROOT_URLCONF = "{{ project_name }}.urls"



# TODO: env var
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.sitemaps',
    'django.contrib.staticfiles',
    'django.contrib.messages',

    'django_extensions',
    'registration',
    'profiles',
    'avatar',
    'dialogos',
    'agon_ratings',
    'south',

    'geonode.core',
    'geonode.maps',
    'geonode.proxy',
]

#
# GeoNode specific settings
#

# Setting a custom test runner to avoid running the tests for some problematic 3rd party apps
TEST_RUNNER= os.getenv('TEST_RUNNER', 'geonode.testrunner.GeoNodeTestRunner')

# TODO: env var
NOSE_ARGS = [
      '--verbosity=2',
      '--cover-erase',
      '--nocapture',
      '--with-coverage',
      '--cover-package=geonode',
      '--cover-inclusive',
      '--cover-tests',
      '--detailed-errors',
      '--with-xunit',

# This is very beautiful/usable but requires: pip install rudolf
#      '--with-color',

# The settings below are useful while debugging test failures or errors

#      '--failed',
#      '--pdb-failures',
#      '--stop',
#      '--pdb',
      ]
# Google API Key valid for localhost. This is used for the Google Earth API
# TODO: env var
GOOGLE_API_KEY = "ABQIAAAAkofooZxTfcCv9Wi3zzGTVxTnme5EwnLVtEDGnh-lFVzRJhbdQhQgAhB1eT_2muZtc0dl-ZSWrtzmrw"

# Needed to override serving of Javascript files
# TODO: env var
GEONODE_CLIENT_LOCATION = STATIC_URL + "geonode/"

# TODO: env var
TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "geonode.maps.context_processors.resource_urls",
)


# The FULLY QUALIFIED url to the GeoServer instance for this GeoNode.
GEOSERVER_BASE_URL = os.getenv('GEOSERVER_BASE_URL',
                               "http://localhost:8001/geoserver-geonode-dev/")

# The username and password for a user that can add and edit layer details on GeoServer

# TODO: env var
GEOSERVER_CREDENTIALS = "geoserver_admin", SECRET_KEY

# TODO: env var
AUTHENTICATION_BACKENDS = ('geonode.core.auth.GranularBackend',)

# Where should newly created maps be focused?
# TODO: Allow overriding with an env var
# TODO: env var
DEFAULT_MAP_CENTER = (0, 0)

# How tightly zoomed should newly created maps be?
# 0 = entire world;
# maximum zoom is between 12 and 15 (for Google Maps, coverage varies by area)
# TODO: env var
DEFAULT_MAP_ZOOM = 0

# TODO: env var
DEFAULT_LAYER_SOURCE = {
    "ptype":"gxp_wmscsource",
    "url":"/geoserver/wms",
    "restUrl": "/gs/rest"
}

# TODO: env var
MAP_BASELAYERS = [{
    "source": {"ptype": "gx_olsource"},
    "type":"OpenLayers.Layer",
    "args":["No background"],
    "visibility": False,
    "fixed": True,
    "group":"background"
  },{
    "source": { "ptype":"gx_olsource"},
    "type":"OpenLayers.Layer.OSM",
    "args":["OpenStreetMap"],
    "visibility": True,
    "fixed": True,
    "group":"background"
  },{
    "source": {"ptype":"gx_olsource"},
    "type":"OpenLayers.Layer.WMS",
    "group":"background",
    "visibility": False,
    "fixed": True,
    "args":[
      "bluemarble",
      "http://maps.opengeo.org/geowebcache/service/wms",
      {
        "layers":["bluemarble"],
        "format":"image/png",
        "tiled": True,
        "tilesOrigin":[-20037508.34,-20037508.34]
      },
      {"buffer":0}
    ]

}]


_DEFAULT_LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'null': {
            'level':'DEBUG',
            'class':'django.utils.log.NullHandler',
        },
        'console':{
            'level':'DEBUG',
            'class':'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file':{
            'level':'DEBUG',
            'class' : 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'filename': 'yemendata.log',
            'maxBytes': '1024',
            'backupCount': '3',
         },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers':['null'],
            'propagate': True,
            'level':'INFO',
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'geonode': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    }
}

LOGGING = os.getenv('LOGGING', _DEFAULT_LOGGING)


def get_user_url(u):
    from django.contrib.sites.models import Site
    s = Site.objects.get_current()
    return "http://" + s.domain + "/profiles/" + u.username

# TODO: Allow overriding with an env var
ABSOLUTE_URL_OVERRIDES = {
    'auth.user': get_user_url
}


# TODO: Allow overriding with an env var
AUTH_PROFILE_MODULE = 'maps.Contact'
# TODO: Allow overriding with an env var
REGISTRATION_OPEN = True
# TODO: Allow overriding with an env var
ACCOUNT_ACTIVATION_DAYS = 7

# TODO: Allow overriding with an env var
DB_DATASTORE = True

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', ['localhost', ])
