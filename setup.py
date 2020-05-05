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
try:
    # pip >=20
    from pip._internal.network.session import PipSession
    try:
        from pip._internal.req import parse_requirements
    except ImportError:
        # pip >=21
        from pip._internal.req.req_file import parse_requirements
except ImportError:
    try:
        # 10.0.0 <= pip <= 19.3.1
        from pip._internal.download import PipSession
        from pip._internal.req import parse_requirements
    except ImportError:
        # pip <= 9.0.3
        from pip.download import PipSession
        from pip.req import parse_requirements

from distutils.core import setup

from setuptools import find_packages

# Parse requirements.txt to get the list of dependencies
inst_req = parse_requirements("requirements.txt", session=PipSession())
REQUIREMENTS = [str(r.req) if hasattr(r, 'req') else r.requirement if not r.is_editable else ''
                for r in inst_req]

def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

setup(
    name="{{ project_name }}",
    version="3.0",
    author="",
    author_email="",
    description="{{ project_name }}, based on GeoNode",
    long_description=(read('README.md')),
    # Full list of classifiers can be found at:
    # http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 1 - Planning',
    ],
    license="GPL",
    keywords="{{ project_name }} geonode django",
    url='https://github.com/{{ project_name }}/{{ project_name }}',
    packages=find_packages(),
    install_requires=REQUIREMENTS,
    dependency_links=[
        "git+https://github.com/GeoNode/geonode.git#egg=geonode"
    ],
    include_package_data=True,
    zip_safe=False,
)
