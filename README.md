# Material-Process Property Warehouse (MPPW) API PoC

## Prerequisites

* Python 3.8 with Poetry installed
    * `$ pip install poetry`
* Docker and Docker Compose

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

## Manage Dev deployments

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

## Manage production deployments

Specifying a remote `DOCKER_HOST` via SSH is currently the best way to manage remote Docker systems - essentially it changes your Docker context to that of the remote machine.  All docker operations continue to work as expected from the local CLI on the remote machine (aside from local filesystem bind-mounts, which of course are not available remotely).

To point at a remote SSH host:

```sh
$ export DOCKER_HOST=ssh://username@host
$ docker container ls
$ poetry run mppw-docker build
```

** All build and compose commands will now be directed to the remote host **

> NOTE that the remote host is a completely separate Docker service, and so build commands may have to be re-run in the remote context to allow deployment.

To check or go back to the local host, simply echo unset the `DOCKER_HOST` variable:
```sh
$ echo $DOCKER_HOST
$ export DOCKER_HOST=
```

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

## Debug production deployments

Often it's useful to be able to connect directly to ports on production machines - to do so, you can use SSH port-forwarding.  To make this easy, a helper script is available:

```sh
$ poetry run mppw-docker tunnel
```

The `tunnel` script will forward remote port `:80` to local port `:8080` (though due to nginx redirect `http:` will be redirected incorrectly with a remote host).  `Https` should work at forwarded port `:44443`.  Also MongoDB port `:27017` will be forwarded to local port `:27037`.

> NOTE that port-forwarding will only be available while the script is active.

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
