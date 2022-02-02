import fastapi
from fastapi import Security, Depends
import typing
from typing import Union, List
import pydantic

from mppw import logger
from . import models
from . import repositories
from .repositories import request_repo_layer
from . import security
from .security import request_user, PROVENANCE_SCOPE
from . import projects

def create_router(app):

    router = fastapi.APIRouter(prefix="/api/artifacts")

    @router.post("/", response_model=Union[models.MaterialArtifact, models.DigitalArtifact], status_code = fastapi.status.HTTP_201_CREATED)
    def create(artifact: Union[models.MaterialArtifact, models.DigitalArtifact],
               user: security.ScopedUser = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
               repo_layer = Depends(request_repo_layer(app))):
        
        projects.check_project_claims_for_user(user, [str(artifact.project)])

        art_repo = repo_layer.artifacts
        return art_repo.create(artifact)

    @router.get("/{id}", response_model=Union[models.MaterialArtifact, models.DigitalArtifact])
    def read(id: str,
             user: security.ScopedUser = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
             repo_layer = Depends(request_repo_layer(app))):
        
        result = repo_layer.artifacts.query_one(
            id=id,
            project_ids=projects.project_claims_for_user(user)
        )

        if result is None:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)
        
        return result

    @router.get("/", response_model=List[Union[models.DigitalArtifact, models.MaterialArtifact]])
    def query(project_ids: List[str] = fastapi.Query(None),
              active: bool = fastapi.Query(True),
              user: security.ScopedUser = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
              repo_layer = Depends(request_repo_layer(app))):

        if project_ids is None:
            project_ids = projects.project_claims_for_user(user)
        
        projects.check_project_claims_for_user(user, project_ids)
        
        return list(repo_layer.artifacts.query(
            project_ids=project_ids,
            active=active,
        ))

    @router.delete("/{id}", response_model=bool)
    def delete(id: str,
               preserve_data: bool = True,
               current_user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
               repo_layer = Depends(request_repo_layer(app))):
        
        modified = (repo_layer.artifacts.deactivate if preserve_data else repo_layer.artifacts.delete)(
            id,
            project_ids=projects.project_claims_for_user(current_user)
        )
        
        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    return router
