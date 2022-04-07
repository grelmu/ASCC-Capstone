import sys
import os
import subprocess
import argh

import mppw
import pymongo_migrate.mongo_migrate

mppw_dir = os.path.dirname(mppw.__file__)
migrations_dir = os.path.join(mppw_dir, "migrations", "mongodb")


def gen(name: str):
    migrator = pymongo_migrate.mongo_migrate.MongoMigrate(
        client=None, migrations_dir=migrations_dir
    )
    migrator.generate(name=None, description=name)


def ls():
    migrator = pymongo_migrate.mongo_migrate.MongoMigrate(
        client=None, migrations_dir=migrations_dir
    )
    for migration in migrator.get_migrations():
        print(migration)


def show(mongodb_url: str):
    subprocess.run(["pymongo-migrate", "show", "-m", migrations_dir, "-u", mongodb_url])


parser = argh.ArghParser()
parser.add_commands([gen, ls, show])


def main():
    parser.dispatch()


if __name__ == "__main__":
    main()
