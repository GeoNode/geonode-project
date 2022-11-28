# {{ project_name|title }}

GeoNode template project. Generates a django project with GeoNode support.

## Table of Contents

-  [Developer Workshop](#developer-Workshop)
-  [Create a custom project](#create-a-custom-project)
-  [Start your server using Docker](#start-your-server-using-docker)
-  [Run the instance in development mode](#run-the-instance-in-development-mode)
-  [Run the instance on a public site](#run-the-instance-on-a-public-site)
-  [Stop the Docker Images](#stop-the-docker-images)
-  [Backup and Restore from Docker Images](#backup-and-restore-the-docker-images)
-  [Recommended: Track your changes](#recommended-track-your-changes)
-  [Hints: Configuring `requirements.txt`](#hints-configuring-requirementstxt)

## Developer Workshop

Available at

  ```bash
    http://geonode.org/dev-workshop
  ```

## Create a custom project

**NOTE**: *You can call your geonode project whatever you like **except 'geonode'**. Follow the naming conventions for python packages (generally lower case with underscores (``_``). In the examples below, replace ``{{ project_name }}`` with whatever you would like to name your project.*

To setup your project follow these instructions:

1. Generate the project

    ```bash
    git clone https://github.com/GeoNode/geonode-project.git -b <your_branch>
    source /usr/share/virtualenvwrapper/virtualenvwrapper.sh
    mkvirtualenv --python=/usr/bin/python3 {{ project_name }}
    pip install Django==3.2.16

    django-admin startproject --template=./geonode-project -e py,sh,md,rst,json,yml,ini,env,sample,properties -n monitoring-cron -n Dockerfile {{ project_name }}

    cd {{ project_name }}
    ```

2. Create the .env file

    An `.env` file is requird to run the application. It can be created from the `.env.sample` either manually or with the create-envfile.py script.

    The script accepts several parameters to create the file, in detail:

    - *hostname*: e.g. master.demo.geonode.org, default localhost
    - *https*: (boolean), default value is False
    - *email*: Admin email (this is required if https is set to True since a valid email is required by Letsencrypt certbot)
    - *env_type*: `prod`, `test` or `dev`. It will set the `DEBUG` variable to `False` (`prod`, `test`) or `True` (`dev`)
    - *geonodepwd*: GeoNode admin password (required inside the .env)
    - *geoserverpwd*: Geoserver admin password (required inside the .env)
    - *pgpwd*: PostgreSQL password (required inside the .env)
    - *dbpwd*: GeoNode DB user password (required inside the .env)
    - *geodbpwd*: Geodatabase user password (required inside the .env)
    - *clientid*: Oauth2 client id (required inside the .env)
    - *clientsecret*: Oauth2 client secret (required inside the .env)
    - *secret key*: Django secret key (required inside the .env)
    - *sample_file*: absolute path to a env_sample file used to create the env_file. If not provided, the one inside the GeoNode project is used.
    - *file*: absolute path to a json file that contains all the above configuration

     **NOTE:**
    - if the same configuration is passed in the json file and as an argument, the CLI one will overwrite the one in the JSON file
    - If some value is not provided, a random string is used

      Example USAGE

      ```bash
      python create-envfile.py -f /opt/core/geonode-project/file.json \
        --hostname localhost \
        --https \
        --email random@email.com \
        --geonodepwd gn_password \
        --geoserverpwd gs_password \
        --pgpwd pg_password \
        --dbpwd db_password \
        --geodbpwd _db_password \
        --clientid 12345 \
        --clientsecret abc123 
      ```

      Example JSON expected:

      ```JSON
      {
        "hostname": "value",
        "https": "value",
        "email": "value",
        "geonodepwd": "value",
        "geoserverpwd": "value",
        "pgpwd": "value",
        "dbpwd": "value",
        "geodbpwd": "value",
        "clientid": "value",
        "clientsecret": "value"
      } 
      ```

### Start your server
*Skip this part if you want to run the project using Docker instead* see [Start your server using Docker](#start-your-server-using-docker)

1. Setup the Python Dependencies

    **NOTE**: *Important: modify your `requirements.txt` file, by adding the `GeoNode` branch before continue!*

    (see [Hints: Configuring `requirements.txt`](#hints-configuring-requirementstxt))

    ```bash
    cd src
    pip install -r requirements.txt --upgrade
    pip install -e . --upgrade

    # Install GDAL Utilities for Python
    pip install pygdal=="`gdal-config --version`.*"

    # Dev scripts
    mv ../.override_dev_env.sample ../.override_dev_env
    mv manage_dev.sh.sample manage_dev.sh
    mv paver_dev.sh.sample paver_dev.sh

    source ../.override_dev_env

    # Using the Default Settings
    sh ./paver_dev.sh reset
    sh ./paver_dev.sh setup
    sh ./paver_dev.sh sync
    sh ./paver_dev.sh start
    ```

2. Access GeoNode from browser

    **NOTE**: default admin user is ``admin`` (with pw: ``admin``)

    ```bash
    http://localhost:8000/
    ```

### Start your server using Docker

You need Docker 1.12 or higher, get the latest stable official release for your platform.
Once you have the project configured run the following command from the root folder of the project.

1. Run `docker-compose` to start it up (get a cup of coffee or tea while you wait)

    ```bash
    docker-compose build --no-cache
    docker-compose up -d
    ```

    ```bash
    set COMPOSE_CONVERT_WINDOWS_PATHS=1
    ```

    before running `docker-compose up`

2. Access the site on http://localhost/

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

## Backup and Restore from Docker Images

### Run a Backup

```bash
SOURCE_URL=$SOURCE_URL TARGET_URL=$TARGET_URL ./{{project_name}}/br/backup.sh $BKP_FOLDER_NAME
```

- BKP_FOLDER_NAME:
  Default value = backup_restore
  Shared Backup Folder name.
  The scripts assume it is located on "root" e.g.: /$BKP_FOLDER_NAME/

- SOURCE_URL:
  Source Server URL, the one generating the "backup" file.

- TARGET_URL:
  Target Server URL, the one which must be synched.

e.g.:

```bash
docker exec -it django4{{project_name}} sh -c 'SOURCE_URL=$SOURCE_URL TARGET_URL=$TARGET_URL ./{{project_name}}/br/backup.sh $BKP_FOLDER_NAME'
```

### Run a Restore

```bash
SOURCE_URL=$SOURCE_URL TARGET_URL=$TARGET_URL ./{{project_name}}/br/restore.sh $BKP_FOLDER_NAME
```

- BKP_FOLDER_NAME:
  Default value = backup_restore
  Shared Backup Folder name.
  The scripts assume it is located on "root" e.g.: /$BKP_FOLDER_NAME/

- SOURCE_URL:
  Source Server URL, the one generating the "backup" file.

- TARGET_URL:
  Target Server URL, the one which must be synched.

e.g.:

```bash
docker exec -it django4{{project_name}} sh -c 'SOURCE_URL=$SOURCE_URL TARGET_URL=$TARGET_URL ./{{project_name}}/br/restore.sh $BKP_FOLDER_NAME'
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
Django==3.2.16
git+git://github.com/<your organization>/geonode.git@<your branch>
```

## Increasing PostgreSQL Max connections

In case you need to increase the PostgreSQL Max Connections , you can modify
the **POSTGRESQL_MAX_CONNECTIONS** variable in **.env** file as below:

```
POSTGRESQL_MAX_CONNECTIONS=200
```

In this case PostgreSQL will run accepting 200 maximum connections.

## Test project generation and docker-compose build Vagrant usage

Testing with [vagrant](https://www.vagrantup.com/docs) works like this:
What vagrant does:

Starts a vm for test on docker swarm:
    - configures a GeoNode project from template every time from your working directory (so you can develop directly on geonode-project).
    - exposes service on localhost port 8888
    - rebuilds everytime everything with cache [1] to avoid banning from docker hub with no login.
    - starts, reboots to check if docker services come up correctly after reboot.

```bash
vagrant plugin install vagrant-reload
#test things for docker-compose
vagrant up
# check services are up upon reboot
vagrant ssh geonode-compose -c 'docker ps'
```

Test geonode on [http://localhost:8888/](http://localhost:8888/)

To clean up things and delete the vagrant box:

```bash
vagrant destroy -f
```

## Test project generation and Docker swarm build on vagrant

What vagrant does:

Starts a vm for test on docker swarm:
    - configures a GeoNode project from template every time from your working directory (so you can develop directly on geonode-project).
    - exposes service on localhost port 8888
    - rebuilds everytime everything with cache [1] to avoid banning from docker hub with no login.
    - starts, reboots to check if docker services come up correctly after reboot.

To test on a docker swarm enable vagrant box:

```bash
vagrant up
VAGRANT_VAGRANTFILE=Vagrantfile.stack vagrant up
# check services are up upon reboot
VAGRANT_VAGRANTFILE=Vagrantfile.stack vagrant ssh geonode-compose -c 'docker service ls'
```

Test geonode on [http://localhost:8888/](http://localhost:8888/)
Again, to clean up things and delete the vagrant box:

```bash
VAGRANT_VAGRANTFILE=Vagrantfile.stack vagrant destroy -f
```

for direct deveolpment on geonode-project after first `vagrant up` to rebuild after changes to project, you can do `vagrant reload` like this:

```bash
vagrant up
```

What vagrant does (swarm or comnpose cases):

Starts a vm for test on plain docker service with docker-compose:
    - configures a GeoNode project from template every time from your working directory (so you can develop directly on geonode-project).
    - rebuilds everytime everything with cache [1] to avoid banning from docker hub with no login.
    - starts, reboots.

[1] to achieve `docker-compose build --no-cache` just destroy vagrant boxes `vagrant destroy -f`

