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
from . import security
from .security import request_user, PROVENANCE_SCOPE
from . import projects

class NewArtifactTransform(models.ArtifactTransform):
    new_input_artifacts: Optional[List[models.AnyArtifact]]
    new_output_artifacts: Optional[List[models.AnyArtifact]]

def create_router(app):

    combined_router = fastapi.APIRouter()

    router = fastapi.APIRouter(prefix="/api/operations")

    @router.post("/", response_model=models.Operation, status_code = fastapi.status.HTTP_201_CREATED)
    def create(operation: models.Operation,
               user: security.ScopedUser = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
               repo_layer = Depends(request_repo_layer(app))):
        
        projects.check_project_claims_for_user(user, [str(operation.project)])

        return repo_layer.operations.create(operation)

    @router.get("/{id}", response_model=models.Operation)
    def read(id: str,
             user: security.ScopedUser = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
             repo_layer = Depends(request_repo_layer(app))):
        
        result = repo_layer.operations.query_one(
            id=id,
            project_ids=projects.project_claims_for_user(user)
        )

        if result is None:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)
        
        return result

    @router.get("/", response_model=List[models.Operation])
    def query(project_ids: List[str] = fastapi.Query(None),
              name: str = fastapi.Query(None),
              active: bool = fastapi.Query(True),
              user: security.ScopedUser = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
              repo_layer = Depends(request_repo_layer(app))):

        if project_ids is None:
            project_ids = projects.project_claims_for_user(user)

        projects.check_project_claims_for_user(user, project_ids)
        
        return list(repo_layer.operations.query(
            project_ids=project_ids,
            name=name,
            active=active,
        ))

    @router.post("/{id}/artifacts/", response_model=NewArtifactTransform, status_code = fastapi.status.HTTP_201_CREATED)
    def attach(id: str,
               new_transform: NewArtifactTransform,
               user: security.ScopedUser = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
               repo_layer = Depends(request_repo_layer(app))):
    
        if new_transform.input_artifacts is None: new_transform.input_artifacts = []
        if new_transform.output_artifacts is None: new_transform.output_artifacts = []

        for new_artifacts, artifact_ids in [(new_transform.new_input_artifacts, new_transform.input_artifacts),
                                            (new_transform.new_output_artifacts, new_transform.output_artifacts)]:
            if new_artifacts is None: continue
            for new_artifact in new_artifacts:
                projects.check_project_claims_for_user(user, [str(new_artifact.project)])
                artifact_ids.append(repo_layer.artifacts.create(new_artifact).id)

        transform = models.ArtifactTransform(**(new_transform.dict()))
        modified = repo_layer.operations.attach(id, transform, project_ids=projects.project_claims_for_user(user))
        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return new_transform

    @router.delete("/{id}/artifacts/{kind_urn}", response_model=bool)
    def detach(id: str,
               kind_urn: str,
               partial_transform: models.ArtifactTransform = fastapi.Body(None),
               user: security.ScopedUser = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
               service_layer: services.ServiceLayer = Depends(request_service_layer(app))):
    
        if partial_transform is None:
            
            modified = service_layer.repo_layer.operations.detach(id, kind_urn, project_ids=projects.project_claims_for_user(user))
            if not modified:
                raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

            return True

        else:

            operation = read(id, user, service_layer.repo_layer)

            


        kind_urn = transform.kind_urn

        modified = repo_layer.operations.detach(id, kind_urn, project_ids=projects.project_claims_for_user(user))

        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    @router.get("/{id}/artifacts/attachments/default", response_model=models.DigitalArtifact)
    def get_default_attachments(id: str,
                                user: security.ScopedUser = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
                                service_layer: services.ServiceLayer = Depends(request_service_layer(app))):
                

        op: models.Operation = read(id, user, service_layer.repo_layer)
        service: services.OperationServices  = service_layer.operation_service(op.type_urn)
        attachments: models.Artifact = service.get_default_attachments_artifact(op)

        return attachments

    @router.delete("/{id}", response_model=bool)
    def delete(id: str,
               preserve_data: bool = True,
               current_user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
               repo_layer = Depends(request_repo_layer(app))):
        
        modified = (repo_layer.operations.deactivate if preserve_data else repo_layer.operations.delete)(
            id,
            project_ids=projects.project_claims_for_user(current_user)
        )
        
        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    combined_router.include_router(router)

    router = fastapi.APIRouter(prefix="/api/operation-services")

    @router.post("/", response_model=models.Operation, status_code = fastapi.status.HTTP_201_CREATED)
    def create_serviced(operation: models.Operation,
                        user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
                        service_layer: services.ServiceLayer = Depends(request_service_layer(app))):
            
        projects.check_project_claims_for_user(user, [str(operation.project)])

        return service_layer.create_default_operation(operation)

    @router.get("/types/", response_model=List[services.ServicedOperationType])
    def query_serviced_types(user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
                             service_layer: services.ServiceLayer = Depends(request_service_layer(app))):

        return list(service_layer.serviced_operation_types())

    @router.get("/{rel_type_urn}/attachment-kinds/", response_model=List[services.AttachmentKind])
    def query_attachment_kinds(rel_type_urn: str,
                               user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
                               service_layer: services.ServiceLayer = Depends(request_service_layer(app))):

        rel_type_urn = ":" + rel_type_urn
        return list(service_layer.operation_service(rel_type_urn).attachment_kinds)

    combined_router.include_router(router)

    return combined_router
