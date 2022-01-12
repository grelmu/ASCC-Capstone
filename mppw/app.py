import os
import types
import fastapi
import fastapi.staticfiles

from mppw import logger
from mppw import __version__ as __mppw_version__

from . import storage
from . import models
from . import services

def create_app(model_storage_layer: storage.ModelStorageLayer):

    app = fastapi.FastAPI()

    #
    # Setup storage basics
    #

    storage.init_app_model_storage_layer(app, model_storage_layer)

    models.init_request_repo_layer(app)

    services.init_request_service_layer(app)

    #
    # Setup core endpoints
    #

    @app.get("/")
    def root():
        return fastapi.responses.RedirectResponse("/ui")

    @app.get("/ui")
    @app.get("/ui/")
    def ui_root():
        return fastapi.responses.RedirectResponse("/ui/index.html")

    app.mount("/ui", fastapi.staticfiles.StaticFiles(directory=os.path.join(os.path.dirname(__file__), "ui")), name="ui")

    @app.get("/version")
    def version():
        return {"version": __mppw_version__}

    #
    # Setup API
    #

    from . import security

    # Must be initialized *first*, as it also initializes request_user lookups
    app.include_router(security.create_router(app))

    from . import artifacts

    app.include_router(artifacts.create_router(app))

    from . import operations

    app.include_router(operations.create_router(app))

    return app