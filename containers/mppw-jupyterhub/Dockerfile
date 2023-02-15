FROM jupyterhub/jupyterhub:2.1.1

RUN apt-get update
RUN apt-get install git vim -y

COPY dist /root/dist
RUN mkdir -p /root/.ssh
COPY ssh_config /root/.ssh/config
RUN --mount=type=ssh ["bash", "-c", "pip install /root/dist/*.whl"]

RUN pip install pkginfo
RUN mkdir -p /etc/skel/notebooks
RUN touch /etc/skel/notebooks/.touch
COPY skel_notebooks.py /root/dist/skel_notebooks.py
RUN python3 /root/dist/skel_notebooks.py

COPY mppwauth /root/mppwauth
RUN pip install /root/mppwauth

COPY jupyterhub_config.py ./jupyterhub_config.py

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT /entrypoint.sh

RUN pip install jupyterlab-git
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && apt-get install -y nodejs

RUN chmod 0750 /srv/jupyterhub
RUN cat /etc/adduser.conf | sed -e 's/DIR_MODE=0755/DIR_MODE=0750/' > /etc/adduser.conf.tmp && mv /etc/adduser.conf.tmp /etc/adduser.conf

# Extra tools
# MongoDB Shell
RUN apt-get install mongodb-clients
# Pytorch (CPU)
RUN pip3 install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cpu