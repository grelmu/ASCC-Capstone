import sys
import os
import subprocess
import toml
import glob
import shutil
import argh
import furl

root_dir = os.path.dirname(os.path.dirname(__file__))
dist_dir = os.path.join(root_dir, "dist")
containers_dir = os.path.join(root_dir, "containers")


def build(*args):

    project = None
    with open("pyproject.toml") as f:
        project = toml.load(f)

    project_name = project["tool"]["poetry"]["name"]
    project_version = project["tool"]["poetry"]["version"]

    os.environ["DOCKER_BUILDKIT"] = "1"

    if not args or "nginx" in args or "mppw-nginx" in args:
        subprocess.run(
            [
                "docker",
                "build",
                "--ssh",
                "default",
                os.path.join(containers_dir, f"{project_name}-nginx"),
                "--tag",
                f"ascc/{project_name}-nginx:dev",
                "--tag",
                f"ascc/{project_name}-nginx:{project_version}",
            ]
        )

    if not args or "mongodb" in args or "mppw-mongodb" in args:
        subprocess.run(
            [
                "docker",
                "build",
                "--ssh",
                "default",
                os.path.join(containers_dir, f"{project_name}-mongodb"),
                "--tag",
                f"ascc/{project_name}-mongodb:dev",
                "--tag",
                f"ascc/{project_name}-mongodb:{project_version}",
            ]
        )

    if not args or "jupyterhub" in args or "mppw-jupyterhub" in args:

        jupyterhub_dist_dir = os.path.join(containers_dir, "mppw-jupyterhub", "dist")
        shutil.rmtree(
            jupyterhub_dist_dir, ignore_errors=True
        )

        fff_analysis_dir = os.path.join(root_dir, "fff_analysis")
        subprocess.run(["poetry", "build"], cwd=fff_analysis_dir)

        shutil.copytree(
            os.path.join(fff_analysis_dir, "dist"),
            jupyterhub_dist_dir, dirs_exist_ok=True,
        )

        mat_analysis_dir = os.path.join(root_dir, "mat_analysis")
        subprocess.run(["poetry", "build"], cwd=mat_analysis_dir)

        shutil.copytree(
            os.path.join(mat_analysis_dir, "dist"),
            jupyterhub_dist_dir, dirs_exist_ok=True
        )

        prop_analysis_dir = os.path.join(root_dir, "prop_analysis")
        subprocess.run(["poetry", "build"], cwd=prop_analysis_dir)

        shutil.copytree(
            os.path.join(prop_analysis_dir, "dist"),
            jupyterhub_dist_dir, dirs_exist_ok=True
        )

        subprocess.run(
            [
                "docker",
                "build",
                "--ssh",
                "default",
                os.path.join(containers_dir, f"{project_name}-jupyterhub"),
                "--tag",
                f"ascc/{project_name}-jupyterhub:dev",
                "--tag",
                f"ascc/{project_name}-jupyterhub:{project_version}",
            ]
        )

    if not args or "mppw" in args:

        mppw_dist_dir = os.path.join(containers_dir, "mppw", "dist")
        shutil.rmtree(
            mppw_dist_dir, ignore_errors=True
        )

        mppw_dir = os.path.join(root_dir, "mppw")
        subprocess.run(["poetry", "build"], cwd=mppw_dir)

        shutil.copytree(
            os.path.join(mppw_dir, "dist"),
            mppw_dist_dir, dirs_exist_ok=True
        )

        mppw_web_dir = os.path.join(root_dir, "mppw_web")
        subprocess.run(["poetry", "build"], cwd=mppw_web_dir)

        shutil.copytree(
            os.path.join(mppw_web_dir, "dist"),
            mppw_dist_dir, dirs_exist_ok=True
        )

        # mppw_clients_dir = os.path.join(root_dir, "mppw_clients")
        # subprocess.run(["poetry", "build"], cwd=mppw_clients_dir)
        # shutil.copytree(
        #     os.path.join(mppw_clients_dir, "dist"),
        #     mppw_dist_dir, dirs_exist_ok=True
        # )

        shutil.copy(
            os.path.join(containers_dir, f"{project_name}-stack.yml"),
            os.path.join(containers_dir, project_name, "dist"),
        )
        shutil.copy(
            os.path.join(containers_dir, f"{project_name}-stack.dev.yml"),
            os.path.join(containers_dir, project_name, "dist"),
        )

        subprocess.run(
            [
                "docker",
                "build",
                "--build-arg",
                f"PACKAGE_NAME={project_name}",
                "--build-arg",
                f"PACKAGE_VERSION={project_version}",
                "--ssh",
                "default",
                os.path.join(containers_dir, project_name),
                "--tag",
                f"ascc/{project_name}:dev",
                "--tag",
                f"ascc/{project_name}:{project_version}",
            ]
        )

    if not args or "registry" in args or "mppw-registry" in args:
        
        subprocess.run(
            [
                "docker",
                "build",
                "--ssh",
                "default",
                os.path.join(containers_dir, f"{project_name}-registry"),
                "--tag",
                f"ascc/{project_name}-registry:dev",
                "--tag",
                f"ascc/{project_name}-registry:{project_version}",
            ]
        )

def compose():

    subprocess.run(
        [
            "docker-compose",
            "-p",
            "mppw",
            "-f",
            os.path.join(containers_dir, "mppw-stack.yml"),
        ]
        + sys.argv[2:]
    )


def compose_dev():

    os.environ.setdefault("MPPW_EXTERNAL_PORT", "8000")
    os.environ.setdefault("MONGODB_EXTERNAL_PORT", "27027")
    os.environ.setdefault("MONGODB_ADMIN_USERNAME", "admin")
    os.environ.setdefault("MONGODB_ADMIN_PASSWORD", "password")
    os.environ.setdefault(
        "MPPW_LOCAL_PACKAGE_DIR", os.path.abspath(os.path.join(root_dir, "mppw", "mppw"))
    )
    os.environ.setdefault(
        "MPPW_WEB_LOCAL_PACKAGE_DIR", os.path.abspath(os.path.join(root_dir, "mppw_web", "mppw_web"))
    )

    subprocess.run(
        [
            "docker-compose",
            "-p",
            "mppw-dev",
            "-f",
            os.path.join(containers_dir, "mppw-stack.yml"),
            "-f",
            os.path.join(containers_dir, "mppw-stack.dev.yml"),
        ]
        + sys.argv[2:]
    )

def compose_registry(dev=True):

    subprocess.run(
        [
            "docker-compose",
            "-p",
            "mppw-registry" + ("-dev" if dev else ""),
            "-f",
            os.path.join(containers_dir, "mppw-registry.yml"),
        ] +
        ([
            "-f",
            os.path.join(containers_dir, "mppw-registry.dev.yml"),
        ] if dev else [])
        + sys.argv[2:]
    )

def push(repository: str, *images):

    project = None
    with open("pyproject.toml") as f:
        project = toml.load(f)

    project_name = project["tool"]["poetry"]["name"]
    project_version = project["tool"]["poetry"]["version"]

    for image in ["mppw", "mongodb", "nginx", "jupyterhub", "registry"]:
        
        if images and (image not in images and f"mppw-{image}" not in images):
            continue

        image = f"ascc/mppw-{image}" if image != "mppw" else f"ascc/{image}"

        for tag in ["dev", project_version]:

            subprocess.run(["docker", "image", "tag",
                f"{image}:{tag}", f"{repository}/{image}:{tag}"])

            subprocess.run(["docker", "image", "push", f"{repository}/{image}:{tag}"])

def tunnel():

    tunnel_furl = furl.furl(os.environ.get("DOCKER_HOST", ""))
    if not tunnel_furl.url:
        print("Remote $DOCKER_HOST is not configured, no tunneling required.")
    if not tunnel_furl.scheme == "ssh":
        print("Remote $DOCKER_HOST is not available via ssh:// protocol.")

    tunnel_forward_host = "localhost"  # tunnel_furl.netloc.split("@")[-1]

    tunnel_args = ["ssh", "-N", tunnel_furl.netloc]
    for local_port, remote_port in [(8080, 80), (44443, 443), (21037, 21017)]:
        tunnel_args.append("-L")
        tunnel_args.append(f"{local_port}:{tunnel_forward_host}:{remote_port}")

    print("Starting " + " ".join(tunnel_args) + " ...")

    subprocess.run(tunnel_args)


parser = argh.ArghParser()
parser.add_commands([build, push, tunnel])  # , compose])


def main():
    if sys.argv[1] == "compose":
        # Need raw access to CL args
        compose()
    elif sys.argv[1] == "compose-dev":
        compose_dev()
    elif sys.argv[1] == "compose-registry":
        compose_registry(dev=False)
    elif sys.argv[1] == "compose-registry-dev":
        compose_registry(dev=True)
    else:
        parser.dispatch()


if __name__ == "__main__":
    main()
