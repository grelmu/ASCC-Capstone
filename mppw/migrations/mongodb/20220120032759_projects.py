"""
projects
"""

import pymongo
import pymongo.database


name = '20220120032759_projects'
dependencies = ['20220113185527_core']


def upgrade(db: pymongo.database.Database):
    
    db["projects"].create_index("name")
    db["operations"].create_index([("project", pymongo.ASCENDING), ("type_urn", pymongo.ASCENDING)])

def downgrade(db: pymongo.database.Database):
    
    db["operations"].drop_index([("project", pymongo.ASCENDING), ("type_urn", pymongo.ASCENDING)])
    db["projects"].drop_index("name")