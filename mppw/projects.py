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
from .security import request_user, ADMIN_SCOPE, PROVENANCE_SCOPE

def create_router(app):

    router = fastapi.APIRouter(prefix="/api/projects")
    
    @router.post("/", response_model=models.Project, status_code = fastapi.status.HTTP_201_CREATED)
    def create(project: models.Project,
               user: security.ScopedUser = Security(request_user(app), scopes=[ADMIN_SCOPE, PROVENANCE_SCOPE]),
               repo_layer = Depends(request_repo_layer(app))):
        
        result = repo_layer.projects.create(project)
        security.reload_project_claims(app)
        return result

    @router.get("/{id}", response_model=models.Project)
    def read(id: str,
             user: security.ScopedUser = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
             repo_layer = Depends(request_repo_layer(app))):
        
        check_project_claims_for_user(user, [str(id)])

        result = repo_layer.projects.query_one(ids=[id])
        if result is None:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)
        
        return result

    @router.get("/", response_model=List[models.Project])
    def query(active: bool = fastapi.Query(True),
              user: security.ScopedUser = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
              repo_layer = Depends(request_repo_layer(app))):

        ids = project_claims_for_user(user)
        
        logger.info(f"Project Claims: {ids}")

        return list(repo_layer.projects.query(ids=ids, active=active))

    @router.delete("/{id}", response_model=bool)
    def delete(id: str,
               preserve_data: bool = True,
               user: security.ScopedUser = Security(request_user(app), scopes=[ADMIN_SCOPE, PROVENANCE_SCOPE]),
               repo_layer = Depends(request_repo_layer(app))):

        modified = (repo_layer.projects.deactivate if preserve_data else repo_layer.projects.delete)(id)
        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        security.reload_project_claims(app)
        return True

    return router

def project_claims_for_user(user: security.ScopedUser):
    if security.has_admin_scope(user): return None
    return list(map(str, user.claims["projects"]))

def check_project_claims_for_user(user: security.ScopedUser, project_ids: List[str]):
    if security.has_admin_scope(user): return
    project_claims = project_claims_for_user(user)
    for project_id in (project_ids or []):
        if project_id not in project_claims:
            raise fastapi.HTTPException(fastapi.status.HTTP_401_UNAUTHORIZED)