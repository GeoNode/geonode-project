FROM geonode/geonode:2.7.x
MAINTAINER GeoNode development team

RUN mkdir -p /usr/src/{app,geonode}

WORKDIR /usr/src/app

# This section is borrowed from the official Django image but adds GDAL and others
RUN apt-get update && apt-get install -y \
		gcc \
		gettext \
		postgresql-client libpq-dev \
		sqlite3 \
                python-gdal python-psycopg2 \
                python-imaging python-lxml \
                python-dev libgdal-dev \
                python-ldap \
                libmemcached-dev libsasl2-dev zlib1g-dev \
                python-pylibmc \
                uwsgi uwsgi-plugin-python \
	--no-install-recommends && rm -rf /var/lib/apt/lists/*


COPY wait-for-databases.sh /usr/bin/wait-for-databases

RUN chmod +x /usr/bin/wait-for-databases

# fix for known bug in system-wide packages
RUN ln -fs /usr/lib/python2.7/plat-x86_64-linux-gnu/_sysconfigdata*.py /usr/lib/python2.7/

#RUN cp /usr/src/geonode/tasks.py /usr/src/app/
#RUN cp /usr/src/geonode/entrypoint.sh /usr/src/app/

COPY . /usr/src/app

RUN chmod +x /usr/src/app/tasks.py \
    && chmod +x /usr/src/app/entrypoint.sh

COPY requirements.txt /usr/src/app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt --upgrade
RUN python manage.py makemigrations --settings={{ project_name }}.settings
RUN python manage.py migrate --settings={{ project_name }}.settings

EXPOSE 8000

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
CMD ["uwsgi", "--ini", "/usr/src/app/uwsgi.ini"]