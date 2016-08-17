up:
	# bring up the services
	docker-compose up -d

build:
	docker-compose build django
	docker-compose build celery

sync:
	# set up the database tables
	docker-compose run django python manage.py migrate --noinput

wait:
	sleep 5

logs:
	docker-compose logs --follow

down:
	docker-compose down

test:
	docker-compose run django python manage.py test --failfast

reset: down up wait sync

hardreset: build reset
