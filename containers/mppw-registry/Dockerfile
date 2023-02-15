FROM registry:2.8.1

RUN apk add openssl
RUN apk add apache2-utils

ENV ACTIVE_CERTIFICATE_DIR=/etc/certificates/registry
ENV ACTIVE_CERTIFICATE_FILE=/etc/certificates/registry/cert.pem
ENV REGISTRY_HTTP_TLS_CERTIFICATE=/etc/certificates/registry/cert.pem
ENV ACTIVE_KEY_FILE=/etc/certificates/registry/key.pem
ENV REGISTRY_HTTP_TLS_KEY=/etc/certificates/registry/key.pem
ENV ACTIVE_KEY_CERTIFICATE_FILE=/etc/certificates/registry/key-cert.pem

ENV REGISTRY_AUTH_HTPASSWD_REALM="Registry Realm"
ENV REGISTRY_AUTH_HTPASSWD_PATH=/etc/certificates/registry/htpasswd
ENV REGISTRY_AUTH=htpasswd

RUN mv /entrypoint.sh /docker-entrypoint.sh
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh