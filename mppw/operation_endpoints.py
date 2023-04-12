import fastapi
from fastapi import Security, Depends
import typing
from typing import Union, List, Dict, Optional, Any
import pydantic
import datetime
import itertools

from mppw import logger
from . import models
from . import schemas
from . import repositories
from .repositories import request_repo_layer
from . import services
from .services import request_service_layer
from . import security
from .security import (
    request_user,
    READ_PROVENANCE_SCOPE,
    MODIFY_PROVENANCE_SCOPE,
    MODIFY_OPERATION_SCOPE,
)
from . import project_endpoints
from . import endpoints


class NewArtifactTransform(models.ArtifactTransform):
    new_input_artifacts: Optional[List[models.AnyArtifact]]
    new_output_artifacts: Optional[List[models.AnyArtifact]]


def create_router(app):

    router = fastapi.APIRouter(prefix="/api/operations")

    #
    # CRUD
    #

    @router.post(
        "/",
        response_model=models.Operation,
        status_code=fastapi.status.HTTP_201_CREATED,
        tags=["operations"],
    )
    def create(
        operation: models.Operation,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[MODIFY_PROVENANCE_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        project_endpoints.check_project_claims_for_user(user, [str(operation.project)])

        return repo_layer.operations.create(operation)

    @router.get(
        "/{id}",
        response_model=models.Operation,
        tags=["operations"],
    )
    def read(
        id: str,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        result = repo_layer.operations.query_one(
            id=id, project_ids=project_endpoints.project_claims_for_user(user)
        )

        if result is None:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return result

    @router.get(
        "/",
        response_model=List[models.Operation],
        tags=["operations"],
    )
    def query(
        project_ids: List[str] = fastapi.Query(None),
        name: str = fastapi.Query(None),
        tags: List[str] = fastapi.Query(None),
        active: bool = fastapi.Query(True),
        fulltext_query: str = fastapi.Query(None),
        limit: int = fastapi.Query(None),
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        if project_ids is None:
            project_ids = project_endpoints.project_claims_for_user(user)

        project_endpoints.check_project_claims_for_user(user, project_ids)

        result = repo_layer.operations.query(
            project_ids=project_ids,
            name=name,
            tags=tags,
            active=active,
            fulltext_query=fulltext_query,
        )

        # TODO: Pagination
        if limit is not None:
            result = itertools.islice(result, limit)

        return list(result)

    class PaginatedOperations(models.BaseJsonModel):
        results: List[models.Operation]
        total: int

    @router.get(
        "/paged/",
        response_model=PaginatedOperations,
        tags=["operations"],
    )
    def paged_query(
        project_ids: List[str] = fastapi.Query(None),
        name: str = fastapi.Query(None),
        tags: List[str] = fastapi.Query(None),
        active: bool = fastapi.Query(True),
        status: str = fastapi.Query(None),
        type_urn: str = fastapi.Query(None),
        fulltext_query: str = fastapi.Query(None),
        page_size: int = fastapi.Query(None),
        page_num: int = fastapi.Query(None),
        sort_col: str = fastapi.Query(None),
        sort_dir: str = fastapi.Query(None),
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        if project_ids is None:
            project_ids = project_endpoints.project_claims_for_user(user)

        project_endpoints.check_project_claims_for_user(user, project_ids)

        # Calculate the skip value based on page_size and page_num args
        skip = page_size * (page_num - 1) if None not in (page_size, page_num) else None

        # MongoDB's sort function expects either 1 or -1
        #   Convert sort_dir to match
        if sort_dir is not None:
            sort_dir = 1 if sort_dir == "asc" else -1

        results, total = repo_layer.operations.paged_query(
            project_ids=project_ids,
            name=name,
            tags=tags,
            active=active,
            status=status,
            type_urn=type_urn,
            skip=skip,
            limit=page_size,
            sort_col=sort_col,
            sort_dir=sort_dir,
            fulltext_query=fulltext_query,
        )

        return PaginatedOperations(results=list(results), total=total)

    @router.put(
        "/{id}",
        response_model=bool,
        tags=["operations"],
    )
    def update(
        id: str,
        operation: models.Operation,
        current_user: models.User = Security(
            request_user(app), scopes=[MODIFY_OPERATION_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        if id != str(operation.id):
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_400_BAD_REQUEST)

        modified = repo_layer.operations.update(
            operation,
            project_ids=project_endpoints.project_claims_for_user(current_user),
        )

        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    @router.patch(
        "/{id}",
        response_model=bool,
        tags=["operations"],
    )
    def patch(
        id: str,
        changes: List[endpoints.Change],
        current_user: models.User = Security(
            request_user(app), scopes=[MODIFY_OPERATION_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):
        def update_fn(metadata: models.Operation):

            for change in changes:
                if change.op == "replace":
                    setattr(metadata, change.path, change.value)
                elif change.op == "remove":
                    setattr(metadata, change.path, None)

            return metadata

        modified = repo_layer.operations.partial_update(
            id,
            update_fn,
            project_ids=project_endpoints.project_claims_for_user(current_user),
        )

        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    @router.delete(
        "/{id}",
        response_model=bool,
        tags=["operations"],
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
            repo_layer.operations.deactivate
            if preserve_data
            else repo_layer.operations.delete
        )(id, project_ids=project_endpoints.project_claims_for_user(current_user))

        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    #
    # Services
    #

    @router.post(
        "/{id}/services/operation/init",
        response_model=models.Operation,
        tags=["operations"],
    )
    def init(
        id: str,
        args: dict = {},
        user: models.User = Security(
            request_user(app), scopes=[MODIFY_OPERATION_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        operation: models.Operation = read(id, user, service_layer.repo_layer)
        services = service_layer.operation_services_for(operation)
        return services.init(operation, **args)

    #
    # Schema
    #

    @router.get(
        "/{id}/services/operation/schema",
        response_model=services.ResolvedSchema,
        tags=["operations"],
    )
    def get_schema(
        id: str,
        user: models.User = Security(request_user(app), scopes=[READ_PROVENANCE_SCOPE]),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):
        operation: models.Operation = read(id, user, service_layer.repo_layer)

        schema = service_layer.schema_services().query_resolved_project_schema(
            operation.project,
            type_urns=[operation.type_urn],
            active=True,
            current=True,
        )

        if not schema:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return schema

    #
    # Artifact attachments
    #

    @router.post("/{id}/artifacts/", response_model=bool, tags=["operations"])
    def attach_artifact(
        id: str,
        attachment: models.AttachmentGraph.AttachmentNode,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[MODIFY_PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        operation: models.Operation = read(id, user, service_layer.repo_layer)
        services = service_layer.operation_services_for(operation)
        modified = services.attach(operation, attachment)

        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    @router.get(
        "/{id}/artifacts/",
        response_model=List[models.AttachmentGraph.AttachmentNode],
        tags=["operations"],
    )
    def query_artifacts(
        id: str,
        artifact_path: str = None,
        kind_path: str = None,
        artifact_id: str = None,
        attachment_mode: models.AttachmentMode = None,
        parent_artifact_path: str = None,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):
        if artifact_path:
            artifact_path = artifact_path.split(".")
            kind_path, artifact_id = artifact_path[0:-1], artifact_path[-1]
        elif kind_path:
            kind_path = kind_path.split(".")

        if parent_artifact_path:
            parent_artifact_path = parent_artifact_path.split(".")

        if attachment_mode:
            attachment_mode = models.AttachmentMode(attachment_mode)

        operation: models.Operation = read(id, user, service_layer.repo_layer)

        return list(
            operation.attachments.find_nodes(
                kind_path=kind_path,
                artifact_id=artifact_id,
                attachment_mode=attachment_mode,
                parent_artifact_path=parent_artifact_path,
            ),
        )

    @router.post(
        "/{id}/artifacts/claim",
        response_model=bool,
        tags=["operations"],
    )
    def claim_artifact(
        id: str,
        attachment: models.AttachmentGraph.AttachmentNode,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[MODIFY_PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        operation: models.Operation = read(id, user, service_layer.repo_layer)
        services = service_layer.operation_services_for(operation)
        claimed = services.claim(operation, attachment)

        if not claimed:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    @router.delete(
        "/{id}/artifacts/",
        response_model=bool,
        tags=["operations"],
    )
    def detach_artifact(
        id: str,
        attachment: models.AttachmentGraph.AttachmentNode,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[MODIFY_PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        operation: models.Operation = read(id, user, service_layer.repo_layer)
        services = service_layer.operation_services_for(operation)
        modified = services.detach(operation, attachment)

        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    #
    # Artifact candidate helper queries - pulls back artifact nodes *and* artifact data
    #

    @router.get(
        "/{id}/artifacts/all",
        response_model=List[services.OperationServices.AttachedArtifact],
        tags=["operations"],
    )
    def all_artifacts(
        id: str,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):
        operation: models.Operation = read(id, user, service_layer.repo_layer)
        services = service_layer.operation_services_for(operation)

        return list(services.get_attached_artifacts(operation))

    @router.get(
        "/{id}/artifacts/frame_candidates",
        response_model=List[services.OperationServices.AttachedArtifact],
        tags=["operations"],
    )
    def frame_candidates(
        id: str,
        strategy: str,
        artifact_path: str = None,
        kind_path: str = None,
        artifact_id: str = None,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):
        operation: models.Operation = read(id, user, service_layer.repo_layer)
        services = service_layer.operation_services_for(operation)

        if artifact_path:
            artifact_path = artifact_path.split(".")
            kind_path, artifact_id = artifact_path[0:-1], artifact_path[-1]

        attachment = operation.attachments.find_node(
            kind_path=kind_path, artifact_id=artifact_id
        )

        return list(
            services.frame_candidates(
                operation,
                attachment,
                strategy=strategy,
            ),
        )

    @router.get(
        "/{id}/artifacts/attachments/default",
        response_model=models.AnyArtifact,
        tags=["operations"],
    )
    def get_default_attachments(
        id: str,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        op: models.Operation = read(id, user, service_layer.repo_layer)
        service: services.OperationServices = service_layer.operation_services_for(op)
        return service.get_default_attachments_artifact(op)

    #
    # Provenance
    #

    @router.get(
        "/{id}/services/operation/provenance/steps",
        response_model=endpoints.ProvenanceGraphModel,
        tags=["operations"],
    )
    def get_provenance_steps(
        id: str,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        op: models.Operation = read(id, user, service_layer.repo_layer)
        service: services.ProvenanceServices = service_layer.provenance_services()

        return endpoints.ProvenanceGraphModel.from_graph(
            service.build_operation_steps(op)
        )

    return router
