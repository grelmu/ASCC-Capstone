FROM python:3.8.11-slim

RUN apt-get update
RUN apt-get install -y build-essential libpq-dev python3.8-dev curl vim
RUN apt-get clean

ARG PACKAGE_NAME
ARG PACKAGE_VERSION

COPY dist/$PACKAGE_NAME-$PACKAGE_VERSION-py3-none-any.whl $PACKAGE_NAME-$PACKAGE_VERSION-py3-none-any.whl

RUN echo $PACKAGE_NAME > PACKAGE_NAME
RUN echo $PACKAGE_VERSION > PACKAGE_VERSION
RUN pip install $PACKAGE_NAME-$PACKAGE_VERSION-py3-none-any.whl

COPY dist/$PACKAGE_NAME-stack.yml compose.yml
RUN pip install docker-compose==1.29.2
ENV COMPOSE_PROJECT_NAME=$PACKAGE_NAME-stack

CMD ["uvicorn", "--host", "0.0.0.0", "mppw.main:app"]