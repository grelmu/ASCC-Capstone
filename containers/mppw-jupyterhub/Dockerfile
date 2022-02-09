FROM jupyterhub/jupyterhub:2.1.1

RUN pip install notebook
COPY jupyterhub_config.py jupyterhub_config.py

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT /entrypoint.sh

# HACK HACK HACK
COPY base.py /usr/local/lib/python3.8/dist-packages/jupyterhub/handlers/base.py