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
    
    project_name = project['tool']['poetry']['name']
    project_version = project['tool']['poetry']['version']

    os.environ["DOCKER_BUILDKIT"] = "1"

    if not args or "nginx" in args or "mppw-nginx" in args:
        subprocess.run(["docker",  "build",
                        "--ssh", "default",
                        os.path.join(containers_dir, f"{project_name}-nginx"),
                        "--tag", f"ascc/{project_name}-nginx:dev",
                        "--tag", f"ascc/{project_name}-nginx:{project_version}"])

    if not args or "mongodb" in args or "mppw-mongodb" in args:
        subprocess.run(["docker",  "build",
                        "--ssh", "default",
                        os.path.join(containers_dir, f"{project_name}-mongodb"),
                        "--tag", f"ascc/{project_name}-mongodb:dev",
                        "--tag", f"ascc/{project_name}-mongodb:{project_version}"])

    if not args or "jupyterhub" in args or "mppw-jupyterhub" in args:
        subprocess.run(["docker",  "build",
                        "--ssh", "default",
                        os.path.join(containers_dir, f"{project_name}-jupyterhub"),
                        "--tag", f"ascc/{project_name}-jupyterhub:dev",
                        "--tag", f"ascc/{project_name}-jupyterhub:{project_version}"])

    if not args or "mppw" in args:
        subprocess.run(["poetry", "build"])

        shutil.rmtree(os.path.join(containers_dir, project_name, "dist"))
        shutil.copytree(dist_dir, os.path.join(containers_dir, project_name, "dist"))
        shutil.copy(os.path.join(containers_dir, f"{project_name}-stack.yml"), os.path.join(containers_dir, project_name, "dist"))

        subprocess.run(["docker",  "build",  
                        "--build-arg", f"PACKAGE_NAME={project_name}", 
                        "--build-arg", f"PACKAGE_VERSION={project_version}",
                        "--ssh", "default",
                        os.path.join(containers_dir, project_name),
                        "--tag", f"ascc/{project_name}:dev",
                        "--tag", f"ascc/{project_name}:{project_version}"])

def compose():

    subprocess.run(["docker-compose", "-p", "mppw", "-f", os.path.join(containers_dir, "mppw-stack.yml")] + sys.argv[2:])

def compose_dev():

    os.environ.setdefault("MPPW_EXTERNAL_PORT", "8000")
    os.environ.setdefault("MONGODB_EXTERNAL_PORT", "27027")
    os.environ.setdefault("MONGODB_ADMIN_USERNAME", "admin")
    os.environ.setdefault("MONGODB_ADMIN_PASSWORD", "password")
    os.environ.setdefault("MPPW_LOCAL_PACKAGE_DIR", os.path.abspath(os.path.join(root_dir, "mppw")))

    subprocess.run(["docker-compose", "-p", "mppw-dev", 
        "-f", os.path.join(containers_dir, "mppw-stack.yml"),
        "-f", os.path.join(containers_dir, "mppw-stack.dev.yml")] + sys.argv[2:])

def tunnel():

    tunnel_furl = furl.furl(os.environ.get("DOCKER_HOST", ""))
    if not tunnel_furl.url:
        print("Remote $DOCKER_HOST is not configured, no tunneling required.")
    if not tunnel_furl.scheme == "ssh":
        print("Remote $DOCKER_HOST is not available via ssh:// protocol.")

    tunnel_forward_host = "localhost" #tunnel_furl.netloc.split("@")[-1]

    tunnel_args = ["ssh", "-N", tunnel_furl.netloc]
    for local_port, remote_port in [(8080, 80), (44443, 443), (21037, 21017)]:
        tunnel_args.append("-L")
        tunnel_args.append(f"{local_port}:{tunnel_forward_host}:{remote_port}")

    print("Starting " + " ".join(tunnel_args) + " ...")

    subprocess.run(tunnel_args)

parser = argh.ArghParser()
parser.add_commands([build, tunnel]) #, compose])

def main():
    if sys.argv[1] == "compose":
        # Need raw access to CL args
        compose()
    elif sys.argv[1] == "compose-dev":
        compose_dev()
    else:
        parser.dispatch()

if __name__ == "__main__":
    main()