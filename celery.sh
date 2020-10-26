#!/bin/bash
celery -A geonode.celery_app:app beat -l DEBUG -f /var/log/celery.log &
celery -A geonode.celery_app:app worker -B -E -Q broadcast,default,geonode,update,cleanup,email,email.events,notifications.events,all.geoserver,geoserver.catalog,geoserver.data,geoserver.events,geonode.layer.viewer -l DEBUG -c 4 -P threads -f /var/log/celery.log &
celery -A geonode.celery_app:app flower --auto_refresh=True --debug=False --broker=${BROKER_URL} --basic_auth=${ADMIN_USERNAME}:${ADMIN_PASSWORD} --address=0.0.0.0 --port=5555 &
