# Deploying the Warehouse Stack

The full MPPW stack is deployed via a set of images available at a release repository. For the purposes of this document it is assumed the repository is `docker-images.composites.maine.edu:5000` and the username is `dev`.

> The overall deployment process is simple, but the images may be several GiB in size.

## Prerequisites

- Docker and Docker Compose (for Linux or WSL)

## Recommended Hardware

The MPPW stack can be deployed on any kind of system which can run x86/64 Linux-based Docker containers.
The database components are the performance bottlenecks and perform best with memory proportional to the active working set - I/O-optimized hardware is recommended. By default, all data collected from manufacturing operations is stored in the data warehouse database, so the warehouse storage should be sized by estimating the amount of data each operation will collect `x` estimated number of operations. Image and video data collection usually dominates storage.

> Currently the warehouse software images do not provide automatic data scale-out options, but the warehouse can run on any external MongoDB 4.x instance. Support for sharded collections is possible but not yet tested.

The file system managing the Docker container volumes contains the full state of the running warehouse. In
production deployments, this file system may either support snapshots (for live backups) or, alternately,
periodic read-only downtime. Best practice is a local backup as well as a remote backup if the underlying file system block storage is not itself durable. NFS file systems traditionally interact badly with databases.

For an isolated compute environment, the JupyterHub components of the warehouse may be deployed separately
on compute-optimized hardware with network access to the warehouse. This is recommended for production
deployments.

## Quickstart

### Setup remote image repository

A remote repository can be used from the command line in docker using the `login` command with proper credentials:

```sh
$ docker login docker-images.composites.maine.edu:5000 -u dev
Password:
...
```

> The composites.maine.edu domains now have secure certificates, but to use docker repositories from unverified domains see [`docs.docker`](https://docs.docker.com/registry/insecure/).

Once logged in, docker images of the form `docker-images.composites.maine.edu:5000/ascc/xyz` are available to `pull`.

### Pull warehouse images

In order to speed up further steps, it is a good idea to pull down the large images to your local docker instance as the first step. This isn't strictly necessary, but it makes debugging any issues simpler:

```sh
$ export MPPW_VERSION=0.9.0
$ docker pull docker-images.composites.maine.edu:5000/ascc/mppw:$MPPW_VERSION
...
$ docker pull docker-images.composites.maine.edu:5000/ascc/mppw-mongodb:$MPPW_VERSION
...
$ docker pull docker-images.composites.maine.edu:5000/ascc/mppw-nginx:$MPPW_VERSION
...
$ docker pull docker-images.composites.maine.edu:5000/ascc/mppw-jupyterhub:$MPPW_VERSION
...
```

### Alternate load of warehouse images from files

If direct registry access is not possible, Docker images may also be loaded as `.tar(.gz)` files from any filesystem - to do so first download the `-mppw-X_Y_Z.tar.gz`, `-mppw-mongodb_X_Y_Z.tar.gz`, `-mppw-nginx_X_Y_Z.tar.gz`, and `-mppw-jupyterhub_X_Y_Z.tar.gz` images to the target system. The images can then be loaded into docker via:

```sh
$ docker load < image_file.tar[.gz]
```

> Note that this command, by default, will only load Docker images onto the machine-local Docker instance. To load images onto a remote machine, it is possible to use the `$DOCKER_HOST` variable.

### Extract warehouse stack

The full MPPW stack is defined in a configurable `docker-compose` file - this file is included in the `ascc/mppw` images. To extract it, run:

```sh
$ docker run --rm --entrypoint cat \
    docker-images.composites.maine.edu:5000/ascc/mppw:$MPPW_VERSION \
      ./compose.yml > mppw-stack.yml
```

### Deploy warehouse stack

All configuration of the MPPW deployments happens via environment variables. The ones that are mandatory to set are:

- `MPPW_VERSION` - mandatory for a versioned deployment, otherwise defaults to `dev`
- `MPPW_REPOSITORY_PREFIX` - the repository prefix used above, for example `docker-images.composites.maine.edu:5000/`, to specify the images used. Re-tagging images is also possible. Note the trailing slash.
- `MONGODB_ADMIN_PASSWORD` - the `admin` user password for the warehouse database, and, if not overridden, the `admin` user password for the data warehouse API/UI

By running `docker-compose` with these variables, the stack can be created (and safely upgraded) with:

```sh
$ export MPPW_REPOSITORY_PREFIX=docker-images.composites.maine.edu:5000/
$ export MONGODB_ADMIN_PASSWORD=pick-a-better-password
$ docker-compose -p mppw -f mppw-stack.yml up
```

Navigate in a browser to `http://localhost/version` to see the API working.

Other variables that may be useful to set are:

- `MPPW_ADMIN_PASSWORD` - overrides and ensures a different password for the data warehouse API/UI

If deploying the JupyterHub service to different hardware than the database and API/UI:

- `AUTHENTICATOR_MPPW_URL` - overrides the `MPPW_URL` (ending with /api) that JupyterHub authenticates against
- `MPPW_PROXY_ENABLED/JUPYTERHUB_PROXY_ENABLED` - if set to 0/1, disables/enables http/s access to the warehouse API/UI and the JupyterHub analysis service, respectively

## Managing deployments

In order to make it simple to manage deployments, the above steps may be combined, stored, and version-controlled in a customized deployment script such as the one at [`scripts/manage_deployment.sh`](scripts/manage_deployment.sh):

```sh
$ scripts/manage_deployment.sh config
0.9.0: Pulling from ascc/mppw
Digest: sha256:87636e4b22e7d23639e7c666285c64fc4ef1016230645ab3a1bc20fc0272974b
Status: Image is up to date for docker-images.composites.maine.edu:5000/ascc/mppw:0.9.0
...
name: mppw
services:
  jupyterhub:
    environment:
...
```

The example `manage_deployment.sh` invokes `docker-compose` with whatever arguments are passed in at the command line. For example, to check the `mppw` API/UI and `nginx` ingress controller logs:

```sh
$ scripts/manage_deployment.sh logs mppw nginx
```

As another example, the common case of upgrading the API/UI only without restarting the other services would be:

```sh
$ scripts/manage_deployment.sh up -d mppw
```

As another example, to login to the `MongoDB` database:

```sh
$ scripts/manage_deployment.sh exec -it mongodb mongo
```

Essentially all docker commands are available with `docker-compose` service aliases.

> NOTE that running `down -v` on a managed deployment will _wipe_ all data, irrecoverably. If a deployment is sensitive, consider adding double-checks of dangerous commands to any scripting (and backups).

### Alternate Management via `.env` Files

Alternately, as a simpler approach, it may be useful to create and version `.env-my.hostname.xyz` files which just include the relevant `DOCKER_HOST`, `MONGODB_ADMIN_PASSWORD`, and other values in one place. This allows you to `source` these values together into your environment and not remember them individually every time while using standard `docker-compose` tools.

### The `DOCKER_HOST` variable

It is often very convenient to manage deployments on remote hosts with `docker` via an SSH connection - to do this, simply set the `DOCKER_HOST` to `ssh://my.hostname.xyz`. All subsequent `docker` commands will then be sent to the remote `docker` daemon.

> NOTE this can be confusing if not managed well - shell extensions are recommended to make the state of `DOCKER_HOST` visible when it is set. Alternately deployment scripts should always report this information loudly.

### Credentials

The deployment variables are not permanently stored anywhere in the stack, by design - if the `MONGODB_ADMIN_PASSWORD` is lost there is no recovery mechanism possible for the data. For that reason, it is highly encouraged to save either the deployment scripts or at least the password to one or more secure locations. Restarting the database with a different admin password is currently untested and should be avoided.

### Alternate deployment via direct image copy

Sometimes a remote host may have different or limited access to the `docker` repository at `docker-images.composites.maine.edu` or elsewhere. In this case, instead of pulling directly we can pull the images locally and then _copy_ them to the remote `docker` host using the form:

```sh
$ docker pull docker-images.composites.maine.edu:5000/ascc/mppw:$MPPW_VERSION
$ docker save docker-images.composites.maine.edu:5000/ascc/mppw:$MPPW_VERSION | bzip2 | pv | \
    ssh user@limited.host.xyz docker load
```

Once the images are copied to the remote host the rest of the deployment can be managed from a remote `DOCKER_HOST` as usual.

### Advanced JupyterHub deployment

The MPPW stack includes a JupyterHub service pre-configured to authenticate against the MPPW, however
often it is best practice to deploy the sandbox notebook service separately from the data storage and API
services. In order to do so, first, bring up only the `mppw`, `mongodb`, and `nginx` services via docker-compose on the warehouse host.

```sh
$ export MPPW_REPOSITORY_PREFIX=...
$ export MONGODB_ADMIN_PASSWORD=...
$ export JUPYTERHUB_PROXY_ENABLED=0
$ docker-compose -p mppw -f mppw-stack.yml up -d mppw mongodb nginx
```

This will not start the JupyterHub service and will not proxy web requests. On the JupyterHub host, similarly run:

```sh
$ export MPPW_REPOSITORY_PREFIX=...
$ export MONGODB_ADMIN_PASSWORD=...
$ export MPPW_PROXY_ENABLED=0
$ export AUTHENTICATOR_MPPW_URL=https://warehouse-host-name/api
$ docker-compose -p mppw -f mppw-stack.yml up -d nginx jupyterhub
```

This will start the JupyterHub environment on the host and link authentication back to the warehouse host.

### Advanced API deployment

The API services (`mppw`, `nginx`) of the data warehouse can also be deployed separately - this is done
by setting the `MONGODB_URL` to a different value pointing at another MongoDB host. Separate service deployment is done similarly to the JupyterHub case - see the `compose.yml` file for more details.
