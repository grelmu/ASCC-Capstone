"""
add_user_schemas
"""

import pymongo
import pymongo.database

name = "20230224205953_add_user_schemas"
dependencies = ["20220601192603_artifacts_spatial_parent_index"]


def upgrade(db: pymongo.database.Database):
    db["user_schemas"].create_index("type_urn")
    db["user_schemas"].create_index("tags")
    db["user_schemas"].create_index(
        [("project", pymongo.ASCENDING), ("type_urn", pymongo.ASCENDING)]
    )


def downgrade(db: pymongo.database.Database):
    db["user_schemas"].drop_index("type_urn")
    db["user_schemas"].drop_index("tags")
    db["user_schemas"].drop_index(
        [("project", pymongo.ASCENDING), ("type_urn", pymongo.ASCENDING)]
    )
