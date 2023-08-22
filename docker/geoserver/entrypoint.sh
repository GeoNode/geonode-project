#!/bin/bash
set -e

source /root/.bashrc


INVOKE_LOG_STDOUT=${INVOKE_LOG_STDOUT:-TRUE}
invoke () {
    if [ $INVOKE_LOG_STDOUT = 'true' ] || [ $INVOKE_LOG_STDOUT = 'True' ]
    then
        /usr/local/bin/invoke $@
    else
        /usr/local/bin/invoke $@ > /usr/src/geonode/invoke.log 2>&1
    fi
    echo "$@ tasks done"
}

# control the values of LB settings if present
if [ -n "$GEONODE_LB_HOST_IP" ];
then
    echo "GEONODE_LB_HOST_IP is defined and not empty with the value '$GEONODE_LB_HOST_IP' \n"
    echo export GEONODE_LB_HOST_IP=${GEONODE_LB_HOST_IP} >> /root/.override_env
else
    echo "GEONODE_LB_HOST_IP is either not defined or empty with the value 'django' \n"
    echo export GEONODE_LB_HOST_IP=django >> /root/.override_env
fi

if [ -n "$GEONODE_LB_PORT" ];
then
    echo "GEONODE_LB_HOST_IP is defined and not empty with the value '$GEONODE_LB_PORT' \n"
    echo export GEONODE_LB_PORT=${GEONODE_LB_PORT} >> /root/.override_env
else
    echo "GEONODE_LB_PORT is either not defined or empty with the value '8000' \n"
    echo export GEONODE_LB_PORT=8000 >> /root/.override_env
fi

if [ ! -z "${GEOSERVER_JAVA_OPTS}" ]
then
    echo "GEOSERVER_JAVA_OPTS is filled so I replace the value of '$JAVA_OPTS' with '$GEOSERVER_JAVA_OPTS' \n"
    JAVA_OPTS=${GEOSERVER_JAVA_OPTS}
fi

# control the value of NGINX_BASE_URL variable
if [ -z `echo ${NGINX_BASE_URL} | sed 's/http:\/\/\([^:]*\).*/\1/'` ]
then
    echo "NGINX_BASE_URL is empty so I'll use the default Geoserver location \n"
    echo "Setting GEOSERVER_LOCATION='${GEOSERVER_PUBLIC_LOCATION}' \n"
    echo export GEOSERVER_LOCATION=${GEOSERVER_PUBLIC_LOCATION} >> /root/.override_env
else
    echo "NGINX_BASE_URL is filled so GEOSERVER_LOCATION='${NGINX_BASE_URL}' \n"
    echo "Setting GEOSERVER_LOCATION='${NGINX_BASE_URL}' \n"
    echo export GEOSERVER_LOCATION=${NGINX_BASE_URL} >> /root/.override_env
fi

if [ -n "$SUBSTITUTION_URL" ];
then
    echo "SUBSTITUTION_URL is defined and not empty with the value '$SUBSTITUTION_URL' \n"
    echo "Setting GEONODE_LOCATION='${SUBSTITUTION_URL}' \n"
    echo export GEONODE_LOCATION=${SUBSTITUTION_URL} >> /root/.override_env
else
    echo "SUBSTITUTION_URL is either not defined or empty so I'll use the default GeoNode location \n"
    echo "Setting GEONODE_LOCATION='http://${GEONODE_LB_HOST_IP}:${GEONODE_LB_PORT}' \n"
    echo export GEONODE_LOCATION=http://${GEONODE_LB_HOST_IP}:${GEONODE_LB_PORT} >> /root/.override_env
fi

# set basic tagname
TAGNAME=( "baseUrl" "authApiKey" )

if ! [ -f ${GEOSERVER_DATA_DIR}/security/auth/geonodeAuthProvider/config.xml ]
then
    echo "Configuration file '$GEOSERVER_DATA_DIR'/security/auth/geonodeAuthProvider/config.xml is not available so it is gone to skip \n"
else
    # backup geonodeAuthProvider config.xml
    cp ${GEOSERVER_DATA_DIR}/security/auth/geonodeAuthProvider/config.xml ${GEOSERVER_DATA_DIR}/security/auth/geonodeAuthProvider/config.xml.orig
    # run the setting script for geonodeAuthProvider
    /usr/local/tomcat/tmp/set_geoserver_auth.sh ${GEOSERVER_DATA_DIR}/security/auth/geonodeAuthProvider/config.xml ${GEOSERVER_DATA_DIR}/security/auth/geonodeAuthProvider/ ${TAGNAME[@]} > /dev/null 2>&1
fi

# backup geonode REST role service config.xml
cp "${GEOSERVER_DATA_DIR}/security/role/geonode REST role service/config.xml" "${GEOSERVER_DATA_DIR}/security/role/geonode REST role service/config.xml.orig"
# run the setting script for geonode REST role service
/usr/local/tomcat/tmp/set_geoserver_auth.sh "${GEOSERVER_DATA_DIR}/security/role/geonode REST role service/config.xml" "${GEOSERVER_DATA_DIR}/security/role/geonode REST role service/" ${TAGNAME[@]} > /dev/null 2>&1

# set oauth2 filter tagname
TAGNAME=( "cliendId" "clientSecret" "accessTokenUri" "userAuthorizationUri" "redirectUri" "checkTokenEndpointUrl" "logoutUri" )

# backup geonode-oauth2 config.xml
cp ${GEOSERVER_DATA_DIR}/security/filter/geonode-oauth2/config.xml ${GEOSERVER_DATA_DIR}/security/filter/geonode-oauth2/config.xml.orig
# run the setting script for geonode-oauth2
/usr/local/tomcat/tmp/set_geoserver_auth.sh ${GEOSERVER_DATA_DIR}/security/filter/geonode-oauth2/config.xml ${GEOSERVER_DATA_DIR}/security/filter/geonode-oauth2/ "${TAGNAME[@]}" > /dev/null 2>&1

# set global tagname
TAGNAME=( "proxyBaseUrl" )

# backup global.xml
cp ${GEOSERVER_DATA_DIR}/global.xml ${GEOSERVER_DATA_DIR}/global.xml.orig
# run the setting script for global configuration
/usr/local/tomcat/tmp/set_geoserver_auth.sh ${GEOSERVER_DATA_DIR}/global.xml ${GEOSERVER_DATA_DIR}/ ${TAGNAME[@]} > /dev/null 2>&1

# set correct amqp broker url
sed -i -e 's/localhost/rabbitmq/g' ${GEOSERVER_DATA_DIR}/notifier/notifier.xml

# exclude wrong dependencies
sed -i -e 's/xom-\*\.jar/xom-\*\.jar,bcprov\*\.jar/g' /usr/local/tomcat/conf/catalina.properties

# J2 templating for this docker image we should also do it for other configuration files in /usr/local/tomcat/tmp

declare -a geoserver_datadir_template_dirs=("geofence")

for template in in ${geoserver_datadir_template_dirs[*]}; do
    #Geofence templates
    if [ "$template" == "geofence" ]; then
      cp -R /templates/$template/* ${GEOSERVER_DATA_DIR}/geofence

      for f in $(find ${GEOSERVER_DATA_DIR}/geofence/ -type f -name "*.j2"); do
          echo -e "Evaluating template\n\tSource: $f\n\tDest: ${f%.j2}"
          /usr/local/bin/j2 $f > ${f%.j2}
          rm -f $f
      done

    fi
done

# configure CORS (inspired by https://github.com/oscarfonts/docker-geoserver)
# if enabled, this will add the filter definitions
# to the end of the web.xml
# (this will only happen if our filter has not yet been added before)
if [ "${GEOSERVER_CORS_ENABLED}" = "true" ] || [ "${GEOSERVER_CORS_ENABLED}" = "True" ]; then
  if ! grep -q DockerGeoServerCorsFilter "$CATALINA_HOME/webapps/geoserver/WEB-INF/web.xml"; then
    echo "Enable CORS for $CATALINA_HOME/webapps/geoserver/WEB-INF/web.xml"
    sed -i "\:</web-app>:i\\
    <filter>\n\
      <filter-name>DockerGeoServerCorsFilter</filter-name>\n\
      <filter-class>org.apache.catalina.filters.CorsFilter</filter-class>\n\
      <init-param>\n\
          <param-name>cors.allowed.origins</param-name>\n\
          <param-value>${GEOSERVER_CORS_ALLOWED_ORIGINS}</param-value>\n\
      </init-param>\n\
      <init-param>\n\
          <param-name>cors.allowed.methods</param-name>\n\
          <param-value>${GEOSERVER_CORS_ALLOWED_METHODS}</param-value>\n\
      </init-param>\n\
      <init-param>\n\
        <param-name>cors.allowed.headers</param-name>\n\
        <param-value>${GEOSERVER_CORS_ALLOWED_HEADERS}</param-value>\n\
      </init-param>\n\
    </filter>\n\
    <filter-mapping>\n\
      <filter-name>DockerGeoServerCorsFilter</filter-name>\n\
      <url-pattern>/*</url-pattern>\n\
    </filter-mapping>" "$CATALINA_HOME/webapps/geoserver/WEB-INF/web.xml";
  fi
fi

if [ ${FORCE_REINIT} = "true" ]  || [ ${FORCE_REINIT} = "True" ] || [ ! -e "${GEOSERVER_DATA_DIR}/geoserver_init.lock" ]; then
    # Run async configuration, it needs Geoserver to be up and running
    nohup sh -c "invoke configure-geoserver" &
fi

# start tomcat
exec env JAVA_OPTS="${JAVA_OPTS}" catalina.sh run
