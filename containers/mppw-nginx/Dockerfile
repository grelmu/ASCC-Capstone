FROM nginx:1.21.5

COPY default.conf.template /etc/nginx/templates/default.conf.template

ENV ACTIVE_CERTIFICATE_DIR=/etc/certificates/nginx
ENV ACTIVE_CERTIFICATE_FILE=/etc/certificates/nginx/cert.pem
ENV ACTIVE_KEY_FILE=/etc/certificates/nginx/key.pem
ENV ACTIVE_KEY_CERTIFICATE_FILE=/etc/certificates/nginx/key-cert.pem

COPY ss-cert.pem /etc/nginx/conf.d/ss-cert.pem
COPY ss-key.pem /etc/nginx/conf.d/ss-key.pem
COPY 40-init-certificates.sh /docker-entrypoint.d/40-init-certificates.sh
