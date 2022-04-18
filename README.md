# Material-Process Property Warehouse (MPPW) API PoC

## Prerequisites

### Ubuntu or Windows WSL

* Docker and Docker Compose
* Python 3.8.3 (with Poetry)
* (Optional) PCL (Point Cloud Library) for PCL-file APIs
    * ```sh
      $ sudo apt install -y libpcl-apps1.10 libpcl-common1.10 libpcl-features1.10 libpcl-filters1.10 libpcl-io1.10 libpcl-kdtree1.10 libpcl-keypoints1.10 libpcl-ml1.10 libpcl-octree1.10 libpcl-outofcore1.10 libpcl-people1.10 libpcl-recognition1.10 libpcl-registration1.10 libpcl-sample-consensus1.10 libpcl-search1.10 libpcl-segmentation1.10 libpcl-stereo1.10 libpcl-surface1.10 libpcl-tracking1.10 libpcl-visualization1.10
      ```

> NOTE that PCL is a very large and finicky dependency - installing the core libraries is system-specific, and then system-specific python bindings must be used.  Consider containerizing this functionality going forward if we start using it for more than I/O.

For more details installing these basics on WSL, see ['README_WSL.md`](./README_WSL.md).

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

To save typing, it may also be useful to copy the `.env-local` file to an `.env-prod-host` file and set the `DOCKER_HOST` and `MONGODB_ADMIN_PASSWORD` values in one place.  This allows you to `source` these values together into your environment and not remember them individually every time.

```sh
$ source .env-prod-host
... do stuff on prod ...
$ source .env-local
... back to local docker
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

## Alternate version with container copy

Sometimes it isn't possible to build on the remote host directly - in this case we can use the form:

```sh
$ docker save ascc/mppw:dev | bzip2 | pv | ssh user@host docker load
$ source .env-prod-host
$ poetry run mppw-docker compose up -d mppw
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
