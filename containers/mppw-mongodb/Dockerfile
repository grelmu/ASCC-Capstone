FROM mongo:4.4.6

COPY wait-for-it.sh wait-for-it.sh
COPY rs-init.sh /usr/local/bin/rs-init.sh
COPY rs-init.js /usr/local/bin/rs-init.js

ENTRYPOINT ["rs-init.sh"]