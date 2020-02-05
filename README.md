# {{ project_name|title }}

GeoNode template project. Generates a django project with GeoNode support.

## Table of Contents

-  [Developer Workshop](#developer-Workshop)
-  [Create a custom project](#create-a-custom-project)
-  [Start your server using Docker](#start-your-server-using-docker)
-  [Run the instance in development mode](#run-the-instance-in-development-mode)
-  [Run the instance on a public site](#run-the-instance-on-a-public-site)
-  [Stop the Docker Images](#stop-the-docker-images)
-  [Recommended: Track your changes](#recommended-track-your-changes)
-  [Hints: Configuring `requirements.txt`](#hints-configuring-requirementstxt)
-  [Hints: Using Ansible](#hints-using-ansible)
-  [Configuration](#configuration)

## Developer Workshop

Available at

  ```bash
    http://geonode.org/dev-workshop
  ```

## Create a custom project

**NOTE**: *You can call your geonode project whatever you like following the naming conventions for python packages (generally lower case with underscores (``_``). In the examples below, replace ``{{ project_name }}`` with whatever you would like to name your project.*

### Using a Python virtual environment

**NOTE**: *Skip this part if you want to run the project using Docker instead*

(see [Start your server using Docker](#start-your-server-using-docker))

To setup your project using a local python virtual environment, follow these instructions:

1. Prepare the Environment

    ```bash
    git clone https://github.com/GeoNode/geonode-project.git -b <your_branch>
    source /usr/share/virtualenvwrapper/virtualenvwrapper.sh
    mkvirtualenv --python=/usr/bin/python3 {{ project_name }}
    pip install Django==2.2.9

    django-admin startproject --template=./geonode-project -e py,sh,md,rst,json,yml,ini,env,sample -n monitoring-cron -n Dockerfile {{ project_name }}

    cd {{ project_name }}
    ```

2. Setup the Python Dependencies

    **NOTE**: *Important: modify your `requirements.txt` file, by adding the `GeoNode` branch before continue!*

    (see [Hints: Configuring `requirements.txt`](#hints-configuring-requirementstxt))

    ```bash
    pip install -r requirements.txt --upgrade
    pip install -e . --upgrade

    # Install GDAL Utilities for Python
    pip install pygdal=="`gdal-config --version`.*"

    # Using the Default Settings
    DJANGO_SETTINGS_MODULE={{ project_name }}.settings paver reset
    DJANGO_SETTINGS_MODULE={{ project_name }}.settings paver setup
    DJANGO_SETTINGS_MODULE={{ project_name }}.settings paver sync
    DJANGO_SETTINGS_MODULE={{ project_name }}.settings paver start

    # Using the Custom Local Settings
    # - Remember that `.settings` includes `.local_settings`
    cp {{ project_name }}/local_settings.py.sample {{ project_name }}/local_settings.py

    DJANGO_SETTINGS_MODULE={{ project_name }}.local_settings paver reset
    DJANGO_SETTINGS_MODULE={{ project_name }}.local_settings paver setup
    DJANGO_SETTINGS_MODULE={{ project_name }}.local_settings paver sync
    DJANGO_SETTINGS_MODULE={{ project_name }}.local_settings paver start
    ```

3. Access GeoNode from browser

    **NOTE**: default admin user is ``admin`` (with pw: ``admin``)

    ```bash
    http://localhost:8000/
    ```

## Start your server using Docker

You need Docker 1.12 or higher, get the latest stable official release for your platform.

1. Prepare the Environment

    ```bash
    git clone https://github.com/GeoNode/geonode-project.git -b <your_branch>
    source /usr/share/virtualenvwrapper/virtualenvwrapper.sh
    mkvirtualenv --python=/usr/bin/python3 {{ project_name }}
    pip install Django==2.2.9

    django-admin startproject --template=./geonode-project -e py,sh,md,rst,json,yml,ini,env,sample -n monitoring-cron -n Dockerfile {{ project_name }}

    cd {{ project_name }}
    ```

2. Run `docker-compose` to start it up (get a cup of coffee or tea while you wait)

    ```bash
    docker-compose build --no-cache
    docker-compose up -d
    ```

    ```bash
    set COMPOSE_CONVERT_WINDOWS_PATHS=1
    ```

    before running `docker-compose up`

3. Access the site on http://localhost/

## Run the instance in development mode

### Use dedicated docker-compose files while developing

**NOTE**: In this example we are going to keep localhost as the target IP for GeoNode

  ```bash
  docker-compose -f docker-compose.development.yml -f docker-compose.development.override.yml up
  ```

## Run the instance on a public site

### Preparation of the image (First time only)

**NOTE**: In this example we are going to publish to the public IP http://123.456.789.111

```bash
vim .env
  --> replace localhost with 123.456.789.111 everywhere
```

### Startup the image

```bash
docker-compose up --build -d
```

### Stop the Docker Images

```bash
docker-compose stop
```

### Fully Wipe-out the Docker Images

**WARNING**: This will wipe out all the repositories created until now.

**NOTE**: The images must be stopped first

```bash
docker system prune -a
```

## Recommended: Track your changes

Step 1. Install Git (for Linux, Mac or Windows).

Step 2. Init git locally and do the first commit:

```bash
git init
git add *
git commit -m "Initial Commit"
```

Step 3. Set up a free account on github or bitbucket and make a copy of the repo there.

## Hints: Configuring `requirements.txt`

You may want to configure your requirements.txt, if you are using additional or custom versions of python packages. For example

```python
Django==2.2.9
git+git://github.com/<your organization>/geonode.git@<your branch>
```

## Hints: Using Ansible

You will need to use Ansible Role in order to run the playbook.

In order to install and setup Ansible, run the following commands

```bash
sudo apt-get install software-properties-common
sudo apt-add-repository ppa:ansible/ansible
sudo apt-get update
sudo apt-get install ansible
```

A sample Ansible Role can be found at https://github.com/GeoNode/ansible-geonode

To install the default one, run

```bash
sudo ansible-galaxy install GeoNode.geonode
```

you will find the Ansible files into the ``~/.ansible/roles`` folder. Those must be updated in order to match the GeoNode and GeoServer versions you will need to install.

To run the Ansible playbook use something like this

```bash
ANSIBLE_ROLES_PATH=~.ansible/roles ansible-playbook -e "gs_root_password=<new gs root password>" -e "gs_admin_password=<new gs admin password>" -e "dj_superuser_password=<new django admin password>" -i inventory --limit all playbook.yml
```

## Configuration

**NOTE**: *For `GeoNode` settings, make use of the `ENVIRONMENT` variables whenever is possible. Avoid overwriting them yourself, you might me missing some additional logic done on `geonode.settings`*

Since this application uses geonode, base source of settings is ``geonode.settings`` module. It provides defaults for many items, which are used by geonode. This application has own settings module, ``{{project_name}}.settings``, which includes ``geonode.settings``. It customizes few elements:
 * static/media files locations - they will be collected and stored along with this application files by default. This is useful during development.
 * Adds ``{{project_name}}`` to installed applications, updates templates, staticfiles dirs, sets urlconf to ``{{project_name}}.urls``.

Whether you deploy development or production environment, you should create additional settings file. Convention is to make ``{{project_name}}.local_settings`` module. It is recommended to use ``{{project_name}}/local_settings.py``.. That file contains small subset of settings for edition. It should:
 * not be versioned along with application (because changes you make for your private deployment may become public),
 * have customized at least ``DATABASES``, ``SECRET_KEY`` and ``SITEURL``.

You can add more settings there, note however, some settings (notably ``DEBUG_STATIC``, ``EMAIL_ENABLE``, ``*_ROOT``, and few others) can be used by other settings, or as condition values, which change other settings. For example, ``EMAIL_ENABLE`` defined in ``geonode.settings`` enables whole email handling block, so if you disable it in your ``local_settings``, derived settings will be preserved. You should carefully check if additional settings you change don't trigger other settings.

To illustrate whole concept of chained settings:

|GeoNode configuration|   |(optionally) Your deployment(s)   |   |Your application default configuration|
|---|---|---|---|---|
|`geonode.settings`|included by ->|`{{project_name}}.local_settings`|included by ->|`{{project_name}}.settings`|
