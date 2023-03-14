import fastapi
from fastapi import Depends

from .. import repositories
from .service_layer import ServiceLayer
from .operation_services import OperationServices
from .artifact_services import ArtifactServices
from .provenance_services import ProvenanceServices
from .schema_services import SchemaServices, ResolvedSchema


def init_request_service_layer(app: fastapi.FastAPI):

    repositories.using_app_repo_layer(
        app, lambda repo_layer: ServiceLayer.init_persistent(repo_layer)
    )

    def request_service_layer(repo_layer=Depends(repositories.request_repo_layer(app))):
        return ServiceLayer(repo_layer)

    app.state.services_request_service_layer = request_service_layer


def request_service_layer(app: fastapi.FastAPI) -> ServiceLayer:
    return app.state.services_request_service_layer
