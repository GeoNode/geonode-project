{{ project_name|title }}
========================

You should write some docs, it's good for the soul.

Installation
------------

Install geonode with::

    $ sudo add-apt-repository ppa:geonode/release

    $ sudo apt-get update

    $ sudo apt-get install geonode

Create a new template based on the geonode example project.::
    
    $ django-admin startproject my_geonode --template=https://github.com/GeoNode/geonode-project/archive/2.4.zip -epy,rst 
    $ sudo pip install -e my_geonode

.. note:: You should NOT use the name geonode for your project as it will conflict with the default geonode package name.

Usage
-----

Rename the local_settings.py.sample to local_settings.py and edit it's content by setting the SITEURL and SITENAME.

Edit the file /etc/apache2/sites-available/geonode and change the following directive from:

    WSGIScriptAlias / /var/www/geonode/wsgi/geonode.wsgi

to:

    WSGIScriptAlias / /path/to/my_geonode/my_geonode/wsgi.py
    
To avoid having to grant apache permissions (i.e. www-data user and group) to your home dir where you likely setup the geonode-project; you may want to instead copy the wsgi.py file next to geonode.wsgi and replace the file name instead of the entire path.

    $ cp /path/to/my_geonode/my_geonode/wsgi.py /var/www/geonode/wsgi/wsgi.py

Add the "Directory" directive for your folder like the following example:

    <Directory "/home/vagrant/my_geonode/my_geonode/">

       Order allow,deny

       Options Indexes FollowSymLinks

       Allow from all

       Require all granted

       IndexOptions FancyIndexing
       
    </Directory>

Restart apache::

    $ sudo service apache2 restart

Edit the templates in my_geonode/templates, the css and images to match your needs.

In the my_geonode folder run::

    $ python manage.py collectstatic

Github Considerations
------------------------

While it is helpful to recommit your django project wrapper back to a distributed version control repository. 
* It is also important to remember that production instances will store security information in the local_settings.py
* Admin/Devs should always remember to exclude this file in the .gitignore file in the same folder as the .git::

    $ nano .gitignore
    
    /{project}/local_settings.py

save, make sure the file is also removed from git cache::
    
    $ git rm -f --cache /{{project}}/local_settings.py
    
    $ git status
    
confirm the file is no longer staged for the next commit or that if it is as "removed"
