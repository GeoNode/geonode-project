#!/bin/sh
set -eu

if [ "${1:-}" = "postgres" ] || [ "${1:-}" != "${1#-}" ]; then
  : "${POSTGRESQL_MAX_CONNECTIONS:=200}"
  case "$POSTGRESQL_MAX_CONNECTIONS" in
    ''|*[!0-9]*)
      echo "POSTGRESQL_MAX_CONNECTIONS must be a positive integer" >&2
      exit 1
      ;;
  esac

  cat > /tmp/geonode-postgresql-defaults.conf <<EOF
# Generated at container start from GeoNode environment variables.
max_connections = ${POSTGRESQL_MAX_CONNECTIONS}
EOF

  if [ -n "${POSTGRESQL_PROFILE:-}" ]; then
    profile_dir="/etc/postgresql/profiles/${POSTGRESQL_PROFILE}"
    if [ ! -d "$profile_dir" ]; then
      echo "PostgreSQL profile not found: ${POSTGRESQL_PROFILE}" >&2
      exit 1
    fi
    echo "include_dir '${profile_dir}'" >> /tmp/geonode-postgresql-defaults.conf
  fi
fi

exec docker-entrypoint.sh "$@"
