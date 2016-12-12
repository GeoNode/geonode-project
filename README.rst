{{ project_name|title }}
========================

GeoNode template project. Generates a django project with GeoNode support.

Create a custom project
-----------------------

Note: You can call your geonode project whatever you like following the naming conventions for python packages (generally lower case with underscores (``_``). In the examples below, replace ``my_geonode`` with whatever you would like to name your project. 

Using Docker
++++++++++++

To setup your project using Docker, follow these instructions:

1. Install Docker (for Linux, Mac or Windows).
2. Run the following command in a terminal.::

    docker run -v `pwd`:/usr/src/app GeoNode/django:geonode django-admin.py startproject --template=https://github.com/GeoNode/geonode-project/archive/docker.zip -epy,rst,yml my_geonode 
    cd my_geonode

If you experience a permissions problem, make sure that the files belong to your user and not the root user.

Using a Virtualenvironment
++++++++++++++++++++++++++

To setup your project using a local Virtualenvironment, follow these instructions:

1. Setup your virtualenvironment ``mkvirtualenv my_geonode``
2. Install django into your virtualenviornment ``pip install Django==1.8.7``
3. Create your project using the template project::

    django-admin.py startproject --template=https://github.com/GeoNode/geonode-project/archive/master.zip -epy,rst,yml my_geonode

Template inheritance
^^^^^^^^^^^^^^^^^^^^

Follow the snippets below and use the template tag ``overextends`` to extend an existing template from the core:

.. code-block:: django
 
 	{% comment %}geonode/base/templates/base/resourcebase_info_panel.html{% endcomment %}
	{% block content %}
	  <div>Hello</div>
	{% endblock %}

.. code-block:: django

    	{% comment %}project_name/templates/base/resourcebase_info_panel.html{% endcomment %}
    	{% overextends "base/resourcebase_info_panel.html" %}
	{% block content %}
	  {{ block.super }}
	  <div>GeoNode developers</div>
	{% endblock %}

Start your server
----------------

You need Docker 1.12 or higher, get the latest stable official release for your platform. Run `docker-compose` to start it up (get a cup of coffee or tea while you wait)::

    docker-compose up

Create the tables in your postgres database::

    docker-compose run django python manage.py migrate

Set up a superuser so you can access the admin area::

    docker-compose run django python manage.py createsuperuser

Access the site on http://localhost/


Recommended: Track your changes
-----

Step 1. Install Git (for Linux, Mac or Windows).

Step 2. Init git locally and do the first commit:

    git init
    
    git add *
    
    git commit -m "Initial Commit"

Step 3. Set up a free account on github or bitbucket and make a copy of the repo there.
