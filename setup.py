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
try:  # for pip >= 10
    from pip._internal.req import parse_requirements
    try:
        from pip._internal.download import PipSession
        pip_session = PipSession()
    except ImportError:  # for pip >= 20
        from pip._internal.network.session import PipSession
        pip_session = PipSession()
except ImportError:  # for pip <= 9.0.3
    try:
        from pip.req import parse_requirements
        from pip.download import PipSession
        pip_session = PipSession()
    except ImportError:  # backup in case of further pip changes
        pip_session = 'hack'

from distutils.core import setup

from setuptools import find_packages

# Parse requirements.txt to get the list of dependencies
inst_req = parse_requirements('requirements.txt',
                              session=pip_session)

REQUIREMENTS = [str(r.req) for r in inst_req]

def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

setup(
    name="my_geonode",
    version="2.10.1",
    author="",
    author_email="",
    description="my_geonode, based on GeoNode",
    long_description=(read('README.md')),
    # Full list of classifiers can be found at:
    # http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 1 - Planning',
    ],
    license="GPL",
    keywords="my_geonode geonode django",
    url='https://github.com/my_geonode/my_geonode',
    packages=find_packages(),
    install_requires=REQUIREMENTS,
    dependency_links=[
        "git+https://github.com/GeoNode/geonode.git@2.10.1#egg=geonode"
    ],
    include_package_data=True,
    zip_safe=False,
)
