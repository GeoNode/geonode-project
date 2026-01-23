FROM geonode/geonode-base:latest-ubuntu-24.04
RUN mkdir -p /usr/src/project

RUN apt-get update -y && apt-get install curl wget unzip gnupg2 locales -y

RUN sed -i -e 's/# C.UTF-8 UTF-8/C.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

WORKDIR /usr/src/project

COPY src/tasks.py \
    src/entrypoint.sh \
    src/requirements.txt \
    /usr/src/project/

COPY src/wait-for-databases.sh /usr/bin/wait-for-databases
RUN chmod +x /usr/bin/wait-for-databases
RUN chmod +x /usr/src/project/tasks.py \
    && chmod +x /usr/src/project/entrypoint.sh

COPY src/celery.sh /usr/bin/celery-commands
RUN chmod +x /usr/bin/celery-commands

COPY src/celery-cmd /usr/bin/celery-cmd
RUN chmod +x /usr/bin/celery-cmd

RUN python -m pip install -U pip setuptools wheel
RUN yes w | pip install --src /usr/src -r requirements.txt

RUN apt-get autoremove --purge &&\
    apt-get clean &&\
    rm -rf /var/lib/apt/lists/*

COPY src/ /usr/src/project/
RUN yes w | pip install -e .

EXPOSE 8000
