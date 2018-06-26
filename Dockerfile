FROM python:2.7.14-stretch
MAINTAINER GeoNode development team

RUN mkdir -p /usr/src/{app,geonode,{{project_name}}}

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

# Upgrade pip
RUN pip install --upgrade pip

# Install Celery
RUN pip install celery==4.1.0

# To understand the next section (the need for requirements.txt and setup.py)
# Please read: https://packaging.python.org/requirements/

# python-gdal does not seem to work, let's install manually the version that is
# compatible with the provided libgdal-dev
# superseded by pygdal
#RUN pip install GDAL==2.1.3 --global-option=build_ext --global-option="-I/usr/include/gdal"

# install shallow clone of geonode master branch
RUN git clone --depth=1 git://github.com/geosolutions-it/geonode.git --branch 2.7.x /usr/src/geonode
RUN cd /usr/src/geonode/; pip install -r requirements.txt --no-cache-dir; pip install -e .

# fix for known bug in system-wide packages
RUN ln -fs /usr/lib/python2.7/plat-x86_64-linux-gnu/_sysconfigdata*.py /usr/lib/python2.7/

#RUN cp /usr/src/geonode/tasks.py /usr/src/app/
#RUN cp /usr/src/geonode/entrypoint.sh /usr/src/app/

COPY . /usr/src/app

RUN chmod +x /usr/src/app/tasks.py \
    && chmod +x /usr/src/app/entrypoint.sh

# app-specific requirements
RUN pip install --no-cache-dir -r /usr/src/app/requirements.txt
RUN pip install -e /usr/src/app

EXPOSE 8000

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
CMD ["uwsgi", "--ini", "/usr/src/app/uwsgi.ini"]
