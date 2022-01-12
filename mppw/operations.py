import fastapi
from fastapi import Security, Depends
import typing
from typing import Union, List

from mppw import logger
from . import models
from . import repositories
from .repositories import request_repo_layer
from . import security
from .security import request_user, PROVENANCE_SCOPE

def create_router(app):

    router = fastapi.APIRouter(prefix="/api/operations")

    @router.post("/", response_model=models.Operation)
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
    def query(current_user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
              repo_layer = Depends(request_repo_layer(app))):

        op_repo = repo_layer.operations
        return list(op_repo.query())

    @router.delete("/{id}", response_model=bool)
    def delete(id: str,
               current_user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
               repo_layer = Depends(request_repo_layer(app))):
        
        op_repo = repo_layer.operations
        return op_repo.delete(id) > 0

    return router
