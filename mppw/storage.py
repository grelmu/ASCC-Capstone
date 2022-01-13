from email.policy import default
import os
import fastapi
from fastapi.applications import FastAPI
import pymongo
import pymongo.errors
import gridfs
import furl
import time

from mppw import logger
from mppw import __file__ as __mppw_file__

import pymongo_migrate.mongo_migrate

def from_env(upgrade_storage_on_startup=None):
    if os.environ.get("MONGODB_URL"):
        return MongoDBStorageLayer.from_env(upgrade_storage_on_startup)
    else:
        raise Exception("Could not detect storage layer from environment variables")

def init_app_storage_layer(app: fastapi.FastAPI, storage_layer):
    app.state.storage_layer = storage_layer

def app_storage_layer(app: fastapi.FastAPI):
    return app.state.storage_layer

def add_username_password(url_str, username, password):
    if url_str is None: return None
    if username is None: return url_str
    url = furl.furl(url_str)
    url.username = username
    url.password = password
    return str(url)

#
# MongoDB Storage layer implementation
#

class MongoDBStorageLayer:

    @staticmethod
    def from_env(upgrade_storage_on_startup=None):
        
        mdb_url = os.environ.get("MONGODB_URL")
        admin_username = os.environ.get("MONGODB_ADMIN_USERNAME")
        admin_password = os.environ.get("MONGODB_ADMIN_PASSWORD")
        
        layer = MongoDBStorageLayer(
            mdb_url,
            admin_username,
            admin_password)

        upgrade_storage_on_startup = bool(os.environ.get('UPGRADE_STORAGE_ON_STARTUP', True)) \
            if upgrade_storage_on_startup is None else upgrade_storage_on_startup

        if upgrade_storage_on_startup:
            layer.upgrade_schema()
        
        # Don't store the sensitive credentials anywhere but the environment, which we can clear
        # if/when required
        layer.get_admin_username = lambda: os.environ.get("MONGODB_ADMIN_USERNAME")
        layer.get_admin_password = lambda: os.environ.get("MONGODB_ADMIN_PASSWORD")

        return layer

    def __init__(self, mdb_url, admin_username, admin_password):

        self.mdb_url = mdb_url
        self.mdb_client = pymongo.MongoClient(
            self.mdb_url,
            username=admin_username,
            password=admin_password)    

        # Ensure our auth has worked
        self.mdb_client.get_default_database()

    def upgrade_schema(self):
        
        logger.info("Upgrading storage schema...")
        
        migrations_dir = os.path.join(os.path.dirname(__file__), "migrations", "mongodb")

        migrator = pymongo_migrate.mongo_migrate.MongoMigrate(
            client=self.mdb_client,
            migrations_dir=migrations_dir,
            logger=logger)

        while True:
            try:
                migrator.upgrade()
                break
            except pymongo.errors.NotPrimaryError as ex:
                logger.warning(f"Waiting for primary node to upgrade storage schema...\n{ex}")
                time.sleep(2)

        logger.info("Done upgrading.")

    def start_session(self):
        return self.mdb_client.start_session(causal_consistency=True)

    def get_gridfs_db(self, name):
        default_db_name = self.mdb_client.get_default_database().name
        return self.mdb_client[f"{default_db_name}_files"]
