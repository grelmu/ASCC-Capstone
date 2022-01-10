#!/usr/bin/env bash

echo "Creating root password keyfile..."
echo "${MONGO_INITDB_ROOT_PASSWORD}" | md5sum | awk '{print $1}' > /root_password_keyfile.key
chmod 400 /root_password_keyfile.key
chown mongodb:root /root_password_keyfile.key
echo "  Done creating root password keyfile."

set -m
/usr/local/bin/docker-entrypoint.sh "$@" &

if [ -n "$MONGO_INITRS_CONFIG" ]; then
  echo "Initializing replica set..."
  mongo --nodb /usr/local/bin/rs-init.js
  echo "  Done initializing replica set."
fi

fg