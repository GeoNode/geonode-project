#!/bin/sh
# ##########################################################
# Run a restore
#  SOURCE_URL=$SOURCE_URL TARGET_URL=$TARGET_URL ./geonode_project/br/restore.sh $BKP_FOLDER_NAME
#   - BKP_FOLDER_NAME:
#     Default value = backup_restore
#     Shared Backup Folder name.
#     The scripts assume it is located on "root" e.g.: /$BKP_FOLDER_NAME/
#
#   - SOURCE_URL:
#     Source Server URL, the one generating the "backup" file.
#
#   - TARGET_URL:
#     Target Server URL, the one which must be synched.
#
# e.g.:
#  docker exec -it django4geonode_project sh -c 'SOURCE_URL=$SOURCE_URL TARGET_URL=$TARGET_URL ./geonode_project/br/restore.sh $BKP_FOLDER_NAME'
# ##########################################################

# Exit script in case of error
set -e

echo "-----------------------------------------------------"
echo "STARTING project RESTORE $(date)"
echo "-----------------------------------------------------"

if [ "$1" != "" ]; then
    BKP_FOLDER_NAME="$1"
else
    BKP_FOLDER_NAME="backup_restore"
fi

if [ -z "$SOURCE_URL" ] || [ -z "$TARGET_URL" ]
then
    echo "-----------------------------------------------------"
    echo "ERROR: SOURCE_URL and TARGET_URL environment variables not set"
    echo " e.g.: SOURCE_URL=test.webgis.adbpo.it TARGET_URL=staging.webgis.adbpo.it"
    echo "-----------------------------------------------------"
    exit 1
else
    echo "$SOURCE_URL --> $TARGET_URL"
fi

cd /usr/src/project/

echo "-----------------------------------------------------"
echo " 1. BACKUP $TARGET_URL"
echo "-----------------------------------------------------"

NEW_UUID=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1)
mkdir /$BKP_FOLDER_NAME/$NEW_UUID/
SOURCE_URL=$SOURCE_URL TARGET_URL=$TARGET_URL ./geonode_project/br/backup.sh $BKP_FOLDER_NAME/$NEW_UUID

echo "-----------------------------------------------------"
echo " 2. CHECK BACKUP.md5 $TARGET_URL"
echo "-----------------------------------------------------"

BKP_FILE_LATEST=$(find /$BKP_FOLDER_NAME/$NEW_UUID/*.zip -type f -exec stat -c '%Y %n' {} \; | sort -nr | awk 'NR==1,NR==1 {print $2}')
BKP_FILE_NAME=$(echo $BKP_FILE_LATEST | tail -n 1 | grep -oP -m 1 "\/$BKP_FOLDER_NAME\/$NEW_UUID\/\K.*" | sed 's|.zip||')

if md5sum -c /$BKP_FOLDER_NAME/$NEW_UUID/$BKP_FILE_NAME.md5; then

    echo "-----------------------------------------------------"
    echo " - Original Backup of $TARGET_URL --> /$BKP_FOLDER_NAME/$NEW_UUID/"
    echo " 3. RESTORE FROM $SOURCE_URL"
    echo "-----------------------------------------------------"

    RECOVERY_FILE_NAME=$BKP_FILE_NAME
    BKP_FILE_LATEST=$(find /$BKP_FOLDER_NAME/*.zip -type f -exec stat -c '%Y %n' {} \; | sort -nr | awk 'NR==1,NR==1 {print $2}')
    BKP_FILE_NAME=$(echo $BKP_FILE_LATEST | tail -n 1 | grep -oP -m 1 "\/$BKP_FOLDER_NAME\/\K.*" | sed 's|.zip||')

    if md5sum -c /$BKP_FOLDER_NAME/$BKP_FILE_NAME.md5; then
        # The MD5 sum matched
        django-admin restore -l -n -f --backup-file /$BKP_FOLDER_NAME/$BKP_FILE_NAME.zip --recovery-file /$BKP_FOLDER_NAME/$NEW_UUID/$RECOVERY_FILE_NAME.zip
        django-admin migrate_baseurl -f --source-address=$SOURCE_URL --target-address=$TARGET_URL
        django-admin create_tile_layers -f
        django-admin set_all_datasets_metadata -d -i
        echo "-----------------------------------------------------"
        echo " Fixup GeoServer styles"
        echo "-----------------------------------------------------"
        XML_FILE="/geoserver_data/data/workspaces/geonode/workspace.xml"
        ID_VALUE=$(sed -n 's|.*<id>\(.*\)</id>.*|\1|p' "$XML_FILE")
        find /geoserver_data/data/workspaces/geonode/styles -type f -name "*.xml" -exec sed -i "s|<name>geonode</name>|<id>$ID_VALUE</id>|g" {} +
        echo " GeoServer reloading catalog"
        curl -w "%{http_code}\n" -u $GEOSERVER_ADMIN_USER:$GEOSERVER_ADMIN_PASSWORD -X POST "http://geoserver:8080/geoserver/rest/reload"
        echo "-----------------------------------------------------"
        echo " Geoserver Styles fixup completed"
        echo "-----------------------------------------------------"
        echo "-----------------------------------------------------"
        echo " Cleanup memcached"
        echo "-----------------------------------------------------"
        echo "flush_all" | nc -q 1 memcached 11211
        echo "-----------------------------------------------------"
        echo "Cache cleanup done"
        echo "-----------------------------------------------------"
    else
        # The MD5 sum didn't match
        echo "-----------------------------------------------------"
        echo " - Original Backup of $TARGET_URL --> /$BKP_FOLDER_NAME/$NEW_UUID/"
        echo "ERROR: The MD5 sum didn't match"
        echo "-----------------------------------------------------"
        exit 1
    fi
else
    # The MD5 sum didn't match
    echo "-----------------------------------------------------"
    echo " - Original Backup of $TARGET_URL --> /$BKP_FOLDER_NAME/$NEW_UUID/"
    echo "ERROR: Could not save $TARGET_URL"
    echo "-----------------------------------------------------"
    exit 1
fi

echo "-----------------------------------------------------"
echo " - Original Backup of $TARGET_URL --> /$BKP_FOLDER_NAME/$NEW_UUID/"
echo "FINISHED project RESTORE $(date)"
echo "-----------------------------------------------------"
