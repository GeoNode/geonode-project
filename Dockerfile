FROM geonode/geonode:2.7.x
MAINTAINER GeoNode development team

RUN mkdir -p /usr/src/{app,{{project_name}}}

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

COPY . /usr/src/app

# fix for known bug in system-wide packages
RUN ln -fs /usr/lib/python2.7/plat-x86_64-linux-gnu/_sysconfigdata*.py /usr/lib/python2.7/

# Upgrade pip
RUN pip install --upgrade pip

# To understand the next section (the need for requirements.txt and setup.py)
# Please read: https://packaging.python.org/requirements/

# python-gdal does not seem to work, let's install manually the version that is
# compatible with the provided libgdal-dev
RUN pip install GDAL==1.10 --global-option=build_ext --global-option="-I/usr/include/gdal"

# install shallow clone of geonode master branch
RUN cd ./src/geonode/; pip install --upgrade --no-cache-dir -r requirements.txt; pip install --upgrade -e .

RUN cp ./src/geonode/tasks.py /usr/src/app/
RUN cp ./src/geonode/entrypoint.sh /usr/src/app/

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
