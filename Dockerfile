FROM python:3.7.6-stretch
MAINTAINER GeoNode development team

RUN mkdir -p /usr/src/{{project_name}}

# Enable postgresql-client-11.2
RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ stretch-pgdg main" | tee /etc/apt/sources.list.d/pgdg.list
RUN wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -


# This section is borrowed from the official Django image but adds GDAL and others
RUN apt-get update && apt-get install -y \
		gcc \
                zip \
		gettext \
		postgresql-client-11 libpq-dev \
		sqlite3 \
                python3-gdal python3-psycopg2 \
                python3-pil python3-lxml \
                python3-dev libgdal-dev \
                libmemcached-dev libsasl2-dev zlib1g-dev \
                python3-pylibmc \
                uwsgi uwsgi-plugin-python3 \
	--no-install-recommends && rm -rf /var/lib/apt/lists/*


RUN printf "deb http://archive.debian.org/debian/ jessie main\ndeb-src http://archive.debian.org/debian/ jessie main\ndeb http://security.debian.org jessie/updates main\ndeb-src http://security.debian.org jessie/updates main" > /etc/apt/sources.list
RUN apt-get update && apt-get install -y geoip-bin

# add bower and grunt command
COPY . /usr/src/{{project_name}}/
WORKDIR /usr/src/{{project_name}}

RUN apt-get update && apt-get -y install cron
COPY monitoring-cron /etc/cron.d/monitoring-cron
RUN chmod 0644 /etc/cron.d/monitoring-cron
RUN crontab /etc/cron.d/monitoring-cron
RUN touch /var/log/cron.log
RUN service cron start

COPY wait-for-databases.sh /usr/bin/wait-for-databases
RUN chmod +x /usr/bin/wait-for-databases
RUN chmod +x /usr/src/{{project_name}}/tasks.py \
    && chmod +x /usr/src/{{project_name}}/entrypoint.sh

# Upgrade pip
RUN pip install pip==20.1

# app-specific requirements
RUN pip install --upgrade --no-cache-dir --src /usr/src -r requirements.txt
RUN pip install --upgrade -e .

# Install pygdal (after requirements for numpy 1.16)
RUN pip install pygdal==$(gdal-config --version).*

# Install "geonode-contribs" apps
RUN cd /usr/src; git clone https://github.com/GeoNode/geonode-contribs.git -b master
# Install logstash and centralized dashboard dependencies
RUN cd /usr/src/geonode-contribs/geonode-logstash; pip install --upgrade -e .

ENTRYPOINT service cron restart && /usr/src/{{project_name}}/entrypoint.sh
