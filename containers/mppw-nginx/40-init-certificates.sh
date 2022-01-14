#!/usr/bin/env bash

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