#!/usr/bin/env bash

for f in /docker-entrypoint.d/*; do
  case "$f" in
    *.sh) echo "$0: running $f"; . "$f" ;;
    *)    echo "$0: ignoring $f" ;;
  esac
done

set -m
/usr/local/bin/docker-entrypoint.sh "$@" &

if [ -n "$MONGO_INITRS_CONFIG" ]; then
  echo "Initializing replica set..."

  MONGO_INITRS_TLS_OPTIONS=""
  if [ -n "$MONGO_INITRS_TLS" ]; then
    MONGO_INITRS_TLS_OPTIONS="--tls --tlsAllowInvalidCertificates"
  fi

  until mongo localhost:27017 $MONGO_INITRS_TLS_OPTIONS  /usr/local/bin/rs-init.js; do
    echo "  Failed to initialize replica set, trying again..."
    sleep 1
  done
  
  echo "  Done initializing replica set."
fi

fg