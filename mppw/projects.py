from tokenize import String
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

    router = fastapi.APIRouter(prefix="/api/projects")
    
    @router.post("/", response_model=models.Project, status_code = fastapi.status.HTTP_201_CREATED)
    def create(project: models.Project,
               current_user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
               repo_layer = Depends(request_repo_layer(app))):
        
        return repo_layer.projects.create(project)

    @router.get("/{id}", response_model=models.Project)
    def read(id: str,
             current_user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
             repo_layer = Depends(request_repo_layer(app))):
        
        return repo_layer.projects.read(id)

    @router.get("/", response_model=List[models.Project])
    def query(current_user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
              repo_layer = Depends(request_repo_layer(app))):

        return list(repo_layer.projects.query())

    @router.delete("/{id}", response_model=bool)
    def delete(id: str,
               current_user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
               repo_layer = Depends(request_repo_layer(app))):
        
        return repo_layer.projects.delete(id) > 0

    return router
