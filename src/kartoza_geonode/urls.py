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

from django.conf.urls.i18n import i18n_patterns
from django.urls import include, path, re_path
from django.views.generic.base import RedirectView
from geonode.urls import urlpatterns

from kartoza_geonode.models.preferences import SitePreferences


class SitePreferencesRedirectView(RedirectView):
    """Redirect to preferences admin page."""

    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        """Return absolute URL to redirect to."""
        SitePreferences.load()
        return '/admin/kartoza_geonode/sitepreferences/1/change/'


urlpatterns = i18n_patterns(
    re_path(
        r'^admin/kartoza_geonode/sitepreferences/$',
        SitePreferencesRedirectView.as_view(),
        name='index'
    )
) + [
    path("mapaction/", include("mapaction.urls")),
] + urlpatterns
