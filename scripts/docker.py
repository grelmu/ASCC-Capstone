import sys
import os
import subprocess
import toml
import glob
import shutil
import argh

def build():

    root_dir = os.path.dirname(os.path.dirname(__file__))
    dist_dir = os.path.join(root_dir, "dist")
    containers_dir = os.path.join(root_dir, "containers")

    project = None
    with open("pyproject.toml") as f:
        project = toml.load(f)
    
    project_name = project['tool']['poetry']['name']
    project_version = project['tool']['poetry']['version']

    subprocess.run(["poetry", "build"])

    shutil.copy(os.path.join(containers_dir, f"{project_name}-stack.yml"), os.path.join(containers_dir, project_name))
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

    root_dir = os.path.dirname(os.path.dirname(__file__))
    containers_dir = os.path.join(root_dir, "containers")

    subprocess.run(["docker-compose", "-p", "mppw", "-f", os.path.join(containers_dir, "mppw-stack.yml")] + sys.argv[2:])

parser = argh.ArghParser()
parser.add_commands([build]) #, compose])

def main():
    if sys.argv[1] == "compose":
        # Need raw access to CL args
        compose()
    else:
        parser.dispatch()

if __name__ == "__main__":
    main()