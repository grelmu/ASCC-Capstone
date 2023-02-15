# MPPW Deployments

The full MPPW stack is deployed via a set of images available at a release repository.  For the purposes of this document it is assumed the repository is `docker-images.composites.maine.edu:5000` and the username is `dev`.

> The overall deployment process is simple, but the images may be several GiB in size.

## Prerequisites

* Docker and Docker Compose (for Linux or WSL)

## Quickstart

### Setup remote image repository

A remote repository can be used from the command line in docker using the `login` command with proper credentials:

```sh
$ docker login docker-images.composites.maine.edu:5000 -u dev
Password:
...
```

> Unfortunately, the composites.maine.edu domains currently use self-signed certificates.  To work around this, it is necessary to explicitly whitelist the `docker-images.composites.maine.edu:5000` hostname in `daemon.json`.  See [`docs.docker`](https://docs.docker.com/registry/insecure/) for more details on how to do so.

Once logged in, docker images of the form `docker-images.composites.maine.edu:5000/ascc/xyz` are available to `pull`.

### Pull warehouse images

In order to speed up further steps, it is a good idea to pull down the large images to your local docker instance as the first step.  This isn't strictly necessary, but it makes debugging any issues simpler:

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

### Extract warehouse stack

The full MPPW stack is defined in a configurable `docker-compose` file - this file is included in the `ascc/mppw` images.  To extract it, run:

```sh
$ docker run --rm --entrypoint cat docker-images.composites.maine.edu:5000/ascc/mppw:$MPPW_VERSION ./compose.yml > mppw-stack.yml
```

### Deploy warehouse stack

All configuration of the MPPW deployments happens via environment variables.  The ones that are mandatory to set are:

* `MPPW_VERSION` - mandatory for a versioned deployment, otherwise defaults to `dev`
* `MPPW_REPOSITORY_PREFIX` - the repository prefix used above, for example `docker-images.composites.maine.edu:5000/`, to specify the images used.  Re-tagging images is also possible.  Note the trailing slash.
* `MONGODB_ADMIN_PASSWORD` - the `admin` user password for the warehouse database, and, if not overridden, the `admin` user password for the data warehouse API/UI

By running `docker-compose` with these variables, the stack can be created (and safely upgraded) with:

```sh
$ export MPPW_REPOSITORY_PREFIX=docker-images.composites.maine.edu:5000/
$ export MONGODB_ADMIN_PASSWORD=pick-a-better-password
$ docker-compose -p mppw -f mppw-stack.yml up
```

Navigate in a browser to `http://localhost/version` to see the API working.

Other variables that may be useful to set are:

* `MPPW_ADMIN_PASSWORD` - overrides and ensures a different password for the data warehouse API/UI

If deploying the JupyterHub service to different hardware than the database and API/UI:

* `AUTHENTICATOR_MPPW_URL` - overrides the `MPPW_URL` (ending with /api) that JupyterHub authenticates against
* `MPPW_PROXY_ENABLED/JUPYTERHUB_PROXY_ENABLED` - if set to 0/1, disables/enables http/s access to the warehouse API/UI and the JupyterHub analysis service, respectively

## Managing deployments

In order to make it simple to manage deployments, the above steps may be combined, stored, and version-controlled in a customized deployment script such as the one at `scripts/manage_deployment.sh`:

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

The example `manage_deployment.sh` invokes `docker-compose` with whatever arguments are passed in at the command line.  For example, to check the `mppw` API/UI and `nginx` ingress controller logs:

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

> NOTE that running `down -v` on a managed deployment will *wipe* all data, irrecoverably.  If a deployment is sensitive, consider adding double-checks of dangerous commands to any scripting (and backups).  

### Alternate Management via `.env` Files

Alternately, as a simpler approach, it may be useful to create and version `.env-my.hostname.xyz` files which just include the relevant `DOCKER_HOST`, `MONGODB_ADMIN_PASSWORD`, and other values in one place.  This allows you to `source` these values together into your environment and not remember them individually every time while using standard `docker-compose` tools.

### The `DOCKER_HOST` variable

It is often very convenient to manage deployments on remote hosts with `docker` via an SSH connection - to do this, simply set the `DOCKER_HOST` to `ssh://my.hostname.xyz`.  All subsequent `docker` commands will then be sent to the remote `docker` daemon.

> NOTE this can be confusing if not managed well - shell extensions are recommended to make the state of `DOCKER_HOST` visible when it is set.  Alternately deployment scripts should always report this information loudly.

### Credentials

The deployment variables are not permanently stored anywhere in the stack, by design - if the `MONGODB_ADMIN_PASSWORD` is lost there is no recovery mechanism possible for the data.  For that reason, it is highly encouraged to save either the deployment scripts or at least the password to one or more secure locations.  Restarting the database with a different admin password is currently untested and should be avoided.

### Alternate deployment via direct image copy

Sometimes a remote host may have different or limited access to the `docker` repository at `docker-images.composites.maine.edu` or elsewhere.  In this case, instead of pulling directly we can pull the images locally and then *copy* them to the remote `docker` host using the form:

```sh
$ docker pull docker-images.composites.maine.edu:5000/ascc/mppw:$MPPW_VERSION
$ docker save docker-images.composites.maine.edu:5000/ascc/mppw:$MPPW_VERSION | bzip2 | pv | \
    ssh user@limited.host.xyz docker load
```

Once the images are copied to the remote host the rest of the deployment can be managed from a remote `DOCKER_HOST` as usual.
