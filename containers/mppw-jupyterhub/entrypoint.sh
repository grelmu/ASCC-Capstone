#!/bin/bash

mkdir -p /etc/skel/notebooks
touch /etc/skel/notebooks/.touch

useradd -m "$ADMIN_USERNAME"
echo "$ADMIN_USERNAME:$ADMIN_PASSWORD" | chpasswd
export ADMIN_TOKEN="$ADMIN_PASSWORD"

cp jupyterhub_config.py "/home/$ADMIN_USERNAME/jupyterhub_config.py"
cd "/home/$ADMIN_USERNAME"
exec jupyterhub "$@"