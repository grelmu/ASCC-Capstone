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
from .security import request_user, PROVENANCE_SCOPE
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
    )
    def create(
        operation: models.Operation,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[PROVENANCE_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        project_endpoints.check_project_claims_for_user(user, [str(operation.project)])

        return repo_layer.operations.create(operation)

    @router.get("/{id}", response_model=models.Operation)
    def read(
        id: str,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[PROVENANCE_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        result = repo_layer.operations.query_one(
            id=id, project_ids=project_endpoints.project_claims_for_user(user)
        )

        if result is None:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return result

    @router.get("/", response_model=List[models.Operation])
    def query(
        project_ids: List[str] = fastapi.Query(None),
        name: str = fastapi.Query(None),
        active: bool = fastapi.Query(True),
        fulltext_query: str = fastapi.Query(None),
        limit: int = fastapi.Query(None),
        user: security.ScopedUser = Security(
            request_user(app), scopes=[PROVENANCE_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        if project_ids is None:
            project_ids = project_endpoints.project_claims_for_user(user)

        project_endpoints.check_project_claims_for_user(user, project_ids)

        result = repo_layer.operations.query(
            project_ids=project_ids,
            name=name,
            active=active,
            fulltext_query=fulltext_query,
        )

        # TODO: Pagination
        if limit is not None:
            result = itertools.islice(result, limit)

        return list(result)

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
            operation,
            project_ids=project_endpoints.project_claims_for_user(current_user),
        )

        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True
        
    @router.patch("/{id}", response_model=bool)
    def patch(
        id: str,
        changes: List[endpoints.Change],
        current_user: models.User = Security(
            request_user(app), scopes=[PROVENANCE_SCOPE]
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
            id, update_fn, project_ids=project_endpoints.project_claims_for_user(current_user)
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
        )(id, project_ids=project_endpoints.project_claims_for_user(current_user))

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

    @router.post("/{id}/artifacts/", response_model=bool)
    def attach_artifact(
        id: str,
        attachment: models.AttachmentGraph.AttachmentNode,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[PROVENANCE_SCOPE]
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
    )
    def query_artifacts(
        id: str,
        artifact_path: str = None,
        kind_path: str = None,
        artifact_id: str = None,
        attachment_mode: models.AttachmentMode = None,
        parent_artifact_path: str = None,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[PROVENANCE_SCOPE]
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

    @router.delete("/{id}/artifacts/", response_model=bool)
    def detach_artifact(
        id: str,
        attachment: models.AttachmentGraph.AttachmentNode,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        operation: models.Operation = read(id, user, service_layer.repo_layer)
        services = service_layer.operation_services_for(operation)
        modified = services.detach(operation, attachment)

        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    @router.get(
        "/{id}/artifacts/frame_candidates",
        response_model=List[services.OperationServices.AttachedArtifact],
    )
    def frame_candidates(
        id: str,
        strategy: str,
        attachment: models.AttachmentGraph.AttachmentNode,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):
        operation: models.Operation = read(id, user, service_layer.repo_layer)
        services = service_layer.operation_services_for(operation)
        return list(
            services.frame_candidates(
                operation,
                attachment,
                strategy=strategy,
            ),
        )

    @router.get(
        "/{id}/artifacts/attachments/default", response_model=models.AnyArtifact
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
        return service.get_default_attachments_artifact(op)

    #
    # Provenance
    #

    @router.get(
        "/{id}/services/operation/provenance/steps",
        response_model=endpoints.ProvenanceGraphModel,
    )
    def get_provenance_steps(
        id: str,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        op: models.Operation = read(id, user, service_layer.repo_layer)
        service: services.ProvenanceServices = service_layer.provenance_services()

        return endpoints.ProvenanceGraphModel.from_graph(
            service.build_operation_steps(op)
        )

    return router
