import os
import sqlmodel
import alembic.config
import furl

from mppw import logger
from mppw import __file__ as __mppw_file__

def add_username_password(url_str, username, password):
    if username is None: return url_str
    url = furl.furl(url_str)
    url.username = username
    url.password = password
    return str(url)

STORAGE_USERNAME = os.environ.get("STORAGE_USERNAME")
STORAGE_PASSWORD = os.environ.get("STORAGE_PASSWORD")
STORAGE_URL = add_username_password(os.environ.get("STORAGE_URL", "sqlite://"), STORAGE_USERNAME, STORAGE_PASSWORD)

print(STORAGE_URL, flush=True)

class ModelStorageLayer:

    _default_storage_layer = None
    _active_storage_layers = []

    @staticmethod
    def get_active():
        if len(ModelStorageLayer._active_storage_layers) > 0:
            return ModelStorageLayer._active_storage_layers[0]
        return ModelStorageLayer.get_default()

    @staticmethod
    def get_default():
        if ModelStorageLayer._default_storage_layer is None:
            ModelStorageLayer._default_storage_layer = ModelStorageLayer(STORAGE_URL, STORAGE_USERNAME, STORAGE_PASSWORD)
        return ModelStorageLayer._default_storage_layer

    def __init__(self, url, username, password):

        self.url = url
        if username is not None:
            self.url = add_username_password(url, username, password)
        self.engine = sqlmodel.create_engine(STORAGE_URL)

    def upgrade_schema(self):
        
        ini_filename = os.path.join(os.path.dirname(__mppw_file__), 'migrations', 'alembic.ini')
        
        logger.info("Upgrading storage schema...")
        
        try:
            ModelStorageLayer._active_storage_layers.append(self)
            alembic.config.main(argv=[
                '--raiseerr',
                '--config', ini_filename,
                'upgrade',
                'head'
            ])
        finally:
            ModelStorageLayer._active_storage_layers.pop()

        logger.info("Done upgrading.")

    def new_session(self):
        return sqlmodel.Session(self.engine)
