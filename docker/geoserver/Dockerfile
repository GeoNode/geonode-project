FROM tomcat:8
MAINTAINER Wayner Barrios <waybarrios@gmail.com>

#
# Set GeoServer version and data directory 
#
ENV GEOSERVER_VERSION=2.6.0 \
    GEOSERVER_DATA_DIR="/geoserver_data"

#
# Download and install GeoServer
#
RUN cd /usr/local/tomcat/webapps \
    && wget --progress=bar:force:noscroll http://sourceforge.net/projects/geoserver/files/GeoServer/$GEOSERVER_VERSION/geoserver-$GEOSERVER_VERSION-war.zip \
    && unzip -q geoserver-$GEOSERVER_VERSION-war.zip \
    && rm geoserver-$GEOSERVER_VERSION-war.zip \
    && mkdir $GEOSERVER_DATA_DIR

VOLUME $GEOSERVER_DATA_DIR
