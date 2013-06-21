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

Usage
-----

    $ cd my_geonode
    $ paver setup # downloads geoserver
    $ paver start 
