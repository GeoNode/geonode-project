#!/usr/bin/env bash
set -euo pipefail

# Defaults
GEONODE_BRANCH="master"
MAPSTORE_BRANCH="master"

usage() {
    echo "Usage: $0 [-g|--geonode-branch <branch>] [-m|--mapstore-branch <branch>]"
    echo ""
    echo "  -g, --geonode-branch      Branch/tag for geonode/geonode (default: master)"
    echo "  -m, --mapstore-branch     Branch/tag for GeoNode/geonode-mapstore-client (default: master)"
    echo "  -h, --help                Show this help message"
    exit 1
}

# Parse options
while [[ $# -gt 0 ]]; do
    case "$1" in
        -g|--geonode-branch)
            GEONODE_BRANCH="$2"
            shift 2
            ;;
        -m|--mapstore-branch)
            MAPSTORE_BRANCH="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Parent devrequirements directory
DEV_REQ_DIR="/usr/src/.devrequirements"

# repo_name | folder_name | git_url | egg_name | branch
REPOS=(
    "geonode|geonode|https://github.com/GeoNode/geonode.git|geonode|${GEONODE_BRANCH}"
    "geonode-mapstore-client|django-geonode-mapstore-client|https://github.com/GeoNode/geonode-mapstore-client.git|django_geonode_mapstore_client|${MAPSTORE_BRANCH}"
)

for entry in "${REPOS[@]}"; do
    IFS='|' read -r name folder url egg branch <<< "$entry"

    echo ">>> Installing ${name} @ ${branch}"

    # Safely remove the specific subfolder if it exists
    rm -rf "${DEV_REQ_DIR}/${folder}"

    # Install
    yes w | pip install --src "$DEV_REQ_DIR" -e "git+${url}@${branch}#egg=${egg}"

    # Fix ownership
    chown -R 1000:1000 "${DEV_REQ_DIR}/${folder}"
done