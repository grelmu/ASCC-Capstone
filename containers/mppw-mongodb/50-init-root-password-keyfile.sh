#!/usr/bin/env bash

if [ ! -f "$ROOT_PASSWORD_KEYFILE" ]; then

  echo "Generating a new keyfile based on the root password..."

  echo "${MONGO_INITDB_ROOT_PASSWORD}" | md5sum | awk '{print $1}' > "$ROOT_PASSWORD_KEYFILE"
  chmod 400 "$ROOT_PASSWORD_KEYFILE"
  chown mongodb:root "$ROOT_PASSWORD_KEYFILE"

  echo "  Done creating root password keyfile."

fi