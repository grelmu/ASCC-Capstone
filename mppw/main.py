import os
from mppw import logger
from . import storage
from . import app

app = app.create_app(storage.from_env())
