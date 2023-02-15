#!/bin/sh

mkdir -p "$ACTIVE_CERTIFICATE_DIR"

if [ ! -f "$ACTIVE_CERTIFICATE_FILE" ]; then

  echo "Generating a new self-signed certificate..."

  openssl req -x509 -newkey rsa:4096 -nodes -keyout "$ACTIVE_CERTIFICATE_DIR/ss-key.pem" -out "$ACTIVE_CERTIFICATE_DIR/ss-cert.pem" -days 36500 -subj '/CN=localhost'
  cat "$ACTIVE_CERTIFICATE_DIR/ss-key.pem"  "$ACTIVE_CERTIFICATE_DIR/ss-cert.pem" > "$ACTIVE_CERTIFICATE_DIR/ss-key-cert.pem"

  ln -s "$ACTIVE_CERTIFICATE_DIR/ss-key.pem" "$ACTIVE_KEY_FILE"
  ln -s "$ACTIVE_CERTIFICATE_DIR/ss-cert.pem" "$ACTIVE_CERTIFICATE_FILE"
  ln -s "$ACTIVE_CERTIFICATE_DIR/ss-key-cert.pem" "$ACTIVE_KEY_CERTIFICATE_FILE"

  echo "  Done generating self-signed certificate."

fi

if [ "$REGISTRY_AUTH" == "htpasswd" ]; then

  echo "Generating registry HTPASSWD file..."

  htpasswd -Bbc "$REGISTRY_AUTH_HTPASSWD_PATH" "$MPPW_REGISTRY_ADMIN_USERNAME" "$MPPW_REGISTRY_ADMIN_PASSWORD"

  if [ -n "$MPPW_REGISTRY_USERNAMES_PASSWORDS" ]; then

    echo "$MPPW_REGISTRY_USERNAMES_PASSWORDS" | while IFS= read -r MPPW_REGISTRY_USERNAMES_PASSWORDS_LINE ; do

      MPPW_REGISTRY_USERNAME="$(echo "$MPPW_REGISTRY_USERNAMES_PASSWORDS_LINE" | cut -d ':' -f 1)"
      MPPW_REGISTRY_PASSWORD="$(echo "$MPPW_REGISTRY_USERNAMES_PASSWORDS_LINE" | cut -d ':' -f 2-)"

      htpasswd -Bb "$REGISTRY_AUTH_HTPASSWD_PATH" "$MPPW_REGISTRY_USERNAME" "$MPPW_REGISTRY_PASSWORD"

    done

  fi

  echo "Done generating registry HTPASSWD file."

fi

echo /bin/sh /docker-entrypoint.sh "$@" 
/bin/sh /docker-entrypoint.sh "$@"