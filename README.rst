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

Using a Python virtual environment
++++++++++++++++++++++++++

To setup your project using a local python virtual environment, follow these instructions:

1. Setup your virtualenvironment ``mkvirtualenv my_geonode``
2. Install django into your virtualenviornment ``pip install Django==1.8.7``
3. Create your project using the template project::

    django-admin.py startproject --template=https://github.com/GeoNode/geonode-project/archive/master.zip -epy,rst,yml my_geonode

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

Configuring Requirements.txt
++++++++++++

You may want to configure your requirements.txt, if you are using additional or custom versions of python packages.  For example::

    five==0.4.0
    django-geonode-client==0.0.22
    django-cors-headers==1.3.1
    git+git://github.com/<your organization>/geonode.git@<your branch>
    pymemcache
    defusedxml
    django-floppyforms


Using Ansibe
++++++++++++

To run the Ansible playbook use something like this::

    ANSIBLE_ROLES_PATH=~/workspaces/public ansible-playbook -e "gs_root_password=<new gs root password>" -e "gs_admin_password=<new gs admin password>" -e "dj_superuser_password=<new django admin password>" -i inventory --limit all playbook.yml
