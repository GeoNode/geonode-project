# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright (C) 2018 OSGeo
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

import os
from distutils.core import setup

def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

setup(
    name="{{ project_name }}",
    version="0.1",
    author="",
    author_email="",
    description="{{ project_name }}, based on GeoNode",
    long_description=(read('README.rst')),
    # Full list of classifiers can be found at:
    # http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 1 - Planning',
    ],
    license="BSD",
    keywords="{{ project_name }} geonode django",
    url='https://github.com/{{ project_name }}/{{ project_name }}',
    packages=['{{ project_name }}',],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
       'Django==1.8.19',
       'six==1.10.0',
       'django-cuser==2017.3.16',
       'django-model-utils==3.1.1',
       'django-autocomplete-light==2.3.3',
       'pyshp==1.2.12',
       'celery==4.1.0',
       'Shapely>=1.5.13,<1.6.dev0',
       'OWSLib==0.15.0',
       'proj==0.1.0',
       'pyproj==1.9.5.1',
       'inflection==0.3.1',
       'oauthlib==2.0.1',
       'python-dateutil==2.6.1',
       'pycsw==2.0.3',
    ],
)
