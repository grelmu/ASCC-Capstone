import fastapi
from fastapi import Security, Depends
import typing
from typing import Union, List, Dict, Optional, Any
import pydantic
import datetime
import itertools

from mppw import logger
from . import models
from . import repositories
from .repositories import request_repo_layer
from . import services
from .services import request_service_layer
from . import security
from .security import request_user, PROVENANCE_SCOPE
from . import projects


class NewArtifactTransform(models.ArtifactTransform):
    new_input_artifacts: Optional[List[models.AnyArtifact]]
    new_output_artifacts: Optional[List[models.AnyArtifact]]


def create_router(app):

    combined_router = fastapi.APIRouter()

    router = fastapi.APIRouter(prefix="/api/operations")

    #
    # CRUD
    #

    @router.post(
        "/",
        response_model=models.Operation,
        status_code=fastapi.status.HTTP_201_CREATED,
    )
    def create(
        operation: models.Operation,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[PROVENANCE_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        projects.check_project_claims_for_user(user, [str(operation.project)])

        return repo_layer.operations.create(operation)

    # TODO: Paginate this or create matching paginated endpoint
    @router.get("/{id}", response_model=models.Operation)
    def read(
        id: str,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[PROVENANCE_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        result = repo_layer.operations.query_one(
            id=id, project_ids=projects.project_claims_for_user(user)
        )

        if result is None:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return result

    # class PaginatedOperations(pydantic.BaseModel):
    #         results: List[models.Operation]
    #         total: int

    # @router.get("/", response_model=PaginatedOperations)
    @router.get("/")
    def query(
        project_ids: List[str] = fastapi.Query(None),
        name: str = fastapi.Query(None),
        active: bool = fastapi.Query(True),
        status: str = fastapi.Query(None),
        fulltext_query: str = fastapi.Query(None),
        page_size: int = fastapi.Query(None),
        page_num: int = fastapi.Query(None),
        user: security.ScopedUser = Security(
            request_user(app), scopes=[PROVENANCE_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        if project_ids is None:
            project_ids = projects.project_claims_for_user(user)

        projects.check_project_claims_for_user(user, project_ids)

        result = repo_layer.operations.query(
            project_ids=project_ids,
            name=name,
            active=active,
            status=status,
            fulltext_query=fulltext_query,
        )

        result = list(result)
        total = len(result)

        # TODO: Pagination
        # alternative method is to do this during the find() call
        #   using .find(...).skip(...).limit(...)
        if page_size is not None and page_num is not None:
            start = page_size * (page_num - 1)
            stop = page_size * page_num
            result = list(itertools.islice(result, start, stop))

        return {
            'results': result,
            'total': total
            }

    @router.put("/{id}", response_model=bool)
    def update(
        id: str,
        operation: models.Operation,
        current_user: models.User = Security(
            request_user(app), scopes=[PROVENANCE_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        if id != str(operation.id):
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_400_BAD_REQUEST)

        modified = repo_layer.operations.update(
            operation, project_ids=projects.project_claims_for_user(current_user)
        )

        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    @router.delete("/{id}", response_model=bool)
    def delete(
        id: str,
        preserve_data: bool = True,
        current_user: models.User = Security(
            request_user(app), scopes=[PROVENANCE_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        modified = (
            repo_layer.operations.deactivate
            if preserve_data
            else repo_layer.operations.delete
        )(id, project_ids=projects.project_claims_for_user(current_user))

        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    #
    # Services
    #

    @router.post("/{id}/services/operation/init", response_model=models.Operation)
    def init(
        id: str,
        args: dict = {},
        user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        operation: models.Operation = read(id, user, service_layer.repo_layer)
        services = service_layer.operation_services_for(operation)
        return services.init(operation, **args)

    class ArtifactPath(pydantic.BaseModel):
        artifact_path: Optional[List[str]]

    @router.get("/{id}/artifacts", response_model=services.ArtifactNode)
    def attached_artifact(
        id: str,
        artifact_path: str = None,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        artifact_path = (artifact_path.split(".")) if artifact_path else []
        operation: models.Operation = read(id, user, service_layer.repo_layer)
        services = service_layer.operation_services_for(operation)
        return services.find_artifact_at(operation, artifact_path)

    @router.get("/{id}/artifacts/ls", response_model=List[services.AttachedArtifact])
    def artifacts_ls(
        id: str,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        operation: models.Operation = read(id, user, service_layer.repo_layer)
        services = service_layer.operation_services_for(operation)
        return list(services.artifacts_ls(operation))

    @router.get(
        "/{id}/artifacts/frame_candidates",
        response_model=List[services.AttachedArtifact],
    )
    def frame_candidates(
        id: str,
        artifact_path: str,
        strategy: str,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        artifact_path = (artifact_path.split(".")) if artifact_path else []
        operation: models.Operation = read(id, user, service_layer.repo_layer)
        services = service_layer.operation_services_for(operation)
        return list(
            services.frame_candidates(operation, artifact_path, strategy=strategy)
        )

    class ArtifactAttachment(pydantic.BaseModel):
        kind_urn: str
        is_input: bool = False
        artifact_id: str
        artifact_path: Optional[List[str]]

    @router.post("/{id}/artifacts/", response_model=bool)
    def attach(
        id: str,
        attachment: ArtifactAttachment,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        operation: models.Operation = read(id, user, service_layer.repo_layer)
        services = service_layer.operation_services_for(operation)
        modified = services.attach(
            operation,
            attachment.kind_urn,
            attachment.artifact_id,
            attachment.is_input,
            attachment.artifact_path,
        )

        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    @router.delete("/{id}/artifacts/", response_model=bool)
    def detach(
        id: str,
        attachment: ArtifactAttachment,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        operation: models.Operation = read(id, user, service_layer.repo_layer)
        services = service_layer.operation_services_for(operation)
        modified = services.detach(
            operation,
            attachment.kind_urn,
            attachment.artifact_id,
            attachment.is_input,
            attachment.artifact_path,
        )

        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    @router.get(
        "/{id}/artifacts/attachments/default", response_model=models.DigitalArtifact
    )
    def get_default_attachments(
        id: str,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        op: models.Operation = read(id, user, service_layer.repo_layer)
        service: services.OperationServices = service_layer.operation_service(
            op.type_urn
        )
        attachments: models.Artifact = service.get_default_attachments_artifact(op)

        return attachments

    combined_router.include_router(router)

    router = fastapi.APIRouter(prefix="/api/operation-services")

    @router.get("/types/", response_model=List[services.ServicedOperationType])
    def query_serviced_types(
        user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        return list(service_layer.serviced_operation_types())

    @router.get(
        "/{rel_type_urn}/attachment-kinds", response_model=List[services.AttachmentKind]
    )
    def query_attachment_kinds(
        rel_type_urn: str,
        user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        rel_type_urn = ":" + rel_type_urn
        return list(service_layer.operation_service(rel_type_urn).attachment_kinds)

    combined_router.include_router(router)

    return combined_router
