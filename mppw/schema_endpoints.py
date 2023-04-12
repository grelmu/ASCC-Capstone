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
from . import endpoints

from . import schemas
from . import security
from .security import (
    request_user,
    READ_PROVENANCE_SCOPE,
    MODIFY_PROVENANCE_SCOPE,
)


def create_router(app):

    router = fastapi.APIRouter(prefix="/api/schemas")

    @router.post(
        "/user/",
        response_model=models.StoredSchema,
        status_code=fastapi.status.HTTP_201_CREATED,
        tags=["schema"],
    )
    def create(
        stored_schema: models.StoredSchema,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[MODIFY_PROVENANCE_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        project_endpoints.check_project_claims_for_user(
            user, [str(stored_schema.project)]
        )

        return repo_layer.user_schemas.create(stored_schema)

    @router.get(
        "/user/{id}",
        response_model=models.StoredSchema,
        tags=["schema"],
    )
    def read(
        id: str,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):
        result = repo_layer.user_schemas.query_one(
            id=id, project_ids=project_endpoints.project_claims_for_user(user)
        )

        if result is None:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return result

    @router.get(
        "/user/",
        response_model=List[models.StoredSchema],
        tags=["schema"],
    )
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
    ):
        if project_ids is None:
            project_ids = project_endpoints.project_claims_for_user(user)
        else:
            project_endpoints.check_project_claims_for_user(user, project_ids)

        result = repo_layer.user_schemas.query(
            project_ids=project_ids,
            type_urns=([type_urn] if type_urn is not None else type_urns),
            type_urn_prefix=type_urn_prefix,
            name=name,
            tags=tags,
            active=active,
        )

        return list(result)

    @router.patch(
        "/user/{id}",
        response_model=bool,
        tags=["schema"],
    )
    def patch(
        id: str,
        changes: List[endpoints.Change],
        current_user: models.User = Security(
            request_user(app), scopes=[MODIFY_PROVENANCE_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):
        def update_fn(schema: models.StoredSchema):

            for change in changes:
                if change.op == "replace":
                    setattr(schema, change.path, change.value)
                elif change.op == "remove":
                    setattr(schema, change.path, None)
                if change.path in ["storage_schema_json5", "storage_schema_yaml"]:
                    schema.storage_schema_json = None
                    schema.storage_schema_hash = None
                if change.path in ["storage_schema_json"]:
                    schema.storage_schema_hash = None
                    schema.storage_schema_json5 = None
                    schema.storage_schema_yaml = None

            schema = models.StoredSchema(**schema.dict())
            return schema

        modified = repo_layer.user_schemas.partial_update(
            id,
            update_fn,
            project_ids=project_endpoints.project_claims_for_user(current_user),
        )

        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    @router.delete(
        "/user/{id}",
        response_model=bool,
        tags=["schema"],
    )
    def delete(
        id: str,
        preserve_data: bool = True,
        current_user: models.User = Security(
            request_user(app), scopes=[MODIFY_PROVENANCE_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        modified = (
            repo_layer.user_schemas.deactivate
            if preserve_data
            else repo_layer.user_schemas.delete
        )(id, project_ids=project_endpoints.project_claims_for_user(current_user))

        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    #
    # Module schemas
    #

    @router.get(
        "/module/",
        response_model=List[models.StoredSchema],
        tags=["schema"],
    )
    def query(
        module_names: List[str] = None,
        type_urn: str = None,
        type_urns: List[str] = None,
        type_urn_prefix: str = None,
        name: str = None,
        tags: List[str] = None,
        active: bool = None,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):
        result = repo_layer.module_schemas.query(
            module_names=module_names,
            type_urns=([type_urn] if type_urn is not None else type_urns),
            type_urn_prefix=type_urn_prefix,
            name=name,
            tags=tags,
            active=active,
        )

        return list(result)

    return router
