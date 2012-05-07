import os
from setuptools import setup, find_packages

def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

setup(
    name="y{{ projecT_name }}",
    version="0.1",
    author="",
    author_email="",
    description="{{ project_name }}, based on GeoNode",
    long_description=(read('README.rst')),
    # Full list of classifiers can be found at:
    # http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 1 - Planning',
        'Framework :: GeoNode',
        'License :: License :: OSI Approved :: BSD License'
    ],
    license="BSD",
    keywords="{{ project_name }} geonode django",
    url='https://github.com/{{ project_name }}/{{ project_name }}',
    packages=find_packages('.'),
    include_package_data=True,
    zip_safe=False,
)
