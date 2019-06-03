#!/bin/bash
set -e

/usr/local/bin/invoke update

source $HOME/.override_env

echo DATABASE_URL=$DATABASE_URL
echo GEODATABASE_URL=$GEODATABASE_URL
echo SITEURL=$SITEURL
echo ALLOWED_HOSTS=$ALLOWED_HOSTS
echo GEOSERVER_PUBLIC_LOCATION=$GEOSERVER_PUBLIC_LOCATION

/usr/local/bin/invoke waitfordbs
echo "waitfordbs task done"

echo "running migrations"
/usr/local/bin/invoke migrations
echo "migrations task done"

cmd="$@"

echo DOCKER_ENV=$DOCKER_ENV

if [ -z ${DOCKER_ENV} ] || [ ${DOCKER_ENV} = "development" ]
then

    echo "Executing standard Django server $cmd for Development"

else

    if [ ${IS_CELERY} = "true" ]  || [ ${IS_CELERY} = "True" ]
    then

        cmd=$CELERY_CMD
        echo "Executing Celery server $cmd for Production"

    else

        if [ ! -e "/mnt/volumes/statics/geonode_init.lock" ]; then
            /usr/local/bin/invoke prepare
            echo "prepare task done"
            /usr/local/bin/invoke fixtures
            echo "fixture task done"
        fi
        /usr/local/bin/invoke initialized
        echo "initialized"

        echo "refresh static data"
        /usr/local/bin/invoke statics
        echo "static data refreshed"

        cmd=$UWSGI_CMD
        echo "Executing UWSGI server $cmd for Production"

    fi

fi
echo 'got command ${cmd}'
exec $cmd
