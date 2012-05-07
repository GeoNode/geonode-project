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
        'Framework :: GeoNode',
        'License :: License :: OSI Approved :: BSD License'
    ],
    license="BSD",
    keywords="{{ project_name }} geonode django",
    url='https://github.com/{{ project_name }}/{{ project_name }}',
    packages=['{{ project_name }}',],
    include_package_data=True,
    zip_safe=False,
)
