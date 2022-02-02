"""
seed_projects
"""

import os
import pymongo
import pymongo.database

from mppw.migrations import include_seed_data

name = '20220120033703_seed_projects'
dependencies = ['20220120032759_projects']

def upgrade(db: pymongo.database.Database):
    if include_seed_data():
        db["projects"].insert_one({ "name": "ExampleProject", "description": "A dev-only example project" })
    else:
        pass

def downgrade(db: pymongo.database.Database):
    if include_seed_data():
        db["projects"].remove_one({ "name": "ExampleProject" })
