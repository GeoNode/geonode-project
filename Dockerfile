FROM geonode/geonode-base:latest-ubuntu-22.10
LABEL GeoNode development team

RUN mkdir -p /usr/src/{{project_name}}

# add bower and grunt command
COPY src /usr/src/{{project_name}}/
WORKDIR /usr/src/{{project_name}}

COPY src/monitoring-cron /etc/cron.d/monitoring-cron
RUN chmod 0644 /etc/cron.d/monitoring-cron
RUN crontab /etc/cron.d/monitoring-cron
RUN touch /var/log/cron.log
RUN service cron start

COPY src/wait-for-databases.sh /usr/bin/wait-for-databases
RUN chmod +x /usr/bin/wait-for-databases
RUN chmod +x /usr/src/{{project_name}}/tasks.py \
    && chmod +x /usr/src/{{project_name}}/entrypoint.sh

COPY src/celery.sh /usr/bin/celery-commands
RUN chmod +x /usr/bin/celery-commands

COPY src/celery-cmd /usr/bin/celery-cmd
RUN chmod +x /usr/bin/celery-cmd

# # Install "geonode-contribs" apps
# RUN cd /usr/src; git clone https://github.com/GeoNode/geonode-contribs.git -b master
# # Install logstash and centralized dashboard dependencies
# RUN cd /usr/src/geonode-contribs/geonode-logstash; pip install --upgrade  -e . \
#     cd /usr/src/geonode-contribs/ldap; pip install --upgrade  -e .

RUN pip install --upgrade --no-cache-dir  --src /usr/src -r requirements.txt
RUN pip install --upgrade  -e .

# Cleanup apt update lists
RUN rm -rf /var/lib/apt/lists/*

# Export ports
EXPOSE 8000

# We provide no command or entrypoint as this image can be used to serve the django project or run celery tasks
# ENTRYPOINT /usr/src/{{project_name}}/entrypoint.sh
