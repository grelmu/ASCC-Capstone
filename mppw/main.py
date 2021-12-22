import os
from mppw import logger
from . import storage
from . import app

app = app.create_app(
    storage.ModelStorageLayer.get_default(),
    upgrade_storage_on_startup=bool(os.environ.get('UPGRADE_STORAGE_ON_STARTUP', True)))