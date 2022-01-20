from typing import Optional, List, ClassVar, Any
import fastapi
from fastapi import Depends
import fastapi.encoders
import pydantic
import bson
import datetime
import bson

from mppw import logger

from . import models
from . import repositories

DATABASE_BUCKET_URN_PREFIX = f"{models.DigitalArtifact.URN_PREFIX}:database-bucket"
FILE_BUCKET_URN_PREFIX = f"{models.DigitalArtifact.URN_PREFIX}:file-bucket"

class OperationServices:

    STATUS_DRAFT = "draft"

    ARTIFACT_KIND_ATTACHMENTS = ":attachments"
    ARTIFACT_KIND_PROCESS_DATA = ":process-data"

    def __init__(self, repo_layer):
        self.repo_layer = repo_layer

    def set_default_fields(self, operation: models.Operation, clazz):

        if not operation.name:
            operation.name = clazz.DEFAULT_NAME

        if not operation.description:
            operation.description = clazz.DEFAULT_DESCRIPTION

        if operation.start_at is None:
            start_at = datetime.datetime.now()

        if not operation.status:
            operation.status = OperationServices.STATUS_DRAFT

    def create_default_attachments(self, project, scheme=None):

        attachments = models.DigitalArtifact(
            type_urn = FILE_BUCKET_URN_PREFIX,
            project = project,
            name = "Attachments",
            description = "Default attachments",   
        )

        self.repo_layer.artifacts.create(attachments)
        self.initialize_file_bucket_artifact(attachments, scheme)
        self.repo_layer.artifacts.update(attachments)

        return models.ArtifactTransform(
            kind_urn = OperationServices.ARTIFACT_KIND_ATTACHMENTS,
            output_artifacts = [attachments.id]
        )

    def create_default_process_data(self, project, scheme=None):

        process_data = models.DigitalArtifact(
            type_urn = DATABASE_BUCKET_URN_PREFIX,
            project = project,
            name = "Process Data",
            description = "Default process data",   
        )

        self.repo_layer.artifacts.create(process_data)
        self.initialize_db_bucket_artifact(process_data, scheme)
        self.repo_layer.artifacts.update(process_data)

        return models.ArtifactTransform(
            kind_urn = OperationServices.ARTIFACT_KIND_PROCESS_DATA,
            output_artifacts = [process_data.id]
        )

    def initialize_artifact(self, id: str, scheme=None):
        artifact = self.repo_layer.artifacts.read(id)
        if artifact.type_urn.startswith(DATABASE_BUCKET_URN_PREFIX):
            return self.initialize_db_bucket_artifact(artifact)
        elif artifact.type_urn.startswith(FILE_BUCKET_URN_PREFIX):
            return self.initialize_file_bucket_artifact(artifact)
        else:
            return False

    def initialize_db_bucket_artifact(self, artifact: models.DigitalArtifact, scheme=None):

        bucket_id = f"artdb-{str(artifact.id)}"
        scheme = scheme or self.repo_layer.buckets.default_db_bucket_scheme
        artifact.url_data = self.repo_layer.buckets.create_db_bucket(bucket_id, scheme)
        return True

    def initialize_file_bucket_artifact(self, artifact: models.DigitalArtifact, scheme=None):

        bucket_id = f"artfiles-{str(artifact.id)}"
        scheme = scheme or self.repo_layer.buckets.default_file_bucket_scheme
        artifact.url_data = self.repo_layer.buckets.create_file_bucket(bucket_id, scheme)
        return True

class FffServices(OperationServices):

    URN_PREFIX = f"{models.Operation.URN_PREFIX}:fff"
    DEFAULT_NAME = "FFF Manufacture"
    DEFAULT_DESCRIPTION = "FFF or FDM manufacturing operation"

    ARTIFACT_KIND_OPERATOR_NOTES = ":operator-notes"
    ARTIFACT_KIND_OUTPUT_PARTS = ":output-parts"

    def __init__(self, repo_layer):
        self.repo_layer = repo_layer
    
    def create_default(self, operation: models.Operation):

        self.set_default_fields(operation, type(self))
        
        if not operation.artifact_transform_graph:
            operation.artifact_transform_graph = [
                models.ArtifactTransform(
                    kind_urn=FffServices.ARTIFACT_KIND_OPERATOR_NOTES,
                ),
                models.ArtifactTransform(
                    kind_urn=FffServices.ARTIFACT_KIND_OUTPUT_PARTS,
                ),
                self.create_default_process_data(operation.project),
                self.create_default_attachments(operation.project),
            ]

        return self.repo_layer.operations.create(operation)

class ServicedOperationType(pydantic.BaseModel):
    urn_prefix: str
    name: str
    description: Optional[str]

class UnservicedOperationTypeException(Exception):
    pass

class ServiceLayer:

    def __init__(self, repo_layer):

        self.repo_layer = repo_layer
        
        self.operation_services = [
            FffServices(self.repo_layer)
        ]

    @property
    def operation_service_types(self):
        return [type(service) for service in self.operation_services]

    def serviced_operation_types(self):
        return [ServicedOperationType(urn_prefix=service_type.URN_PREFIX,
                                     name=service_type.DEFAULT_NAME,
                                     description=service_type.DEFAULT_DESCRIPTION) for service_type in self.operation_service_types]

    def create_default(self, operation: models.Operation):
        for service in self.operation_services:
            if operation.type_urn.startswith(type(service).URN_PREFIX):
                return service.create_default(operation)

        raise UnservicedOperationTypeException(f"Operation of type {operation.type_urn} is not a serviced type.")

def init_request_service_layer(app: fastapi.FastAPI):

    def request_service_layer(repo_layer = Depends(repositories.request_repo_layer(app))):
        return ServiceLayer(repo_layer)

    app.state.services_request_service_layer = request_service_layer

def request_service_layer(app: fastapi.FastAPI) -> ServiceLayer:
    return app.state.services_request_service_layer