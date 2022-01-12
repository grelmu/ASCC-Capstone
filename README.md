# Material-Process Property Warehouse (MPPW) API PoC

## Prerequisites

* Python 3.8 with Poetry installed
    * `$ pip install poetry`
* Docker and Docker Compose
    * `docker-machine` for remote deployments

## Quickstart

First install all python prerequisites:

```sh
$ cd <dir>
$ poetry install
```

Next, build the containers and start the MPPW (dev) stack:

```sh
$ poetry run mppw-docker build
$ poetry run mppw-docker compose-dev up [-d]
```

Navigate in a browser to `http://localhost:8000/version` to see the API working.  The admin username/password for the API and database is `admin:password`.  The `dev` deployment here will automaticaly watch for code changes in the `mppw` folder and restart the app when changes are detected.

> NOTE that by using FastAPI, we automatically also have a full API listing available at `http://localhost/docs` which is very useful for exploration and testing.

## Deploy production stack

The production deploy is near-identical except for using the packaged `mppw` code versus mapping in the local filesystem `mppw`.  To deploy, run: 

```sh
$ poetry run mppw-docker build
$ MONGODB_ADMIN_PASSWORD=<password> [MPPW_ADMIN_PASSWORD=<other_password>] \
    poetry run mppw-docker compose up [-d]
```

Navigate in a browser to `http://localhost/version` to see the API working.

> NOTE that the `MONGODB_ADMIN_PASSWORD` is **required**.  The `MPPW_ADMIN_PASSWORD` for the API itself will default to the `MONGODB_ADMIN_PASSWORD` if not specified.  The default admin username is `admin` in both cases.

> NOTE that the container deployment targets HTTP default port `:80` while the local dev deployment targets `:8000` to allow both dev and deployed work.  Also, the containerized deploy exposes `:27017` ports directly while local dev deployment exposes `:27027`.

The standard docker deployment is considered fully productionized, and deployment options can be overridden for stage or development deployments via additional compose files (`containers/mppw-stack.dev.yml`) or env vars.  This makes it simpler to ensure that our production deployments don't require extra undocumented configuration (because they actually require less configuration).

## Manage Dev or Production deployments

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

> NOTE be very careful **not** to tear down the production deployment in the same way - it will reset all data!  A password must be specified for production deployments, which provides a level of safety here.

To upgrade a production deployment to use new code:

```sh
$ poetry run mppw-docker build
$ MONGODB_ADMIN_PASSWORD=<password> [MPPW_ADMIN_PASSWORD=<other_password>] \
    poetry run mppw-docker compose up [-d]
```

To revert a production deployment to old code:

```sh
$ MPPW_VERSION=<X.Y.Z> MONGODB_ADMIN_PASSWORD=<password> [MPPW_ADMIN_PASSWORD=<other_password>] \
    poetry run mppw-docker compose up [-d]
```

## Manage data migrations

Though MongoDB is a schema-free database, the MPPW app itself relies on an implicit data schema as well as the presence of indices.  To manage indexes as well as any schema changes which are awkward to migrate in application code, on startup the MPPW app ensures a set of migrations are run against the data store (at `mppw/migrations/mongodb`).

In order to list all the current migrations, run:

```
$ poetry run mppw-migrations ls
```

In order to create a new migration, run:

```
$ poetry run mppw-migrations gen <name_of_new_migration>
```

A new (timestamped) migration file will be created at `mppw/migrations/mongodb`

In order to determine which migrations have been applied against a MongoDB instance, run:

```
$ poetry run mppw-migrations show <url, for example mongodb://admin:password@localhost:27027/mppw_dev?authSource=admin>
```

> NOTE that the `authSource=admin` URL parameter is required in order for the admin user to authenticate correctly. 
