FROM geonode/geonode-base:latest-ubuntu-24.04

ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8
WORKDIR /usr/src/project

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    curl \
    wget \
    unzip \
    gnupg2 \
    locales \
    netcat-openbsd \
    && sed -i -e 's/# C.UTF-8 UTF-8/C.UTF-8 UTF-8/' /etc/locale.gen \
    && locale-gen \
    && apt-get autoremove --purge -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir -U pip setuptools wheel

COPY src/wait-for-databases.sh /usr/bin/wait-for-databases
COPY src/celery.sh /usr/bin/celery-commands
COPY src/celery-cmd /usr/bin/celery-cmd
RUN chmod +x /usr/bin/wait-for-databases /usr/bin/celery-commands /usr/bin/celery-cmd

COPY src/ /usr/src/project/
RUN chmod +x /usr/src/project/tasks.py /usr/src/project/entrypoint.sh

RUN pip install --no-cache-dir -e .

EXPOSE 8000
