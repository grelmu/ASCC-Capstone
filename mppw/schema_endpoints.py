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
from . import project_endpoints

from . import schemas
from . import security
from .security import (
    request_user,
    ADMIN_SCOPE,
    READ_PROVENANCE_SCOPE,
    MODIFY_PROVENANCE_SCOPE,
)


def create_router(app):

    router = fastapi.APIRouter(prefix="/api/schema")

    for repo_name, repo_fn in [
        ("user", lambda r: r.user_schemas),
        ("module", lambda r: r.module_schemas),
    ]:

        @router.get("/" + repo_name + "/{id}", response_model=models.StoredSchema)
        def read(
            id: str,
            user: security.ScopedUser = Security(
                request_user(app), scopes=[READ_PROVENANCE_SCOPE]
            ),
            repo_layer=Depends(request_repo_layer(app)),
            repo_fn=repo_fn,
        ):
            result = repo_fn(repo_layer).query_one(
                id=id, project_ids=project_endpoints.project_claims_for_user(user)
            )

            if result is None:
                raise fastapi.HTTPException(
                    status_code=fastapi.status.HTTP_404_NOT_FOUND
                )

            return result

        @router.get("/" + repo_name + "/", response_model=List[models.StoredSchema])
        def query(
            project_ids: List[str] = fastapi.Query(None),
            type_urn: str = None,
            type_urns: List[str] = None,
            type_urn_prefix: str = None,
            name: str = fastapi.Query(None),
            tags: List[str] = fastapi.Query(None),
            active: bool = fastapi.Query(True),
            user: security.ScopedUser = Security(
                request_user(app), scopes=[READ_PROVENANCE_SCOPE]
            ),
            repo_layer=Depends(request_repo_layer(app)),
            repo_fn=repo_fn,
        ):
            if project_ids is None:
                project_ids = project_endpoints.project_claims_for_user(user)
            else:
                project_endpoints.check_project_claims_for_user(user, project_ids)

            result = repo_fn(repo_layer).query(
                project_ids=project_ids,
                type_urns=([type_urn] if type_urn is not None else type_urns),
                type_urn_prefix=type_urn_prefix,
                name=name,
                tags=tags,
                active=active,
            )

            return list(result)

    return router
