import os


def include_seed_data():
    return (
        os.environ.get("MPPW_MIGRATIONS_INCLUDE_SEED_DATA", "false").lower() == "true"
    )
