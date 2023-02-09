FROM jupyterhub/jupyterhub:2.1.1

RUN pip install notebook

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT /entrypoint.sh

COPY dist ./dist

RUN apt-get update
RUN apt-get install git -y

RUN mkdir -p /root/.ssh
COPY ssh_config /root/.ssh/config
RUN --mount=type=ssh ["bash", "-c", "pip install dist/*.whl"]

RUN pip install pkginfo
RUN mkdir -p /etc/skel/notebooks
RUN touch /etc/skel/notebooks/.touch
COPY skel_notebooks.py ./skel_notebooks.py
RUN python3 ./skel_notebooks.py

COPY jupyterhub_config.py jupyterhub_config.py
COPY mppwauth ./mppwauth
RUN pip install ./mppwauth
