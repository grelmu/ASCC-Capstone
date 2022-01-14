FROM mongo:4.4.6

ENV ACTIVE_CERTIFICATE_DIR=/etc/certificates/mongodb
ENV ACTIVE_CERTIFICATE_FILE=/etc/certificates/mongodb/cert.pem
ENV ACTIVE_KEY_FILE=/etc/certificates/mongodb/key.pem
ENV ACTIVE_KEY_CERTIFICATE_FILE=/etc/certificates/mongodb/key-cert.pem

ENV ROOT_PASSWORD_KEYFILE=/etc/certificates/mongodb/root-password-keyfile.key

RUN mkdir -p /docker-entrypoint.d
COPY 40-init-certificates.sh /docker-entrypoint.d/40-init-certificates.sh
COPY 50-init-root-password-keyfile.sh /docker-entrypoint.d/50-init-root-password-keyfile.sh

COPY wait-for-it.sh wait-for-it.sh
COPY rs-init.js /usr/local/bin/rs-init.js
COPY rs-entrypoint.sh /usr/local/bin/rs-entrypoint.sh

ENTRYPOINT ["rs-entrypoint.sh"]