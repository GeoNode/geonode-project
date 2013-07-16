{{ project_name|title }}
========================

You should write some docs, it's good for the soul.

Installation
------------

Create a new virtualenv for {{ project_name }}, install GeoNode and setup your project::

    $ mkvirtualenv my_geonode
    $ pip install Django
    $ django-admin.py startproject my_geonode --template=https://github.com/GeoNode/geonode-project/archive/master.zip -epy,rst 
    $ pip install -e my_geonode

To install the latest from GeoNode's master branch use the following command::

    $ pip install -e git+https://github.com/GeoNode/geonode.git#egg=geonode --upgrade

.. note:: You should NOT use the name geonode for your project as it will conflict with the default geonode package name.

Usage
-----

Setup your GeoNode for usage. Download a geoserver.war to use and start the development server::

    $ cd my_geonode
    $ paver setup # downloads geoserver
    $ paver start 
