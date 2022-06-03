"""
artifacts_spatial_parent_index
"""

import pymongo
import pymongo.database

name = "20220601192603_artifacts_spatial_parent_index"
dependencies = ["20220321192855_operations_ftindex"]


def upgrade(db: pymongo.database.Database):
    db["artifacts"].create_index("spatial_frame.parent_frame")


def downgrade(db: pymongo.database.Database):
    db["artifacts"].drop_index("spatial_frame.parent_frame")
