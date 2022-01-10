# Material-Process Property API PoC

## Prerequisites

* Python 3.8 with Poetry installed
    * `$ pip install poetry`
* Docker and Docker Compose

## Quickstart

```
$ cd <dir>
$ poetry install
$ poetry run uvicorn mppw.main:app --reload
```

Navigate in a browser to `http://localhost:8000` to see the API working.

## Run full stack via Docker Compose

First the app must be built and packaged as a container, then it can be run alongside a test MongoDB instance:

```
$ poetry run docker-mppw build
$ MONGODB_ADMIN_PASSWORD=<password> [MPPW_ADMIN_PASSWORD=<other_password>] \
    poetry run docker-mppw compose up [-d]
```

Navigate in a browser to `http://localhost/version` to see the API working.

> NOTE that the `MONGODB_ADMIN_PASSWORD` is **required**.  The `MPPW_ADMIN_PASSWORD` for the API itself will default to the `MONGODB_ADMIN_PASSWORD` if not specified.  The default admin username is `admin` in both cases.

> NOTE that by using FastAPI, we automatically also have a full API listing available at `http://localhost/docs` which is very useful for exploration and testing.

> NOTE that the container deployment targets HTTP default port `:80` while the local dev deployment targets `:8000` to allow both dev and deployed work.  Also, the containerized deploy does **not** expose database ports directly.

The standard docker deployment is considered fully productionized, and deployment options can be overridden for stage or development deployments via additional compose files (see `containers\mppw-stack.dev.yml`).  This makes it simpler to ensure that our production deployments don't require extra undocumented configuration (because they actually require fewer configuration files).

## Run local dev app with Docker MongoDB

It's often useful to run the app locally, for testing - there is a custom script to help with this.  In the background it starts a dev instance of the `mongodb` container and then runs the app directly (via uvicorn):

```
$ poetry run app dev
```

Navigate in a browser to `http://localhost:8000/version` to see the local dev API working.

## Manage data migrations

Though MongoDB is a schema-free database, the MPPW app itself relies on an implicit data schema as well as the presence of indices.  To manage indexes as well as any schema changes which are awkward to migrate in application code, on startup the MPPW app ensures a set of migrations are run against the data store (at `mppw/migrations/mongodb`).

In order to list all the current migrations, run:

```
$ poetry run migrations ls
```

In order to create a new migration, run:

```
$ poetry run migrations gen <name_of_new_migration>
```

A new (timestamped) migration file will be created at `mppw/migrations/mongodb`

In order to determine which migrations have been applied against a MongoDB instance, run:

```
$ poetry run migrations show <url, for example mongodb://admin:password@localhost:27027/mppw_dev?authSource=admin>
```

> NOTE that the `authSource=admin` URL parameter is required in order for the admin user to authenticate correctly. 
