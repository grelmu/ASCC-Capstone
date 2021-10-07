# Material-Process Property API PoC

## Prerequisites

* Python 3.8 with Poetry installed
    * `$ pip install poetry`
* Docker and Docker Compose

## Quickstart

```
$ cd <dir>
$ poetry install
$ poetry run uvicorn mppapi:app --reload
```

Navigate in a browser to `http://localhost:8000` to see the API working.

## Run full stack via Docker Compose

First the app must be built and packaged as a container, then it can be run alongside
a test MongoDB instance:

```
$ poetry run python scripts/docker-build.py
$ docker-compose -f scripts/docker-compose.yaml up
```

Navigate in a browser to `http://localhost:8001` to see the API working.

> NOTE that the container deployment targets port `:8001` to allow both local and containerized work.
