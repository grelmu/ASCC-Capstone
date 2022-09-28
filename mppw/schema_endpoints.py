from tokenize import String
import fastapi
from fastapi import Security, Depends
import typing
from typing import Union, List, Optional
import pydantic
import datetime

from mppw import logger
from . import models
from . import schemas
from . import security
from .security import request_user, ADMIN_SCOPE, PROVENANCE_SCOPE


def create_router(app):

    router = fastapi.APIRouter(prefix="/api/schema")

    @router.get("/operations/", response_model=List[schemas.OperationSchema])
    def query_operation_schemas(
        user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
    ):
        return list(schemas.get_operation_schemas())

    @router.get("/operations/by_type", response_model=schemas.OperationSchema)
    def query_operation_schema(
        type_urn: str,
        user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
    ):
        return schemas.get_operation_schema(type_urn)

    @router.get("/artifacts/", response_model=List[schemas.ArtifactSchema])
    def query_artifact_schema(
        user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
    ):
        return list(schemas.get_artifact_schemas())

    @router.get("/artifacts/by_type", response_model=schemas.ArtifactSchema)
    def query_artifact_schema(
        type_urn: str,
        user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
    ):
        return schemas.get_artifact_schema(type_urn)

    return router
