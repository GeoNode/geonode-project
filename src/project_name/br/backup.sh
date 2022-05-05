#!/bin/sh
# ##########################################################
# Run a backup
#  SOURCE_URL=$SOURCE_URL TARGET_URL=$TARGET_URL ./{{project_name}}/br/backup.sh $BKP_FOLDER_NAME
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
#  docker exec -it django4{{project_name}} sh -c 'SOURCE_URL=$SOURCE_URL TARGET_URL=$TARGET_URL ./{{project_name}}/br/backup.sh $BKP_FOLDER_NAME'
# ##########################################################

# Exit script in case of error
set -e

echo "-----------------------------------------------------"
echo "STARTING {{project_name}} BACKUP $(date)"
echo "-----------------------------------------------------"

if [ "$1" != "" ]; then
    BKP_FOLDER_NAME="$1"
else
    BKP_FOLDER_NAME="backup_restore"
fi

cd /usr/src/{{project_name}}/ 

./manage.sh backup -i -f -c $PWD/{{project_name}}/br/settings_docker.ini --backup-dir /$BKP_FOLDER_NAME/

BKP_FILE_LATEST=$(find /$BKP_FOLDER_NAME/*.zip -type f -exec stat -c '%Y %n' {} \; | sort -nr | awk 'NR==1,NR==1 {print $2}')
BKP_FILE_NAME=$(echo $BKP_FILE_LATEST | tail -n 1 | grep -oP -m 1 "\/$BKP_FOLDER_NAME\/\K.*" | sed 's|.zip||')

sed -i 's~$~ /'"$BKP_FOLDER_NAME"'/'"$BKP_FILE_NAME"'.zip~g' /$BKP_FOLDER_NAME/$BKP_FILE_NAME.md5

echo "-----------------------------------------------------"
cat /$BKP_FOLDER_NAME/$BKP_FILE_NAME.md5
echo "\n"
echo "-----------------------------------------------------"
