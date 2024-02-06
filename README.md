# Material-Process-Property Warehouse (MPPW) Images

The Material-Process-Property Warehouse is a software stack which allows storing, querying, and exploring large quantities of scientific data focused on manufacturing.  This repository includes the tools used to build images
of the warehouse as well as being a monorepo for integration tests.

## Prerequisites

### Ubuntu or Windows WSL

* Docker and Docker Compose
* Python 3.8.3 (with Poetry)

For more details installing these basics on WSL, see [`README_WSL.md`](./README_WSL.md).

> If your use case is just to install/deploy released versions of the warehouse, see [`DEPLOY.md`](./DEPLOY.md).  The instructions below are for building the data warehouse from source code.

## Quickstart

First, add your source control SSH key to the SSH agent - Docker and git (depending on your configuration) will require the key to run checkouts:

```sh
$ ssh-add <path-to-source-control-ssh-key>
```

Git submodules are used - ensure these are properly checked-out:

```sh
$ git submodule update --init --recursive
```

Next install all python prerequisites:

```sh
$ cd <dir>
$ poetry install
```

Finally, build the containers and start the MPPW (dev) stack:

```sh
$ poetry run mppw-docker build
$ poetry run mppw-docker compose-dev up [-d]
```

Navigate in a browser to `http://localhost:8000/version` to see the API working.  The admin username/password for the API and database is `admin:password`.  The `dev` deployment here will automaticaly watch for code changes in the `mppw` and `mppw_web` folder and restart the app when changes are detected.

> NOTE that by using FastAPI, we automatically also have a full API listing available at `http://localhost/docs` which is very useful for exploration and testing.

## Run unit and API tests

Once the MPPW development stack is running, automated integration tests can be run to validate the codebase and API.  Tests are written using pytest:

```sh
$ poetry run pytest
```

## Dev Versus Standard Stack

The standard deploy is near-identical to the dev deploy except for:

* The dev deploy maps in the the local filesystem `mppw` and `mppw_web` instead of using packaged `mppw[_web]` files.  This allows local `mppw` and `mppw_web` file changes to be reflected in the container immediately for debugging.  

* The dev deploy exposes the HTTP `mppw` port (`:8000`) and `mongodb` port (`:27027`) to the outside world for debugging.

* The standard deploy *requires* a `MONGODB_ADMIN_PASSWORD` be specified, it is not defaulted to `password`.

> Note that the admin password is also used to create other keys for MongoDB and changes have not been tested.

To deploy a standard stack locally, run:

```sh
$ poetry run mppw-docker build
$ MONGODB_ADMIN_PASSWORD=<password> [MPPW_ADMIN_PASSWORD=<other_password>] \
    poetry run mppw-docker compose up [-d]
```

Navigate in a browser to `http://localhost/version` to see the standard API working.

The standard docker deployment is considered fully productionized, and deployment options can be overridden for stage or development deployments via additional compose files (`containers/mppw-stack.dev.yml`) or env vars.  This makes it simpler to ensure that our production deployments don't require extra undocumented configuration (because they actually require less configuration).

## Manage Dev Deployments

All deployment management is done via Docker, using the `mppw-docker compose[-dev]` helper script.  The script just sets some default variables and `docker-compose` files depending on the environment chosen, all other parameters are passed to `docker-compose`.  For example, to start only the `dev` `mongodb` service in the background:

```sh
$ poetry run mppw-docker compose-dev up -d mongodb
```

To stop the `dev` deployment while preserving data:

```sh
$ poetry run mppw-docker compose-dev down
```

To fully tear-down the `dev` deployment and reset all data:

```sh
$ poetry run mppw-docker compose-dev down -v
```

> NOTE be very careful **not** to tear down a production deployment in the same way - it will reset all data!  A password must be specified for production deployments, which provides a level of safety here.  In general, if using docker-compose with production data it is recommended to avoid the use of `down` as containers will be replaced when needed.

# Attributions
This work was funded in part by the following projects:
- Accelerating Rapid Prototyping: Advanced Hardware Development project from the U.S. Army Engineer Research and Development Center. Contract number: W912HZ21C0007P00001
- Accelerating Rapid Prototyping Phase 3 project - Polymer Naval Vessel and Army Shelter Prototypes that are Large Scale Additive Manufactured.  Other Transaction Agreement Number: W15QKN-17-9-5555, Sub-Agreement Number: C5-21-1011
- Accelerating Rapid Prototyping Phase 4 project - Polymer Naval Vessel and Army Shelter Prototypes that are Large Scale Additive Manufactured.  Other Transaction Agreement Number: W15QKN-17-9-5555, Sub-Agreement Number: C5-23-1003

# Contributors/Points of Contact
@gstuder-composites
@ben1111111111111111111111111111111111111111111111111111111111111111111
@ngarfield-composites

Copyright (c) 2024-01-01 University of Maine