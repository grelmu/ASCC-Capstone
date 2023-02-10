#!/bin/bash

if [ -f jupyterhub_crypt_key ]; then
    echo "Using existing jupyterhub_crypt_key..."
else
    echo "Generating new jupyterhub_crypt_key..."
    openssl rand -hex 32 > jupyterhub_crypt_key
fi

export JUPYTERHUB_CRYPT_KEY=$(cat jupyterhub_crypt_key)

exec jupyterhub "$@"