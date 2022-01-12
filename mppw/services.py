from typing import Optional, List, ClassVar, Any
import fastapi
from fastapi import Depends
import fastapi.encoders
import pydantic
import bson
import datetime

from mppw import logger

from . import models
from . import repositories

DATABASE_BUCKET_URN = f"{models.DigitalArtifact.URN_PREFIX}:database-bucket"
FILE_BUCKET_URN = f"{models.DigitalArtifact.URN_PREFIX}:file-bucket"

class ProvenanceServices:

    def __init__(self, repo_layer):
        self.repo_layer = repo_layer

    def initialize_artifact(self, id: str):
        artifact = self.repo_layer.artifacts.read(id)
        if artifact.type_urn == DATABASE_BUCKET_URN:
            return self.initialize_db_bucket_artifact(artifact)
        elif artifact.type_urn == FILE_BUCKET_URN:
            return self.initialize_file_bucket_artifact(artifact)
        else:
            return False

    def initialize_db_bucket_artifact(self, artifact: models.DigitalArtifact):
        pass

    def initialize_file_bucket_artifact(self, artifact: models.DigitalArtifact):
        pass

class ServiceLayer:

    def __init__(self, repo_layer):
        self.repo_layer = repo_layer

    def get(self, clazz):
        return clazz(self.repo_layer)

def init_request_service_layer(app: fastapi.FastAPI):

    def request_service_layer(repo_layer = Depends(repositories.request_repo_layer(app))):
        return ServiceLayer(repo_layer)

    app.state.services_request_service_layer = request_service_layer

def request_service_layer(app: fastapi.FastAPI) -> ServiceLayer:
    return app.state.services_request_service_layer