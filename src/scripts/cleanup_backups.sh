#!/bin/sh
# Remove the old backups; run by the uwsgi cron.
# Kept out of uwsgi.ini, where uwsgi would expand the "%" magic variables (%p is the ini path).
DIR=${1:-/backup_restore}

# backup files older than 30 days, except the most recent 3 (a backup is composed by 3 files)
find "$DIR" -maxdepth 1 -type f -mtime +30 -printf '%T@ %p\n' | sort -n | head -n -3 | cut -d' ' -f2- | xargs -r -d '\n' rm -f --

# backup directories older than 30 days, never DIR itself
find "$DIR" -mindepth 1 -maxdepth 1 -type d -ctime +30 -exec rm -rf {} +
