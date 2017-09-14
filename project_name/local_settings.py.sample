# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright (C) 2017 OSGeo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################

# Django settings for the GeoNode project.
import os
from {{ project_name}}.settings import *

#
# General Django development settings
#
POSTGIS_VERSION = (2, 0, 7)

DATABASES = {
    'default': {
         'ENGINE': 'django.db.backends.postgresql_psycopg2',
         'NAME': 'geonode',
         'USER': 'geonode',
         'PASSWORD': 'geonode',
         'CONN_TOUT': 900,
     },
    # vector datastore for uploads
    'datastore' : {
        #'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'ENGINE': '', # Empty ENGINE name disables
        'NAME': 'geonode',
        'USER' : 'geonode',
        'PASSWORD' : 'geonode',
        'HOST' : 'localhost',
        'PORT' : '5432',
        'CONN_TOUT': 900,
    }
}

GEOSERVER_LOCATION = os.getenv(
    'GEOSERVER_LOCATION', 'http://localhost:8080/geoserver/'
)

GEOSERVER_PUBLIC_LOCATION = os.getenv(
#    'GEOSERVER_PUBLIC_LOCATION', '{}/geoserver/'.format(SITEURL)
    'GEOSERVER_LOCATION', 'http://localhost:8080/geoserver/'
)

OGC_SERVER_DEFAULT_USER = os.getenv(
    'GEOSERVER_ADMIN_USER', 'admin'
)

OGC_SERVER_DEFAULT_PASSWORD = os.getenv(
    'GEOSERVER_ADMIN_PASSWORD', 'geoserver'
)

# OGC (WMS/WFS/WCS) Server Settings
OGC_SERVER = {
    'default': {
        'BACKEND': 'geonode.geoserver',
        'LOCATION': GEOSERVER_LOCATION,
        'LOGIN_ENDPOINT': 'j_spring_oauth2_geonode_login',
        'LOGOUT_ENDPOINT': 'j_spring_oauth2_geonode_logout',
        # PUBLIC_LOCATION needs to be kept like this because in dev mode
        # the proxy won't work and the integration tests will fail
        # the entire block has to be overridden in the local_settings
        'PUBLIC_LOCATION': GEOSERVER_PUBLIC_LOCATION,
        'USER' : OGC_SERVER_DEFAULT_USER,
        'PASSWORD' : OGC_SERVER_DEFAULT_PASSWORD,
        'MAPFISH_PRINT_ENABLED' : True,
        'PRINT_NG_ENABLED' : True,
        'GEONODE_SECURITY_ENABLED' : True,
        'GEOGIG_ENABLED' : False,
        'WMST_ENABLED' : False,
        'BACKEND_WRITE_ENABLED': True,
        'WPS_ENABLED' : False,
        'LOG_FILE': '%s/geoserver/data/logs/geoserver.log' % os.path.abspath(os.path.join(PROJECT_ROOT, os.pardir)),
        # Set to dictionary identifier of database containing spatial data in DATABASES dictionary to enable
        'DATASTORE': '', #'datastore',
        'PG_GEOGIG': False,
        'TIMEOUT': 3600  # number of seconds to allow for HTTP requests
    }
}

# If you want to enable Mosaics use the following configuration
#UPLOADER = {
##    'BACKEND': 'geonode.rest',
#    'BACKEND': 'geonode.importer',
#    'OPTIONS': {
#        'TIME_ENABLED': True,
#        'MOSAIC_ENABLED': True,
#        'GEOGIG_ENABLED': False,
#    }
#}


CATALOGUE = {
    'default': {
        # The underlying CSW implementation
        # default is pycsw in local mode (tied directly to GeoNode Django DB)
        'ENGINE': 'geonode.catalogue.backends.pycsw_local',
        # pycsw in non-local mode
        # 'ENGINE': 'geonode.catalogue.backends.pycsw_http',
        # GeoNetwork opensource
        # 'ENGINE': 'geonode.catalogue.backends.geonetwork',
        # deegree and others
        # 'ENGINE': 'geonode.catalogue.backends.generic',

        # The FULLY QUALIFIED base url to the CSW instance for this GeoNode
        'URL': '%s/catalogue/csw' % SITEURL,
        # 'URL': 'http://localhost:8080/geonetwork/srv/en/csw',
        # 'URL': 'http://localhost:8080/deegree-csw-demo-3.0.4/services',

        # login credentials (for GeoNetwork)
        'USER': 'admin',
        'PASSWORD': 'admin',
        'ALTERNATES_ONLY': True,
    }
}

# pycsw settings
PYCSW = {
    # pycsw configuration
    'CONFIGURATION': {
        # uncomment / adjust to override server config system defaults
        # 'server': {
        #    'maxrecords': '10',
        #    'pretty_print': 'true',
        #    'federatedcatalogues': 'http://catalog.data.gov/csw'
        # },
        'metadata:main': {
            'identification_title': 'GeoNode Catalogue',
            'identification_abstract': 'GeoNode is an open source platform' \
            ' that facilitates the creation, sharing, and collaborative use' \
            ' of geospatial data',
            'identification_keywords': 'sdi, catalogue, discovery, metadata,' \
            ' GeoNode',
            'identification_keywords_type': 'theme',
            'identification_fees': 'None',
            'identification_accessconstraints': 'None',
            'provider_name': 'Organization Name',
            'provider_url': SITEURL,
            'contact_name': 'Lastname, Firstname',
            'contact_position': 'Position Title',
            'contact_address': 'Mailing Address',
            'contact_city': 'City',
            'contact_stateorprovince': 'Administrative Area',
            'contact_postalcode': 'Zip or Postal Code',
            'contact_country': 'Country',
            'contact_phone': '+xx-xxx-xxx-xxxx',
            'contact_fax': '+xx-xxx-xxx-xxxx',
            'contact_email': 'Email Address',
            'contact_url': 'Contact URL',
            'contact_hours': 'Hours of Service',
            'contact_instructions': 'During hours of service. Off on ' \
            'weekends.',
            'contact_role': 'pointOfContact',
        },
        'metadata:inspire': {
            'enabled': 'true',
            'languages_supported': 'eng,gre',
            'default_language': 'eng',
            'date': 'YYYY-MM-DD',
            'gemet_keywords': 'Utility and governmental services',
            'conformity_service': 'notEvaluated',
            'contact_name': 'Organization Name',
            'contact_email': 'Email Address',
            'temp_extent': 'YYYY-MM-DD/YYYY-MM-DD',
        }
    }
}

# Default preview library
LAYER_PREVIEW_LIBRARY = 'geoext'
#LAYER_PREVIEW_LIBRARY = 'leaflet'
#LEAFLET_CONFIG = {
#    'TILES': [
#        # Find tiles at:
#        # http://leaflet-extras.github.io/leaflet-providers/preview/
#
#        # Map Quest
#        ('Map Quest',
#         'http://otile4.mqcdn.com/tiles/1.0.0/osm/{z}/{x}/{y}.png',
#         'Tiles Courtesy of <a href="http://www.mapquest.com/">MapQuest</a> '
#         '&mdash; Map data &copy; '
#         '<a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'),
#        # Stamen toner lite.
#        # ('Watercolor',
#        #  'http://{s}.tile.stamen.com/watercolor/{z}/{x}/{y}.png',
#        #  'Map tiles by <a href="http://stamen.com">Stamen Design</a>, \
#        #  <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a> &mdash; Map data &copy; \
#        #  <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, \
#        #  <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>'),
#        # ('Toner Lite',
#        #  'http://{s}.tile.stamen.com/toner-lite/{z}/{x}/{y}.png',
#        #  'Map tiles by <a href="http://stamen.com">Stamen Design</a>, \
#        #  <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a> &mdash; Map data &copy; \
#        #  <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, \
#        #  <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>'),
#    ],
#    'PLUGINS': {
#        'esri-leaflet': {
#            'js': 'lib/js/esri-leaflet.js',
#            'auto-include': True,
#        },
#        'leaflet-fullscreen': {
#            'css': 'lib/css/leaflet.fullscreen.css',
#            'js': 'lib/js/Leaflet.fullscreen.min.js',
#            'auto-include': True,
#        },
#    },
#    'SRID': 3857,
#    'RESET_VIEW': False
#}

PROXY_ALLOWED_HOSTS += ('nominatim.openstreetmap.org',)

# AUTH_IP_WHITELIST property limits access to users/groups REST endpoints
# to only whitelisted IP addresses.
#
# Empty list means 'allow all'
#
# If you need to limit 'api' REST calls to only some specific IPs
# fill the list like below:
#
# AUTH_IP_WHITELIST = ['192.168.1.158', '192.168.1.159']
AUTH_IP_WHITELIST = []

MANAGERS = ADMINS = os.getenv('ADMINS', [])
TIME_ZONE = os.getenv('TIME_ZONE', "America/Chicago")
USE_TZ = True

# leave below if you want to have notifications
# notification settings
NOTIFICATION_ENABLED = False
# pinax.notifications
# or notification
NOTIFICATIONS_MODULE = 'pinax.notifications'

if NOTIFICATION_ENABLED:
    INSTALLED_APPS += (NOTIFICATIONS_MODULE, )

# set to true to have multiple recipients in /message/create/
USER_MESSAGES_ALLOW_MULTIPLE_RECIPIENTS = False

# allow users to add new keywrods or not
FREETEXT_KEYWORDS_READONLY = False

# allow modification of Topic Categories from Admin UI
MODIFY_TOPICCATEGORY = True

# Each uploaded Layer must be approved by an Admin before becoming visible
ADMIN_MODERATE_UPLOADS = False

# If this option is enabled, Resources belonging to a Group won't be visible by others
GROUP_PRIVATE_RESOURCES = False

# If this option is enabled, Groups will become strictly Mandatory on Metadata Wizard
GROUP_MANDATORY_RESOURCES = False

# default map projection
# Note: If set to EPSG:4326, then only EPSG:4326 basemaps will work.
DEFAULT_MAP_CRS = "EPSG:900913"

# Where should newly created maps be focused?
DEFAULT_MAP_CENTER = (0, 0)

# How tightly zoomed should newly created maps be?
# 0 = entire world;
# maximum zoom is between 12 and 15 (for Google Maps, coverage varies by area)
DEFAULT_MAP_ZOOM = 0

ALT_OSM_BASEMAPS = os.environ.get('ALT_OSM_BASEMAPS', False)
CARTODB_BASEMAPS = os.environ.get('CARTODB_BASEMAPS', False)
STAMEN_BASEMAPS = os.environ.get('STAMEN_BASEMAPS', False)
THUNDERFOREST_BASEMAPS = os.environ.get('THUNDERFOREST_BASEMAPS', False)
MAPBOX_ACCESS_TOKEN = os.environ.get('MAPBOX_ACCESS_TOKEN', '')
BING_API_KEY = os.environ.get('BING_API_KEY', None)

MAP_BASELAYERS = [{
    "source": {"ptype": "gxp_olsource"},
    "type": "OpenLayers.Layer",
    "args": ["No background"],
    "name": "background",
    "visibility": False,
    "fixed": True,
    "group":"background"
}, {
    "source": {"ptype": "gxp_olsource"},
    "type": "OpenLayers.Layer.XYZ",
    "title": "Humanitarian OpenStreetMap",
    "args": ["Humanitarian OpenStreetMap", "http://a.tile.openstreetmap.fr/hot/${z}/${x}/${y}.png"],
    "name": "background",
    "attribution": "&copy; <a href='http://www.openstreetmap.org/copyright'>OpenStreetMap</a>, Tiles courtesy of <a href='http://hot.openstreetmap.org/' target='_blank'>Humanitarian OpenStreetMap Team</a>",
    "visibility": False,
    "fixed": True,
    "group":"background"
}, {
    "source": {"ptype": "gxp_olsource"},
    "type": "OpenLayers.Layer.XYZ",
    "title": "MapBox Satellite Streets",
    "args": ["MapBox Satellite Streets", "http://api.mapbox.com/styles/v1/mapbox/satellite-streets-v9/tiles/${z}/${x}/${y}?access_token="+MAPBOX_ACCESS_TOKEN],
    "name": "background",
    "attribution": "&copy; <a href='https://www.mapbox.com/about/maps/'>Mapbox</a> &copy; <a href='http://www.openstreetmap.org/copyright'>OpenStreetMap</a> <a href='https://www.mapbox.com/feedback/' target='_blank'>Improve this map</a>",
    "visibility": False,
    "fixed": True,
    "group":"background"
}, {
    "source": {"ptype": "gxp_olsource"},
    "type": "OpenLayers.Layer.XYZ",
    "title": "MapBox Streets",
    "args": ["MapBox Streets", "http://api.mapbox.com/styles/v1/mapbox/streets-v9/tiles/${z}/${x}/${y}?access_token="+MAPBOX_ACCESS_TOKEN],
    "name": "background",
    "attribution": "&copy; <a href='https://www.mapbox.com/about/maps/'>Mapbox</a> &copy; <a href='http://www.openstreetmap.org/copyright'>OpenStreetMap</a> <a href='https://www.mapbox.com/feedback/' target='_blank'>Improve this map</a>",
    "visibility": False,
    "fixed": True,
    "group":"background"
}, {
    "source": {"ptype": "gxp_osmsource"},
    "type": "OpenLayers.Layer.OSM",
    "title": "OpenStreetMap",
    "name": "mapnik",
    "attribution": "&copy; <a href='http://osm.org/copyright'>OpenStreetMap</a> contributors",
    "visibility": True,
    "fixed": True,
    "group": "background"
}]

LOCAL_GEOSERVER = {
    "source": {
        "ptype": "gxp_wmscsource",
        "url": OGC_SERVER['default']['PUBLIC_LOCATION'] + "wms",
        "restUrl": "/gs/rest"
    }
}
baselayers = MAP_BASELAYERS
MAP_BASELAYERS = [LOCAL_GEOSERVER]
MAP_BASELAYERS.extend(baselayers)

# ######################

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d '
                      '%(thread)d %(message)s'
        },
        'simple': {
            'format': '%(message)s',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'null': {
            'level': 'INFO',
            'class': 'django.utils.log.NullHandler',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'mail_admins': {
            'level': 'INFO', 'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
        }
    },
    "loggers": {
        "django": {
            "handlers": ["console"], "level": "INFO", },
        "geonode": {
            "handlers": ["console"], "level": "INFO", },
        "gsconfig.catalog": {
            "handlers": ["console"], "level": "INFO", },
        "owslib": {
            "handlers": ["console"], "level": "INFO", },
        "pycsw": {
            "handlers": ["console"], "level": "INFO", },
        "{{ project_name}}": {
            "handlers": ["console"], "level": "INFO", },
        },
    }

# ######################
