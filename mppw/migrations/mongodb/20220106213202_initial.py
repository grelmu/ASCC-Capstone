"""
initial
"""

name = "20220106213202_initial"
dependencies = []


def upgrade(db: "pymongo.database.Database"):
    db["users"].create_index("username")


def downgrade(db: "pymongo.database.Database"):
    db["users"].drop_index("username")
