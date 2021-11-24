#!/bin/sh

# This will watch the /geonode-certificates folder and run nginx -s reload whenever there are some changes.
# We use this to reload nginx config when certificates changed.

# inspired/copied from https://github.com/kubernetes/kubernetes/blob/master/examples/https-nginx/auto-reload-nginx.sh

while true
do
        inotifywait -e create -e modify -e delete -e move -r --exclude "\\.certbot\\.lock|\\.well-known" "/geonode-certificates/$LETSENCRYPT_MODE"
        echo "Changes noticed in /geonode-certificates"

        echo "Waiting 5s for additionnal changes"
        sleep 5

        echo "Creating autoissued certificates for HTTP host"
        if [ ! -f "/geonode-certificates/autoissued/privkey.pem" ] || [[ $(find /geonode-certificates/autoissued/privkey.pem -mtime +365 -print) ]]; then
                echo "Autoissued certificate does not exist or is too old, we generate one"
                mkdir -p "/geonode-certificates/autoissued/"
                openssl req -x509 -nodes -days 1825 -newkey rsa:2048 -keyout "/geonode-certificates/autoissued/privkey.pem" -out "/geonode-certificates/autoissued/fullchain.pem" -subj "/CN=${HTTP_HOST:-null}" 
        else
                echo "Autoissued certificate already exists"
                if [ "$LETSENCRYPT_MODE" == "disabled" ] && [ -z "$CUSTOM_SSL_PATH" ]; then
                        echo "Certbot certificate does not exist, we symlink to autoissued"
                        export CERT_PATH="/geonode-certificates/autoissued"
                fi
        fi

        if [ "$LETSENCRYPT_MODE" != "disabled" ]; then
                echo "Creating symbolic link for HTTPS certificate because letsencrypt is enabled"
                mkdir -p "/geonode-certificates/$LETSENCRYPT_MODE"
                if [ -d "/geonode-certificates/$LETSENCRYPT_MODE/live/$HTTPS_HOST/" ]; then
                        echo "Certbot certificate exists, we configure the live cert"
                        export CERT_PATH="/geonode-certificates/$LETSENCRYPT_MODE/live/$HTTPS_HOST/"
                else
                        echo "CRITICAL - cert in path /geonode-certificates/$LETSENCRYPT_MODE/live/$HTTPS_HOST/ does not exists - back to autoissued"
                        export CERT_PATH="/geonode-certificates/autoissued"
                fi
        else
                echo "letsencrypt is $LETSENCRYPT_MODE so I am doing nothing"
                export CERT_PATH="/geonode-certificates/autoissued"
        fi	

        #in case we have custom ssl certificates we override any the self-signed autoissued here.
        if [ -d "$CUSTOM_SSL_PATH" ]; then
                export CERT_PATH=$CUSTOM_SSL_PATH
        fi

        echo "Sanity checks on http/s ports configuration"
        if [ -z "${HTTP_PORT}" ]; then
                HTTP_PORT=80
        fi
        if [ -z "${HTTPS_PORT}" ]; then
                HTTPS_PORT=443
        fi
        if [ -z "${JENKINS_HTTP_PORT}" ]; then
                JENKINS_HTTP_PORT=9080
        fi

        echo "Replacing environement variables"
        envsubst '\$HTTP_PORT \$HTTPS_PORT \$HTTP_HOST \$HTTPS_HOST \$RESOLVER' < /etc/nginx/nginx.conf.envsubst > /etc/nginx/nginx.conf
        envsubst '\$HTTP_PORT \$HTTPS_PORT \$HTTP_HOST \$HTTPS_HOST \$RESOLVER \$CERT_PATH' < /etc/nginx/nginx.https.available.conf.envsubst > /etc/nginx/nginx.https.available.conf
        envsubst '\$HTTP_PORT \$HTTPS_PORT \$HTTP_HOST \$HTTPS_HOST \$JENKINS_HTTP_PORT' < /etc/nginx/sites-enabled/geonode.conf.envsubst > /etc/nginx/sites-enabled/geonode.conf

        echo "Enabling or not https configuration"
        if [ -z "${HTTPS_HOST}" ]; then 
                echo "" > /etc/nginx/nginx.https.enabled.conf
        else
                ln -sf /etc/nginx/nginx.https.available.conf /etc/nginx/nginx.https.enabled.conf
        fi


        # Test nginx configuration
        nginx -t
        # If it passes, we reload
        if [ $? -eq 0 ]
        then
                echo "Configuration valid, we reload..."
                envsubst '\$HTTP_PORT \$HTTPS_PORT \$HTTP_HOST \$HTTPS_HOST \$RESOLVER \$CERT_PATH' < /etc/nginx/nginx.https.available.conf.envsubst > /etc/nginx/nginx.https.available.conf
                nginx -s reload
                rm /geonode-certificates/RELOAD_NGINX
        else
                echo "Configuration not valid, we do not reload."
        fi
done
