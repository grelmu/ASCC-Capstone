import sys
import os
import subprocess
import toml
import glob
import shutil
import argh

root_dir = os.path.dirname(os.path.dirname(__file__))
dist_dir = os.path.join(root_dir, "dist")
containers_dir = os.path.join(root_dir, "containers")

def build():

    project = None
    with open("pyproject.toml") as f:
        project = toml.load(f)
    
    project_name = project['tool']['poetry']['name']
    project_version = project['tool']['poetry']['version']

    subprocess.run(["poetry", "build"])

    shutil.copy(os.path.join(containers_dir, f"{project_name}-stack.yml"), os.path.join(containers_dir, project_name))
    shutil.copy(os.path.join(containers_dir, f"{project_name}-stack.dev.yml"), os.path.join(containers_dir, project_name))
    shutil.rmtree(os.path.join(containers_dir, project_name, "dist"))
    shutil.copytree(dist_dir, os.path.join(containers_dir, project_name, "dist"))

    subprocess.run(["docker",  "build",
                    os.path.join(containers_dir, f"{project_name}-mongodb"),
                    "--tag", f"ascc/{project_name}-mongodb:dev",
                    "--tag", f"ascc/{project_name}-mongodb:{project_version}"])
    
    subprocess.run(["docker",  "build",  
                    "--build-arg", f"PACKAGE_NAME={project_name}", 
                    "--build-arg", f"PACKAGE_VERSION={project_version}",
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

parser = argh.ArghParser()
parser.add_commands([build]) #, compose])

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