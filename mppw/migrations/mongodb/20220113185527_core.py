"""
core
"""
name = "20220113185527_core"
dependencies = ["20220106213202_initial"]


def upgrade(db: "pymongo.database.Database"):

    for field in ["type_urn", "name", "tags"]:
        db["artifacts"].create_index(field)
        db["operations"].create_index(field)

    for field in ["start_at", "end_at", "status"]:
        db["operations"].create_index(field)


def downgrade(db: "pymongo.database.Database"):

    for field in ["start_at", "end_at", "status"]:
        db["operations"].drop_index(field)

    for field in ["type_urn", "name", "tags"]:
        db["artifacts"].drop_index(field)
        db["operations"].drop_index(field)
