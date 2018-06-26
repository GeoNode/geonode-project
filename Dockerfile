FROM geonode/geonode:2.7.x
MAINTAINER GeoNode development team

COPY requirements.txt /usr/src/app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt --upgrade
RUN python manage.py makemigrations --settings={{ project_name }}.settings
RUN python manage.py migrate --settings={{ project_name }}.settings

EXPOSE 8000

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
CMD ["uwsgi", "--ini", "/usr/src/app/uwsgi.ini"]