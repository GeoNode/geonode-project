FROM tomcat:9-jre8
MAINTAINER GeoNode Development Team

#
# Set GeoServer version and data directory
#
ENV GEOSERVER_VERSION=2.17.2
ENV GEOSERVER_DATA_DIR="/geoserver_data/data"

#
# Download and install GeoServer
#
RUN cd /usr/local/tomcat/webapps \
    && wget --no-check-certificate --progress=bar:force:noscroll https://build.geo-solutions.it/geonode/geoserver/latest/geoserver-${GEOSERVER_VERSION}.war \
    && unzip -q geoserver-${GEOSERVER_VERSION}.war -d geoserver \
    && rm geoserver-${GEOSERVER_VERSION}.war \
    && mkdir -p $GEOSERVER_DATA_DIR

VOLUME $GEOSERVER_DATA_DIR

# added by simonelanucara https://github.com/simonelanucara
# Optionally add JAI, ImageIO and Marlin Render for improved Geoserver performance
WORKDIR /tmp
ARG JAI_IMAGEIO=true
RUN if [ "$JAI_IMAGEIO" = true ]; then \
    # marlin plugin
    wget https://github.com/bourgesl/marlin-renderer/releases/download/v0_9_3/marlin-0.9.3-Unsafe.jar && \
    mv /tmp/marlin-0.9.3-Unsafe.jar /usr/local/tomcat/webapps/geoserver/WEB-INF/lib/ ; \
    fi

RUN wget --no-check-certificate https://build.geo-solutions.it/geonode/geoserver/latest/postgis-jdbc-1.3.3/postgis-jdbc-1.3.3.jar && \
    wget --no-check-certificate https://build.geo-solutions.it/geonode/geoserver/latest/hibernate-spatial-postgis-1.1.3.1/hibernate-spatial-postgis-1.1.3.1.jar && \
    rm /usr/local/tomcat/webapps/geoserver/WEB-INF/lib/hibernate-spatial-h2-geodb-1.1.3.1.jar && \
    mv hibernate-spatial-postgis-1.1.3.1.jar /usr/local/tomcat/webapps/geoserver/WEB-INF/lib/ && \
    mv postgis-jdbc-1.3.3.jar /usr/local/tomcat/webapps/geoserver/WEB-INF/lib/

###########docker host###############
# Set DOCKERHOST variable if DOCKER_HOST exists
ARG DOCKERHOST=${DOCKERHOST}
# for debugging
RUN echo -n #1===>DOCKERHOST=${DOCKERHOST}
#
ENV DOCKERHOST ${DOCKERHOST}
# for debugging
RUN echo -n #2===>DOCKERHOST=${DOCKERHOST}

###########docker host ip#############
# Set GEONODE_HOST_IP address if it exists
ARG GEONODE_HOST_IP=${GEONODE_HOST_IP}
# for debugging
RUN echo -n #1===>GEONODE_HOST_IP=${GEONODE_HOST_IP}
#
ENV GEONODE_HOST_IP ${GEONODE_HOST_IP}
# for debugging
RUN echo -n #2===>GEONODE_HOST_IP=${GEONODE_HOST_IP}
# If empty set DOCKER_HOST_IP to GEONODE_HOST_IP
ENV DOCKER_HOST_IP=${DOCKER_HOST_IP:-${GEONODE_HOST_IP}}
# for debugging
RUN echo -n #1===>DOCKER_HOST_IP=${DOCKER_HOST_IP}
# Trying to set the value of DOCKER_HOST_IP from DOCKER_HOST
RUN if ! [ -z ${DOCKER_HOST_IP} ]; \
    then echo export DOCKER_HOST_IP=${DOCKERHOST} | \
    sed 's/tcp:\/\/\([^:]*\).*/\1/' >> /root/.bashrc; \
    else echo "DOCKER_HOST_IP is already set!"; fi
# for debugging
RUN echo -n #2===>DOCKER_HOST_IP=${DOCKER_HOST_IP}

# Set WEBSERVER public port
ARG PUBLIC_PORT=${PUBLIC_PORT}
# for debugging
RUN echo -n #1===>PUBLIC_PORT=${PUBLIC_PORT}
#
ENV PUBLIC_PORT=${PUBLIC_PORT}
# for debugging
RUN echo -n #2===>PUBLIC_PORT=${PUBLIC_PORT}

# set nginx base url for geoserver
RUN echo export NGINX_BASE_URL=http://${NGINX_HOST}:${NGINX_PORT}/ | \
    sed 's/tcp:\/\/\([^:]*\).*/\1/' >> /root/.bashrc

# copy the script and perform the run of scripts from entrypoint.sh
RUN mkdir -p /usr/local/tomcat/tmp
WORKDIR /usr/local/tomcat/tmp
COPY set_geoserver_auth.sh /usr/local/tomcat/tmp
COPY setup_auth.sh /usr/local/tomcat/tmp
COPY requirements.txt /usr/local/tomcat/tmp
COPY get_dockerhost_ip.py /usr/local/tomcat/tmp
COPY get_nginxhost_ip.py /usr/local/tomcat/tmp
COPY entrypoint.sh /usr/local/tomcat/tmp
COPY datasource-ovr.properties /usr/local/tomcat/tmp
COPY multidump.sh /usr/local/tomcat/tmp
COPY multidump-alt.sh /usr/local/tomcat/tmp

RUN apt-get update \
    && apt-get -y upgrade \
    && apt-get install -y openjdk-8-jdk \
    && apt-get install -y python3 python3-pip python3-dev \
    && chmod +x /usr/local/tomcat/tmp/set_geoserver_auth.sh \
    && chmod +x /usr/local/tomcat/tmp/setup_auth.sh \
    && chmod +x /usr/local/tomcat/tmp/entrypoint.sh \
    && pip3 install pip==9.0.3 \
    && pip3 install -r requirements.txt \
    && chmod +x /usr/local/tomcat/tmp/get_dockerhost_ip.py \
    && chmod +x /usr/local/tomcat/tmp/get_nginxhost_ip.py

ENV JAVA_OPTS="-Djava.awt.headless=true -XX:+UnlockDiagnosticVMOptions -XX:+LogVMOutput -XX:LogFile=/var/log/jvm.log -XX:MaxPermSize=512m -XX:PermSize=256m -Xms512m -Xmx2048m -XX:+UseConcMarkSweepGC -XX:+UseParNewGC -XX:ParallelGCThreads=4 -Dfile.encoding=UTF8 -Djavax.servlet.request.encoding=UTF-8 -Djavax.servlet.response.encoding=UTF-8 -Duser.timezone=GMT -Dorg.geotools.shapefile.datetime=false -DGEOSERVER_CSRF_DISABLED=true -DPRINT_BASE_URL=http://geoserver:8080/geoserver/pdf -Xbootclasspath/a:/usr/local/tomcat/webapps/geoserver/WEB-INF/lib/marlin-0.9.3-Unsafe.jar -Dsun.java2d.renderer=org.marlin.pisces.MarlinRenderingEngine"

CMD ["/usr/local/tomcat/tmp/entrypoint.sh"]
