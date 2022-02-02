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
from . import projects

def create_router(app):

    combined_router = fastapi.APIRouter()

    router = fastapi.APIRouter(prefix="/api/operations")

    @router.post("/", response_model=models.Operation, status_code = fastapi.status.HTTP_201_CREATED)
    def create(operation: models.Operation,
               user: security.ScopedUser = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
               repo_layer = Depends(request_repo_layer(app))):
        
        projects.check_project_claims_for_user(user, [str(operation.project)])

        return repo_layer.operations.create(operation)

    @router.get("/{id}", response_model=models.Operation)
    def read(id: str,
             user: security.ScopedUser = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
             repo_layer = Depends(request_repo_layer(app))):
        
        result = repo_layer.operations.query_one(
            id=id,
            project_ids=projects.project_claims_for_user(user)
        )

        if result is None:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)
        
        return result

    @router.get("/", response_model=List[models.Operation])
    def query(project_ids: List[str] = fastapi.Query(None),
              active: bool = fastapi.Query(True),
              user: security.ScopedUser = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
              repo_layer = Depends(request_repo_layer(app))):

        if project_ids is None:
            project_ids = projects.project_claims_for_user(user)

        projects.check_project_claims_for_user(user, project_ids)
        
        return list(repo_layer.operations.query(
            project_ids=project_ids,
            active=active,
        ))

    @router.delete("/{id}", response_model=bool)
    def delete(id: str,
               preserve_data: bool = True,
               current_user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
               repo_layer = Depends(request_repo_layer(app))):
        
        modified = (repo_layer.operations.deactivate if preserve_data else repo_layer.operations.delete)(
            id,
            project_ids=projects.project_claims_for_user(current_user)
        )
        
        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    combined_router.include_router(router)

    router = fastapi.APIRouter(prefix="/api/serviced-operations")

    @router.post("/", response_model=models.Operation, status_code = fastapi.status.HTTP_201_CREATED)
    def create_serviced(operation: models.Operation,
                        user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
                        service_layer: services.ServiceLayer = Depends(request_service_layer(app))):
            
        projects.check_project_claims_for_user(user, [str(operation.project)])

        return service_layer.create_default(operation)


    @router.get("/types/", response_model=List[services.ServicedOperationType])
    def query_serviced_types(user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
                             service_layer: services.ServiceLayer = Depends(request_service_layer(app))):

        return list(service_layer.serviced_operation_types())

    combined_router.include_router(router)

    return combined_router
