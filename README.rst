{{ project_name|title }}
========================

You should write some docs, it's good for the soul.

Installation
------------

With GeoNode's virtualenv activated in development or production mode, do the following::


    $ git clone git://github.com/GeoNode/geonode-project.git
    $ django-admin.py startproject --template=geonode-project -epy,rst my_geonode 

Usage
-----

    $ pip install -e my_geonode
    $ cd my_geonode
    $ python manage.py runserver

To install on a virtual environment do::

    $ pip install -e my_geonode

Replace all uses of ``geonode.settings`` for ``my_geonode.settings``.

In production, you can modify the 'geonode' binary tool and geonode.wsgi file to point to this one.
