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

def create_router(app):

    router = fastapi.APIRouter(prefix="/api/artifacts")

    # class InitializedArtifact(pydantic.BaseModel):
    #     initialize: bool
    #     artifact: models.DigitalArtifact

    @router.post("/", response_model=Union[models.MaterialArtifact, models.DigitalArtifact])
    def create(artifact: Union[models.MaterialArtifact, models.DigitalArtifact],
               current_user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
               repo_layer = Depends(request_repo_layer(app))):
        
        art_repo = repo_layer.artifacts
        return art_repo.create(artifact)

    @router.get("/{id}", response_model=Union[models.MaterialArtifact, models.DigitalArtifact])
    def read(id: str,
             current_user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
             repo_layer = Depends(request_repo_layer(app))):
        
        art_repo = repo_layer.artifacts
        return art_repo.read(id)

    @router.get("/", response_model=List[Union[models.DigitalArtifact, models.MaterialArtifact]])
    def query(current_user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
              repo_layer = Depends(request_repo_layer(app))):

        art_repo = repo_layer.artifacts
        return list(art_repo.query())

    @router.delete("/{id}", response_model=bool)
    def delete(id: str,
               current_user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
               repo_layer = Depends(request_repo_layer(app))):
        
        art_repo = repo_layer.artifacts
        return art_repo.delete(id) > 0

    # @router.post("/initialize/{id}", response_model=bool)
    # def initialize(id: str,
    #                current_user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
    #                repo_layer = Depends(request_repo_layer(app))):
        
    #     art_repo = repo_layer.artifacts
    #     return art_repo.create(artifact)

    return router
