{{ project_name|title }}
========================

You should write some docs, it's good for the soul.

Installation
------------

With GeoNode's virtualenv activated in development or production mode, do the following::


    $ git clone git://github.com/ingenieroariel/geonode-project.git
    $ django-admin.py startproject --template=geonode-project -epy,rst myprettygeonode

Usage
-----

    $ pip install -e myprettygeonode
    $ cd myprettygeonode
    $ python manage.py runserver

To install on a virtual environment do::

    $ pip install -e myprettygeonode

Replace all uses of ``geonode.settings`` for ``myprettygeonode.settings``.

In production, you can modify the 'geonode' binary tool and geonode.wsgi file to point to this one.