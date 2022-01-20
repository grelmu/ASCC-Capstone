import fastapi
from fastapi import Security, Depends
import typing
from typing import Union, List, Optional
import pydantic
import datetime

from mppw import logger
from . import models
from . import repositories
from .repositories import request_repo_layer
from . import services
from .services import request_service_layer
from . import security
from .security import request_user, PROVENANCE_SCOPE

def create_router(app):

    combined_router = fastapi.APIRouter()

    router = fastapi.APIRouter(prefix="/api/operations")

    @router.post("/", response_model=models.Operation, status_code = fastapi.status.HTTP_201_CREATED)
    def create(operation: models.Operation,
               current_user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
               repo_layer = Depends(request_repo_layer(app))):
        
        op_repo = repo_layer.operations
        return op_repo.create(operation)

    @router.get("/{id}", response_model=models.Operation)
    def read(id: str,
             current_user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
             repo_layer = Depends(request_repo_layer(app))):
        
        op_repo = repo_layer.operations
        return op_repo.read(id)

    @router.get("/", response_model=List[models.Operation])
    def query(project_id: str = None,
              current_user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
              repo_layer = Depends(request_repo_layer(app))):

        op_repo = repo_layer.operations
        return list(op_repo.query(project_id=project_id))

    @router.delete("/{id}", response_model=bool)
    def delete(id: str,
               current_user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
               repo_layer = Depends(request_repo_layer(app))):
        
        op_repo = repo_layer.operations
        return op_repo.delete(id) > 0

    combined_router.include_router(router)

    router = fastapi.APIRouter(prefix="/api/serviced-operations")

    @router.post("/", response_model=models.Operation, status_code = fastapi.status.HTTP_201_CREATED)
    def create_serviced(operation: models.Operation,
                        current_user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
                        service_layer: services.ServiceLayer = Depends(request_service_layer(app))):
            
        return service_layer.create_default(operation)


    @router.get("/types/", response_model=List[services.ServicedOperationType])
    def query_serviced_types(current_user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
                             service_layer: services.ServiceLayer = Depends(request_service_layer(app))):

        return list(service_layer.serviced_operation_types())

    combined_router.include_router(router)

    return combined_router
