import os
import types
from fastapi import FastAPI, Request, Depends

from mppw import logger
from mppw import __version__ as __mppw_version__

from . import models
from . import storage

def create_app(model_storage_layer: storage.ModelStorageLayer,
               upgrade_storage_on_startup=False):

    app = FastAPI()

    # This MUST come before including router components
    if upgrade_storage_on_startup:
        @app.on_event('startup')
        def upgrade_model_storage_layer():
            model_storage_layer.upgrade_schema()

    app.state.model_storage_layer = model_storage_layer

    def request_repo_layer():
        with app.state.storage_layer.new_session() as session:
            yield models.RepositoryLayer(session)

    app.state.request_repo_layer = request_repo_layer

    @app.get("/version")
    def version():
        return {"version": __mppw_version__}

    from . import security

    security.create_router(app)

    return app