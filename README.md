# GeoNode Project

GeoNode Django project. This can be forked to customize, add Python modules or Django apps to your GeoNode instance.

> [!IMPORTANT]  
This repository has been converted from a Django project template into a concrete Django project, ready to be forked and deployed. The goal is to make it easier to track updates and pull changes from this repo into your own project.s

## Table of Contents

-  [Quick Docker Start](#quick-docker-start)
-  [Start your server using Docker](#start-your-server-using-docker)
-  [Run the instance in development mode](#run-the-instance-in-development-mode)
-  [Run the instance on a public site](#run-the-instance-on-a-public-site)
-  [Stop the Docker Images](#stop-the-docker-images)
-  [Backup and Restore from Docker Images](#backup-and-restore-the-docker-images)
-  [Recommended: Track your changes](#recommended-track-your-changes)
-  [Hints: Configuring `requirements.txt`](#hints-configuring-requirementstxt)

## Quick Docker Start
To setup your project follow these instructions:

1. Generate the project

    ```bash
    git clone https://github.com/GeoNode/geonode-project.git -b <your_branch>
    cd project
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
SOURCE_URL=$SOURCE_URL TARGET_URL=$TARGET_URL ./project/br/backup.sh $BKP_FOLDER_NAME
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
docker exec -it django4project sh -c 'SOURCE_URL=$SOURCE_URL TARGET_URL=$TARGET_URL ./project/br/backup.sh $BKP_FOLDER_NAME'
```

### Run a Restore

```bash
SOURCE_URL=$SOURCE_URL TARGET_URL=$TARGET_URL ./project/br/restore.sh $BKP_FOLDER_NAME
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
docker exec -it django4project sh -c 'SOURCE_URL=$SOURCE_URL TARGET_URL=$TARGET_URL ./project/br/restore.sh $BKP_FOLDER_NAME'
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

## Developing with Dev Containers in VS Code

This repo includes a .devcontainer folder with the condigurations to run Django and Celery inside a VS Code Dev Container.
A `docker.sh` script aliases the `docker compose` command with the pre-configured arguments to use the customized compose files.

You can run the Dev Container with the following commands:

```bash
cd .devcontainer
chmod +x docker.sh
./docker.sh build
.docker.sh up -d
```

The Django and the Celery containers will be started **without** running the Django and Celery processes. They can be started manually inside the dev container. The container is autopopulated with VS Code development extensions for Python and a list of pre-configured luanch configurations (for Django and Celery).

Within VS Code open the command palette with `Ctrl+P` and run `Dev Container: Reopen in Container`. VS Code will recognize the presence of the two dev container, and will allow to reopen the current window inside the container's workspace.
Wait a few seconds to let VS Code setup the dev extensions, then you should see the launch configurations.

To simplify the debugging of GeoNode and the GeoNode client, these modules can be installed as editable (PEP-660) with the following commands:

```bash
pip install -e git+https://github.com/GeoNode/geonode.git@master#egg=geonode --src=/usr/src
pip install -e git+https://github.com/GeoNode/geonode-mapstore-client.git@master#egg=django_geonode_mapstore_client --src=/usr/src
```

The modules will be isntalled under `/usr/src` and so at te root of the VS Code workspace.
Notice that at the time of writing Pylance can't resolve PEP-660 editable installs. For this reason the `.vscode/settings.py` contain extrPaths for the modules.

### Running Django
The `GeoNode` launch configuration for Django sets the `ASYNC_SIGNALS` env variable to False. This way GeoNode can be developed and debugged in sync mode, without Celery.
If you want to test Django in async mode, you can switch this variable to `True` and tun Celery (see below).

Running the Debug sessions for Django will start Django with its internal development server.

### Running Celery
Celery exectutions requires luanching three Debug processes:

 - `Celery Worker`: the generic worker process
 - `Celery Beat`: the scheduler
 - `Celery Harvesters`: The worker dedicated to the harvesters

You can also remove the `-X harvesting` argument inside the Celery Worker launch configuration to have also the harvesters running in the same worker. this way you don't need to run the Beat and the Celery Harvesters processes.
