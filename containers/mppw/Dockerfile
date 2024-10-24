FROM ubuntu:20.04
# NOTE: There's a very annoying mismatch between PCL libs in debian / ubuntu:
# Debian buster - v1.9
# Ubuntu 20.04 - v1.10
# Debian bullseye - v1.11
# We can probably use the debian container again when we adopt 22.04
#FROM python:3.8.11-slim

RUN --mount=type=cache,target=/root/.cache \
    apt-get update && \
    apt-get install -y build-essential libpq-dev python3.8-dev curl vim
RUN DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get -y install tzdata
RUN --mount=type=cache,target=/root/.cache \
    apt-get update && \
    apt-get install -y python3-pip && \
    apt-get install -y libpcl-apps1.10 libpcl-common1.10 libpcl-features1.10 libpcl-filters1.10 libpcl-io1.10 libpcl-kdtree1.10 libpcl-keypoints1.10 libpcl-ml1.10 libpcl-octree1.10 libpcl-outofcore1.10 libpcl-people1.10 libpcl-recognition1.10 libpcl-registration1.10 libpcl-sample-consensus1.10 libpcl-search1.10 libpcl-segmentation1.10 libpcl-stereo1.10 libpcl-surface1.10 libpcl-tracking1.10 libpcl-visualization1.10 && \
    apt-get install -y git
RUN apt-get clean

ARG PACKAGE_NAME
ARG PACKAGE_VERSION

COPY dist/$PACKAGE_NAME-$PACKAGE_VERSION-py3-none-any.whl $PACKAGE_NAME-$PACKAGE_VERSION-py3-none-any.whl
COPY dist/${PACKAGE_NAME}_web-$PACKAGE_VERSION-py3-none-any.whl ${PACKAGE_NAME}_web-$PACKAGE_VERSION-py3-none-any.whl

RUN echo $PACKAGE_NAME > PACKAGE_NAME
RUN echo $PACKAGE_VERSION > PACKAGE_VERSION

RUN mkdir -p /root/.ssh
COPY ssh_config /root/.ssh/config
RUN pip install --upgrade pip
RUN --mount=type=ssh --mount=type=cache,target=/root/.cache pip install $PACKAGE_NAME-$PACKAGE_VERSION-py3-none-any.whl
RUN --mount=type=ssh --mount=type=cache,target=/root/.cache pip install ${PACKAGE_NAME}_web-$PACKAGE_VERSION-py3-none-any.whl

COPY dist/$PACKAGE_NAME-stack.yml compose.yml
COPY dist/$PACKAGE_NAME-stack.dev.yml compose.dev.yml
COPY dist/$PACKAGE_NAME-stack.bmark.yml compose.bmark.yml

RUN pip install docker-compose==1.29.2
ENV COMPOSE_PROJECT_NAME=$PACKAGE_NAME-stack

RUN pip install gunicorn[gevent]
#CMD ["gunicorn", "-w", "3", "-b", "0.0.0.0", "-k", "uvicorn.workers.UvicornWorker", "mppw.main:app"]
CMD ["uvicorn", "--host", "0.0.0.0", "mppw.main:app"]