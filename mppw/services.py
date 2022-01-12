from typing import Optional, List, ClassVar, Any
import fastapi
from fastapi import Depends
import fastapi.encoders
import pydantic
import bson
import datetime

from . import models
from .models import request_repo_layer

from mppw import logger

class ProvenanceServices:

    def __init__(self, repo_layer):

        self.repo_layer = repo_layer
        self.art_repo = repo_layer.get(models.ArtifactRepository)
        self.op_repo = repo_layer.get(models.OperationRepository)

class ServiceLayer:

    def __init__(self, repo_layer):
        self.repo_layer = repo_layer

    def get(self, clazz):
        return clazz(self.repo_layer)

def init_request_service_layer(app: fastapi.FastAPI):

    def request_service_layer(repo_layer: models.RepositoryLayer = Depends(request_repo_layer(app))):
        return ServiceLayer(repo_layer)

    app.state.services_request_service_layer = request_service_layer

def request_service_layer(app: fastapi.FastAPI) -> ServiceLayer:
    return app.state.services_request_service_layer