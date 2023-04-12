from tokenize import String
import fastapi
from fastapi import Security, Depends
import typing
from typing import Union, List, Optional
import pydantic
import datetime

from mppw import logger
from . import endpoints
from . import models
from . import repositories
from .repositories import request_repo_layer
from . import services
from .services import request_service_layer
from . import security
from .security import request_user, ADMIN_SCOPE, READ_PROVENANCE_SCOPE


def create_router(app):

    router = fastapi.APIRouter(prefix="/api/projects")

    @router.post(
        "/",
        response_model=models.Project,
        status_code=fastapi.status.HTTP_201_CREATED,
        tags=["projects"],
    )
    def create(
        project: models.Project,
        user: security.ScopedUser = Security(request_user(app), scopes=[ADMIN_SCOPE]),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        result = repo_layer.projects.create(project)
        security.reload_project_claims(app)
        return result

    @router.get(
        "/{id}",
        response_model=models.Project,
        tags=["projects"],
    )
    def read(
        id: str,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        check_project_claims_for_user(user, [str(id)])

        result = repo_layer.projects.query_one(ids=[id])
        if result is None:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return result

    @router.get(
        "/",
        response_model=List[models.Project],
        tags=["projects"],
    )
    def query(
        name: str = fastapi.Query(None),
        active: bool = fastapi.Query(True),
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        ids = project_claims_for_user(user)
        return list(repo_layer.projects.query(ids=ids, name=name, active=active))

    @router.patch(
        "/{id}",
        response_model=bool,
        tags=["projects"],
    )
    def patch(
        id: str,
        changes: List[endpoints.Change],
        current_user: models.User = Security(request_user(app), scopes=[ADMIN_SCOPE]),
        repo_layer=Depends(request_repo_layer(app)),
    ):
        def update_fn(metadata: models.Project):

            for change in changes:
                if change.op == "replace":
                    setattr(metadata, change.path, change.value)
                elif change.op == "remove":
                    setattr(metadata, change.path, None)

            return metadata

        modified = repo_layer.projects.partial_update(id, update_fn)

        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    @router.delete(
        "/{id}",
        response_model=bool,
        tags=["projects"],
    )
    def delete(
        id: str,
        preserve_data: bool = True,
        user: security.ScopedUser = Security(request_user(app), scopes=[ADMIN_SCOPE]),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        modified = (
            repo_layer.projects.deactivate
            if preserve_data
            else repo_layer.projects.delete
        )(id)
        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        security.reload_project_claims(app)
        return True

    @router.get(
        "/{id}/services/project/schema/",
        response_model=List[services.ResolvedSchema],
        tags=["projects"],
    )
    def query_project_schemas(
        id: str,
        type_urn: str = None,
        type_urns: List[str] = None,
        type_urn_prefix: str = None,
        active: bool = True,
        current: bool = True,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        service_layer=Depends(request_service_layer(app)),
    ):
        if id is not None:
            check_project_claims_for_user(user, [id])

        result = service_layer.schema_services().query_resolved_project_schemas(
            id,
            type_urns=([type_urn] if type_urn is not None else type_urns),
            type_urn_prefix=type_urn_prefix,
            active=active,
            current=True,
        )

        return list(result)

    @router.get(
        "/{id}/services/project/schema/operations/",
        response_model=List[services.ResolvedSchema],
        tags=["projects"],
    )
    def query_project_operations_schemas(
        id: str,
        active: bool = True,
        current: bool = True,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        service_layer=Depends(request_service_layer(app)),
    ):
        return query_project_schemas(
            id,
            type_urn_prefix="urn:x-mfg:operation:",
            active=active,
            current=current,
            user=user,
            service_layer=service_layer,
        )

    @router.get(
        "/{id}/services/project/schema/artifacts/",
        response_model=List[services.ResolvedSchema],
        tags=["projects"],
    )
    def query_project_artifacts_schemas(
        id: str,
        active: bool = True,
        current: bool = True,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        service_layer=Depends(request_service_layer(app)),
    ):
        return query_project_schemas(
            id,
            type_urn_prefix="urn:x-mfg:artifact:",
            active=active,
            current=current,
            user=user,
            service_layer=service_layer,
        )

    return router


def project_claims_for_user(user: security.ScopedUser):
    if security.has_admin_scope(user):
        return None
    return list(map(str, user.claims.get("projects", [])))


def check_project_claims_for_user(user: security.ScopedUser, project_ids: List[str]):
    if security.has_admin_scope(user):
        return
    project_claims = project_claims_for_user(user)
    for project_id in project_ids or []:
        if project_id not in project_claims:
            raise fastapi.HTTPException(fastapi.status.HTTP_401_UNAUTHORIZED)
