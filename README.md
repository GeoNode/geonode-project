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

**NOTE**: *You can call your geonode project whatever you like following the naming conventions for python packages (generally lower case with underscores (``_``). In the examples below, replace ``{{ project_name }}`` with whatever you would like to name your project.*

### Using a Python virtual environment

**NOTE**: *Skip this part if you want to run the project using Docker instead*

(see [Start your server using Docker](#start-your-server-using-docker))

To setup your project using a local python virtual environment, follow these instructions:

1. Prepare the Environment

    ```bash
    git clone https://github.com/GeoNode/geonode-project.git -b <your_branch>
    export VIRTUALENVWRAPPER_PYTHON='/usr/bin/python3'
    source $(whereis virtualenvwrapper.sh | cut -f 2 -d " ")
    mkvirtualenv --python=/usr/bin/python3 {{ project_name }}
    pip install Django==2.2.12

    django-admin startproject --template=./geonode-project -e py,sh,md,rst,json,yml,ini,env,sample,properties -n monitoring-cron -n Dockerfile {{ project_name }}

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

    # Dev scripts
    mv .override_dev_env.sample .override_dev_env
    mv manage_dev.sh.sample manage_dev.sh
    mv paver_dev.sh.sample paver_dev.sh

    # Using the Default Settings
    ./paver_dev.sh reset
    ./paver_dev.sh setup
    ./paver_dev.sh sync
    ./paver_dev.sh start
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
    export VIRTUALENVWRAPPER_PYTHON='/usr/bin/python3'
    source $(whereis virtualenvwrapper.sh | cut -f 2 -d " ")
    mkvirtualenv --python=/usr/bin/python3 {{ project_name }}
    pip install Django==2.2.15

    django-admin startproject --template=./geonode-project -e py,sh,md,rst,json,yml,ini,env,sample,properties -n monitoring-cron -n Dockerfile {{ project_name }}

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
Django==2.2.12
git+git://github.com/<your organization>/geonode.git@<your branch>
```
