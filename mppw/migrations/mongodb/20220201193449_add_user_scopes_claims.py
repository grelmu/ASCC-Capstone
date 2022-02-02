"""
add_user_scopes_claims
"""
name = '20220201193449_add_user_scopes_claims'
dependencies = ['20220201175716_seed_more_projects']

import pymongo
import pymongo.database

def upgrade(db: pymongo.database.Database):
        
    for user_doc in db["users"].find({ "allowed_scopes": None }):
        db["users"].update({ "_id": user_doc["_id"] }, { "$set": { "allowed_scopes": ["*"] }})


def downgrade(db: pymongo.database.Database):
    pass
