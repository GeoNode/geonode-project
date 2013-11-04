from django.conf.urls import patterns, url

from geonode.urls import *

urlpatterns = patterns('',

    # Static pages
    url(r'^$', 'geonode.views.index', {'template': 'site_index.html'}, name='home'),
 ) + urlpatterns
