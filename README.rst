{{ project_name|title }}
========================

GeoNode template project. Generates a django project with GeoNode support.

Create a custom project
-----------------------

Note: You can call your geonode project whatever you like following the naming conventions for python packages (generally lower case with underscores (``_``). In the examples below, replace ``my_geonode`` with whatever you would like to name your project.

Using a Python virtual environment
++++++++++++++++++++++++++++++++++

To setup your project using a local python virtual environment, follow these instructions:

1. Prepare the Environment

  .. code:: bash

    git clone https://github.com/GeoNode/geonode-project.git -b 2.7
    mkvirtualenv my_geonode
    pip install Django==1.8.19

    django-admin.py startproject --template=../geonode-project -e py,rst,json,yml,ini,env,sample -n Dockerfile my_geonode

    cd my_geonode

2. Setup the Python Dependencies

  .. code:: bash

    pip install -r requirements.txt --upgrade
    pip install -e . --upgrade

    GDAL_VERSION=`gdal-config --version`
    PYGDAL_VERSION="$(pip install pygdal==$GDAL_VERSION 2>&1 | grep -oP '(?<=: )(.*)(?=\))' | grep -oh $GDAL_VERSION\.[0-9])"
    pip install pygdal==$PYGDAL_VERSION

    # Using Default Settings
    DJANGO_SETTINGS_MODULE=my_geonode.settings paver reset
    DJANGO_SETTINGS_MODULE=my_geonode.settings paver setup
    DJANGO_SETTINGS_MODULE=my_geonode.settings paver sync
    DJANGO_SETTINGS_MODULE=my_geonode.settings paver start

    # Using Custom Local Settings
    cp my_geonode/local_settings.py.sample my_geonode/local_settings.py

    DJANGO_SETTINGS_MODULE=my_geonode.local_settings paver reset
    DJANGO_SETTINGS_MODULE=my_geonode.local_settings paver setup
    DJANGO_SETTINGS_MODULE=my_geonode.local_settings paver sync
    DJANGO_SETTINGS_MODULE=my_geonode.local_settings paver start
  
3. Access GeoNode from browser::

    http://localhost:8000/
    
.. note:: default admin user is ``admin`` (with pw: ``admin``)

Start your server
-----------------

You need Docker 1.12 or higher, get the latest stable official release for your platform.

1. Prepare the Environment

  .. code:: bash

    git clone https://github.com/GeoNode/geonode-project.git -b 2.7
    mkvirtualenv my_geonode
    pip install Django==1.8.19

    django-admin.py startproject --template=../geonode-project -e py,rst,json,yml,ini,env,sample -n Dockerfile my_geonode

    cd my_geonode

2. Run `docker-compose` to start it up (get a cup of coffee or tea while you wait)::

    docker-compose build --no-cache
    docker-compose up -d

3. Access the site on http://localhost/


Recommended: Track your changes
-------------------------------

Step 1. Install Git (for Linux, Mac or Windows).

Step 2. Init git locally and do the first commit:

    git init

    git add *

    git commit -m "Initial Commit"

Step 3. Set up a free account on github or bitbucket and make a copy of the repo there.

Configuring Requirements.txt
++++++++++++++++++++++++++++

You may want to configure your requirements.txt, if you are using additional or custom versions of python packages.  For example::

    Django==1.8.19
    six==1.10.0
    django-cuser==2017.3.16
    django-model-utils==3.1.1
    pyshp==1.2.12
    celery==4.1.0
    Shapely>=1.5.13,<1.6.dev0
    proj==0.1.0
    pyproj==1.9.5.1
    pygdal==2.2.1.3
    inflection==0.3.1
    git+git://github.com/<your organization>/geonode.git@<your branch>


Using Ansibe
++++++++++++

To run the Ansible playbook use something like this::

    ANSIBLE_ROLES_PATH=~/workspaces/public ansible-playbook -e "gs_root_password=<new gs root password>" -e "gs_admin_password=<new gs admin password>" -e "dj_superuser_password=<new django admin password>" -i inventory --limit all playbook.yml


Configuration
+++++++++++++

Since this application uses geonode, base source of settings is ``geonode.settings`` module. It provides defaults for many items, which are used by geonode. This application has own settings module, ``{{project_name}}.settings``, which includes ``geonode.settings``. It customizes few elements:
 * static/media files locations - they will be collected and stored along with this application files by default. This is useful during development.
 * Adds ``{{project_name}}`` to installed applications, updates templates, staticfiles dirs, sets urlconf to ``{{project_name}}.urls``. 

Whether you deploy development or production environment, you should create additional settings file. Convention is to make ``{{project_name}}.local_settings`` module. It is recommended to use ``{{project_name}}/local_settings.py``.. That file contains small subset of settings for edition. It should:
 * not be versioned along with application (because changes you make for your private deployment may become public),
 * have customized at least``DATABASES``, ``SECRET_KEY`` and ``SITEURL``. 

You can add more settings there, note however, some settings (notably ``DEBUG_STATIC``, ``EMAIL_ENABLE``, ``*_ROOT``, and few others) can be used by other settings, or as condition values, which change other settings. For example, ``EMAIL_ENABLE`` defined in ``geonode.settings`` enables whole email handling block, so if you disable it in your ``local_settings``, derived settings will be preserved. You should carefully check if additional settings you change don't trigger other settings.

To ilustrate whole concept of chanied settings:
::
    +------------------------+-------------+-------------------------------+-------------+----------------------------------+
    |  GeoNode configuration |             |   Your application default    |             |  (optionally) Your deployment(s) |
    |                        |             |        configuration          |             |                                  |
    +========================|=============|===============================|=============|==================================+
    |                        | included by |                               | included by |                                  |
    |   geonode.settings     |     ->      |  {{project_name}}.settings    |      ->     |  {{project_name}}.local_settings |
    +------------------------|-------------|-------------------------------|-------------|----------------------------------+
