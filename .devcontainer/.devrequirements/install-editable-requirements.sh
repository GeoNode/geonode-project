# Define the parent devrequirements directory variable
DEV_REQ_DIR="/usr/src/.devrequirements"

# Safely remove only the specific subfolders if they exist
rm -rf "$DEV_REQ_DIR/geonode" "$DEV_REQ_DIR/django-geonode-mapstore-client"

# Run your installations
yes w | pip install --src "$DEV_REQ_DIR" -e git+https://github.com/GeoNode/geonode.git@master#egg=geonode && \
yes w | pip install --src "$DEV_REQ_DIR" -e git+https://github.com/GeoNode/geonode-mapstore-client.git@master#egg=django_geonode_mapstore_client ;
chown -R 1000:1000 "$DEV_REQ_DIR"/geonode && chown -R 1000:1000 "$DEV_REQ_DIR"/django-geonode-mapstore-client;