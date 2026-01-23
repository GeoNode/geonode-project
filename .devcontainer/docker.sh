#!/bin/bash
set -o allexport
source ../.env
set +o allexport
docker compose -f ../docker-compose.yml -f docker-compose-dev.yml -f ./django/docker-compose.yml -f ./celery/docker-compose.yml "$@"