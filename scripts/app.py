import sys
import os
import subprocess
import argh

def dev(reset_db=False):

    root_dir = os.path.dirname(os.path.dirname(__file__))
    containers_dir = os.path.join(root_dir, "containers")

    os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27027/mppw_dev?authSource=admin")
    os.environ.setdefault("MONGODB_ADMIN_USERNAME", "admin")
    os.environ.setdefault("MONGODB_ADMIN_PASSWORD", "password")

    if reset_db:
        subprocess.run([
            "docker-compose",
            "-p", "mppw-dev",
            "-f", os.path.join(containers_dir, "mppw-stack.yml"),
            "-f", os.path.join(containers_dir, "mppw-stack.dev.yml"),
            "down", "-v"])

    subprocess.run([
        "docker-compose",
        "-p", "mppw-dev",
        "-f", os.path.join(containers_dir, "mppw-stack.yml"),
        "-f", os.path.join(containers_dir, "mppw-stack.dev.yml"),
        "up", "-d", "mongodb"])

    subprocess.run([
        "uvicorn", "--host", "0.0.0.0", "mppw.main:app", "--debug"
    ])

parser = argh.ArghParser()
parser.add_commands([dev])

def main():
    parser.dispatch()

if __name__ == "__main__":
    main()