"""
operations_ftindex
"""

import pymongo
import pymongo.database

name = "20220321192855_operations_ftindex"
dependencies = ["20220201193449_add_user_scopes_claims"]


def upgrade(db: pymongo.database.Database):

    db["operations"].create_index([("name", "text"), ("description", "text")])


def downgrade(db: pymongo.database.Database):

    db["operations"].drop_index([("name", "text"), ("description", "text")])
