#!/bin/sh

export DOCKER_HOST=${DOCKER_HOST:-}

echo "DOCKER_HOST is ${DOCKER_HOST:-local}..."

export MPPW_VERSION=${MPPW_VERSION:-0.9.0}
export MPPW_REPOSITORY_PREFIX=${MPPW_REPOSITORY_PREFIX:-docker-images.composites.maine.edu:5000/}
export MONGODB_ADMIN_PASSWORD=${MONGODB_ADMIN_PASSWORD:-pick-a-better-password}

if [ -z "${COMPOSE_ONLY}" ]; then
    docker pull ${MPPW_REPOSITORY_PREFIX}ascc/mppw:${MPPW_VERSION}
    docker pull ${MPPW_REPOSITORY_PREFIX}ascc/mppw-mongodb:${MPPW_VERSION}
    docker pull ${MPPW_REPOSITORY_PREFIX}ascc/mppw-nginx:${MPPW_VERSION}
    docker pull ${MPPW_REPOSITORY_PREFIX}ascc/mppw-jupyterhub:${MPPW_VERSION}
fi

if [ "$1" = "down" ]; then
    while true; do
        read -p "Are you sure you want to take the MPPW stack DOWN?  This may destroy data [yn]: " yn
        case $yn in
            [Yy]* ) break;;
            [Nn]* ) exit;;
            * ) echo "Please answer y[es] or n[o].";;
        esac
    done
fi

MPPW_STACK_FILE="$(mktemp)"
docker run --rm --entrypoint cat ${MPPW_REPOSITORY_PREFIX}ascc/mppw:${MPPW_VERSION} ./compose.yml > $MPPW_STACK_FILE
docker-compose -p mppw -f "${MPPW_STACK_FILE}" "$@"