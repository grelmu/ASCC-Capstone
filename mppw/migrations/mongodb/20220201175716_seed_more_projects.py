"""
seed_more_projects
"""
name = "20220201175716_seed_more_projects"
dependencies = ["20220120033703_seed_projects"]

import os
import pymongo
import pymongo.database
import passlib.context

from mppw.migrations import include_seed_data

password_context = passlib.context.CryptContext(schemes=["bcrypt"], deprecated="auto")


def upgrade(db: pymongo.database.Database):
    if include_seed_data():
        result = db["projects"].insert_one(
            {
                "name": "Example Project (with users)",
                "description": "A dev-only example project with users",
            }
        )
        db["users"].insert_one(
            {
                "username": "example",
                "hashed_password": password_context.hash("example"),
                "allowed_scopes": ["provenance"],
                "local_claims": {
                    "projects": [result.inserted_id],
                },
            }
        )


def downgrade(db: pymongo.database.Database):
    if include_seed_data():
        db["users"].remove_one({"username": "example"})
        db["projects"].remove_one({"name": "Example Project (with users)"})
