import subprocess
import toml
import os
import glob
import shutil

def main():

    root_dir = os.path.dirname(os.path.dirname(__file__))
    dist_dir = os.path.join(root_dir, "dist")
    project = None
    with open("pyproject.toml") as f:
        project = toml.load(f)
        
    project_name = project['tool']['poetry']['name']
    project_version = project['tool']['poetry']['version']

    subprocess.run(["poetry", "build"])
    subprocess.run(["docker",  "build",  
                    "--build-arg", "PACKAGE_NAME=%s" % project_name, 
                    "--build-arg", "PACKAGE_VERSION=%s" % project_version,
                    ".",
                    "--tag", "ascc/%s:dev" % (project_name,),
                    "--tag", "ascc/%s:%s" % (project_name, project_version,)])

if __name__ == "__main__":
    import argh
    argh.dispatch_command(main)