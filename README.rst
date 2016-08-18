{{ project_name|title }}
========================

GeoNode project. Generates a django project with GeoNode support.

Create a custom project
-----------------------

Step 1. Install Docker (for Linux, Mac or Windows).
Step 2. Run the following command in a terminal. Remember to replace the name of the project from `{{project_name}}` to whatever you want, for example `awesomegeonode`.::

    docker run -v `pwd`:/usr/src/app terranodo/django:geonode django-admin.py startproject --template=https://github.com/GeoNode/geonode-project/archive/docker.zip -epy,rst,yml {{project_name}}
    cd {{project_name}}

If you experience a permissions problem, make sure that the files belong to your user and not the root user.

Start your server
----------------

Run `docker-compose` to start it up (get a cup of coffee or tea while you wait)::

    docker-compose up

Create the tables in your postgres database::

    docker-compose run django python manage.py migrate

Set up a superuser so you can access the admin area::

    docker-compose run django python manage.py createsuperuser

Access the site on http://localhost/


Optional: Track your changes
-----

Step 1. Install Git (for Linux, Mac or Windows).

Step 2. Init git locally and do the first commit:

    git init
    
    git add *
    
    git commit -m "Initial Commit"

Step 3. Set up a free account on github or bitbucket and make a copy of the repo there.
